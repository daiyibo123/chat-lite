"""ORM 模型：User / UserApiKey / Model / Conversation / Message / UsageLog / ImageTask。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ───────────────────────── users ─────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    api_keys: Mapped[List[UserApiKey]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List[Conversation]] = relationship(back_populates="user", cascade="all, delete-orphan")

# ───────────────────── user_api_keys ─────────────────────

class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_type: Mapped[str] = mapped_column(
        Enum("openai_key", "claude_key", "gemini_key", name="key_type_enum"),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="api_keys")


class KeyInputSetting(Base):
    __tablename__ = "key_input_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_type: Mapped[str] = mapped_column(
        Enum("openai_key", "claude_key", "gemini_key", name="key_input_type_enum"),
        nullable=False,
        unique=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str] = mapped_column(String(256), nullable=False, default="该模型正在修复中.....")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

# ──────────────────────── models ─────────────────────────

class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    company_type: Mapped[str] = mapped_column(
        Enum("openai", "claude", "gemini", name="company_type_enum"),
        nullable=False,
    )
    endpoint_type: Mapped[str] = mapped_column(
        Enum("openai_chat", "anthropic", "gemini", "openai_image", name="endpoint_type_enum"),
        nullable=False,
    )
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    required_key_type: Mapped[str] = mapped_column(
        Enum("openai_key", "claude_key", "gemini_key", name="required_key_type_enum"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    context_limit: Mapped[int] = mapped_column(Integer, default=200000)
    support_image: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

# ──────────────────── conversations ──────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="新对话")
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    share_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[List[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

# ──────────────────────── messages ───────────────────────

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", "summary", name="message_role_enum"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

# ──────────────────── usage_logs ─────────────────────────

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint_type: Mapped[str] = mapped_column(String(32), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# ──────────────────── image_tasks ────────────────────────

class ImageTask(Base):
    __tablename__ = "image_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "success", "failed", name="image_task_status_enum"),
        nullable=False,
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
