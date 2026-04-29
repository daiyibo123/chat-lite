"""读取 .env 配置。"""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "local"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./data/chat_lite.db"

    JWT_SECRET: str = "please_change_me"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    KEY_SECRET: str = "please_change_me_key_secret"
    ENCRYPTION_KEY: str = ""

    ADMIN_USERNAMES: str = "admin"
    ADMIN_PASSWORD: str = "please_change_admin_password"

    SUB2API_BASE: str = "https://www.dai1bo.tech"
    SUB2API_LOGIN_URL: str = "https://www.dai1bo.tech/api/v1/auth/login"
    # 用于 SSO：前端把 sub2api token 传过来，后端调这个接口验证 token 并取用户信息
    SUB2API_ME_URL: str = "https://www.dai1bo.tech/api/v1/auth/me"

    CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
