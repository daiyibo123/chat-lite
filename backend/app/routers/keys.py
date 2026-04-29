"""API Key 配置：测试 / 加密保存 / 7 天有效期 / 状态查询。"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_guest_user
from app.models import User, UserApiKey
from app.schemas import (
    KeySaveRequest,
    KeySaveResponse,
    KeyStatusItem,
    KeyStatusResponse,
    KeyTestResult,
)
from app.security import decrypt_api_key, encrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keys", tags=["keys"])

KEY_EXPIRE_DAYS = 7
SUB2API = "https://www.dai1bo.tech"
KEY_TEST_TIMEOUT = httpx.Timeout(8, connect=3, read=5, write=5, pool=3)


async def _run_key_test(test_call: Awaitable[KeyTestResult], key_name: str) -> KeyTestResult:
    try:
        return await asyncio.wait_for(test_call, timeout=10)
    except asyncio.TimeoutError:
        return KeyTestResult(success=False, message=f"{key_name} 测试超时，请稍后重试")

async def _test_openai_key(api_key: str) -> KeyTestResult:
    try:
        async with httpx.AsyncClient(timeout=KEY_TEST_TIMEOUT) as c:
            r = await c.post(
                f"{SUB2API}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "你好，只回复 OK"}], "stream": False},
            )
        if r.status_code == 200:
            return KeyTestResult(success=True, message="OpenAI Key 测试成功")
        return KeyTestResult(success=False, message=f"OpenAI 测试失败: HTTP {r.status_code}")
    except Exception as e:
        return KeyTestResult(success=False, message=f"OpenAI 测试异常: {e}")


async def _test_claude_key(api_key: str) -> KeyTestResult:
    try:
        async with httpx.AsyncClient(timeout=KEY_TEST_TIMEOUT) as c:
            r = await c.post(
                f"{SUB2API}/antigravity/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-opus-4-6", "max_tokens": 64, "messages": [{"role": "user", "content": "你好，只回复 OK"}]},
            )
        if r.status_code == 200:
            return KeyTestResult(success=True, message="Claude Key 测试成功")
        return KeyTestResult(success=False, message=f"Claude 测试失败: HTTP {r.status_code}")
    except Exception as e:
        return KeyTestResult(success=False, message=f"Claude 测试异常: {e}")


async def _test_gemini_key(api_key: str) -> KeyTestResult:
    try:
        async with httpx.AsyncClient(timeout=KEY_TEST_TIMEOUT) as c:
            r = await c.post(
                f"{SUB2API}/antigravity/v1beta/models/gemini-3-pro-low:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={"contents": [{"role": "user", "parts": [{"text": "你好，只回复 OK"}]}]},
            )
        if r.status_code == 200:
            return KeyTestResult(success=True, message="Gemini Key 测试成功")
        return KeyTestResult(success=False, message=f"Gemini 测试失败: HTTP {r.status_code}")
    except Exception as e:
        return KeyTestResult(success=False, message=f"Gemini 测试异常: {e}")


TEST_FN = {
    "openai_key": (_test_openai_key, "OpenAI Key"),
    "claude_key": (_test_claude_key, "Claude Key"),
    "gemini_key": (_test_gemini_key, "Gemini Key"),
}


# ──────────── 保存 / upsert ─────────────

def _upsert_key(db: Session, user_id: int, key_type: str, plain_key: str) -> None:
    now = datetime.utcnow()
    expires = now + timedelta(days=KEY_EXPIRE_DAYS)
    existing = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id,
        UserApiKey.key_type == key_type,
    ).first()
    if existing:
        existing.api_key_encrypted = encrypt_api_key(plain_key)
        existing.expires_at = expires
        existing.updated_at = now
    else:
        db.add(UserApiKey(
            user_id=user_id,
            key_type=key_type,
            api_key_encrypted=encrypt_api_key(plain_key),
            expires_at=expires,
        ))


# ──────────────── 接口 ──────────────────

@router.post("/save", response_model=KeySaveResponse)
async def save_keys(
    body: KeySaveRequest,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    results = {}
    for key_type in ("openai_key", "claude_key", "gemini_key"):
        raw_value: Optional[str] = getattr(body, key_type, None)
        if not raw_value or not raw_value.strip():
            continue
        raw_value = raw_value.strip()
        test_fn, key_name = TEST_FN[key_type]
        test_result = await _run_key_test(test_fn(raw_value), key_name)
        results[key_type] = test_result
        if test_result.success:
            _upsert_key(db, current_user.id, key_type, raw_value)
    db.commit()
    return KeySaveResponse(**results)


@router.get("/status", response_model=KeyStatusResponse)
def key_status(
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    out = {}
    for key_type in ("openai_key", "claude_key", "gemini_key"):
        row = db.query(UserApiKey).filter(
            UserApiKey.user_id == current_user.id,
            UserApiKey.key_type == key_type,
        ).first()
        if row and row.expires_at > now:
            plain = decrypt_api_key(row.api_key_encrypted)
            out[key_type] = KeyStatusItem(
                configured=True,
                expires_at=row.expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                masked=mask_api_key(plain),
            )
        else:
            out[key_type] = KeyStatusItem(configured=False)
    return KeyStatusResponse(**out)
