# 聊天流程详细说明

## 当前完整流程（WebSocket）

### 流程图

```
用户输入
  ↓
[0] 获取历史对话记录
  ↓
[0.5] 查询重写（QueryRewriter）
  ├─ 输入: 原始问题 + 历史记录 + 上下文
  ├─ 处理: 将问题拆分成更具体的问题
  └─ 输出: 重写后的问题
  ↓
[1] 保存用户消息到数据库
  ├─ 生成 message_id (UUID)
  ├─ 记录 timestamp
  └─ 保存到 chat_history 表
  ↓
[1.5] 立即返回用户消息确认（newChatMessage）
  ├─ type: "newChatMessage"
  └─ data: {session_id, content, message_id, role: "user", timestamp, type: "text"}
  ↓
[2] 意图识别（IntentAgent）
  ├─ 输入: 重写后的问题 + 历史记录
  ├─ 处理: 识别用户意图（如：数据查询、闲聊、设备控制等）
  └─ 输出: intent (字符串)
  ↓
[3] 路由决策（RoutingAgent）
  ├─ 输入: 重写后的问题 + intent + 上下文
  ├─ 处理: 判断是否需要调用专家、是否需要数据查询
  └─ 输出: route_decision {needs_expert, needs_data, decision, reason}
  ↓
[4] 根据路由决策执行操作
  │
  ├─ [4.1] 如果需要专家咨询 (needs_expert || needs_data)
  │   ├─ 构建专家API配置
  │   ├─ 调用专家服务 (ExpertConsultationService)
  │   │   ├─ 请求: 重写后的问题 + 上下文
  │   │   ├─ 专家进行: 数据查询 + 数据聚合 + 结论生成
  │   │   └─ 返回: expert_response {success, answer, confidence, sources}
  │   └─ 记录专家咨询结果
  │
  └─ [4.2] 如果不需要专家，但需要数据查询（兜底方案）
      ├─ 关键词匹配查询（温度、溶解氧、pH等）
      └─ 返回: tool_results []
  ↓
[5] 生成 AI 回答（ThinkingAgent）
  ├─ 生成 assistant_message_id (UUID)
  ├─ 生成 assistant_timestamp
  │
  ├─ [5.1] 如果专家咨询成功
  │   ├─ 输入: 用户问题 + 专家回答
  │   ├─ 上下文: expert_answer, expert_confidence, expert_sources
  │   └─ 处理: 基于专家回答生成最终回答（流式）
  │
  └─ [5.2] 如果没有专家回答
      ├─ 输入: 重写后的问题
      ├─ 上下文: tool_results（如果有）
      └─ 处理: 基于数据查询结果生成回答（流式）
  ↓
[6] 发送流式消息块（stream_chunk）
  ├─ type: "stream_chunk"
  └─ data: {session_id, content, event: "content", message_id, role: "assistant", timestamp, type: "stream_chunk"}
  ↓
[7] 保存 AI 回答到数据库
  ├─ 保存完整回答内容
  ├─ 保存 intent
  └─ 保存 metadata {route_decision, data_used, expert_consulted}
```

## 当前完整流程（REST API）

### 流程图

```
用户输入 (POST /api/v1/chat)
  ↓
[0] 获取历史对话记录
  ↓
[0.5] 查询重写（QueryRewriter）
  ↓
[1] 保存用户消息到数据库
  ↓
[2] 意图识别（IntentAgent）
  ↓
[3] 路由决策（RoutingAgent）
  ↓
[4] 根据路由决策执行操作
  ├─ [4.1] 专家咨询（如果需要）
  └─ [4.2] 数据查询（兜底方案）
  ↓
[5] 生成 AI 回答（ThinkingAgent）
  ├─ [5.1] 基于专家回答
  └─ [5.2] 基于数据查询结果
  ↓
[6] 保存 AI 回答到数据库
  ↓
[7] 返回完整响应（JSON）
  └─ {status, response, intent, route_decision, data_used, session_id, history_count}
```

## 关键组件说明

### 1. QueryRewriter（查询重写）
- **作用**: 将用户问题拆分成更具体的问题
- **输入**: 原始问题、历史记录、上下文
- **输出**: 重写后的问题
- **示例**:
  - 输入: "那pH值呢？"
  - 输出: "查询当前养殖池的pH值数据，包括最新值和历史趋势"

### 2. IntentAgent（意图识别）
- **作用**: 识别用户意图
- **输入**: 重写后的问题、历史记录
- **输出**: intent（如："数据查询"、"闲聊"、"设备控制"等）

### 3. RoutingAgent（路由决策）
- **作用**: 判断是否需要调用专家、是否需要数据查询
- **输入**: 重写后的问题、intent、上下文
- **输出**: route_decision
  ```json
  {
    "needs_expert": true,
    "needs_data": true,
    "decision": "调用专家",
    "reason": "用户请求最新的数据和相关信息，涉及专业分析和数据查询。"
  }
  ```

### 4. ExpertConsultationService（专家咨询服务）
- **作用**: 调用外部专家API，进行数据查询、聚合和结论生成
- **输入**: 重写后的问题、上下文、会话ID、配置
- **输出**: expert_response
  ```json
  {
    "success": true,
    "answer": "专家生成的完整回答...",
    "confidence": 1.0,
    "sources": [],
    "metadata": {...}
  }
  ```

### 5. ThinkingAgent（思考智能体）
- **作用**: 基于专家回答或数据查询结果生成最终回答
- **输入**: 用户问题、上下文、历史记录、工具结果
- **输出**: 最终回答内容（支持流式输出）

## 消息格式

### 用户消息确认（newChatMessage）
```json
{
  "type": "newChatMessage",
  "data": {
    "session_id": "e84aec61-1f5f-47a6-b1b8-b8b12ce6270d",
    "content": "hi",
    "message_id": "ca6951a2-8048-44bf-8220-a492f8934633",
    "role": "user",
    "timestamp": 1765451250,
    "type": "text"
  }
}
```

### AI 回答（stream_chunk）
```json
{
  "type": "stream_chunk",
  "data": {
    "session_id": "e5a522b5-b83a-45f1-923e-ea54f06ec968",
    "content": "你好，我是one，有什么可以帮助你的吗？",
    "event": "content",
    "message_id": "60324fac-f05d-4e1a-a462-ac93d4cb9441",
    "role": "assistant",
    "timestamp": 1765451251,
    "type": "stream_chunk"
  }
}
```

## 优化建议

### 1. 流式输出优化
- **当前**: 收集所有块后一次性发送
- **建议**: 实现真正的流式输出，逐块发送给前端

### 2. 错误处理优化
- **当前**: 基本的错误处理
- **建议**: 添加更详细的错误分类和处理机制

### 3. 性能优化
- **当前**: 串行执行各个步骤
- **建议**: 对于可以并行的步骤（如意图识别和路由决策），考虑并行执行

### 4. 缓存优化
- **当前**: 每次请求都查询历史记录
- **建议**: 添加历史记录缓存，减少数据库查询

### 5. 日志优化
- **当前**: 基本的日志记录
- **建议**: 添加更详细的性能监控和追踪日志

