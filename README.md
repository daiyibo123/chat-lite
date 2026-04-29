# Chat Lite

轻量级 ChatGPT 风格多模型聊天系统，支持 OpenAI / Claude / Gemini 多厂商接口、图片生成、LaTeX 公式渲染、对话分享。

## 功能特性

- 多模型切换（OpenAI、Claude、Gemini、图片生成模型）
- 流式输出 (SSE)
- 上下文自动压缩（超出 token 限制时摘要历史）
- 图片生成（gpt-image / dall-e 系列）
- LaTeX 数学公式渲染（KaTeX）
- 对话导出（Markdown / JSON / PDF）
- 对话分享（生成只读链接）
- 后台管理系统（模型 CRUD、API Key 开关、SSO 开关）
- sub2api 一键登录 (SSO)，可在后台开关
- 用户自带 API Key（加密存储）

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.9+ / FastAPI / SQLAlchemy / httpx |
| 前端 | Vue 3 / Vite / Axios / KaTeX |
| 数据库 | MySQL（开发）或 SQLite（部署） |
| 认证 | JWT + bcrypt |

## 目录结构

```
chat-lite/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 入口
│   │   ├── config.py         # 配置（读 .env）
│   │   ├── database.py       # 数据库引擎
│   │   ├── models.py         # ORM 模型
│   │   ├── schemas.py        # Pydantic 模型
│   │   └── routers/          # 路由
│   │       ├── auth.py       # 登录注册
│   │       ├── admin.py      # 后台管理
│   │       ├── chat.py       # 聊天 & 流式
│   │       ├── conversations.py
│   │       ├── keys.py       # API Key 管理
│   │       └── ...
│   ├── requirements.txt
│   └── .env                  # 环境变量（不入库）
├── frontend/         # Vue3 前端
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   ├── components/       # 通用组件
│   │   └── api/request.js    # Axios 封装
│   └── vite.config.js
└── README.md
```

## 部署指南

### 1. 准备环境

- Python 3.9+
- Node.js 18+
- MySQL 8.0（开发环境）或无需安装（部署用 SQLite）

### 2. 后端

```bash
cd backend
python -m venv venv

# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

创建 `.env` 文件：

```ini
# 应用
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库（二选一）
# SQLite（推荐部署用，零配置）
DATABASE_URL=sqlite:///./data/chat_lite.db
# MySQL
# DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/chat_lite?charset=utf8mb4

# 安全（务必修改！）
JWT_SECRET=your_random_jwt_secret_here
KEY_SECRET=your_random_key_secret_here
ENCRYPTION_KEY=your_random_encryption_key_here

# 管理员
ADMIN_USERNAMES=admin
ADMIN_PASSWORD=your_admin_password_here

# sub2api（如使用 SSO 登录）
SUB2API_BASE=https://your-sub2api-domain.com
SUB2API_LOGIN_URL=https://your-sub2api-domain.com/api/v1/auth/login
SUB2API_ME_URL=https://your-sub2api-domain.com/api/v1/auth/me

# CORS（填前端实际域名）
CORS_ORIGINS=https://your-domain.com
```

启动后端：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证：访问 `http://your-server:8000/api/health` 应返回 `{"status":"ok"}`。

### 3. 前端

```bash
cd frontend
npm install
```

开发模式：

```bash
npm run dev
```

生产构建：

```bash
npm run build
```

产物在 `frontend/dist/`，用 Nginx 托管即可。

### 4. Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/chat-lite/frontend/dist;
    index index.html;

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反代
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;           # SSE 流式输出必需
        proxy_cache off;
        proxy_read_timeout 300s;       # 图片生成较慢
    }
}
```

### 5. 首次使用

1. 访问 `https://your-domain.com/admin`，用 `.env` 中配置的管理员账号密码登录
2. 在后台**新增模型**（填写模型名、接口地址、接口类型等）
3. 在**站点设置**中开关 SSO 登录
4. 在**API Key 输入框控制**中管理各厂商 Key 输入开关
5. 访问 `https://your-domain.com`，注册/登录，填入 API Key 即可聊天

## 数据库说明

- 启动时自动建表（`create_all`），无需手动迁移
- SQLite 模式下自动创建 `backend/data/` 目录

### 表结构（8 张表）

| 表名 | 说明 |
|---|---|
| `users` | 用户信息、角色、状态 |
| `user_api_keys` | 用户 API Key（AES 加密存储） |
| `key_input_settings` | 各厂商 Key 输入框开关 |
| `models` | 模型配置（名称、接口、上下文限制等） |
| `conversations` | 对话列表 |
| `messages` | 聊天消息 |
| `usage_logs` | Token 用量记录 |
| `site_settings` | 站点级设置（SSO 开关等） |

## 环境变量参考

| 变量 | 必填 | 说明 |
|---|---|---|
| `DATABASE_URL` | 是 | 数据库连接串 |
| `JWT_SECRET` | 是 | JWT 签名密钥 |
| `KEY_SECRET` | 是 | API Key 加密密钥 |
| `ENCRYPTION_KEY` | 是 | 通用加密密钥 |
| `ADMIN_USERNAMES` | 是 | 管理员账号（逗号分隔） |
| `ADMIN_PASSWORD` | 是 | 管理员密码（同时作为后台 token） |
| `SUB2API_BASE` | 否 | sub2api 服务地址 |
| `SUB2API_LOGIN_URL` | 否 | sub2api 登录接口 |
| `SUB2API_ME_URL` | 否 | sub2api 用户信息接口 |
| `CORS_ORIGINS` | 是 | 允许的前端域名（逗号分隔） |

## License

MIT
