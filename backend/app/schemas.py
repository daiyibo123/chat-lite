"""Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ───────────────── Auth ─────────────────

class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class Sub2apiSsoRequest(BaseModel):
    access_token: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ───────────────── Admin ────────────────

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    admin_token: str


# ───────────────── Model ────────────────

class ModelCreate(BaseModel):
    display_name: str
    model_name: str
    company_type: str
    endpoint_type: str
    endpoint_url: Optional[str] = None
    required_key_type: str
    enabled: bool = True
    context_limit: int = 200000
    support_image: bool = False
    sort_order: int = 0


class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    model_name: Optional[str] = None
    company_type: Optional[str] = None
    endpoint_type: Optional[str] = None
    endpoint_url: Optional[str] = None
    required_key_type: Optional[str] = None
    enabled: Optional[bool] = None
    context_limit: Optional[int] = None
    support_image: Optional[bool] = None
    sort_order: Optional[int] = None


class ModelOut(BaseModel):
    id: int
    display_name: str
    model_name: str
    company_type: str
    endpoint_type: str
    endpoint_url: Optional[str] = None
    required_key_type: str
    enabled: bool
    context_limit: int
    support_image: bool
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelAvailableOut(BaseModel):
    id: int
    display_name: str
    model_name: str
    company_type: str
    endpoint_type: str
    context_limit: int
    support_image: bool

    class Config:
        from_attributes = True


# ────────────── API Keys ─────────────────

class KeySaveRequest(BaseModel):
    openai_key: Optional[str] = None
    claude_key: Optional[str] = None
    gemini_key: Optional[str] = None


class KeyTestResult(BaseModel):
    success: bool
    message: str


class KeySaveResponse(BaseModel):
    openai_key: Optional[KeyTestResult] = None
    claude_key: Optional[KeyTestResult] = None
    gemini_key: Optional[KeyTestResult] = None


class KeyStatusItem(BaseModel):
    configured: bool
    expires_at: Optional[str] = None
    masked: Optional[str] = None


class KeyStatusResponse(BaseModel):
    openai_key: KeyStatusItem
    claude_key: KeyStatusItem
    gemini_key: KeyStatusItem


# ─────────── Conversation / Message ──────

class ConversationOut(BaseModel):
    id: int
    title: str
    model_name: Optional[str] = None
    share_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─────────────── Chat ────────────────────

class ChatSendRequest(BaseModel):
    conversation_id: int
    model_name: str
    message: str
    images: Optional[List[str]] = None  # base64 data-url list


class ChatSendResponse(BaseModel):
    reply: str
    message_id: int
    conversation_id: int
    model_name: str
