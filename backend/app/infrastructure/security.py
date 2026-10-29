"""Authentication boundary: password hashing and signed bearer access tokens."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
import re
from dataclasses import dataclass

from fastapi import Header, HTTPException
from starlette.concurrency import run_in_threadpool
from app.infrastructure.persistence.postgresql_repository import ensure_user
from app.infrastructure.persistence import session_revocation_store as revocations


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
    owner = base64.urlsafe_b64encode(user_id.encode('utf-8')).decode('ascii').rstrip('=')
    payload = f"v2.{owner}.{expires_at}.{secrets.token_hex(16)}"
    signature = hmac.new(TOKEN_SECRET.encode(), b'wardrobe-access-v2\0' + payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


@dataclass(frozen=True)
class VerifiedBearer:
    user_id: str
    expires_at: int
    digest: str


def verified_bearer(token: str) -> VerifiedBearer | None:
    try:
        if not isinstance(token, str) or len(token) > 2048:
            return None
        payload, signature = token.rsplit('.', 1)
        if not re.fullmatch('[0-9a-f]{64}', signature):
            return None
        expected_v2 = hmac.new(TOKEN_SECRET.encode(), b'wardrobe-access-v2\0' + payload.encode(), hashlib.sha256).hexdigest()
        expected_legacy = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_v2):
            version, owner, expires_at_text, nonce = payload.split('.')
            if version != 'v2' or not re.fullmatch('[0-9a-f]{32}', nonce) or not re.fullmatch('[A-Za-z0-9_-]+', owner):
                return None
            user_id = base64.b64decode(owner + '=' * (-len(owner) % 4), altchars=b'-_', validate=True).decode('utf-8')
            if base64.urlsafe_b64encode(user_id.encode()).decode().rstrip('=') != owner:
                return None
        elif hmac.compare_digest(signature, expected_legacy):
            user_id, expires_at_text = payload.rsplit('.', 1)
        else:
            return None
        if not user_id or len(user_id) > 256 or any(ord(c) < 32 for c in user_id) or not re.fullmatch('[0-9]{1,19}', expires_at_text):
            return None
        expires_at = int(expires_at_text)
        if expires_at > 2**63 - 1 or expires_at < int(datetime.now(timezone.utc).timestamp()):
            return None
        return VerifiedBearer(user_id, expires_at, hashlib.sha256(token.encode('utf-8')).hexdigest())
    except (ValueError, TypeError, UnicodeError):
        return None


def token_user_id(token: str) -> str | None:
    """Signature/expiry helper only; protected routes must use current_user_id."""
    claims = verified_bearer(token)
    return claims.user_id if claims else None


async def logout_bearer(authorization: str | None = Header(default=None)) -> VerifiedBearer:
    """Logout-only retry boundary; never inject this into a protected data route."""
    claims = verified_bearer(authorization[7:].strip()) if authorization and authorization.lower().startswith('bearer ') else None
    if claims is None:
        raise HTTPException(401, 'Authenticate with a valid bearer token.')
    return claims


async def current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    if authorization is not None:
        claims = await logout_bearer(authorization)
        try:
            revoked = await run_in_threadpool(revocations.is_revoked, claims.digest, claims.user_id, claims.expires_at)
        except revocations.RevocationUnavailable:
            raise HTTPException(503, 'Authentication service is unavailable. Please try again.') from None
        if revoked:
            raise HTTPException(401, 'Authenticate with a valid bearer token.')
        return claims.user_id
    if ALLOW_DEVELOPMENT_IDENTITY and x_user_id:
        await run_in_threadpool(ensure_user, x_user_id)
        return x_user_id
    raise HTTPException(401, "Authenticate with a valid bearer token.")
