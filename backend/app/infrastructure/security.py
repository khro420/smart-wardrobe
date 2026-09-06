"""Authentication boundary: password hashing and signed bearer access tokens."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

from fastapi import Header, HTTPException
from app.infrastructure.persistence.postgresql_repository import ensure_user


TOKEN_TTL_HOURS = int(os.getenv("SMART_WARDROBE_TOKEN_TTL_HOURS", "12"))
TOKEN_SECRET = os.getenv("SMART_WARDROBE_TOKEN_SECRET", "change-this-development-token-secret")
ALLOW_DEVELOPMENT_IDENTITY = os.getenv("SMART_WARDROBE_ALLOW_DEV_IDENTITY", "false").lower() == "true"

if os.getenv("SMART_WARDROBE_ENVIRONMENT", "development").lower() == "production" and TOKEN_SECRET == "change-this-development-token-secret":
    raise RuntimeError("Set SMART_WARDROBE_TOKEN_SECRET before starting production.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_text, digest_text = encoded.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: str) -> str:
    expires_at = int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).timestamp())
    payload = f"{user_id}.{expires_at}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def token_user_id(token: str) -> str | None:
    try:
        user_id, expires_at_text, signature = token.rsplit(".", 2)
        payload = f"{user_id}.{expires_at_text}"
        expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires_at_text) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return user_id
    except (ValueError, TypeError):
        return None


async def current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        user_id = token_user_id(authorization[7:].strip())
        if user_id:
            return user_id
    if ALLOW_DEVELOPMENT_IDENTITY and x_user_id:
        ensure_user(x_user_id)
        return x_user_id
    raise HTTPException(401, "Authenticate with a valid bearer token.")
