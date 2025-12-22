# 流式输出实现说明

## 概述

已实现真正的流式输出功能，AI 回答会逐块实时发送给前端，而不是等待完整回答生成后再一次性发送。

## 实现原理

### 1. 回调机制

使用回调函数实现真正的流式输出：

```python
async def stream_chunk_callback(chunk: str):
    """流式回调函数，每收到一个块就立即发送给前端"""
    # 立即发送流式消息块
    await websocket.send_text(json.dumps({
        "type": "stream_chunk",
        "data": {
            "session_id": session_id,
            "content": chunk,  # 只发送当前块
            "event": "content",
            "message_id": assistant_message_id,
            "role": "assistant",
            "timestamp": assistant_timestamp,
            "type": "stream_chunk",
        }
    }))
```

### 2. 数据流

```
LLM 生成文本块
  ↓
execute_llm_call 收到块
  ↓
立即调用 stream_callback(chunk)
  ↓
stream_chunk_callback 立即发送给前端
  ↓
前端实时显示文本块
  ↓
累积完整内容用于保存到数据库
```

## 代码修改

### 1. `agents/llm_utils.py`

**修改前**:
```python
async def execute_llm_call(
    messages: List,
    config: Optional[LLMConfig] = None,
    stream: bool = False
) -> tuple[str, Dict[str, Any]]:
    if stream:
        chunks = []
        async for chunk in llm.astream(messages):
            chunks.append(chunk.content)
        response_content = "".join(chunks)  # 收集所有块后返回
```

**修改后**:
```python
async def execute_llm_call(
    messages: List,
    config: Optional[LLMConfig] = None,
    stream: bool = False,
    stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> tuple[str, Dict[str, Any]]:
    if stream:
        chunks = []
        async for chunk in llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                chunk_content = chunk.content
                chunks.append(chunk_content)
                # 立即调用回调函数（真正的流式输出）
                if stream_callback:
                    await stream_callback(chunk_content)
        response_content = "".join(chunks)
```

### 2. `agents/thinking_agent.py`

**修改前**:
```python
async def think(
    self,
    user_input: str,
    ...
    stream: bool = False
) -> tuple[str, Dict[str, Any]]:
    response_content, stats = await execute_llm_call(
        messages, config, stream=stream
    )
```

**修改后**:
```python
async def think(
    self,
    user_input: str,
    ...
    stream: bool = False,
    stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> tuple[str, Dict[str, Any]]:
    response_content, stats = await execute_llm_call(
        messages, config, stream=stream, stream_callback=stream_callback
    )
```

### 3. `main.py` (WebSocket 处理)

**修改前**:
```python
# 生成完整回答后一次性发送
analysis, stats = await thinking_agent.think(...)
assistant_content = str(analysis)
await websocket.send_text(json.dumps({
    "type": "stream_chunk",
    "data": {"content": assistant_content, ...}
}))
```

**修改后**:
```python
# 定义流式回调函数
async def stream_chunk_callback(chunk: str):
    nonlocal assistant_content
    assistant_content += chunk  # 累积内容
    
    # 立即发送当前块
    await websocket.send_text(json.dumps({
        "type": "stream_chunk",
        "data": {"content": chunk, ...}  # 只发送当前块
    }))

# 使用流式回调生成回答
analysis, stats = await thinking_agent.think(
    ...,
    stream=True,
    stream_callback=stream_chunk_callback  # 传入回调函数
)
```

## 优势

### 1. 实时性
- **之前**: 用户需要等待完整回答生成后才能看到内容
- **现在**: 用户可以看到回答逐字逐句地实时生成

### 2. 用户体验
- 减少等待时间感知
- 提供更好的交互反馈
- 符合现代聊天应用的体验标准

### 3. 性能
- 不需要等待完整回答生成
- 可以更早开始处理用户的下一个请求
- 减少内存占用（不需要缓存完整回答）

## 消息格式

### 流式消息块（stream_chunk）

```json
{
  "type": "stream_chunk",
  "data": {
    "session_id": "e5a522b5-b83a-45f1-923e-ea54f06ec968",
    "content": "你",  // 只包含当前块的内容
    "event": "content",
    "message_id": "60324fac-f05d-4e1a-a462-ac93d4cb9441",
    "role": "assistant",
    "timestamp": 1765451251,
    "type": "stream_chunk"
  }
}
```

**注意**: 每个 `stream_chunk` 消息只包含一个文本块，前端需要累积这些块来显示完整的回答。

## 前端处理

前端需要累积接收到的流式消息块：

```javascript
let fullContent = "";

websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === "stream_chunk") {
    // 累积内容
    fullContent += message.data.content;
    
    // 实时更新UI
    updateChatMessage(fullContent);
  }
};
```

## 测试建议

1. **测试流式输出**: 发送一个较长的问题，观察回答是否逐块显示
2. **测试完整性**: 确保所有块都被正确接收和累积
3. **测试错误处理**: 测试在流式输出过程中连接断开的情况
4. **测试性能**: 观察流式输出对系统性能的影响

## 注意事项

1. **累积内容**: 回调函数中需要累积完整内容，用于最后保存到数据库
2. **错误处理**: 如果流式输出过程中发生错误，需要确保已累积的内容能够正确保存
3. **消息顺序**: 确保流式消息块的顺序正确（通常 LLM 会按顺序生成）
4. **网络稳定性**: 流式输出对网络稳定性要求较高，需要处理网络中断的情况

