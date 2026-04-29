"""首次启动初始化默认用户与默认模型。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Model
from app.security import hash_password

logger = logging.getLogger(__name__)

# ───────────────── 默认模型数据 ──────────────────

DEFAULT_MODELS = [
    {
        "display_name": "GPT-5.4",
        "model_name": "gpt-5.4",
        "company_type": "openai",
        "endpoint_type": "openai_chat",
        "endpoint_url": "https://www.dai1bo.tech/v1/chat/completions",
        "required_key_type": "openai_key",
        "enabled": True,
        "context_limit": 200000,
        "support_image": False,
        "sort_order": 10,
    },
    {
        "display_name": "GPT-5.4 Mini",
        "model_name": "gpt-5.4-mini",
        "company_type": "openai",
        "endpoint_type": "openai_chat",
        "endpoint_url": "https://www.dai1bo.tech/v1/chat/completions",
        "required_key_type": "openai_key",
        "enabled": True,
        "context_limit": 200000,
        "support_image": False,
        "sort_order": 20,
    },
    {
        "display_name": "Claude Opus 4.6",
        "model_name": "claude-opus-4-6",
        "company_type": "claude",
        "endpoint_type": "anthropic",
        "endpoint_url": "https://www.dai1bo.tech/antigravity/v1/messages",
        "required_key_type": "claude_key",
        "enabled": True,
        "context_limit": 200000,
        "support_image": False,
        "sort_order": 30,
    },
    {
        "display_name": "Gemini 3 Pro Low",
        "model_name": "gemini-3-pro-low",
        "company_type": "gemini",
        "endpoint_type": "gemini",
        "endpoint_url": "https://www.dai1bo.tech/antigravity",
        "required_key_type": "gemini_key",
        "enabled": True,
        "context_limit": 200000,
        "support_image": False,
        "sort_order": 40,
    },
    {
        "display_name": "GPT Image 2",
        "model_name": "gpt-image-2",
        "company_type": "openai",
        "endpoint_type": "openai_image",
        "endpoint_url": "https://www.dai1bo.tech/v1/images/generations",
        "required_key_type": "openai_key",
        "enabled": False,
        "context_limit": 0,
        "support_image": True,
        "sort_order": 50,
    },
]


def init_default_user(db: Session) -> None:
    """确保 guest 用户存在（免登录默认用户）。"""
    guest = db.query(User).filter(User.username == "guest").first()
    if guest:
        return
    # 兼容旧数据：将 "user" 重命名为 "guest"
    old_user = db.query(User).filter(User.username == "user").first()
    if old_user:
        old_user.username = "guest"
        db.commit()
        logger.info("已将默认用户 user 重命名为 guest")
        return
    user = User(
        username="guest",
        password_hash=hash_password("not_used"),
        role="user",
        status="active",
    )
    db.add(user)
    db.commit()
    logger.info("已创建默认用户: guest")


def init_default_models(db: Session) -> None:
    """models 表为空时，插入默认模型列表。"""
    if db.query(Model).count() > 0:
        return
    for m in DEFAULT_MODELS:
        db.add(Model(**m))
    db.commit()
    logger.info("已插入 %d 个默认模型", len(DEFAULT_MODELS))


def _migrate_add_share_id(db: Session) -> None:
    """为 conversations 表添加 share_id 列（如果不存在）。"""
    from sqlalchemy import text, inspect
    insp = inspect(db.bind)
    cols = [c["name"] for c in insp.get_columns("conversations")]
    if "share_id" not in cols:
        db.execute(text("ALTER TABLE conversations ADD COLUMN share_id VARCHAR(64) NULL"))
        db.commit()
        logger.info("已为 conversations 表添加 share_id 列")


def init_data() -> None:
    """统一入口：建表后调用一次。"""
    db = SessionLocal()
    try:
        init_default_user(db)
        init_default_models(db)
        _migrate_add_share_id(db)
    finally:
        db.close()
