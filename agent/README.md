# 日本陆上养殖数据处理系统 - LangGraph 后端

基于 LangGraph 框架实现的养殖数据处理工作流系统，参考了 `singa_one_server`、`cognitive_model` 和 `db_models` 三个项目的架构设计。

## 项目架构

本项目参考了以下三个项目的设计模式：

1. **singa_one_server**: WebSocket 服务器架构、服务层和仓库层设计
2. **cognitive_model**: Orchestrator 协调器模式、Agent 智能体设计、Handler 处理器模式
3. **db_models**: 数据库模型定义和会话管理

## 核心设计

### LangGraph 状态图工作流

使用 LangGraph 构建了完整的数据处理工作流，包含以下节点：

1. **intent_recognition**: 意图识别节点（参考 IntentAgent）
2. **data_validation**: 数据验证节点
3. **data_cleaning**: 数据清洗节点
4. **database_save**: 数据库存储节点
5. **ai_analysis**: AI 分析节点（参考 ThinkingAgent）
6. **response_generation**: 响应生成节点
7. **error_handling**: 错误处理节点

### 项目结构

```
backend/
├── main.py              # FastAPI 主应用
├── ws_server.py         # WebSocket 服务器（参考 singa_one_server）
├── config.py            # 配置管理
├── database.py          # 数据库连接
├── state.py             # LangGraph 状态定义
├── graph.py             # LangGraph 状态图定义
├── models/              # 数据库模型（参考 db_models）
│   ├── base.py
│   ├── batch.py
│   ├── device.py
│   ├── sensor_reading.py
│   └── ...
├── agents/              # AI 智能体（参考 cognitive_model/agents）
│   ├── intent_agent.py
│   ├── routing_agent.py
│   └── thinking_agent.py
├── handlers/            # 数据处理器（参考 cognitive_model/handlers）
│   ├── base_handler.py
│   ├── sensor_handler.py
│   ├── image_handler.py
│   └── ...
├── repositories/        # 数据仓库层（参考 singa_one_server/repositories）
│   ├── batch_repository.py
│   ├── sensor_repository.py
│   └── ...
└── services/           # 业务服务层（参考 singa_one_server/services）
    ├── data_service.py
    └── ...
```

## 快速开始

### 1. 安装依赖

```bash
cd /srv/japan-aquaculture-project/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# 服务配置
HOST=0.0.0.0
PORT=8000
WS_PORT=8001
DEBUG=false
```

### 3. 启动服务

```bash
# 启动 FastAPI 服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 启动 WebSocket 服务（另一个终端）
python ws_server.py
```

## API 接口

### REST API (FastAPI)

- `GET /health`: 健康检查
- `POST /api/v1/data/sensor`: 处理传感器数据
- `POST /api/v1/data/feeder`: 处理喂食机数据
- `POST /api/v1/data/image`: 处理图像数据
- `GET /api/v1/sensor/readings`: 查询传感器读数

### WebSocket API

- `ws://localhost:8001`: WebSocket 连接
- 支持实时数据流处理

## 工作流说明

LangGraph 工作流参考了 `cognitive_model/orchestrator.py` 的设计：

1. **意图识别**: 使用 IntentAgent 识别用户意图
2. **路由决策**: 根据意图选择处理路径
3. **数据处理**: 验证、清洗、存储
4. **AI 分析**: 使用 ThinkingAgent 进行智能分析
5. **响应生成**: 生成最终响应

## 开发说明

### 添加新的数据类型

1. 在 `models/` 中添加数据库模型
2. 在 `repositories/` 中添加数据仓库
3. 在 `handlers/` 中添加处理器
4. 在 `graph.py` 中更新工作流

### 添加新的 Agent

参考 `cognitive_model/agents/` 的设计，创建新的 Agent 类。

## 许可证

本项目由 AI 产业部所有。
