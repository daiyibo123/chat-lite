"""JWT / 密码哈希 / API Key 加密。"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ───────────────── 密码 ─────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ────────────────── JWT ──────────────────

def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

# ──────────── API Key 加密 ───────────────

def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.KEY_SECRET.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_api_key(plain_key: str) -> str:
    return _get_fernet().encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def mask_api_key(plain_key: str) -> str:
    if len(plain_key) <= 8:
        return plain_key[:2] + "****"
    return plain_key[:6] + "****" + plain_key[-2:]
