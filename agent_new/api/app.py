#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 应用工厂
"""
import logging
import sys
import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes.chat import router as chat_router
from websocket.handler import handle_websocket

# ========== 配置标准 logging ==========
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)

# 设置第三方库的日志级别（降噪）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# ========== 配置 structlog ==========
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    
    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title="日本陆上养殖数据处理系统",
        description="基于 LLM 的养殖数据处理和对话系统",
        version="2.0.0",
    )
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(chat_router, prefix="/api/v1", tags=["对话"])
    
    # 根路径
    @app.get("/")
    async def root():
        return {
            "service": "日本陆上养殖数据处理系统",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "chat": "/api/v1/chat",
                "history": "/api/v1/chat/history",
                "websocket": "/ws",
                "docs": "/docs",
            }
        }
    
    # 健康检查
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    # WebSocket 端点
    @app.websocket("/")
    async def websocket_root(websocket: WebSocket):
        await handle_websocket(websocket)
    
    @app.websocket("/ws")
    async def websocket_ws(websocket: WebSocket):
        await handle_websocket(websocket)
    
    logger.info("FastAPI 应用创建完成")
    
    return app


# 创建应用实例
app = create_app()

