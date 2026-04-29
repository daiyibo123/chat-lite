"""用户登录 / 当前用户 / 登出。"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserApiKey
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, Sub2apiSsoRequest, UserOut
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

KEY_EXTEND_DAYS = 7


def _extend_active_keys(user_id: int, db: Session) -> None:
    now = datetime.utcnow()
    new_expires = now + timedelta(days=KEY_EXTEND_DAYS)
    keys = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id,
        UserApiKey.expires_at > now,
    ).all()
    for k in keys:
        k.expires_at = new_expires
        k.updated_at = now


async def _login_with_sub2api(body: LoginRequest, db: Session) -> LoginResponse:
    account = (body.email or body.username or "").strip()
    password = body.password.strip()
    if not account or not password:
        raise HTTPException(status_code=400, detail="请输入账号和密码")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=5, read=8, write=5, pool=5)) as c:
            res = await c.post(
                settings.SUB2API_LOGIN_URL,
                json={"email": account, "password": password},
                headers={"Content-Type": "application/json"},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="sub2api 登录服务暂时不可用")
    if res.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    data = res.json()
    if data.get("code") != 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=data.get("message") or "账号或密码错误")
    sub_user = data.get("data", {}).get("user") or {}
    if sub_user.get("status") and sub_user.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    sub_id = sub_user.get("id")
    email = sub_user.get("email") or account
    username = sub_user.get("username") or email
    local_username = f"sub2api:{sub_id or email}"
    user = db.query(User).filter(User.username == local_username).first()
    if not user:
        user = User(
            username=local_username,
            password_hash=hash_password("sub2api_login_only"),
            role="user",
            status="active",
        )
        db.add(user)
        db.flush()
    user.last_login_at = datetime.utcnow()
    user.status = "active"
    _extend_active_keys(user.id, db)
    db.commit()
    db.refresh(user)
    token = create_access_token({"uid": user.id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user=UserOut(id=user.id, username=username, role=user.role),
    )


@router.post("/register", response_model=LoginResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    password = body.password.strip()
    if len(username) < 3 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度需要在 3-32 位之间")
    if len(password) < 6 or len(password) > 64:
        raise HTTPException(status_code=400, detail="密码长度需要在 6-64 位之间")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="user",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"uid": user.id, "role": user.role})
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    if settings.SUB2API_LOGIN_URL:
        return await _login_with_sub2api(body, db)

    username = (body.username or body.email or "").strip()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    # 更新 last_login_at
    user.last_login_at = datetime.utcnow()

    _extend_active_keys(user.id, db)

    db.commit()

    token = create_access_token({"uid": user.id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.post("/sub2api-sso", response_model=LoginResponse)
async def sub2api_sso(body: Sub2apiSsoRequest, db: Session = Depends(get_db)):
    """用 sub2api 的 access_token 验证身份并创建本地会话。
    流程：前端 popup 拿到 sub2api token → POST 到这里 → 后端调 sub2api /me 验证 → 找/建本地用户 → 返回本地 JWT。
    """
    token = (body.access_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="缺少 access_token")
    if not settings.SUB2API_ME_URL:
        raise HTTPException(status_code=500, detail="未配置 SUB2API_ME_URL")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=5, read=8, write=5, pool=5)) as c:
            res = await c.get(
                settings.SUB2API_ME_URL,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="sub2api 服务暂时不可用")

    if res.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub2api 登录态已失效，请重新登录")

    data = res.json()
    # sub2api 常见返回: {"code":0,"data":{"user":{...}}} 或直接 {"id":...,"email":...}
    sub_user = None
    if isinstance(data, dict):
        if data.get("code") == 0 and isinstance(data.get("data"), dict):
            sub_user = data["data"].get("user") or data["data"]
        elif "id" in data or "email" in data:
            sub_user = data
    if not sub_user:
        raise HTTPException(status_code=502, detail="无法解析 sub2api 用户信息")

    if sub_user.get("status") and sub_user.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    sub_id = sub_user.get("id")
    email = sub_user.get("email") or ""
    display = sub_user.get("username") or email
    local_username = f"sub2api:{sub_id or email}"
    if not local_username or local_username == "sub2api:":
        raise HTTPException(status_code=502, detail="sub2api 用户信息缺少 id/email")

    user = db.query(User).filter(User.username == local_username).first()
    if not user:
        user = User(
            username=local_username,
            password_hash=hash_password("sub2api_login_only"),
            role="user",
            status="active",
        )
        db.add(user)
        db.flush()
    user.last_login_at = datetime.utcnow()
    user.status = "active"
    _extend_active_keys(user.id, db)
    db.commit()
    db.refresh(user)

    local_token = create_access_token({"uid": user.id, "role": user.role})
    return LoginResponse(
        access_token=local_token,
        user=UserOut(id=user.id, username=display or local_username, role=user.role),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout():
    return {"detail": "已登出"}
