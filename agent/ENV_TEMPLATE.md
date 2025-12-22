# 环境配置文件说明

## .env 文件格式

`.env` 文件应该放在 `backend/` 目录下，格式如下：

```bash
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
WS_PORT=8001
DEBUG=false

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=

# 工作流配置
MAX_RETRY_COUNT=3
ENABLE_AI_ANALYSIS=true
```

## 配置说明

### 数据库配置
- `MYSQL_HOST`: MySQL 服务器地址
- `MYSQL_PORT`: MySQL 端口（默认 3306）
- `MYSQL_USER`: MySQL 用户名
- `MYSQL_PASSWORD`: MySQL 密码
- `MYSQL_DATABASE`: 数据库名称

### OpenAI 配置
- `OPENAI_API_KEY`: OpenAI API 密钥（必需，如果启用 AI 分析）
- `OPENAI_MODEL`: 使用的模型名称（默认 gpt-4o-mini）
- `OPENAI_TEMPERATURE`: 模型温度参数（0.0-2.0，默认 0.7）

### 服务配置
- `HOST`: 服务监听地址（默认 0.0.0.0）
- `PORT`: HTTP 服务端口（默认 8000）
- `WS_PORT`: WebSocket 服务端口（默认 8001）
- `DEBUG`: 调试模式（true/false，默认 false）

### 日志配置
- `LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL，默认 INFO）
- `LOG_FILE`: 日志文件路径（留空则输出到控制台）

### 工作流配置
- `MAX_RETRY_COUNT`: 最大重试次数（默认 3）
- `ENABLE_AI_ANALYSIS`: 是否启用 AI 分析（true/false，默认 true）

## 格式要求

1. **键值对格式**: `KEY=VALUE`，等号两边可以有空格，但建议不加
2. **注释**: 以 `#` 开头的行为注释，会被忽略
3. **空行**: 空行会被忽略
4. **引号**: 值可以加引号，也可以不加（会自动去除首尾引号）
5. **大小写**: 键名区分大小写，必须与配置类中的字段名完全匹配

## 示例

### 正确的格式
```bash
MYSQL_HOST=localhost
MYSQL_PASSWORD="my password"
OPENAI_API_KEY=sk-1234567890abcdef
DEBUG=false
```

### 错误的格式
```bash
# 错误：等号前后有空格（虽然可以工作，但不推荐）
MYSQL_HOST = localhost

# 错误：键名大小写不匹配
mysql_host=localhost  # 应该是 MYSQL_HOST

# 错误：多行值（不支持）
OPENAI_API_KEY=sk-123
4567890abcdef
```

## 加载顺序

配置的加载优先级（从高到低）：
1. 系统环境变量
2. `.env` 文件中的值
3. 代码中的默认值

这意味着如果系统环境变量中已经设置了某个值，`.env` 文件中的值不会覆盖它。

## 创建 .env 文件

1. 复制模板：
```bash
cd /srv/japan-aquaculture-project/backend
cp ENV_TEMPLATE.md .env
```

2. 编辑 `.env` 文件，填入实际配置值

3. 确保文件权限正确（不应被提交到版本控制）

