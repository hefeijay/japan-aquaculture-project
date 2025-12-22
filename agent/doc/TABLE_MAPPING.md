# 数据库表结构映射说明

## chat_history 表映射

### 现有表结构

数据库中的 `chat_history` 表包含以下字段：

| 数据库字段 | 类型 | 说明 |
|-----------|------|------|
| id | int | 主键 |
| session_id | varchar(128) | 会话ID |
| role | varchar(32) | 角色（user/assistant） |
| content | text | 消息内容 |
| type | varchar(50) | 消息类型 |
| status | varchar(50) | 状态 |
| timestamp | timestamp | 时间戳 |
| message_id | varchar(128) | 消息ID |
| tool_calls | text | 工具调用信息 |
| meta_data | text | 元数据（JSON格式） |
| updated_at | timestamp | 更新时间 |

### 模型映射

`ChatHistory` 模型已调整为匹配现有表结构，并提供了兼容属性：

| 模型属性 | 数据库字段 | 说明 |
|---------|-----------|------|
| id | id | 主键 |
| session_id | session_id | 会话ID |
| role | role | 角色 |
| content | content | 消息内容（原始字段） |
| **message** | content | 兼容属性（映射到 content） |
| type | type | 消息类型（用于存储 intent） |
| status | status | 状态 |
| timestamp | timestamp | 时间戳（原始字段） |
| **created_at** | timestamp | 兼容属性（映射到 timestamp） |
| message_id | message_id | 消息ID |
| tool_calls | tool_calls | 工具调用信息 |
| meta_data | meta_data | 元数据（原始字段） |
| **metadata** | meta_data | 兼容属性（映射到 meta_data） |
| updated_at | updated_at | 更新时间 |

### 字段使用说明

1. **消息内容**：
   - 数据库字段：`content`
   - 模型属性：`content`（原始）或 `message`（兼容）
   - 代码中使用 `message` 属性，会自动映射到 `content` 字段

2. **时间戳**：
   - 数据库字段：`timestamp`
   - 模型属性：`timestamp`（原始）或 `created_at`（兼容）
   - 代码中使用 `created_at` 属性，会自动映射到 `timestamp` 字段

3. **元数据**：
   - 数据库字段：`meta_data`
   - 模型属性：`meta_data`（原始）或 `metadata`（兼容）
   - 代码中使用 `metadata` 属性，会自动映射到 `meta_data` 字段

4. **意图存储**：
   - 使用 `type` 字段存储意图（intent）
   - 在 `save_message` 函数中，`intent` 参数会存储在 `type` 字段

### 兼容性

- ✅ 完全兼容现有表结构
- ✅ 不需要修改数据库
- ✅ 可以使用现有数据（5305+ 条记录）
- ✅ 代码中使用友好的属性名（message, created_at, metadata）
- ✅ 自动映射到数据库字段（content, timestamp, meta_data）

### 使用示例

```python
from services.chat_history_service import save_message, get_history

# 保存消息（会自动使用正确的字段）
save_message(
    session_id="user_001",
    role="user",
    message="查询水温数据",
    intent="数据查询",  # 存储在 type 字段
    metadata={"key": "value"}  # 存储在 meta_data 字段
)

# 获取历史（会自动使用 timestamp 字段排序）
history = get_history("user_001", limit=20)

# 使用兼容属性
for record in history:
    print(record.message)  # 自动映射到 content
    print(record.created_at)  # 自动映射到 timestamp
    print(record.metadata)  # 自动映射到 meta_data
```

