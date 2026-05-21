# 开发说明

## 本地后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e .
uvicorn app.main:app --reload
```

## 本地前端

```bash
cd frontend
npm install
npm run dev
```

## Docker Compose

Redis、PostgreSQL、MinIO 都部署在 Docker 中，并统一使用 `agentpilot-服务名` 命名。

```bash
cd deploy
docker compose up --build
```

访问：

- 前端：http://localhost:5173
- 后端：http://localhost:8000/docs
- PostgreSQL：localhost:15432
- Redis：localhost:16379
- MinIO：http://localhost:19001
