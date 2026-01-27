# DeviceExpertService 使用说明

## 概述

`DeviceExpertService` 提供统一的 `consult` 方法，同时支持流式和非流式两种模式。

## 方法签名

```python
async def consult(
    self,
    query: str,                                    # 必需：用户的设备控制请求
    session_id: str,                               # 必需：会话ID
    context: Optional[Dict[str, Any]] = None,      # 可选：上下文信息
    stream_callback: Optional[Callable] = None,    # 可选：流式回调（消息内容）
    event_callback: Optional[Callable] = None,     # 可选：事件回调（所有事件）
) -> Dict[str, Any]:
```

## 返回值结构

```python
{
    "success": True/False,
    "result": "设备操作结果文本",
    "device_type": "feeder/sensor/camera/...",
    "session_id": "session_123",
    "operation_record": {                          # ⭐️ 操作记录
        "operation_id": 12345,
        "action_type": "设备控制-启动投喂",
        "user_id": 1,
        "device_id": "DEV-FEEDER-001",
        "parameters": {...},
        "execution_result": "success",
        "timestamp": 1737000000000
    },
    "tool_calls": [                                # ⭐️ 工具调用列表
        {
            "tool": "device_control_api",
            "action": "start_feeding",
            "parameters": {...},
            "result": {...},
            "duration_ms": 1250
        }
    ],
    "execution_steps": [                           # ⭐️ 执行步骤
        "1. 解析用户意图：启动一号池投喂机",
        "2. 查询设备状态：设备在线，可控制",
        "3. 调用设备API：POST /api/feeder/start"
    ],
    "error": None,                                 # 如果失败则包含错误信息
    "metadata": {
        "response_type": "sse_stream",
        "tool_call_count": 3,
        "execution_step_count": 5
    }
}
```

## 使用场景

### 场景1：非流式调用（只获取最终结果）

**适用于**: 不需要实时反馈的场景，如批量操作、定时任务等。

```python
from agent.services.device_expert_service import device_expert_service

# 调用（不传递回调函数）
result = await device_expert_service.consult(
    query="启动一号池投喂机",
    session_id="session_123",
    context={"user_id": 1, "pond_id": 1}
)

# 处理结果
if result["success"]:
    print(f"✅ 操作成功: {result['result']}")
    print(f"📋 操作记录ID: {result['operation_record']['operation_id']}")
    print(f"🔧 工具调用次数: {len(result['tool_calls'])}")
    print(f"📝 执行步骤: {result['execution_steps']}")
else:
    print(f"❌ 操作失败: {result['error']}")
```

### 场景2：流式调用（只接收消息内容）

**适用于**: 需要实时显示AI回复内容的场景，如聊天界面。

```python
from agent.services.device_expert_service import device_expert_service

# 定义流式回调函数
async def on_message_chunk(chunk: str):
    """接收消息片段"""
    print(f"AI: {chunk}", end="", flush=True)

# 调用（传递 stream_callback）
result = await device_expert_service.consult(
    query="启动一号池投喂机",
    session_id="session_123",
    context={"user_id": 1},
    stream_callback=on_message_chunk  # ← 流式回调
)

# 处理最终结果
print(f"\n✅ 操作完成: {result['success']}")
print(f"📋 操作记录: {result['operation_record']}")
```

### 场景3：完整事件流式调用（接收所有事件）

**适用于**: 需要完整中间过程的场景，如监控面板、详细日志记录。

```python
from agent.services.device_expert_service import device_expert_service

# 定义事件回调函数
async def on_event(event: dict):
    """接收所有类型的事件"""
    event_type = event.get("type")
    
    if event_type == "start":
        print(f"🚀 开始处理: {event.get('query')}")
    
    elif event_type == "node_update":
        print(f"🔄 节点切换: {event.get('node')}")
    
    elif event_type == "message":
        print(f"💬 AI: {event.get('content')}")
    
    elif event_type == "tool_call":
        print(f"🔧 调用工具: {event.get('tool')} - {event.get('action')}")
    
    elif event_type == "tool_result":
        print(f"✅ 工具结果: {event.get('result')}")
    
    elif event_type == "execution_step":
        print(f"📝 执行步骤: {event.get('step')}")
    
    elif event_type == "operation_record":
        print(f"📋 操作记录: {event.get('record')}")
    
    elif event_type == "done":
        print(f"🎉 完成: success={event.get('success')}")
    
    elif event_type == "error":
        print(f"❌ 错误: {event.get('error')}")

# 调用（传递 event_callback）
result = await device_expert_service.consult(
    query="启动一号池投喂机",
    session_id="session_123",
    context={"user_id": 1},
    event_callback=on_event  # ← 事件回调
)

# 处理最终结果
print(f"\n最终结果: {result}")
```

### 场景4：双回调模式（同时接收消息和事件）

**适用于**: 需要区分处理消息内容和其他事件的场景。

