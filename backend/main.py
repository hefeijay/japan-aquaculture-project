#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本陆上养殖生产管理AI助手服务端主入口
使用模块化架构重构的新版本
"""

import os

from app_factory import create_app, print_startup_info
from config.settings import Config 
from services.aggregator_service import aggregator_service
from services.heartbeat_ws_service import HeartbeatWSService

import logging

logger = logging.getLogger(__name__)


def _is_reloader_process() -> bool:
    """Debug 模式下 Werkzeug reloader 会 fork 子进程，父进程不应启动后台服务"""
    return Config.DEBUG and os.environ.get("WERKZEUG_RUN_MAIN") != "true"


def main():
    """
    主函数：创建并启动Flask应用
    """
    # 创建应用实例
    app = create_app()

    if not _is_reloader_process():
        # 启动周期聚合服务（后台线程）
        try:
            aggregator_service.start()
        except Exception as e:
            logger.error(f"启动聚合服务失败: {e}")

        # 启动心跳 WebSocket 监控服务（后台线程）
        try:
            heartbeat_service = HeartbeatWSService(
                ws_port=Config.HEARTBEAT_WS_PORT,
                timeout_seconds=Config.HEARTBEAT_TIMEOUT_SECONDS,
                check_interval_seconds=Config.HEARTBEAT_CHECK_INTERVAL_SECONDS,
                alert_cooldown_seconds=Config.HEARTBEAT_ALERT_COOLDOWN_SECONDS,
            )
            heartbeat_service.start()
        except Exception as e:
            logger.error(f"启动心跳监控服务失败: {e}")

    # 启动Flask服务器
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=Config.THREADED
    )


if __name__ == '__main__':
    main()