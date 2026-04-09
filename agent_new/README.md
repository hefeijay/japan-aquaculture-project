# `agent_new` 服务

这是 `japan-aquaculture-project/agent_new` 的 README。  
当前目录是一个基于 FastAPI 的 Agent 服务，提供 REST 聊天接口、聊天历史、WebSocket 流式对话、会话初始化、专家服务/设备专家服务对接、天气查询和联网搜索能力。

## 当前确认的入口

- 启动文件：`server.py`
- 实际应用：`api.app:app`
- 默认监听：`0.0.0.0:8000`
- 根路径：`GET /`
- 健康检查：`GET /health`
- OpenAPI 文档：`GET /docs`、`GET /redoc`
- WebSocket：`WS /`、`WS /ws`

## 运行前提

### Python 与依赖

建议先创建虚拟环境，再安装依赖：

```bash
cd /home/gmm/srv/japan-aquaculture-project/agent_new
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

说明：

- 代码当前至少依赖 `fastapi`、`uvicorn`、`sqlalchemy`、`pymysql`、`openai`、`structlog`、`python-dotenv`、`pydantic-settings`。
- 联网搜索和天气服务代码实际使用了 `aiohttp`。
- 如果是全新环境，请确认依赖已完整安装后再启动。

### 数据库

服务依赖 MySQL，且当前代码假定相关表已经存在，至少包括：

- `session`
- `chat_history`

当前目录内没有看到自动建表或迁移入口，部署前应先确认数据库结构已准备完成。

### 外部服务

以下能力依赖外部服务或外部 API：

- LLM：`OPENAI_API_KEY`、`OPENAI_BASE_URL`
- 养殖专家服务：默认 `http://localhost:5003`
- 设备专家服务：默认 `http://localhost:5004`
- 联网搜索：Serper
- 天气：OpenWeatherMap

## 启动方式

```bash
cd /home/gmm/srv/japan-aquaculture-project/agent_new
python server.py
```

如需显式使用 `uvicorn`：

