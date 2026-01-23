# 环境配置说明

## .env 配置模板

创建 `.env` 文件并填写以下配置：

```bash
# ============================================
# 日本陆上养殖数据处理系统 - 环境配置
# ============================================

# ========== 数据库配置 ==========
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# ========== OpenAI/LLM 配置 ==========
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=anthropic/claude-sonnet-4.5
OPENAI_TEMPERATURE=0.7
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# ========== 服务配置 ==========
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ========== 日志配置 ==========
LOG_LEVEL=INFO

# ========== 外部专家服务配置 ==========
# 日本养殖专家 API
EXPERT_API_BASE_URL=http://localhost:5003
EXPERT_API_KEY=
EXPERT_API_TIMEOUT=60
ENABLE_EXPERT_CONSULTATION=true

# ========== 外部设备控制专家服务配置 ==========
# DeviceAgent 服务
DEVICE_EXPERT_API_BASE_URL=http://localhost:5004
DEVICE_EXPERT_API_TIMEOUT=60
ENABLE_DEVICE_EXPERT=true
```

## 配置说明

### 必填配置

| 配置项 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI/OpenRouter API 密钥 |
| `MYSQL_*` | 数据库连接配置 |

### 可选配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_MODEL` | `anthropic/claude-sonnet-4.5` | 使用的 LLM 模型 |
| `PORT` | `8000` | 服务端口 |
| `DEBUG` | `false` | 调试模式 |
| `ENABLE_EXPERT_CONSULTATION` | `true` | 是否启用专家咨询 |
| `ENABLE_DEVICE_EXPERT` | `true` | 是否启用设备控制 |

## 启动服务

```bash
cd agent_new
python server.py
```

或使用 uvicorn：

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

