# 对话功能测试指南

## 快速开始

### 1. 启动服务

```bash
cd /srv/japan-aquaculture-project/backend
./start.sh
```

或

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 测试对话功能

#### 方式一：使用测试脚本（推荐）

```bash
# 运行默认测试问题
python3 test_chat.py

# 使用自定义问题
python3 test_chat.py "查询1号池最近的水温数据"
```

#### 方式二：使用 curl

```bash
# 简单对话
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询最近的水温数据",
    "session_id": "test_001"
  }'

# 格式化输出
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "1号池的pH值是多少？"}' | python3 -m json.tool
```

#### 方式三：使用 Python 交互式测试

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "查询最近的水温数据",
        "session_id": "test_001"
    }
)

print(response.json())
```

#### 方式四：使用 API 文档界面（最方便）

1. 启动服务后，访问：`http://localhost:8000/docs`
2. 找到 `/api/v1/chat` 接口
3. 点击 "Try it out"
4. 输入问题，例如：
   ```json
   {
     "message": "查询最近的水温数据",
     "session_id": "test_001"
   }
   ```
5. 点击 "Execute" 执行

## 测试问题示例

### 基础查询

```bash
# 问候
"你好，请介绍一下你自己"

# 查询水温
"查询最近的水温数据"
"1号池的温度是多少？"

# 查询溶解氧
"查询溶解氧数据"
"最近一周的DO值是多少？"

# 查询pH值
"pH值是多少？"
"查询pH数据"
```

### 数据分析

```bash
# 趋势分析
"分析一下最近一周的水温趋势"
"溶解氧的变化趋势如何？"

# 异常检测
"最近有哪些异常数据？"
"哪些指标超出了正常范围？"
```

### 综合查询

```bash
# 多指标查询
"1号池的水质情况如何？"
"给我一个整体的数据报告"
```

## API 接口说明

### POST /api/v1/chat

**请求体**:
```json
{
  "message": "用户的问题",
  "session_id": "会话ID（可选，默认'default'）",
  "context": {
    "额外的上下文信息（可选）"
  }
}
```

**响应**:
```json
{
  "status": "success",
  "response": "AI生成的回答",
  "intent": "识别的意图",
  "route_decision": {
    "decision": "路由决策",
    "needs_data": true/false
  },
  "data_used": [
    {
      "type": "sensor_data",
      "metric": "temp",
      "readings": [...]
    }
  ],
  "session_id": "会话ID"
}
```

## 工作流程

1. **意图识别**: 系统识别用户意图（数据查询、数据分析等）
2. **路由决策**: 决定是否需要查询数据库
3. **数据查询**: 如果需要，从数据库获取相关数据
4. **AI 分析**: 使用 ThinkingAgent 分析数据并生成回答
5. **返回结果**: 返回完整的回答和相关数据

## 故障排查

### 问题 1: 连接失败

**错误**: `Connection refused` 或 `无法连接到服务器`

**解决方案**:
1. 确认服务已启动
2. 检查端口是否正确（默认 8000）
3. 检查防火墙设置

### 问题 2: OpenAI API 错误

**错误**: `OpenAI API error` 或 `Invalid API key`

**解决方案**:
1. 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
2. 确认 API 密钥有效且有额度
3. 如果不想使用 AI，可以设置 `ENABLE_AI_ANALYSIS=false`

### 问题 3: 数据库查询失败

**错误**: `Database connection error`

**解决方案**:
1. 检查数据库配置（`.env` 文件）
2. 确认数据库服务正在运行
3. 确认数据库中存在数据（可以先插入一些测试数据）

### 问题 4: 没有返回数据

**可能原因**:
- 数据库中还没有数据
- 查询条件不匹配

**解决方案**:
1. 先使用 `/api/v1/data/sensor` 接口插入一些测试数据
2. 然后再次测试对话功能

## 插入测试数据

在测试对话前，可以先插入一些测试数据：

```bash
# 插入传感器数据
curl -X POST "http://localhost:8000/api/v1/data/sensor" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "pool_id": "pool_1",
    "metric": "temp",
    "value": 25.5,
    "unit": "°C"
  }'

curl -X POST "http://localhost:8000/api/v1/data/sensor" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "pool_id": "pool_1",
    "metric": "do",
    "value": 8.5,
    "unit": "mg/L"
  }'
```

## 查看日志

服务运行时的日志会显示：
- 意图识别结果
- 路由决策
- 数据库查询
- AI 分析过程

查看日志可以帮助理解系统的工作流程。

## 下一步

测试成功后，可以：
1. 集成到前端应用
2. 添加更多数据源
3. 扩展对话能力
4. 优化 AI 回答质量

