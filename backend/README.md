# Backend 服务

这是 `japan-aquaculture-project/backend` 的目录级 README。  
当前目录是实际运行中的 Flask 后端；如历史文档、旧 README 与代码不一致，请优先以入口文件、蓝图注册和配置文件为准。

## 当前已确认入口

- 主入口：`main.py`
- 兼容入口：`app.py`
- 应用工厂：`app_factory.py`
- 默认监听：`0.0.0.0:5002`
- 附加监听：心跳监控 WebSocket 端口由 `HEARTBEAT_WS_PORT` 控制
- 核心配置：`config/settings.py`

## 目录说明

- `config/`：运行配置与环境变量读取逻辑。
- `routes/`：Flask 蓝图，按业务拆分接口。
- `services/`：业务服务、后台线程和外部系统集成。
- `db_models/`：SQLAlchemy ORM 模型与数据库实例汇总。
- `api_docs/`：接口相关文档、OpenAPI 文件和导入说明。
- `scripts/`：数据修复、迁移和排查脚本。
- `utils/`：认证、钉钉通知等通用辅助逻辑。

## 快速启动

### 1. 安装依赖

```bash
cd /home/gmm/srv/japan-aquaculture-project
uv sync
```

补充说明：

- 当前项目的 Python 依赖统一定义在仓库根目录 `pyproject.toml`。
- Backend 代码还会使用 `paho-mqtt` 与 MQTT Broker 通信；如果运行环境没有该依赖，需要额外安装后再启用 MQTT 相关能力。

### 2. 初始化数据库

```bash
cd /home/gmm/srv/japan-aquaculture-project
uv run python scripts/init_database.py
```

说明：

- `scripts/init_database.py` 会创建 Flask 应用上下文并执行 `db.create_all()`。
- 除了初始化脚本，`main.py` 启动时还会调用 `WorkTaskService.ensure_tables()`，用于确保任务管理表存在。

### 3. 启动 Backend

```bash
cd /home/gmm/srv/japan-aquaculture-project/backend
uv run python main.py
```

也可以使用兼容入口：

```bash
cd /home/gmm/srv/japan-aquaculture-project/backend
uv run python app.py
```

## 运行特性

- `main.py` 在创建 Flask 应用后，会继续按配置启动周期聚合、天气缓存、心跳监控、MQTT 和设备连接监控等后台能力。
- `app_factory.py` 在应用初始化过程中还会注册蓝图，并尝试初始化预警调度器。
- 调试或排障时，不能只看 Flask 主进程是否存活，还要结合相关后台线程、独立监听端口和依赖服务一起判断。
- `app.py` 目前只是兼容入口，实际启动逻辑集中在 `main.py` 和 `app_factory.py`。

## 网络监听说明

- HTTP 服务默认监听 `HOST:PORT`，代码默认值为 `0.0.0.0:5002`。
- 除 Flask HTTP 服务外，`main.py` 还会启动一个独立的心跳监控 WebSocket 服务。
- 心跳监控端口来自 `HEARTBEAT_WS_PORT`。
- 如果不设置环境变量，代码中的默认值是 `8001`。
- `.env.example` 里的示例值也与当前代码默认值一致，都是 `8001`。

## 接口文档说明

- 本 README 不重复罗列全部接口，避免与专门接口文档重复维护后产生偏差。
- 接口说明请统一查看专门接口文档，以及当前目录下的 `api_docs/`。
- 当文档与代码不一致时，应以 `routes/` 下蓝图实现和 `app_factory.py` 中实际注册结果为准。

可优先查看：

- `api_docs/README.md`
- `api_docs/openapi.yaml`
- `api_docs/import_guide.md`

## 环境变量范围

- 服务：`HOST`、`PORT`、`DEBUG`
- 认证：`ENABLE_AUTH`、`JWT_SECRET_KEY`
- 数据库：`DATABASE_URL` 或 `MYSQL_*`
- 聚合：`AGGREGATOR_*`
- 天气：`WEATHER_*`，以及兼容读取的 `OPENWEATHER_API_KEY`
- AI/预测：`PREDICTION_*`、`OPENAI_*`
- 预警调度：`ALERT_*`
- 设备与监控：`MQTT_*`、`DEVICE_*`、`HEARTBEAT_*`
- 实时推送：`SSE_*`
- 告警通知：`DINGTALK_ACCESS_TOKEN`、`DINGTALK_SECRET`
- 其他：`FILE_FORWARD_URL`、`LOCAL_TIMEZONE_OFFSET`

配置补充：

- `config/settings.py` 会优先尝试加载 `backend/.env`。
- 如果 `WEATHER_API_KEY` 未设置，天气逻辑会回退读取 `OPENWEATHER_API_KEY`。
- 生产环境建议显式设置 `DEBUG=false`，因为代码默认是开启调试模式。

最终请以 `config/settings.py` 为准。

## 重要提醒

1. 老文档中出现的 `japan_server`、`python -m japan_server.main`、`/srv/japan_server` 等说法已不适用于当前目录。
2. `config/settings.py` 中 `ENDPOINTS` 的部分值仍保留旧写法，不能把它当作完整且最新的接口清单使用。
3. `api_docs/` 中已有文档主要用于接口说明和导入；如果后续专门接口文档已单独维护，应优先遵循专门接口文档的统一口径。
4. 部署或排障时，不要只关注 `5002` 端口；还要同时核对独立心跳 WebSocket 端口、MQTT Broker、数据库和预警调度是否正常。
5. `uv sync` 能覆盖大部分依赖，但 MQTT 功能仍要额外确认 `paho-mqtt` 是否已经安装。
6. 认证、天气、钉钉告警、MQTT 和设备监控都有各自的环境变量开关或依赖条件，功能异常时应优先从配置和外部依赖联调排查。

## 建议优先阅读

- `main.py`
- `app_factory.py`
- `config/settings.py`
- `routes/main_routes.py`
- `routes/api_routes.py`
- `services/heartbeat_ws_service.py`
- `services/mqtt_service.py`
- `services/device_monitor_service.py`
- `scripts/init_database.py`
- `.env.example`