# 家庭服务导航面板

轻量、自托管的 EasyTier 私网服务导航面板。第一版只包含设备管理、服务入口、搜索、收藏、在线检测和响应耗时。

## 功能范围

- 设备新增、编辑、删除，展示服务总数和在线服务数。
- 服务新增、编辑、删除、启用、停用、收藏、手动检测和新标签打开。
- 未配置完整 URL 时按 `{protocol}://{device.host}:{port}{path}` 生成入口，修改设备地址后自动使用新地址。
- 后端异步执行 `GET` 或 `HEAD` 健康检查，默认每 60 秒批量检测一次。
- 状态映射：`2xx/3xx=online`、`401/403=auth`、其他 HTTP 状态 `degraded`、连接失败或超时 `offline`、未检测 `unknown`。
- 前端基于已加载数据执行服务名、设备名和说明的模糊搜索。

第一版没有登录认证，只能部署在可信 EasyTier 私网，不要直接暴露到公网。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Lucide。
- 后端：FastAPI、Pydantic、SQLAlchemy 2.x 异步模式、HTTPX。
- 数据库：外部 MySQL 8.4，驱动 `asyncmy`，迁移使用 Alembic。
- 部署：单个 Docker 镜像，FastAPI 同时提供 `/api` 和前端静态资源。

## MySQL 初始化

在飞牛 NAS 已有 MySQL 8.4 中执行 `init-mysql.sql`，并把密码替换为强密码：

```sql
CREATE DATABASE home_dashboard
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'home_dashboard'@'%'
  IDENTIFIED BY '请替换为强密码';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON home_dashboard.*
TO 'home_dashboard'@'%';

FLUSH PRIVILEGES;
```

应用容器会在启动时执行 `alembic upgrade head`。迁移失败时 Web 服务不会启动。

## Docker Compose 部署

1. 确认 MySQL 容器已经加入外部网络 `mysql-network`，服务名例如 `mysql8`。
2. 复制 `.env.example` 为 `.env`，填写 `DB_PASSWORD`。
3. 修改 `docker-compose.yml` 里的镜像所有者。
4. 启动：

```bash
docker compose up -d
```

访问地址：`http://10.126.126.10:8080` 或宿主机对应地址。

更新：

```bash
docker compose pull
docker compose up -d
```

回滚固定版本时，把镜像改成例如 `ghcr.io/<owner>/home-service-dashboard:1.0.0` 后重新 `docker compose up -d`。

## 本地开发

后端：

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='mysql+asyncmy://home_dashboard:password@127.0.0.1:3306/home_dashboard?charset=utf8mb4'
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

前端：

```bash
cd frontend
npm install
npm run dev
```

测试：

```bash
cd backend
pytest -q
cd ../frontend
npm run build
```

## GHCR 发布

工作流 `.github/workflows/docker.yml` 会在 PR 中运行后端测试、前端构建和 Docker 构建验证，但不推送镜像。推送 `main` 会发布：

```text
ghcr.io/<owner>/home-service-dashboard:latest
```

推送 `v1.0.0` 会发布 `1.0.0`、`1.0`、`1` 等语义化版本标签。首次发布后，在 GitHub 仓库的 Packages 页面进入镜像设置，把 Package visibility 设置为 Public。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DB_HOST` | `mysql8` | MySQL 容器 DNS 名，容器间连接禁止使用 localhost |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_NAME` | `home_dashboard` | 数据库名 |
| `DB_USER` | `home_dashboard` | 普通业务用户 |
| `DB_PASSWORD` | 空 | 必须从 `.env` 或部署环境提供 |
| `CHECK_INTERVAL_SECONDS` | `60` | 批量健康检查间隔 |
| `CACHE_TTL_SECONDS` | `30` | 单进程 TTL 缓存时间 |

当前缓存只适合单应用副本。多副本部署需要共享缓存或额外一致性设计，第一版不实现 Redis。

## 第一版限制

不包含登录、多用户、权限、分类、系统监控、EasyTier 节点同步、Docker 管理、SSH、告警、历史趋势、导入导出、DDNS、反向代理和自动扫描服务。
