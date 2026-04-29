"""SQLAlchemy 引擎与 Session，兼容 MySQL（本地）和 SQLite（服务器）。"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _make_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # 确保 data/ 目录存在
        db_path = url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        eng = create_engine(url, connect_args={"check_same_thread": False})
        # SQLite 开启外键约束
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        return eng
    # MySQL / 其他
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def create_tables():
    """根据 ORM 模型建表（如果表已存在则跳过）。"""
    from app import models  # noqa: F401  确保所有模型被注册
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
