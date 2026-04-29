"""FastAPI 入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.init_data import init_data
from app.routers import admin, auth, chat, conversations, keys, model_routes, upload

app = FastAPI(title="chat-lite", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_tables()
    init_data()


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(keys.router)
app.include_router(model_routes.router)
app.include_router(conversations.router)
app.include_router(conversations.share_router)
app.include_router(chat.router)
app.include_router(upload.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
