import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

# Initialize Argon2 password hasher
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2 hash."""
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def create_access_token(
    subject: str | uuid.UUID, expires_delta: timedelta | None = None
) -> str:
    """Create a short-lived JWT access token."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "exp": expire,
        "iat": datetime.now(UTC),
        "sub": str(subject),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(
    subject: str | uuid.UUID, expires_delta: timedelta | None = None
) -> str:
    """Create a longer-lived JWT refresh token."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "exp": expire,
        "iat": datetime.now(UTC),
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT token. Raises PyJWT exceptions if expired/invalid."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


def generate_api_key_pair() -> tuple[str, str, str]:
    """
    Generate an API key pair.
    Returns (raw_api_key, prefix, hashed_api_key).
    Format of raw_api_key: tk_live_[32 random hex characters]
    """
    random_hex = uuid.uuid4().hex + uuid.uuid4().hex[:16]  # 48 characters
    prefix = "tk_live"
    raw_key = f"{prefix}_{random_hex}"

    # Hash using SHA-256
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    return raw_key, prefix, hashed_key


def hash_api_key(raw_key: str) -> str:
    """Hash a raw API key using SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()
