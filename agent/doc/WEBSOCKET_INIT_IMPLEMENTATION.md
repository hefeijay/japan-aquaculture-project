# WebSocket 初始化逻辑实现说明

## 概述

根据原项目 `/usr/henry/cognitive-center` 的实现，添加了 WebSocket 会话初始化功能。前端在建立 WebSocket 连接后，需要先发送 `init` 消息进行会话初始化，后端会从数据库加载会话配置和历史消息。

## 实现内容

### 1. 数据库模型

**文件**: `models/session.py`

创建了 `Session` 模型，包含以下字段：
- `session_id`: 会话唯一标识符
- `user_id`: 用户ID
- `config`: 会话配置（JSON格式）
- `status`: 会话状态（active, inactive, archived）
- `session_name`: 会话名称
- `summary`: 会话摘要
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. 数据访问层

**文件**: `repositories/session_repository.py`

实现了以下函数：
- `find_session_by_id(session_id)`: 根据会话ID查找会话
- `create_new_session(session_id, user_id)`: 创建新会话
- `update_session_config(session, new_config)`: 更新会话配置

### 3. 业务逻辑层

**文件**: `services/session_service.py`

实现了 `initialize_session(session_id, user_id)` 函数：
- 如果 `session_id` 存在，从数据库加载会话配置和历史消息
- 如果 `session_id` 不存在，创建新会话并使用默认配置
- 返回包含 `session_id`、`messages` 和 `config` 的字典

### 4. 消息类型常量

**文件**: `core/constants.py`

定义了：
- `MsgType` 类：包含所有消息类型常量
  - `INIT`: 客户端初始化请求
  - `INIT_RESPONSE`: 服务器初始化响应
  - `PING`/`PONG`: 心跳消息
  - `USER_SEND_MESSAGE`: 用户发送消息
  - `NEW_CHAT_MESSAGE`: 新聊天消息
- `DEFAULT_CONFIG_DATA`: 默认会话配置

### 5. WebSocket 处理器更新

**文件**: `main.py`

在 `websocket_endpoint` 函数中添加了：
1. **心跳处理**: 支持 `ping`/`pong` 消息
2. **初始化处理**: 
   - 接收 `{type: "init", data: {session_id, user_id}}`
   - 调用 `initialize_session` 加载或创建会话
   - 返回 `{type: "init", data: {session_id, messages, config}}`
3. **会话验证**: 对于其他消息，检查会话是否已初始化
4. **标准消息格式**: 使用 `MsgType` 常量定义消息类型

## 消息流程

### 1. 前端发送初始化消息

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    // 发送初始化消息
    ws.send(JSON.stringify({
        type: "init",
        data: {
            session_id: "c1106b50-ab10-4361-a287-5c1de9311049",
            user_id: "ac49c0d8-dd00-4114-a8bb-ab0073d92290"
        }
    }));
};
```

### 2. 后端处理初始化

1. 接收 `init` 消息
2. 提取 `session_id` 和 `user_id`
3. 调用 `initialize_session(session_id, user_id)`
4. 如果会话存在，从数据库加载配置和历史消息
5. 如果会话不存在，创建新会话并使用默认配置

### 3. 后端返回初始化响应

```json
{
    "type": "init",
    "data": {
        "session_id": "c1106b50-ab10-4361-a287-5c1de9311049",
        "messages": [
            {
                "id": 1,
                "session_id": "c1106b50-ab10-4361-a287-5c1de9311049",
                "role": "user",
                "content": "之前的问题",
                "type": "数据查询",
                "timestamp": 1234567890,
                "meta_data": "{}"
            }
        ],
        "config": {
            "model": {
                "model_name": "gpt-4o-mini",
                "temperature": 0.7
            },
            "rag": {
                "collection_name": "japan_shrimp",
                "topk_single": 5,
                "topk_multi": 5
            },
            "mode": "single",
            "single": {
                "temperature": 0.4,
                "system_prompt": "...",
                "max_tokens": 4096
            }
        }
    }
}
```

### 4. 前端确认会话建立

前端收到初始化响应后，认为会话已建立，可以开始发送用户消息。

## 数据库表结构

需要创建 `session` 表，SQL 脚本位于 `schema/session.sql`：

```sql
CREATE TABLE IF NOT EXISTS `session` (
    `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(128) NOT NULL UNIQUE,
    `user_id` VARCHAR(128) NOT NULL,
    `config` TEXT,
    `status` VARCHAR(50) DEFAULT 'active',
    `session_name` VARCHAR(128) DEFAULT 'new chat',
    `summary` VARCHAR(2048) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_session_session_id` (`session_id`),
    INDEX `idx_session_user_id` (`user_id`)
);
```

## 使用步骤

### 1. 创建数据库表

```bash
mysql -u root -p aquaculture < schema/session.sql
```

### 2. 重启后端服务

```bash
cd /srv/japan-aquaculture-project/backend
./start.sh
```

### 3. 前端连接流程

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    // 1. 发送初始化消息
    ws.send(JSON.stringify({
        type: "init",
        data: {
            session_id: "your-session-id",  // 可选，不提供则创建新会话
            user_id: "your-user-id"
        }
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === "init") {
        // 2. 收到初始化响应，会话已建立
        console.log("会话初始化完成:", message.data);
        console.log("会话ID:", message.data.session_id);
        console.log("历史消息数:", message.data.messages.length);
        console.log("配置:", message.data.config);
        
        // 3. 现在可以发送用户消息
        ws.send(JSON.stringify({
            type: "userSendMessage",
            data: {
                content: "查询最近的水温数据",
                session_id: message.data.session_id
            }
        }));
    } else if (message.type === "newChatMessage") {
        // 4. 收到AI回答
        console.log("AI回答:", message.data.response);
    }
};
```

## 兼容性

- 支持新的标准消息格式（带 `type` 字段）
- 兼容旧的消息格式（直接发送 `message` 字段）
- 如果未初始化会话，会尝试从消息中提取 `session_id`

## 注意事项

1. **必须初始化**: 前端必须先发送 `init` 消息，才能正常对话
2. **会话持久化**: 会话配置和历史消息存储在数据库中
3. **默认配置**: 新会话使用 `DEFAULT_CONFIG_DATA` 中的默认配置
4. **历史消息**: 初始化时会加载最近 100 条历史消息

## 相关文件

- `models/session.py`: Session 数据库模型
- `repositories/session_repository.py`: 会话数据访问层
- `services/session_service.py`: 会话业务逻辑层
- `core/constants.py`: 消息类型和默认配置
- `main.py`: WebSocket 处理器
- `schema/session.sql`: 数据库表结构

