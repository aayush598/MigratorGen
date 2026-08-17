"""
Authentication and authorization for MigratorGen platform.
JWT tokens, API key management, password hashing, and RBAC.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    from passlib.context import CryptContext
    PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    PWD_CONTEXT = None

logger = logging.getLogger(__name__)


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_HIERARCHY = {
    Role.OWNER: 4,
    Role.ADMIN: 3,
    Role.MEMBER: 2,
    Role.VIEWER: 1,
}


def hash_password(password: str) -> str:
    if not PASSLIB_AVAILABLE:
        raise ImportError("passlib is required for password hashing")
    return PWD_CONTEXT.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not PASSLIB_AVAILABLE:
        raise ImportError("passlib is required for password hashing")
    return PWD_CONTEXT.verify(plain, hashed)


def create_access_token(
    tenant_id: str,
    user_id: str,
    role: str = "member",
    secret: str = "",
    expires_minutes: int = 15,
    extra: Optional[dict] = None,
) -> str:
    if not JWT_AVAILABLE:
        raise ImportError("PyJWT is required for JWT tokens")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "iss": "migrator-gen",
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(
    tenant_id: str,
    user_id: str,
    secret: str = "",
    expires_days: int = 30,
) -> str:
    if not JWT_AVAILABLE:
        raise ImportError("PyJWT is required for JWT tokens")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(days=expires_days),
        "iss": "migrator-gen",
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> Optional[dict]:
    if not JWT_AVAILABLE:
        return None
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], issuer="migrator-gen")
    except jwt.ExpiredSignatureError:
        logger.warning("token_expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("token_invalid: %s", str(e))
        return None


def generate_api_key() -> tuple[str, str]:
    raw = f"mg_{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return hashlib.sha256(raw_key.encode()).hexdigest() == key_hash


def has_permission(user_role: str, required_role: str) -> bool:
    user_level = ROLE_HIERARCHY.get(Role(user_role), 0)
    required_level = ROLE_HIERARCHY.get(Role(required_role), 0)
    return user_level >= required_level
