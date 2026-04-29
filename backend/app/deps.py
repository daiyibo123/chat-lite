"""FastAPI 依赖注入。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer()

GUEST_USERNAME = "guest"


def get_guest_user(db: Session = Depends(get_db)) -> User:
    """免登录：直接返回默认 guest 用户。"""
    user = db.query(User).filter(User.username == GUEST_USERNAME).first()
    if user is None:
        raise HTTPException(status_code=500, detail="默认用户不存在，请检查初始化")
    return user


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(cred.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")
    user_id: int = payload.get("uid")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user
