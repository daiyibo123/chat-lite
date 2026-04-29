"""管理后台：admin 密码登录 + 模型 CRUD。"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import KeyInputSetting, Model as ModelORM, SiteSetting
from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    ModelCreate,
    ModelOut,
    ModelUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
bearer = HTTPBearer()
KEY_TYPES = ("openai_key", "claude_key", "gemini_key")
DEFAULT_REPAIR_MESSAGE = "该模型正在修复中....."


SITE_SETTING_DEFAULTS = {
    "sso_enabled": "true",
}


def _ensure_site_settings(db: Session):
    existing = {row.key: row for row in db.query(SiteSetting).all()}
    changed = False
    for key, default in SITE_SETTING_DEFAULTS.items():
        if key not in existing:
            db.add(SiteSetting(key=key, value=default))
            changed = True
    if changed:
        db.commit()


# ───────────── admin 鉴权依赖 ─────────────

def require_admin(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    # 直接校验 bearer token == ADMIN_PASSWORD，不依赖 JWT，永不过期
    if cred.credentials != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员身份验证失败")
    return {"role": "admin"}


def _ensure_key_settings(db: Session):
    existing = {
        row.key_type: row
        for row in db.query(KeyInputSetting).all()
    }
    changed = False
    for key_type in KEY_TYPES:
        if key_type not in existing:
            db.add(KeyInputSetting(
                key_type=key_type,
                enabled=True,
                message=DEFAULT_REPAIR_MESSAGE,
            ))
            changed = True
    if changed:
        db.commit()


# ────────────── admin 登录 ────────────────

@router.post("/login", response_model=AdminLoginResponse)
def admin_login(body: AdminLoginRequest):
    allowed = [u.strip() for u in settings.ADMIN_USERNAMES.split(",") if u.strip()]
    if body.username not in allowed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员账号不存在")
    if body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员密码错误")
    # 密码本身即为 token，无需 JWT
    return AdminLoginResponse(admin_token=body.password)


@router.get("/key-input-settings")
def list_key_input_settings(
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_key_settings(db)
    rows = db.query(KeyInputSetting).all()
    return {
        row.key_type: {
            "enabled": row.enabled,
            "message": row.message,
        }
        for row in rows
    }


@router.put("/key-input-settings/{key_type}")
def update_key_input_setting(
    key_type: str,
    body: dict,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if key_type not in KEY_TYPES:
        raise HTTPException(status_code=400, detail="Key 类型不存在")
    _ensure_key_settings(db)
    row = db.query(KeyInputSetting).filter(KeyInputSetting.key_type == key_type).first()
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
    if body.get("message"):
        row.message = str(body["message"])[:256]
    db.commit()
    db.refresh(row)
    return {
        "key_type": row.key_type,
        "enabled": row.enabled,
        "message": row.message,
    }


@router.get("/verify")
def verify_admin(_=Depends(require_admin)):
    return {"ok": True}


# ────────────── 站点设置 ────────────────

@router.get("/site-settings")
def get_site_settings(
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_site_settings(db)
    rows = db.query(SiteSetting).all()
    return {row.key: row.value for row in rows}


@router.put("/site-settings/{key}")
def update_site_setting(
    key: str,
    body: dict,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if key not in SITE_SETTING_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"未知设置项: {key}")
    _ensure_site_settings(db)
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    row.value = str(body.get("value", ""))[:512]
    db.commit()
    db.refresh(row)
    return {"key": row.key, "value": row.value}


# ────────────── 模型列表 ──────────────────

@router.get("/models", response_model=List[ModelOut])
def list_models(
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(ModelORM).order_by(ModelORM.sort_order).all()


# ────────────── 新增模型 ──────────────────

@router.post("/models", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
def create_model(
    body: ModelCreate,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    exists = db.query(ModelORM).filter(ModelORM.model_name == body.model_name).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"model_name '{body.model_name}' 已存在")
    obj = ModelORM(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ────────────── 编辑模型 ──────────────────

@router.put("/models/{model_id}", response_model=ModelOut)
def update_model(
    model_id: int,
    body: ModelUpdate,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    obj = db.query(ModelORM).filter(ModelORM.id == model_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="模型不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


# ────────────── 删除模型 ──────────────────

@router.delete("/models/{model_id}")
def delete_model(
    model_id: int,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    obj = db.query(ModelORM).filter(ModelORM.id == model_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="模型不存在")
    db.delete(obj)
    db.commit()
    return {"detail": "已删除"}
