# 历史对话记录功能说明

## ✅ 功能已添加

现在系统已经完整支持历史对话记录功能！

## 功能特性

### 1. 自动保存对话记录

- **用户消息**：每次用户发送消息时，会自动保存到数据库
- **AI 回答**：每次 AI 生成回答后，也会自动保存
- **会话隔离**：不同 `session_id` 的对话记录完全隔离

### 2. 自动加载历史记录

- **智能加载**：每次对话时，会自动加载该会话的历史记录（最多20条）
- **上下文理解**：AI 会基于历史对话上下文生成更准确的回答
- **意图识别**：意图识别也会考虑历史对话

### 3. 历史记录管理

- **查询历史**：可以通过 API 查询指定会话的历史记录
- **清除历史**：可以清除指定会话的所有历史记录

## API 接口

### 1. 对话接口（自动使用历史记录）

**POST /api/v1/chat**

```json
{
  "message": "查询最近的水温数据",
  "session_id": "user_001"
}
```

**响应**：
```json
{
  "status": "success",
  "response": "AI 回答",
  "session_id": "user_001",
  "history_count": 4  // 包含刚保存的两条消息
}
```

### 2. 查询历史记录

**GET /api/v1/chat/history?session_id=user_001&limit=20**

**响应**：
```json
{
  "history": [
    {
      "id": 1,
      "session_id": "user_001",
      "role": "user",
      "message": "查询最近的水温数据",
      "intent": "数据查询",
      "metadata": null,
      "created_at": "2025-12-11T10:30:00"
    },
    {
      "id": 2,
      "session_id": "user_001",
      "role": "assistant",
      "message": "根据查询结果...",
      "intent": "数据查询",
      "metadata": "{\"route_decision\": {...}}",
      "created_at": "2025-12-11T10:30:05"
    }
  ],
  "count": 2,
  "session_id": "user_001"
}
```

### 3. 清除历史记录

**DELETE /api/v1/chat/history?session_id=user_001**

**响应**：
```json
{
  "status": "success",
  "deleted": 10,
  "session_id": "user_001"
}
```

## WebSocket 支持

WebSocket 接口也完全支持历史记录：

```javascript
const ws = new WebSocket('ws://your-server:8001/');

ws.onopen = () => {
    // 使用相同的 session_id 可以保持对话上下文
    ws.send(JSON.stringify({
        message: '查询最近的水温数据',
        session_id: 'user_001'  // 重要：使用固定的 session_id
    }));
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log('回答:', response.response);
    console.log('历史记录数:', response.history_count);
};
```

## 数据库表结构

需要创建 `chat_history` 表：

```sql
CREATE TABLE IF NOT EXISTS chat_history (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  session_id        VARCHAR(128) NOT NULL,
  role              VARCHAR(16) NOT NULL,  -- user 或 assistant
  message           TEXT NOT NULL,
  intent            VARCHAR(64) NULL,
  metadata          TEXT NULL,  -- JSON 格式的额外信息
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_chat_session_ts (session_id, created_at),
  INDEX idx_chat_created_at (created_at)
);
```

执行 SQL 脚本：
```bash
mysql -u root -p your_database < schema/chat_history.sql
```

或使用 Python 自动创建：
```python
from database import Base, engine
from models.chat_history import ChatHistory

Base.metadata.create_all(bind=engine)
```

## 使用示例

### 示例 1: 连续对话（保持上下文）

```python
import requests

session_id = "user_001"
base_url = "http://localhost:8000"

# 第一次对话
response1 = requests.post(f"{base_url}/api/v1/chat", json={
    "message": "查询最近的水温数据",
    "session_id": session_id
})
print(response1.json()["response"])

# 第二次对话（会记住之前的对话）
response2 = requests.post(f"{base_url}/api/v1/chat", json={
    "message": "那pH值呢？",  # AI 会理解"那"指的是什么
    "session_id": session_id  # 使用相同的 session_id
})
print(response2.json()["response"])
```

### 示例 2: 查询历史记录

```python
import requests

# 查询历史记录
history = requests.get(
    "http://localhost:8000/api/v1/chat/history",
    params={"session_id": "user_001", "limit": 10}
)
print(history.json())
```

### 示例 3: 清除历史记录

```python
import requests

# 清除历史记录
result = requests.delete(
    "http://localhost:8000/api/v1/chat/history",
    params={"session_id": "user_001"}
)
print(result.json())
```

## 工作原理

1. **保存阶段**：
   - 用户发送消息 → 保存到 `chat_history` 表（role='user'）
   - AI 生成回答 → 保存到 `chat_history` 表（role='assistant'）

2. **加载阶段**：
   - 根据 `session_id` 查询最近 N 条记录（默认20条）
   - 格式化为 LLM 需要的格式：`[{"role": "user", "content": "..."}, ...]`

3. **使用阶段**：
   - 将历史记录传递给 `IntentAgent` 进行意图识别
   - 将历史记录传递给 `ThinkingAgent` 生成回答
   - AI 可以基于历史上下文理解用户意图

## 注意事项

1. **session_id 的重要性**：
   - 必须使用固定的 `session_id` 才能保持对话上下文
   - 不同的 `session_id` 之间历史记录完全隔离

2. **历史记录数量**：
   - 默认加载最近 20 条记录
   - 可以通过 `limit` 参数调整
   - 建议不要加载太多，避免 token 消耗过大

3. **数据库性能**：
   - 已添加索引：`(session_id, created_at)`
   - 查询性能良好
   - 建议定期清理旧记录

4. **隐私和安全**：
   - 历史记录包含用户对话内容
   - 建议添加访问控制
   - 考虑数据加密存储

## 测试

```bash
# 测试对话（会自动保存历史）
python3 test_chat.py "查询最近的水温数据"

# 查询历史记录
curl "http://localhost:8000/api/v1/chat/history?session_id=test_session"

# 清除历史记录
curl -X DELETE "http://localhost:8000/api/v1/chat/history?session_id=test_session"
```

