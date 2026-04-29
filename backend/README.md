# chat-lite backend

FastAPI 后端骨架。

## 启动

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 健康检查

GET http://127.0.0.1:8000/api/health -> `{"status":"ok"}`

## 目录

- `app/main.py`        FastAPI 入口
- `app/config.py`      读取 `.env`
- `app/database.py`    SQLAlchemy 引擎/Session（第 1 步未启用）
- `app/models.py`      ORM 模型（占位）
- `app/schemas.py`     Pydantic schema（占位）
- `app/security.py`    JWT / 密码 / Key 加密（占位）
- `app/init_data.py`   首次启动初始化数据（占位）
- `app/deps.py`        依赖注入（占位）
- `app/routers/`       路由模块（占位，仅 health 已实现）
- `app/providers/`     调用 sub2api 的 provider（占位）
