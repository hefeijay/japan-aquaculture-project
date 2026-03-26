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
from services.weather_cache_service import weather_cache_service

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

        # 启动天气缓存更新服务（后台线程）
        try:
            weather_cache_service.start()
        except Exception as e:
            logger.error(f"启动天气缓存服务失败: {e}")

        # 启动心跳 WebSocket 监控服务（后台线程）
        heartbeat_service = None
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

        # 启动 MQTT 设备控制服务（后台线程）
        try:
            from services.mqtt_service import MQTTService
            MQTTService.init()
        except Exception as e:
            logger.error(f"启动 MQTT 服务失败: {e}")

        # 启动设备连接监控服务（后台线程）
        try:
            from services.device_monitor_service import DeviceMonitorService
            device_monitor = DeviceMonitorService(
                mqtt_check_interval=Config.DEVICE_MQTT_CHECK_INTERVAL,
                mqtt_timeout=Config.DEVICE_MQTT_TIMEOUT,
                mqtt_probe_wait=Config.DEVICE_MQTT_PROBE_WAIT,
                api_check_interval=Config.DEVICE_API_CHECK_INTERVAL,
                api_connect_timeout=Config.DEVICE_API_CONNECT_TIMEOUT,
                api_offline_timeout=Config.DEVICE_API_OFFLINE_TIMEOUT,
                alert_cooldown=Config.DEVICE_ALERT_COOLDOWN,
                heartbeat_service=heartbeat_service,
            )
            device_monitor.start()
        except Exception as e:
            logger.error(f"启动设备监控服务失败: {e}")

    # 启动Flask服务器
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=Config.THREADED
    )


if __name__ == '__main__':
    main()