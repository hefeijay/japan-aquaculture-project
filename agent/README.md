# 旧 `agent` 服务

这是 `japan-aquaculture-project/agent` 的 README。  
该目录是仓库中保留的旧版 Agent 实现，不应与 `agent_new/` 混为一谈。

## 目录定位

- 入口通常为 `main.py`
- 依赖配置在 `config.py`
- 目录内保留了较多历史文档，例如 WebSocket、端口迁移、环境模板等

## 当前建议

1. 先确认生产是否仍在使用本目录。
2. 如果生产已迁移到 `agent_new/`，这里的文档只能作为历史参考。
3. 如果生产仍在使用本目录，排障时请以代码和当前运行参数为准，不要直接照旧文档里的端口和架构描述执行。

## 为什么需要单独标记

仓库内很多旧文档会把 `agent/`、`agent_new/`、`backend/` 的职责混写，容易导致：

- 启动错目录
- 看错端口
- 把旧 WebSocket 说明当成当前实现
- 把旧环境变量模板当成现网配置

## 建议优先核对

- `main.py`
- `config.py`
- `doc/PORT_MIGRATION.md`
- `doc/WEBSOCKET_GUIDE.md`
- `doc/README_ENV.md`

## 使用说明

若需要维护旧链路，请先从运行中的进程管理配置、反向代理配置和实际环境变量回溯，再决定是否继续依赖本目录。