```python
from agent.services.device_expert_service import device_expert_service

# 定义消息回调（用于显示给用户）
async def on_message_chunk(chunk: str):
    """显示给用户的消息"""
    print(f"[用户界面] {chunk}", end="")

# 定义事件回调（用于系统日志/监控）
async def on_event(event: dict):
    """系统日志记录"""
    event_type = event.get("type")
    
    if event_type == "operation_record":
        # 记录操作日志到监控系统
        record = event.get("record")
        await log_to_monitoring_system(record)
    
    elif event_type == "error":
        # 发送告警
        await send_alert(event.get("error"))

# 调用（同时传递两个回调）
result = await device_expert_service.consult(
    query="启动一号池投喂机",
    session_id="session_123",
    context={"user_id": 1},
    stream_callback=on_message_chunk,  # ← 消息回调
    event_callback=on_event            # ← 事件回调
)
```

## 与 WebSocket/SSE 集成示例

### WebSocket 集成

```python
from fastapi import WebSocket

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 定义流式回调
    async def send_to_websocket(chunk: str):
        await websocket.send_json({
            "type": "message",
            "content": chunk
        })
    
    # 调用设备专家
    result = await device_expert_service.consult(
        query=user_query,
        session_id=session_id,
        stream_callback=send_to_websocket
    )
    
    # 发送最终结果
    await websocket.send_json({
        "type": "done",
        "result": result
    })
```

### SSE (Server-Sent Events) 集成

```python
from fastapi.responses import StreamingResponse

async def sse_endpoint(query: str, session_id: str):
    
    async def event_generator():
        # 定义事件回调
        async def emit_event(event: dict):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # 调用设备专家
        result = await device_expert_service.consult(
            query=query,
            session_id=session_id,
            event_callback=emit_event
        )
        
        # 发送最终结果
        yield f"data: {json.dumps({'type': 'done', 'result': result}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## 事件类型列表

| 事件类型 | 说明 | 何时触发 |
|---------|------|---------|
| `start` | 开始事件 | 收到请求，开始处理 |
| `node_update` | 节点切换 | Workflow 节点切换时 |
| `message` | 消息内容 | AI 生成文本时（流式输出） |
| `tool_call` | 工具调用 | 调用设备API或工具时 |
| `tool_result` | 工具结果 | 工具执行完成后 |
| `execution_step` | 执行步骤 | 每个关键步骤完成时 |
| `operation_record` | ⭐️ 操作记录 | 操作记录写入数据库后 |
| `device_status` | 设备状态更新 | 设备状态变化时 |
| `error` | 错误事件 | 发生错误时 |
| `done` | 完成事件 | 整个流程完成时（成功或失败） |

详细的事件格式请参考: `backend/DEVICE_STREAM_EVENTS.md`

## 注意事项

### 1. 回调函数必须是异步的

```python
# ✅ 正确
async def on_message(chunk: str):
    await some_async_operation(chunk)

# ❌ 错误
def on_message(chunk: str):  # 缺少 async
    print(chunk)
```

### 2. event_callback 会接收所有事件

如果同时传递了 `stream_callback` 和 `event_callback`：
- `event_callback` 会接收所有类型的事件（包括 `message` 事件）
- `stream_callback` 只接收 `message` 事件的 `content` 字段

**建议**: 如果只需要显示消息内容，使用 `stream_callback`；如果需要完整的事件信息，使用 `event_callback`。

### 3. 操作记录的重要性

`operation_record` 字段包含了完整的操作审计信息，建议：
- ✅ 存储到日志系统
- ✅ 显示在操作历史中
- ✅ 用于合规审计
- ✅ 用于故障排查

### 4. 错误处理

即使操作失败，返回值中仍然包含：
- `operation_record`: 失败的操作记录
- `tool_calls`: 已执行的工具调用
- `execution_steps`: 执行到的步骤

这些信息对于故障排查非常重要。

## 完整示例：在 Agent 中使用

```python
# agent/agents/device_agent.py

from agent.services.device_expert_service import device_expert_service

class DeviceControlAgent:
    """设备控制智能体"""
    
    async def execute_device_command(
        self,
        query: str,
        session_id: str,
        user_id: int,
        websocket=None  # 可选的 WebSocket 连接
    ):
        """执行设备控制命令"""
        
        # 如果有 WebSocket，启用流式输出
        stream_callback = None
        event_callback = None
        
        if websocket:
            # 定义流式回调
            async def send_message(chunk: str):
                await websocket.send_json({
                    "type": "stream_chunk",
                    "content": chunk
                })
            
            async def send_event(event: dict):
                await websocket.send_json(event)
            
            stream_callback = send_message
            event_callback = send_event
        
        # 调用设备专家
        result = await device_expert_service.consult(
            query=query,
            session_id=session_id,
            context={
                "user_id": user_id,
                "timestamp": time.time()
            },
            stream_callback=stream_callback,
            event_callback=event_callback
        )
        
        # 记录到数据库（如果还没有记录）
        if result["success"] and result.get("operation_record"):
            await self.save_operation_to_database(result["operation_record"])
        
        return result
```

## 性能优化建议

1. **非流式场景**: 不传递回调函数，减少函数调用开销
2. **流式场景**: 使用 `stream_callback` 而不是 `event_callback`，避免处理不需要的事件
3. **批量操作**: 对于批量设备控制，考虑使用 asyncio.gather 并发执行
4. **超时设置**: 通过 `settings.DEVICE_EXPERT_API_TIMEOUT` 配置超时时间

## 相关文档

- [设备控制流式事件规范](../../backend/DEVICE_STREAM_EVENTS.md)
- [Agent 架构说明](../README.md)

