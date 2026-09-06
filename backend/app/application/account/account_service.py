import json
import uuid
from fastapi import HTTPException
from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from app.infrastructure.security import hash_password, issue_access_token, verify_password


def get_profile(user_id: str) -> dict:
    with connection() as conn:
        user = conn.execute("SELECT id, email, display_name, account_status, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(404, "Account was not found.")
    return dict(user)


def update_profile(user_id: str, display_name: str) -> dict:
    with connection() as conn:
        changed = conn.execute("UPDATE users SET display_name=?, updated_at=? WHERE id=? AND account_status='active'", (display_name, utcnow(), user_id)).rowcount
    if not changed:
        raise HTTPException(404, "Active account was not found.")
    return get_profile(user_id)


def list_preferences(user_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=? AND is_active=1 ORDER BY preference_type",
            (user_id,),
        ).fetchall()
    return [{
        "id": row["id"],
        "preference_type": row["preference_type"],
        "preference_value": json.loads(row["preference_value_json"]),
        "weight": row["weight"],
        "source": row["source"],
        "is_active": bool(row["is_active"]),
    } for row in rows]


def upsert_preference(user_id: str, preference_type: str, preference_value: dict[str, object], weight: float | None) -> dict:
    # The profile lookup enforces the same active-account boundary as profile edits.
    get_profile(user_id)
    now = utcnow()
    with connection() as conn:
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE user_id=? AND preference_type=? AND is_active=1",
            (user_id, preference_type),
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
                "INSERT INTO user_preferences (id, user_id, preference_type, preference_value_json, weight, source, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'user_profile', 1, ?, ?)",
                (preference_id, user_id, preference_type, json.dumps(preference_value), weight, now, now),
            )
    return next(preference for preference in list_preferences(user_id) if preference["id"] == preference_id)


def register(email: str, password: str, display_name: str) -> dict:
    user_id, now = str(uuid.uuid4()), utcnow()
    with connection() as conn:
        exists = conn.execute("SELECT id FROM users WHERE email=?", (email.lower(),)).fetchone()
        if exists:
            raise HTTPException(409, "An account with this email already exists.")
        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, 'active', ?, ?)", (user_id, email.lower(), hash_password(password), display_name, now, now))
    return {"access_token": issue_access_token(user_id), "profile": get_profile(user_id)}


def login(email: str, password: str) -> dict:
    with connection() as conn:
        user = conn.execute("SELECT id, password_hash, account_status FROM users WHERE email=?", (email.lower(),)).fetchone()
    if not user or user["account_status"] != "active" or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    return {"access_token": issue_access_token(user["id"]), "profile": get_profile(user["id"])}