```bash
cd /home/gmm/srv/japan-aquaculture-project/agent_new
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

补充说明：

- `server.py` 会读取 `config.py` 中的 `HOST`、`PORT`、`DEBUG`。
- 当 `DEBUG=true` 时，`uvicorn.run(..., reload=True)` 会开启自动重载。

## HTTP 接口

### 1. 根路径

- `GET /`

返回服务基本信息和主要端点摘要。

### 2. 健康检查

- `GET /health`

返回：

```json
{"status": "healthy"}
```

### 3. 聊天接口

- `POST /api/v1/chat`

请求体：

```json
{
  "message": "今天天气适合喂食吗？",
  "session_id": "default",
  "context": {}
}
```

字段说明：

- `message`：必填，用户输入
- `session_id`：可选，默认 `"default"`
- `context`：可选，附加上下文

响应主体包含：

- `status`
- `response`
- `intent`
- `session_id`
- `metadata`

### 4. 获取聊天历史

- `GET /api/v1/chat/history`

查询参数：

- `session_id`：必填
- `limit`：可选，默认 `20`

### 5. 清空聊天历史

- `DELETE /api/v1/chat/history`

查询参数：

- `session_id`：必填

## WebSocket

### 连接地址

- `WS /`
- `WS /ws`

两者都进入同一个处理逻辑。

### 客户端常见消息类型

- `init`：初始化或加载会话
- `ping`：心跳
- `userSendMessage`：发送用户消息

如果未显式带 `type`，服务端也会把消息按用户消息处理。

### `init` 示例

```json
{
  "type": "init",
  "data": {
    "session_id": "optional-session-id",
    "user_id": "default_user"
  }
}
```

服务端会返回 `type: "init"` 的初始化结果，其中核心字段包括：

- `session_id`
- `messages`
- `config`

### 用户消息示例

```json
{
  "type": "userSendMessage",
  "data": {
    "content": "帮我分析最近一周溶氧趋势",
    "context": {}
  }
}
```

服务端常见推送类型：

- `newChatMessage`：用户消息确认
- `stream_chunk`：AI 流式输出，`data.event` 为 `start` / `content` / `end`
- `sessionNameUpdated`：首次对话后更新会话标题
- `pong`
- `error`

## 会话与数据持久化

- REST 与 WebSocket 最终都走 `core/handler.py` 的统一处理逻辑。
- 每条用户消息和助手回复都会写入 `chat_history`。
- 会话元数据写入 `session`。
- 首次 WebSocket 对话完成后，会基于首条消息更新 `session_name`。
- 如果某次 WebSocket 连接中新建了空会话，但用户没有真正发送消息，断开时会清理该空会话。

## 环境变量

以下为当前代码中实际涉及的主要配置项。

### 数据库

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

### LLM

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TEMPERATURE`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT`

### 服务监听

- `HOST`
- `PORT`
- `DEBUG`

### 日志

- `LOG_LEVEL`
- `LOG_FILE`

### 工作流

- `MAX_RETRY_COUNT`
- `ENABLE_AI_ANALYSIS`

### 养殖专家服务

- `EXPERT_API_BASE_URL`
- `EXPERT_API_KEY`
- `EXPERT_API_TIMEOUT`
- `ENABLE_EXPERT_CONSULTATION`

### 设备专家服务

- `DEVICE_EXPERT_API_BASE_URL`
- `DEVICE_EXPERT_API_TIMEOUT`
- `ENABLE_DEVICE_EXPERT`

### 联网搜索

- `SERPER_API_KEY`
- `ENABLE_WEB_SEARCH`
- `WEB_SEARCH_TIMEOUT`

### 天气

- `OPENWEATHER_API_KEY`
- `OPENWEATHER_BASE_URL`
- `WEATHER_DEFAULT_LOCATION`
- `WEATHER_LANG`
- `ENABLE_WEATHER_SERVICE`

## 当前默认配置特征

1. 默认模型是 `anthropic/claude-sonnet-4.5`。
2. 默认 `OPENAI_BASE_URL` 指向 OpenRouter。
3. 默认 HTTP 监听是 `0.0.0.0:8000`。
4. WebSocket 与 HTTP 运行在同一个 FastAPI 应用中，不使用独立的 WebSocket 服务进程。
5. 专家服务默认地址是 `http://localhost:5003`，设备专家服务默认地址是 `http://localhost:5004`。
6. 默认数据库名在代码里是 `aquaculture`；如果使用 `.env` 或 `.env.example`，会以环境变量覆盖。

## `.env` 与 `.env.example` 说明

- `config.py` 会优先尝试加载当前目录下的 `.env`。
- 如果当前目录没有 `.env`，会继续尝试加载上一级目录中的 `.env`。
- `.env.example` 中保留了 `WS_PORT=8001`，但当前代码并未使用这个变量。
- `.env.example` 主要用于示例，不应把其中的示例值直接视为运行时实际值。

## 目录说明

- `api/`：FastAPI 应用和 REST 路由
- `core/`：意图识别、查询重写、LLM 调用、主处理逻辑
- `services/`：聊天历史、会话、专家咨询、设备专家、天气、联网搜索
- `websocket/`：WebSocket 接入与流式消息处理
- `models/`：SQLAlchemy 模型
- `repositories/`：会话数据访问
- `prompts/`：提示词模板
- `config.py`：配置入口
- `database.py`：数据库连接与会话管理
- `server.py`：进程启动入口

## 已知注意事项

1. 本目录不是旧 `agent/` 的同义替代，两个目录并存。
2. 历史文档中把这里写成 LangGraph 数据处理后端、独立 `ws_server.py` 或单独 `8001` WebSocket 端口的说法，均不适用于当前代码。
3. 当前代码强依赖 MySQL 持久化；如果数据库表不存在，聊天历史和会话功能不会正常工作。
4. 如果生产环境在使用 `agent_new`，请同时核对反向代理、数据库、LLM 配置、专家服务地址、设备专家服务地址、联网搜索和天气开关。
5. `requirements.txt` 中的依赖声明和代码实际使用情况并不完全一致，部署时建议以实际导入报错和运行链路为准复核依赖。

## 建议优先阅读

- `server.py`
- `api/app.py`
- `api/routes/chat.py`
- `websocket/handler.py`
- `core/handler.py`
- `services/session_service.py`
- `config.py`
- `.env.example`
