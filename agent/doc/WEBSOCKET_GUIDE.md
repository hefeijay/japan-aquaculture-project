# WebSocket 使用指南

## 问题说明

如果遇到 `403 Forbidden` 错误，通常是因为：
1. **没有定义 WebSocket 路由** - 已修复 ✅
2. **CORS 配置问题** - 已配置允许所有来源 ✅
3. **防火墙/安全组配置** - 需要检查阿里云安全组 ✅

## WebSocket 端点

- **路径**: `ws://your-server:8001/`
- **协议**: WebSocket (ws:// 或 wss://)

## 连接示例

### JavaScript (浏览器)

```javascript
const ws = new WebSocket('ws://your-server-ip:8001/');

ws.onopen = () => {
    console.log('WebSocket 连接已建立');
    
    // 发送消息
    ws.send(JSON.stringify({
        message: '查询最近的水温数据',
        session_id: 'user_001',
        context: {}
    }));
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log('收到响应:', response);
    
    // 响应格式:
    // {
    //   "status": "success",
    //   "response": "AI 生成的回答",
    //   "intent": "数据查询",
    //   "route_decision": {...},
    //   "data_used": [...],
    //   "session_id": "user_001"
    // }
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
    console.log('WebSocket 连接已关闭');
};
```

### Python

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://your-server-ip:8001/"
    
    async with websockets.connect(uri) as websocket:
        # 发送消息
        message = {
            "message": "查询最近的水温数据",
            "session_id": "test_001",
            "context": {}
        }
        await websocket.send(json.dumps(message))
        
        # 接收响应
        response = await websocket.recv()
        data = json.loads(response)
        print("收到响应:", data)

# 运行
asyncio.run(test_websocket())
```

### curl (测试)

```bash
# 注意：curl 不支持 WebSocket，需要使用专门的工具
# 可以使用 wscat 或 websocat

# 安装 wscat
npm install -g wscat

# 连接测试
wscat -c ws://your-server-ip:8001/

# 发送消息
{"message": "查询最近的水温数据", "session_id": "test_001"}
```

## 消息格式

### 发送消息

```json
{
  "message": "用户的问题",
  "session_id": "会话ID（可选，默认自动生成）",
  "context": {
    "额外的上下文信息（可选）"
  }
}
```

### 接收响应

```json
{
  "status": "success",
  "response": "AI 生成的回答",
  "intent": "识别的意图",
  "route_decision": {
    "decision": "路由决策",
    "needs_data": true
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

## 阿里云安全组配置

### 1. 检查安全组规则

1. 登录阿里云控制台
2. 进入 ECS 实例管理
3. 选择你的实例 → 安全组 → 配置规则

### 2. 添加入站规则

需要添加以下规则：

| 规则方向 | 授权策略 | 协议类型 | 端口范围 | 授权对象 |
|---------|---------|---------|---------|---------|
| 入方向 | 允许 | TCP | 8001/8001 | 0.0.0.0/0 |

或者更安全的配置（仅允许特定 IP）：

| 规则方向 | 授权策略 | 协议类型 | 端口范围 | 授权对象 |
|---------|---------|---------|---------|---------|
| 入方向 | 允许 | TCP | 8001/8001 | 你的IP/32 |

### 3. 检查防火墙

在服务器上检查防火墙设置：

```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 8001/tcp

# CentOS/RHEL
sudo firewall-cmd --list-ports
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

## 测试连接

### 1. 检查服务是否运行

```bash
# 检查端口是否监听
netstat -tlnp | grep 8001
# 或
ss -tlnp | grep 8001

# 应该看到类似输出：
# LISTEN 0 128 0.0.0.0:8001 0.0.0.0:*
```

### 2. 测试 HTTP 连接（确认端口可达）

```bash
curl http://your-server-ip:8001/health
```

### 3. 测试 WebSocket 连接

使用浏览器控制台或专门的 WebSocket 客户端工具。

## 常见问题

### 问题 1: 403 Forbidden

**原因**:
- WebSocket 路由未定义（已修复）
- CORS 配置问题（已配置）

**解决方案**:
- 确认已添加 WebSocket 路由
- 检查 CORS 配置

### 问题 2: 连接超时

**原因**:
- 防火墙阻止
- 安全组未配置
- 服务未启动

**解决方案**:
1. 检查安全组规则
2. 检查服务器防火墙
3. 确认服务正在运行

### 问题 3: 连接被拒绝

**原因**:
- 端口未监听
- 服务未启动

**解决方案**:
```bash
# 检查服务状态
ps aux | grep uvicorn

# 检查端口监听
netstat -tlnp | grep 8001
```

## 生产环境建议

1. **使用 WSS (WebSocket Secure)**
   - 配置 SSL/TLS 证书
   - 使用 `wss://` 协议

2. **添加认证**
   - 在 WebSocket 连接时验证 token
   - 限制连接频率

3. **监控和日志**
   - 记录所有连接和消息
   - 监控连接数

4. **负载均衡**
   - 如果使用负载均衡，确保支持 WebSocket
   - 配置粘性会话（sticky session）

