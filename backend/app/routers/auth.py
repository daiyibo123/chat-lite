"""用户登录 / 当前用户 / 登出。"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserApiKey
from app.schemas import LoginRequest, LoginResponse, UserOut
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

KEY_EXTEND_DAYS = 7


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    # 更新 last_login_at
    user.last_login_at = datetime.utcnow()

    # 续期未过期的 Key
    now = datetime.utcnow()
    new_expires = now + timedelta(days=KEY_EXTEND_DAYS)
    keys = db.query(UserApiKey).filter(
        UserApiKey.user_id == user.id,
        UserApiKey.expires_at > now,
    ).all()
    for k in keys:
        k.expires_at = new_expires
        k.updated_at = now

    db.commit()

    token = create_access_token({"uid": user.id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout():
    return {"detail": "已登出"}
