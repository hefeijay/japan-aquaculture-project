# 日本陆上养殖数据处理系统

## 项目简介

本项目是一个完整的日本陆上工厂化养殖南美白对虾数据采集、处理、质量管理和 AI 智能分析系统。系统采用微服务架构，包含数据收集服务、AI 智能代理服务和数据处理工作流。

**版本：** v2.0  
**最后更新：** 2025.12.11  
**负责人/单位：** AI产业部

## 项目架构

本项目采用模块化微服务架构，包含以下核心服务：

### 1. **Agent 服务** (`agent/`)
基于 LangGraph 的 AI 智能代理服务，提供智能对话、数据处理和 AI 分析功能。

- **技术栈**: FastAPI + LangGraph + LangChain + WebSocket
- **端口**: 8000 (HTTP + WebSocket)
- **核心功能**:
  - 智能对话系统（支持流式响应）
  - 意图识别和路由决策
  - 专家咨询服务集成
  - 数据处理工作流（传感器、图像、喂食机数据）
  - 聊天历史管理
  - 会话管理

### 2. **Backend 服务** (`backend/`)
Flask 后端服务，提供数据收集、存储和查询 API。

- **技术栈**: Flask + SQLAlchemy
- **端口**: 5002
- **核心功能**:
  - 传感器数据接收和存储
  - 喂食机数据管理
  - 图像数据采集
  - 设备状态监控
  - AI 决策记录
  - 数据聚合服务
  - 文件上传服务

### 3. **数据库和脚本** (根目录)
数据库结构定义、初始化脚本和工具脚本。

## 项目结构

```
japan-aquaculture-project/
├── README.md                    # 项目主文档（本文件）
├── QUICK_START.md              # 快速开始指南
├── GITLAB_SETUP.md             # GitLab 同步配置指南
│
├── agent/                      # AI 智能代理服务
│   ├── README.md               # Agent 服务文档
│   ├── main.py                 # FastAPI 主应用
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── graph.py                # LangGraph 工作流定义
│   ├── state.py                # 状态定义
│   ├── start.sh                # 启动脚本
│   ├── requirements.txt        # Python 依赖
│   ├── .env                    # 环境配置（不提交到 Git）
│   │
│   ├── agents/                 # AI 智能体
│   │   ├── intent_agent.py     # 意图识别
│   │   ├── routing_agent.py    # 路由决策
│   │   ├── thinking_agent.py   # AI 思考分析
│   │   ├── chat_agent.py       # 基础对话
│   │   ├── query_rewriter.py   # 查询重写
│   │   └── llm_utils.py        # LLM 工具函数
│   │
│   ├── handlers/               # 数据处理器
│   │   ├── base_handler.py
│   │   ├── sensor_handler.py   # 传感器数据处理
│   │   ├── image_handler.py    # 图像数据处理
│   │   └── feeder_handler.py  # 喂食机数据处理
│   │
│   ├── models/                 # 数据库模型
│   │   ├── sensor_reading.py
│   │   ├── batch.py
│   │   ├── device.py
│   │   ├── chat_history.py
│   │   └── ...
│   │
│   ├── services/               # 业务服务层
│   │   ├── chat_history_service.py
│   │   ├── expert_consultation_service.py
│   │   └── session_service.py
│   │
│   ├── repositories/           # 数据仓库层
│   │   └── session_repository.py
│   │
│   ├── core/                   # 核心常量
│   │   └── constants.py
│   │
│   └── doc/                    # Agent 服务文档
│       ├── CHAT_FLOW.md        # 聊天流程说明
│       ├── WEBSOCKET_GUIDE.md  # WebSocket 使用指南
│       └── ...
│
├── backend/                    # Flask 后端服务
│   ├── README.md               # Backend 服务文档
│   ├── main.py                 # Flask 主入口
│   ├── app.py                  # 应用入口（向后兼容）
│   ├── app_factory.py          # Flask 应用工厂
│   │
│   ├── config/                 # 配置模块
│   │   └── settings.py         # 所有配置和常量
│   │
│   ├── routes/                 # 路由模块
│   │   ├── api_routes.py       # API 路由
│   │   ├── data_collection_routes.py  # 数据收集路由
│   │   ├── ai_decision_routes.py      # AI 决策路由
│   │   ├── file_upload_routes.py      # 文件上传路由
│   │   └── message_queue_routes.py    # 消息队列路由
│   │
│   ├── services/               # 服务模块
│   │   ├── aggregator_service.py     # 数据聚合服务
│   │   ├── sensor_service.py          # 传感器服务
│   │   ├── camera_service.py           # 摄像头服务
│   │   ├── ai_decision_service.py     # AI 决策服务
│   │   └── ...
│   │
│   ├── db_models/              # 数据库模型
│   │   ├── sensor_reading.py
│   │   ├── batch.py
│   │   ├── device.py
│   │   └── ...
│   │
│   ├── api_docs/               # API 文档
│   │   ├── openapi.yaml        # OpenAPI 规范
│   │   └── README.md
│   │
│   └── scripts/                # 工具脚本
│       └── ...
│
├── schema/                     # 数据库结构定义
│   ├── mysql_aquaculture_ddl.sql      # 完整 DDL
│   ├── 01_create_new_tables.sql       # 创建新表
│   ├── 02_alter_existing_tables.sql   # 扩展表结构
│   └── 03_data_migration_guide.sql     # 数据迁移指南
│
├── scripts/                    # 项目级脚本
│   ├── init_database.sh        # 数据库初始化
│   ├── apply_schema_changes.sh # 应用数据库变更
│   ├── validate_schema.sh      # 验证数据库结构
│   └── execute_sql_via_mcp.py # SQL 执行工具
│
├── docs/                       # 项目文档
│   ├── 01-数据源清单.md
│   ├── 02-数据收集方式.md
│   ├── 03-数据处理标准.md
│   ├── 04-数据验收流程.md
│   └── 数据库表结构对比分析.md
│
├── config/                     # 配置文件
│   └── database.conf.example   # 数据库配置示例
│
├── data/                       # 数据目录
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后的数据
│   └── annotations/            # 标注数据
│
└── logs/                       # 日志目录
```

