# chat-lite

轻量版 ChatGPT 风格聊天系统，调用 sub2api 服务（`https://www.dai1bo.tech`）。

- 后端：FastAPI + SQLAlchemy + (MySQL 本地 / SQLite 服务器)
- 前端：Vue3 + Vite
- 部署目标域名：`chat.dai1bo.tech`

## 目录

- `backend/`  FastAPI 后端
- `frontend/` Vue3 前端

## 本地运行（Windows）

### 后端

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/api/health 应返回 `{"status":"ok"}`。

### 前端

```bat
cd frontend
npm install
npm run dev
```

打开 Vite 提示的本地地址（默认 http://127.0.0.1:5173），应显示 `Chat Lite`。

## 数据库说明

- **本地开发**：MySQL 8.0（`.env` 中 `DATABASE_URL=mysql+pymysql://root:xxx@127.0.0.1:3306/chat_lite?charset=utf8mb4`）
- **服务器部署**：SQLite（`.env` 中 `DATABASE_URL=sqlite:///./data/chat_lite.db`）
- 启动时自动建表（`create_all`），无需手动迁移
- SQLite 时自动创建 `backend/data/` 目录

### 表结构（7 张表）

| 表名 | 说明 |
|------|------|
| `users` | 用户：id / username / password_hash / role / status / created_at / last_login_at |
| `user_api_keys` | API Key（加密存储）：id / user_id / key_type / api_key_encrypted / expires_at |
| `models` | 模型配置：display_name / model_name / company_type / endpoint_type / context_limit 等 |
| `conversations` | 对话：user_id / title / model_name / summary |
| `messages` | 消息：conversation_id / role / content / model_name |
| `usage_logs` | 用量记录：user_id / model_name / input_tokens / output_tokens |
| `image_tasks` | 生图任务（预留）：user_id / prompt / image_url / status |

## 默认初始化数据

1. Windows 本地跑通
2. 上传到 GitHub
3. 服务器从 GitHub 拉取
4. 部署到服务器
5. 绑定域名 `chat.dai1bo.tech`
