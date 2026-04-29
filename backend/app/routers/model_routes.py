"""模型列表：只返回用户已配置 Key 且 enabled 的聊天模型。"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import KeyInputSetting, Model as ModelORM, User, UserApiKey
from app.schemas import ModelAvailableOut

router = APIRouter(prefix="/api/models", tags=["models"])


def _ensure_key_settings(db: Session):
    existing = {
        row.key_type: row
        for row in db.query(KeyInputSetting).all()
    }
    changed = False
    for key_type in ("openai_key", "claude_key", "gemini_key"):
        if key_type not in existing:
            db.add(KeyInputSetting(
                key_type=key_type,
                enabled=True,
                message="该模型正在修复中.....",
            ))
            changed = True
    if changed:
        db.commit()


@router.get("/key-availability")
def key_availability(db: Session = Depends(get_db)):
    _ensure_key_settings(db)
    key_types = ("openai_key", "claude_key", "gemini_key")
    rows = {
        row.key_type: row
        for row in db.query(KeyInputSetting).all()
    }
    out = {}
    for key_type in key_types:
        row = rows.get(key_type)
        enabled = True if row is None else row.enabled
        out[key_type] = {
            "available": enabled,
            "message": "" if enabled else (row.message or "该模型正在修复中....."),
        }
    return out


@router.get("/available", response_model=List[ModelAvailableOut])
def available_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    _ensure_key_settings(db)

    # 查询用户未过期的 key_type 集合
    valid_key_types = {
        row.key_type
        for row in db.query(UserApiKey.key_type).filter(
            UserApiKey.user_id == current_user.id,
            UserApiKey.expires_at > now,
        ).all()
    }

    if not valid_key_types:
        return []

    enabled_input_types = {
        row.key_type
        for row in db.query(KeyInputSetting).filter(KeyInputSetting.enabled == True).all()
    }
    valid_key_types = valid_key_types.intersection(enabled_input_types)

    if not valid_key_types:
        return []

    # enabled + key 已配置（包含生图模型）
    models = (
        db.query(ModelORM)
        .filter(
            ModelORM.enabled == True,
            ModelORM.required_key_type.in_(valid_key_types),
        )
        .order_by(ModelORM.sort_order)
        .all()
    )
    return models
