# 日本陆上养殖主业务系统

这是 `/home/gmm/srv/japan-aquaculture-project` 的项目级 README。  
本仓库同时包含业务后端、两套 Agent 实现、数据库脚本和大量历史文档；排障和部署时请优先以代码入口与配置文件为准，不要只看旧 README。

## 目录说明

- `backend/`：当前业务数据面主服务，Flask。
- `agent_new/`：较新的 FastAPI Agent，实现聊天、历史记录、WebSocket、专家服务和设备服务对接。
- `agent/`：保留的旧 Agent 实现，仍有不少历史文档引用它。
- `schema/`：数据库 DDL 和变更 SQL。
- `scripts/`：数据库初始化、校验、导入等脚本。
- `docs/`：业务说明、数据流程和历史分析文档。

## 当前已确认入口

### Backend

- 入口：`backend/main.py`
- 应用工厂：`backend/app_factory.py`
- 默认监听：`0.0.0.0:5002`
- 健康检查：`GET /api/health`
- 文件上传：`POST /api/v1/upload`、`POST /api/v1/upload/multiple`

### `agent_new`

- 入口：`agent_new/server.py`
- 实际启动：`uvicorn api.app:app`
- 默认监听：`0.0.0.0:8000`
- 主要接口：`POST /api/v1/chat`、`GET /api/v1/chat/history`、`GET /health`、`WS /ws`

### 旧 `agent`

- 入口：`agent/main.py`
- 该目录仍在仓库内，但是否还在生产使用，需要现场确认。

## 快速启动

### 1. 安装依赖

```bash
cd /home/gmm/srv/japan-aquaculture-project
uv sync
```

### 2. 初始化数据库

```bash
cd /home/gmm/srv/japan-aquaculture-project
uv run python scripts/init_database.py
```

### 3. 启动 Backend

```bash
cd /home/gmm/srv/japan-aquaculture-project/backend
uv run python main.py
```

### 4. 启动 `agent_new`

```bash
cd /home/gmm/srv/japan-aquaculture-project/agent_new
python server.py
```

## 环境变量范围

### Backend

- 服务：`HOST`、`PORT`、`DEBUG`
- 数据库：`DATABASE_URL` 或 `MYSQL_*`
- 聚合：`AGGREGATOR_*`
- 天气：`WEATHER_*`、`OPENWEATHER_*`
- AI/预测：`PREDICTION_*`、`OPENAI_*`
- MQTT/设备：`MQTT_*`、`DEVICE_*`
- 其他：`FILE_FORWARD_URL`、`HEARTBEAT_*`

### `agent_new`

- 数据库：`MYSQL_*`
- LLM：`OPENAI_*`
- 专家服务：`EXPERT_*`
- 设备专家：`DEVICE_EXPERT_*`
- 喂食机：`AIJ_FEEDER_*`
- 联网搜索：`SERPER_*`、`ENABLE_WEB_SEARCH`

## 重要提醒

1. 仓库内同时存在 `agent/` 和 `agent_new/`，交接前必须确认生产到底跑哪一套。
2. `backend/README.md`、`agent/README.md`、部分 `docs/` 文档仍带有旧结构或旧路径描述，只能作为历史参考。
3. `.env.example` 和 README 中的示例配置不一定等于代码真实读取项，最终应以 `backend/config/settings.py`、`agent_new/config.py`、`agent/config.py` 为准。

## 建议优先阅读

- `backend/main.py`
- `backend/app_factory.py`
- `backend/config/settings.py`
- `agent_new/server.py`
- `agent_new/api/app.py`
- `agent_new/config.py`
- `agent/README.md`
- `backend/README.md`
