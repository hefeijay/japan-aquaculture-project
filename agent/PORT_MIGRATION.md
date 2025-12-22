# 端口迁移指南：从 8001 迁移到 8000

## 概述

本指南说明如何将新后端服务从 8001 端口迁移到 8000 端口，替换原有的旧服务。

## 变更说明

### 端口统一
- **之前**: HTTP 在 8000 端口，WebSocket 在 8001 端口
- **现在**: HTTP 和 WebSocket 统一在 8000 端口

### 优势
1. 简化配置：只需要一个端口
2. 统一管理：HTTP 和 WebSocket 在同一服务
3. 符合标准：FastAPI 支持在同一端口提供 HTTP 和 WebSocket

## 已修改的文件

### 1. `config.py`
- 移除了 `WS_PORT` 配置项
- HTTP 和 WebSocket 统一使用 `PORT` (默认 8000)

### 2. `start.sh`
- 使用环境变量 `PORT`（默认 8000）
- 支持从 `.env` 文件读取端口配置

### 3. `vite.config.ts` (前端)
- `/api/v1` 代理到 `http://localhost:8000`
- 启用 WebSocket 代理支持
- 保留 `/api` 作为旧服务兜底

## 迁移步骤

### 步骤 1: 停止旧服务

```bash
# 检查 8000 端口是否被占用
lsof -i :8000
# 或
netstat -tlnp | grep 8000

# 如果被占用，停止旧服务
# 根据实际情况使用 kill 或 systemctl stop
```

### 步骤 2: 停止当前 8001 端口的服务

```bash
# 检查 8001 端口
lsof -i :8001

# 停止服务（如果正在运行）
# Ctrl+C 或 kill <PID>
```

### 步骤 3: 更新环境变量（可选）

如果 `.env` 文件中有 `WS_PORT` 配置，可以移除：

```bash
# 编辑 .env 文件
# 移除或注释掉 WS_PORT=8001
# 确保 PORT=8000（或使用默认值）
```

### 步骤 4: 启动新服务

```bash
cd /srv/japan-aquaculture-project/backend
./start.sh
```

服务将在 8000 端口启动，同时支持：
- HTTP API: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/`
- API 文档: `http://localhost:8000/docs`

### 步骤 5: 重启前端开发服务器

```bash
cd /srv/digital_screen/japan_digital_screen/aquaculture-control-center
# 停止当前前端服务（Ctrl+C）
# 重新启动
npm run dev
```

前端会自动使用新的代理配置。

## 验证

### 1. 检查服务状态

```bash
# 检查端口监听
netstat -tlnp | grep 8000

# 应该看到类似输出：
# tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN  <PID>/python
```

### 2. 测试 HTTP API

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
curl http://localhost:8000/docs
```

### 3. 测试 WebSocket

```bash
# 使用 wscat 测试（需要安装: npm install -g wscat）
wscat -c ws://localhost:8000/

# 或使用浏览器控制台
const ws = new WebSocket('ws://localhost:8000/');
ws.onopen = () => console.log('连接成功');
ws.send(JSON.stringify({message: '测试', session_id: 'test'}));
```

### 4. 测试前端连接

1. 打开前端应用（通常是 `http://localhost:8083`）
2. 打开浏览器开发者工具
3. 检查 Network 标签，确认请求发送到 `localhost:8000`
4. 测试对话功能，确认 WebSocket 连接正常

## 回滚方案

如果迁移后出现问题，可以回滚：

### 1. 恢复配置

```bash
# 恢复 config.py 中的 WS_PORT
# 恢复 start.sh 中的端口配置
# 恢复 vite.config.ts 中的代理配置
```

### 2. 重新启动服务

```bash
# 在 8001 端口启动（如果需要）
PORT=8001 ./start.sh
```

## 注意事项

1. **端口冲突**: 确保 8000 端口未被其他服务占用
2. **防火墙**: 如果使用防火墙，确保 8000 端口已开放
3. **负载均衡**: 如果使用负载均衡器，需要更新配置
4. **监控**: 更新监控系统的端口配置
5. **文档**: 更新相关文档中的端口引用

## 常见问题

### Q: 为什么统一端口？

A: FastAPI 原生支持在同一端口提供 HTTP 和 WebSocket 服务，简化配置和管理。

### Q: 旧服务还在运行怎么办？

A: 先停止旧服务，或修改新服务的端口（通过 `.env` 文件设置 `PORT=8001`）。

### Q: WebSocket 连接失败？

A: 检查：
1. 服务是否在 8000 端口运行
2. 前端代理配置是否正确
3. 防火墙是否阻止连接
4. 浏览器控制台是否有错误信息

### Q: 前端请求还是发送到旧服务？

A: 确保：
1. 前端开发服务器已重启
2. `vite.config.ts` 已更新
3. 浏览器缓存已清除

## 相关文件

- `config.py`: 服务配置
- `start.sh`: 启动脚本
- `vite.config.ts`: 前端代理配置
- `.env`: 环境变量配置

## 更新日期

2025-12-11

