# 环境配置文件说明

## .env 文件位置

`.env` 文件应该放在 `backend/` 目录下。

## 文件格式

`.env` 文件使用标准的 KEY=VALUE 格式：

```bash
# 注释以 # 开头
MYSQL_HOST=localhost
MYSQL_PASSWORD="密码可以加引号"
OPENAI_API_KEY=sk-xxx
```

## 配置项说明

### 必需配置

- `MYSQL_HOST`: MySQL 服务器地址
- `MYSQL_PORT`: MySQL 端口（默认 3306）
- `MYSQL_USER`: MySQL 用户名
- `MYSQL_PASSWORD`: MySQL 密码
- `MYSQL_DATABASE`: 数据库名称（建议使用 `aquaculture`）

### 可选配置

- `OPENAI_API_KEY`: OpenAI API 密钥（如果启用 AI 分析功能）
- `OPENAI_MODEL`: 使用的模型（默认 `gpt-4o-mini`）
- `HOST`: 服务监听地址（默认 `0.0.0.0`）
- `PORT`: HTTP 服务端口（默认 `8000`）
- `DEBUG`: 调试模式（`true`/`false`，默认 `false`）

## 工具脚本

### 1. 创建新的 .env 文件

```bash
cd /srv/japan-aquaculture-project/backend
python3 create_env.py
```

### 2. 从现有配置转换

```bash
cd /srv/japan-aquaculture-project/backend
python3 convert_env.py
```

这个脚本会：
- 自动查找现有的 .env 文件
- 从 `DATABASE_URL` 解析数据库配置
- 提取 `OPENAI_API_KEY` 等有用配置
- 创建格式正确的新 .env 文件

### 3. 验证 .env 文件格式

```bash
cd /srv/japan-aquaculture-project/backend
python3 create_env.py --validate
```

## 配置加载顺序

1. **系统环境变量**（优先级最高）
2. **backend/.env 文件**
3. **项目根目录/.env 文件**
4. **代码中的默认值**（优先级最低）

## 注意事项

1. **不要提交 .env 到版本控制**
   - `.env` 文件包含敏感信息（密码、API 密钥）
   - 已添加到 `.gitignore`

2. **数据库名称**
   - 如果使用现有的 `cognitive` 数据库，保持 `MYSQL_DATABASE=cognitive`
   - 如果使用新的 `aquaculture` 数据库，设置为 `MYSQL_DATABASE=aquaculture`

3. **格式要求**
   - 键名必须与配置类中的字段名完全匹配（区分大小写）
   - 值可以加引号，也可以不加
   - 等号前后可以有空格，但建议不加

4. **布尔值**
   - `DEBUG` 和 `ENABLE_AI_ANALYSIS` 使用 `true`/`false`（小写）

## 示例

### 最小配置

```bash
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture
```

### 完整配置

```bash
# 数据库配置
MYSQL_HOST=rm-xxx.mysql.japan.rds.aliyuncs.com
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aquaculture

# OpenAI 配置
OPENAI_API_KEY=sk-proj-xxx
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

## 故障排查

### 问题：配置加载失败

**解决方案**：
1. 检查 `.env` 文件格式是否正确
2. 运行验证脚本：`python3 create_env.py --validate`
3. 检查键名是否与配置类字段名匹配

### 问题：数据库连接失败

**解决方案**：
1. 检查 `MYSQL_HOST`、`MYSQL_PORT` 是否正确
2. 检查 `MYSQL_USER`、`MYSQL_PASSWORD` 是否正确
3. 检查 `MYSQL_DATABASE` 是否存在
4. 测试数据库连接：`mysql -h $MYSQL_HOST -u $MYSQL_USER -p`

### 问题：OpenAI API 调用失败

**解决方案**：
1. 检查 `OPENAI_API_KEY` 是否设置
2. 检查 API 密钥是否有效
3. 检查网络连接

