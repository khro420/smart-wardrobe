import json
import uuid
import re
import unicodedata
from fastapi import HTTPException
from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from app.infrastructure.security import hash_password, issue_access_token, verify_password
from app.application.recommendation.preference_normalizer import PreferenceNormalizer, InvalidPreferenceData, precise_weight
from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.infrastructure.persistence.session_revocation_store import revoke, RevocationUnavailable
from app.infrastructure.security import VerifiedBearer
from app.application.wardrobe import profile_service


def logout(claims: VerifiedBearer) -> None:
    try:
        revoke(claims.digest, claims.user_id, claims.expires_at)
    except RevocationUnavailable:
        raise HTTPException(503, "Authentication service is unavailable. Please try again.") from None


def validated_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 100 or any(unicodedata.category(char).startswith("C") for char in value):
        raise HTTPException(422, "Enter a full name of 1 to 100 characters without control characters.")
    return value


def validated_email(value: str) -> str:
    value = value.strip().lower()
    # Prototype mailbox syntax: ASCII dot-atom local part and DNS-style domain.
    parts = value.split("@")
    if len(parts) != 2:
        raise HTTPException(422, "Enter a valid email address.")
    local, domain = parts
    if (len(value) > 254 or not 1 <= len(local) <= 64
            or not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+", local)
            or local.startswith(".") or local.endswith(".") or ".." in local
            or "." not in domain or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in domain.split("."))):
        raise HTTPException(422, "Enter a valid email address.")
    return value


def preference_options() -> dict:
    vocabulary = PreferenceNormalizer().vocabulary
    return {
        "colours": sorted(vocabulary.values["colours"]),
        "styles": sorted(vocabulary.values["style"]),
        "garment_categories": [{"kind": kind, "value": value} for kind, value in sorted(vocabulary.values["garment_categories"])],
        "formality": sorted(SuitabilityPolicy.load().enabled_formality),
    }


def validated_preference(user_id, kind, value, weight):
    if kind not in {"colours", "styles", "garment_categories", "formality", "style_note"}:
        raise HTTPException(422, "Choose a supported preference type.")
    try:
        if weight is not None:
            precise_weight(weight)
        # Empty structured selection explicitly clears that preference; it is never active evidence.
        if kind != "style_note" and value == {"values": []}:
            return None
        row = PreferenceSnapshot("validation", user_id, kind, json.dumps(value, allow_nan=False), "1")
        normalized = PreferenceNormalizer().normalize(user_id, (row,))
        if normalized.diagnostics or len(normalized.preferences) != 1:
            raise ValueError("Unsupported preference value.")
        values = normalized.preferences[0].values
        if kind == "style_note":
            return {"value": values[0]}
        return {"values": [{"kind": item.kind, "value": item.value} for item in values] if kind == "garment_categories" else list(values)}
    except (ValueError, TypeError, InvalidPreferenceData) as exc:
        raise HTTPException(422, "Choose supported preference values and a finite weight from 0 to 1.") from exc


def get_profile(user_id: str) -> dict:
    with connection() as conn:
        user = conn.execute("SELECT id, email, display_name, account_status, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(404, "Account was not found.")
    return dict(user)


def update_profile(user_id: str, display_name: str) -> dict:
    display_name = validated_name(display_name)
    with connection() as conn:
        changed = conn.execute("UPDATE users SET display_name=?, updated_at=? WHERE id=? AND account_status='active'", (display_name, utcnow(), user_id)).rowcount
    if not changed:
        raise HTTPException(404, "Active account was not found.")
    return get_profile(user_id)


def list_preferences(user_id: str, profile_id: str | None = None) -> list[dict]:
    profile_id = profile_service.selected_profile(user_id, profile_id)["id"]
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=? AND profile_id=? AND is_active=1 ORDER BY preference_type",
            (user_id, profile_id),
        ).fetchall()
    return [{
        "id": row["id"],
        "preference_type": row["preference_type"],
        "preference_value": json.loads(row["preference_value_json"]),
        "weight": row["weight"],
        "source": row["source"],
        "is_active": bool(row["is_active"]),
    } for row in rows]


def upsert_preference(user_id: str, preference_type: str, preference_value: dict[str, object], weight: float | None, profile_id: str | None = None) -> dict:
    # Resolve the authenticated owner's account before accepting preference writes.
    get_profile(user_id)
    profile_id = profile_service.selected_profile(user_id, profile_id)["id"]
    preference_value = validated_preference(user_id, preference_type, preference_value, weight)
    now = utcnow()
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if preference_value is None:
            conn.execute("UPDATE user_preferences SET is_active=0, updated_at=? WHERE user_id=? AND profile_id=? AND preference_type=? AND is_active=1", (now, user_id, profile_id, preference_type))
            return {"preference_type": preference_type, "preference_value": {"values": []}, "weight": weight, "is_active": False}
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE user_id=? AND profile_id=? AND preference_type=? AND is_active=1",
            (user_id, profile_id, preference_type),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_preferences SET preference_value_json=?, weight=?, source='user_profile', updated_at=? WHERE id=?",
                (json.dumps(preference_value), weight, now, existing["id"]),
            )
            preference_id = existing["id"]
        else:
            preference_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO user_preferences (id, user_id, profile_id, preference_type, preference_value_json, weight, source, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'user_profile', 1, ?, ?)",
                (preference_id, user_id, profile_id, preference_type, json.dumps(preference_value), weight, now, now),
            )
        # Project our committed operation under its write lock. A competing clear
        # after commit must not turn this successful write into StopIteration/500.
        saved = dict(conn.execute("SELECT * FROM user_preferences WHERE id=?", (preference_id,)).fetchone())
    return {"id": saved["id"], "preference_type": saved["preference_type"],
            "preference_value": json.loads(saved["preference_value_json"]),
            "weight": saved["weight"], "source": saved["source"], "is_active": bool(saved["is_active"])}


def register(email: str, password: str, display_name: str, password_confirmation: str) -> dict:
    email = validated_email(email)
    display_name = validated_name(display_name)
    if not 12 <= len(password) <= 256 or password != password_confirmation:
        raise HTTPException(422, "Passwords must match and contain 12 to 256 characters.")
    user_id, now = str(uuid.uuid4()), utcnow()
    password_hash = hash_password(password)
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT id FROM users WHERE email=?", (email.lower(),)).fetchone()
        if exists:
            raise HTTPException(409, "An account with this email already exists.")
        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, 'active', ?, ?)", (user_id, email, password_hash, display_name, now, now))
        profile_service.ensure_default_profile(conn, user_id)
    return {"status": "Registered", "message": "Account created. Sign in to continue.", "profile": get_profile(user_id)}


def login(email: str, password: str) -> dict:
    with connection() as conn:
        user = conn.execute("SELECT id, password_hash, account_status FROM users WHERE email=?", (email.lower(),)).fetchone()
    if not user or user["account_status"] != "active" or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    return {"access_token": issue_access_token(user["id"]), "profile": get_profile(user["id"])}
