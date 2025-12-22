# 专家API更新说明

## 更新内容

根据参考文件 `/usr/henry/cognitive-center/cognitive_model/tools/tools.json`，已更新专家咨询服务以支持SSE流式API。

## API配置

### 端点信息

- **URL**: `{EXPERT_API_BASE_URL}/sse/stream_qa`（默认: `http://localhost:5003/sse/stream_qa`）
- **Method**: `GET`（不是POST）
- **响应类型**: SSE (Server-Sent Events) 流式响应
- **Content-Type**: `text/event-stream`

### 请求参数

使用GET请求的查询参数：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 向专家提出的具体问题（重写后的问题） |
| `agent_type` | string | 是 | 专家类型，固定为 `"japan"` |
| `session_id` | string | 是 | 当前会话的ID |
| `config` | string | 否 | LLM配置的JSON字符串（可选） |

### 请求示例

```bash
GET http://localhost:5003/sse/stream_qa?query=查询当前养殖池的pH值数据&agent_type=japan&session_id=session_123&config={"model":"gpt-4o-mini","temperature":0.7}
```

### 响应格式

SSE流式响应，格式为：

```
data: {"content": "答案片段1"}
data: {"content": "答案片段2"}
data: {"done": true}
```

或：

```
data: 答案文本
event: message
```

## 配置说明

### 默认配置

```python
EXPERT_API_BASE_URL=http://localhost:5003  # 默认地址
EXPERT_API_TIMEOUT=60  # SSE流式响应需要更长时间
```

### 环境变量

在 `.env` 文件中可以覆盖：

```bash
# 专家API基础地址（默认: http://localhost:5003）
EXPERT_API_BASE_URL=http://localhost:5003

# 专家API密钥（可选）
EXPERT_API_KEY=your_api_key_here

# 超时时间（秒，默认60，SSE流式响应需要更长时间）
EXPERT_API_TIMEOUT=60

# 是否启用专家咨询（默认true）
ENABLE_EXPERT_CONSULTATION=true
```

## 实现细节

### 1. SSE流式响应处理

```python
async with client.stream("GET", url, params=params) as response:
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            # 收集答案片段
            answer_parts.append(data.get("content", ""))
```

### 2. 参数构建

- `query`: 重写后的问题
- `agent_type`: 固定为 `"japan"`
- `session_id`: 从请求中获取
- `config`: LLM配置（模型、温度等）

### 3. 错误处理

- **超时**: SSE流式响应可能需要较长时间，默认超时60秒
- **HTTP错误**: 记录状态码和错误信息
- **解析错误**: 如果SSE格式不正确，尝试直接读取文本

## 与参考实现的一致性

参考文件配置：
```json
{
  "name": "japan_aquaculture_expert",
  "type": "external_api",
  "mode": "async",
  "location": {
    "url": "http://localhost:5003/sse/stream_qa",
    "method": "GET",
    "stream_api": true
  },
  "schema": {
    "properties": {
      "query": {"type": "string"},
      "agent_type": {"type": "string"},
      "session_id": {"type": "string"},
      "config": {"type": "object"}
    }
  }
}
```

我们的实现：
- ✅ 使用GET方法
- ✅ 使用SSE流式API
- ✅ 参数包括query、agent_type、session_id、config
- ✅ agent_type固定为"japan"

## 测试

### 测试专家服务

```python
from services.expert_consultation_service import expert_service

result = await expert_service.consult(
    query="查询当前养殖池的pH值数据",
    session_id="test_session",
    config={"model": "gpt-4o-mini", "temperature": 0.7}
)

if result.get("success"):
    print(f"专家回答: {result['answer']}")
else:
    print(f"错误: {result['error']}")
```

## 注意事项

1. **SSE流式响应**: 需要等待流式响应完成，可能需要较长时间
2. **超时设置**: 默认60秒，可根据实际情况调整
3. **错误处理**: 如果专家服务不可用，不会中断对话流程
4. **会话ID**: 必须提供session_id，否则跳过专家咨询

