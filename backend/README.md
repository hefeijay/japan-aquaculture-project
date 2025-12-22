# 日本陆上养殖生产管理AI助手服务端

## 项目重构说明

原始的 `app.py` 文件（506行）已经被重构为模块化架构，提高了代码的可维护性和可扩展性。

## 新的项目结构

```
japan_server/
├── __init__.py              # 包初始化文件
├── app.py                   # 简化的入口文件（向后兼容）
├── app_old.py              # 原始文件备份
├── main.py                 # 新的主入口文件
├── app_factory.py          # Flask应用工厂
├── config/                 # 配置模块
│   ├── __init__.py
│   └── settings.py         # 所有配置和常量
├── services/               # 服务模块
│   ├── __init__.py
│   └── data_generator.py   # 数据生成服务
└── routes/                 # 路由模块
    ├── __init__.py
    ├── api_routes.py       # API路由蓝图
    └── main_routes.py      # 主路由蓝图
```

## 重构优势

### 1. 模块化设计
- **配置分离**: 所有配置项集中在 `config/settings.py`
- **服务分离**: 数据生成逻辑独立为服务模块
- **路由分离**: API路由使用Flask蓝图进行组织

### 2. 代码可维护性
- **单一职责**: 每个模块负责特定功能
- **易于测试**: 模块化结构便于单元测试
- **易于扩展**: 新功能可以独立添加到相应模块

### 3. 向后兼容性
- 保留原始 `app.py` 入口点
- API端点和功能完全一致
- 无需修改客户端代码

## 启动方式

### 方式1: 使用原始入口（向后兼容）
```bash
python japan_server/app.py
```

### 方式2: 使用新的模块化入口
```bash
python -m japan_server.main
```

### 方式3: 作为包导入使用
```python
from japan_server.app_factory import create_app
app = create_app()
app.run()
```

## API端点

所有API端点保持不变：

- `GET /` - 服务信息
- `GET /api/health` - 健康检查
- `GET /api/ai/decisions/recent` - AI决策消息
- `GET /api/sensors/realtime` - 传感器实时数据
- `GET /api/devices/status` - 设备状态
- `GET /api/location/data` - 地理位置数据
- `GET /api/cameras/{id}/status` - 摄像头状态

## 配置管理

所有配置项现在集中在 `config/settings.py` 中：

- 消息类型和模板
- 传感器配置
- 设备配置
- 地理位置数据
- Flask应用配置

### 环境配置 (.env)

为与 `/usr/henry/cognitive-center/external_data_server` 保持一致，项目支持通过 `.env` 文件加载配置。优先顺序为：`DATABASE_URL` > `MYSQL_*` 分段变量 > 默认值。

在项目根目录创建 `.env`（推荐在仓库根或 `japan_server/` 目录下），示例：

```
# 基础应用
HOST=0.0.0.0
PORT=5002
DEBUG=false

# 完整数据库URI（若设置，将覆盖下方分段变量）
# DATABASE_URL=mysql+pymysql://root:Root155017@rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com:3306/cognitive

# 分段数据库变量（将自动拼接为URI）
MYSQL_HOST=rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=Root155017
MYSQL_DATABASE=cognitive
```

说明：
- 如果使用 `python-dotenv`，会在模块导入阶段自动读取 `.env`；如果未安装，也有内置回退解析，不影响运行。
- `.env` 位于 `japan_server/` 目录或仓库根均可；若两处都存在，优先读取 `japan_server/.env`。
- 运行命令保持不变：`python -m japan_server.main`。

## 开发建议

1. **添加新API**: 在 `routes/` 目录下创建新的蓝图文件
2. **修改配置**: 编辑 `config/settings.py` 文件
3. **添加服务**: 在 `services/` 目录下创建新的服务模块
4. **测试**: 每个模块都可以独立进行单元测试

## 性能优化

重构后的代码具有以下性能优势：

- **更快的启动时间**: 模块按需加载
- **更好的内存管理**: 功能分离减少内存占用
- **更高的并发性**: 蓝图支持更好的请求处理

## 维护说明

- `app_old.py`: 原始文件备份，可在需要时参考
- 所有新功能应该添加到相应的模块中
- 配置修改应该在 `config/settings.py` 中进行
- 保持向后兼容性，避免破坏现有API