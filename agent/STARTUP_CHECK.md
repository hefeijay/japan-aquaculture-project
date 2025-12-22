# 项目启动检查清单

## ✅ 已完成的检查

### 1. 模块导入测试
- ✓ config 模块
- ✓ database 模块
- ✓ state 模块
- ✓ models 模块（所有9个模型）
- ✓ agents 模块（IntentAgent, RoutingAgent, ThinkingAgent）
- ✓ handlers 模块（SensorHandler, ImageHandler, FeederHandler）
- ✓ graph 模块（AquacultureOrchestrator）
- ✓ main 模块（FastAPI 应用）

### 2. 依赖包检查
- ✓ fastapi
- ✓ uvicorn
- ✓ langgraph
- ✓ langchain
- ✓ langchain_openai
- ✓ sqlalchemy
- ✓ pymysql
- ✓ pydantic
- ✓ pydantic_settings

### 3. 配置检查
- ✓ .env 文件已创建
- ✓ 配置可以正确加载
- ✓ 数据库连接配置正确

### 4. 核心组件测试
- ✓ AquacultureOrchestrator 可以正常创建
- ✓ FastAPI 应用可以正常初始化
- ✓ 工作流图已编译

## 🚀 启动方式

### 方式一：使用启动脚本（推荐）

```bash
cd /srv/japan-aquaculture-project/backend
./start.sh
```

### 方式二：直接使用 uvicorn

```bash
cd /srv/japan-aquaculture-project/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式三：Python 模块方式

```bash
cd /srv/japan-aquaculture-project/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📋 启动前检查

在启动前，请确认：

1. **数据库连接**
   - [ ] MySQL 服务正在运行
   - [ ] 数据库 `aquaculture` 或 `cognitive` 已创建
   - [ ] `.env` 文件中的数据库配置正确

2. **OpenAI API（如果启用 AI 分析）**
   - [ ] `OPENAI_API_KEY` 已设置
   - [ ] API 密钥有效且有额度

3. **端口占用**
   - [ ] 端口 8000 未被占用
   - [ ] 端口 8001（WebSocket）未被占用

## 🔍 验证启动

启动后，访问以下 URL 验证：

- 健康检查: `http://localhost:8000/health`
- API 文档: `http://localhost:8000/docs`
- 根路径: `http://localhost:8000/`

## ⚠️ 常见问题

### 问题 1: 数据库连接失败

**错误信息**: `OperationalError: (2003, "Can't connect to MySQL server")`

**解决方案**:
1. 检查 MySQL 服务是否运行: `systemctl status mysql`
2. 检查 `.env` 中的数据库配置
3. 测试连接: `mysql -h $MYSQL_HOST -u $MYSQL_USER -p`

### 问题 2: 模块导入错误

**错误信息**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
cd /srv/japan-aquaculture-project/backend
pip install -r requirements.txt
```

### 问题 3: 端口被占用

**错误信息**: `Address already in use`

**解决方案**:
1. 查找占用进程: `lsof -i :8000`
2. 修改 `.env` 中的 `PORT` 配置
3. 或停止占用进程

## 📊 启动成功标志

看到以下信息表示启动成功：

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 🎯 下一步

启动成功后，可以：

1. 访问 API 文档: `http://localhost:8000/docs`
2. 测试 API 接口
3. 查看日志输出
4. 测试数据处理工作流