## 快速开始

### 前置要求

- Python 3.8+
- MySQL 8.0+
- Git

### 1. 克隆项目

```bash
git clone https://github.com/1shadow1/japan-aquaculture-project.git
cd japan-aquaculture-project
```

### 2. 数据库初始化

```bash
# 使用自动化脚本（推荐）
./scripts/init_database.sh

# 或手动执行
mysql -u root -p < schema/mysql_aquaculture_ddl.sql
```

### 3. 配置 Agent 服务

```bash
cd agent

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件
cat > .env << EOF
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 专家服务配置（可选）
EXPERT_API_BASE_URL=http://localhost:5003
ENABLE_EXPERT_CONSULTATION=true
EOF

# 启动服务
bash start.sh
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 配置 Backend 服务

```bash
cd backend

# 安装依赖（如果使用虚拟环境）
pip install flask flask-sqlalchemy pymysql python-dotenv

# 创建 .env 文件
cat > .env << EOF
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# 服务配置
HOST=0.0.0.0
PORT=5002
DEBUG=false
EOF

# 启动服务
python main.py
# 或
python -m japan_server.main
```

### 5. 验证服务

- **Agent 服务**: http://localhost:8000/docs (FastAPI 文档)
- **Backend 服务**: http://localhost:5002/api/health

## 核心功能

### Agent 服务功能

#### 1. 智能对话系统
- 支持 WebSocket 实时对话
- 流式响应输出
- 聊天历史管理
- 会话持久化

#### 2. AI 工作流
- **意图识别**: 自动识别用户意图（数据查询、闲聊、设备控制等）
- **路由决策**: 智能路由到专家服务或本地处理
- **查询重写**: 优化用户查询，提高准确性
- **专家咨询**: 集成外部专家服务，提供专业分析

#### 3. 数据处理
- 传感器数据验证和存储
- 图像数据检测和分析
- 喂食机数据记录

#### 4. API 接口
- `POST /api/v1/data/sensor` - 传感器数据处理
- `POST /api/v1/data/feeder` - 喂食机数据处理
- `POST /api/v1/data/image` - 图像数据处理
- `GET /api/v1/sensor/readings` - 查询传感器读数
- `WebSocket /ws` - 实时对话接口

### Backend 服务功能

#### 1. 数据收集接口
- `POST /api/data/sensors` - 接收传感器数据
- `POST /api/data/feeders` - 接收喂食机数据
- `POST /api/data/operations` - 接收操作日志
- `POST /api/data/cameras` - 接收摄像头图像

#### 2. 数据查询接口
- `GET /api/sensors/realtime` - 实时传感器数据
- `GET /api/devices/status` - 设备状态
- `GET /api/ai/decisions/recent` - AI 决策记录
- `GET /api/location/data` - 地理位置数据

#### 3. 文件上传
- `POST /api/upload` - 单文件上传
- `POST /api/upload/multiple` - 多文件上传

#### 4. 数据聚合
- 后台周期聚合服务
- 数据清洗和验证
- 异常检测

## 数据源

### 传感器数据
- 水温、浊度、pH、溶解氧
- 水位、盐度、氨氮、亚硝酸盐
- 光照强度、室内温湿度

### 图像数据
- 检测数量、长度、高度
- 预估体重、饲料/虾皮存在标记

### 喂食机数据
- 喂食时间、喂食量、喂食次数
- 剩余饵料估计

### 操作日志
- 人工操作记录
- 设备维护记录

## 数据库设计

核心数据表：

- `batches` - 批次信息
- `devices` - 设备清单
- `sensor_readings` - 传感器读数（窄表设计）
- `feeders_logs` - 喂食机记录
- `image_frames` - 图像帧与元数据
- `image_detections` - 图像检测汇总结果
- `operations_logs` - 操作日志
- `manuals_docs` - 养殖手册文档
- `history_records` - 往期养殖记录
- `chat_history` - 聊天历史记录
- `sessions` - 用户会话

详细表结构请参考：`schema/mysql_aquaculture_ddl.sql`

## 环境配置

### Agent 服务环境变量

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 专家服务配置
EXPERT_API_BASE_URL=http://localhost:5003
EXPERT_API_KEY=optional_api_key
EXPERT_API_TIMEOUT=60
ENABLE_EXPERT_CONSULTATION=true
```

