"""
AI Personal Cloud Drive - Authentication service
"""

import time
import bcrypt
import jwt
from collections import defaultdict
from config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_WINDOW,
)
from models.database import get_db

# In-memory rate limiting: { ip: [(timestamp, success), ...] }
_login_attempts: dict[str, list[tuple[float, bool]]] = defaultdict(list)


def _cleanup_old_attempts(ip: str):
    """Remove attempts older than the lockout window."""
    now = time.time()
    cutoff = now - LOGIN_LOCKOUT_WINDOW
    _login_attempts[ip] = [
        a for a in _login_attempts[ip] if a[0] > cutoff
    ]


def check_rate_limit(ip: str) -> bool:
    """Return False if this IP has exceeded max login attempts."""
    _cleanup_old_attempts(ip)
    recent_failures = sum(
        1 for (_, success) in _login_attempts[ip] if not success
    )
    return recent_failures < LOGIN_MAX_ATTEMPTS


def record_login_attempt(ip: str, success: bool):
    """Record a login attempt for rate limiting."""
    _login_attempts[ip].append((time.time(), success))
    _cleanup_old_attempts(ip)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def authenticate(username: str, password: str, ip: str) -> dict | None:
    """
    Authenticate a user. Returns tokens dict or None on failure.
    Records login attempt for rate limiting.
    """
    if not check_rate_limit(ip):
        return None  # rate limited

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        )
        user = cursor.fetchone()
    finally:
        conn.close()

    if user and verify_password(password, user["password_hash"]):
        record_login_attempt(ip, True)
        access_token = _create_access_token(user["id"], user["username"])
        refresh_token = _create_refresh_token(user["id"], user["username"])
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    record_login_attempt(ip, False)
    return None


def _create_access_token(user_id: int, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_refresh_token(user_id: int, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def refresh_access_token(refresh_token: str) -> str | None:
    """Validate a refresh token and return a new access token."""
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return _create_access_token(
            int(payload["sub"]), payload["username"]
        )
    except jwt.PyJWTError:
        return None


def verify_token(token: str) -> dict | None:
    """Verify an access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