### Backend 服务环境变量

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# 服务配置
HOST=0.0.0.0
PORT=5002
DEBUG=false
```

**注意**: `.env` 文件包含敏感信息，已添加到 `.gitignore`，不会提交到版本控制。

## 开发指南

### 添加新的数据类型

#### Agent 服务
1. 在 `agent/models/` 中添加数据库模型
2. 在 `agent/handlers/` 中添加处理器
3. 在 `agent/graph.py` 中更新工作流

#### Backend 服务
1. 在 `backend/db_models/` 中添加数据库模型
2. 在 `backend/routes/` 中添加路由
3. 在 `backend/services/` 中添加服务逻辑

### 添加新的 Agent

参考 `agent/agents/` 目录下的现有 Agent，创建新的智能体类。

### 数据库迁移

```bash
# 应用数据库变更
./scripts/apply_schema_changes.sh

# 验证数据库结构
./scripts/validate_schema.sh
```

## API 文档

### Agent 服务
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Backend 服务
- API 文档: `backend/api_docs/openapi.yaml`
- 健康检查: http://localhost:5002/api/health

## 相关文档

### 项目文档
- [快速开始指南](QUICK_START.md)
- [GitLab 同步配置](GITLAB_SETUP.md)

### Agent 服务文档
- [Agent 服务 README](agent/README.md)
- [聊天流程说明](agent/doc/CHAT_FLOW.md)
- [WebSocket 使用指南](agent/doc/WEBSOCKET_GUIDE.md)
- [环境配置说明](agent/doc/README_ENV.md)

### Backend 服务文档
- [Backend 服务 README](backend/README.md)
- [API 文档](backend/api_docs/README.md)

### 数据处理文档
- [数据源清单](docs/01-数据源清单.md)
- [数据收集方式](docs/02-数据收集方式.md)
- [数据处理标准](docs/03-数据处理标准.md)
- [数据验收流程](docs/04-数据验收流程.md)
- [数据库表结构对比分析](docs/数据库表结构对比分析.md)

## 技术栈

### Agent 服务
- **Web 框架**: FastAPI
- **AI 框架**: LangGraph, LangChain
- **LLM**: OpenAI GPT-4
- **数据库**: SQLAlchemy + PyMySQL
- **实时通信**: WebSocket
- **日志**: structlog

### Backend 服务
- **Web 框架**: Flask
- **数据库**: SQLAlchemy + PyMySQL
- **配置管理**: python-dotenv

### 数据库
- **数据库**: MySQL 8.0+
- **字符集**: utf8mb4
- **引擎**: InnoDB
- **时间精度**: DATETIME(3)（毫秒级）

## 部署说明

### 生产环境部署

1. **使用进程管理器**（推荐使用 systemd 或 supervisor）

```bash
# systemd 服务示例
[Unit]
Description=Japan Aquaculture Agent Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/srv/japan-aquaculture-project/agent
Environment="PATH=/srv/japan-aquaculture-project/agent/.venv/bin"
ExecStart=/srv/japan-aquaculture-project/agent/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **使用反向代理**（Nginx）

```nginx
# Agent 服务
location /api/ {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Backend 服务
location /backend/ {
    proxy_pass http://localhost:5002;
}
```

3. **环境变量管理**
   - 使用环境变量或密钥管理服务
   - 不要将 `.env` 文件提交到版本控制

## 故障排查

### Agent 服务无法启动
1. 检查 Python 版本（需要 3.8+）
2. 检查依赖是否安装完整
3. 检查 `.env` 文件配置
4. 检查数据库连接

### Backend 服务无法启动
1. 检查 Flask 和依赖是否安装
2. 检查数据库连接
3. 检查端口是否被占用

### 数据库连接问题
1. 检查 MySQL 服务是否运行
2. 检查数据库用户权限
3. 检查网络连接
4. 验证 `.env` 中的数据库配置

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目由 AI 产业部所有。

## 联系方式

如有问题或建议，请联系项目负责人。

---

**最后更新：** 2025.12.11
