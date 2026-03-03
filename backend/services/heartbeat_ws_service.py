#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心跳 WebSocket 监控服务

在独立线程中运行 asyncio WebSocket 服务端，接收 ai_japan 客户端的心跳消息。
后台监控线程定期检查最后一次心跳时间，超时则通过钉钉发送报警通知。
客户端重连后自动发送恢复通知。
"""

import asyncio
import threading
import time
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))


class HeartbeatWSService:
    """WebSocket 心跳监控服务"""

    def __init__(
        self,
        ws_port: int = 8001,
        timeout_seconds: int = 300,
        check_interval_seconds: int = 30,
        alert_cooldown_seconds: int = 3600,
    ):
        self.ws_port = ws_port
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval_seconds
        self.alert_cooldown = alert_cooldown_seconds

        # 心跳状态（受 _lock 保护）
        self.last_heartbeat: float | None = None
        self.client_connected = False
        self.alert_sent = False
        self.last_alert_time: float | None = None

        self._lock = threading.Lock()
        self._active_ws: object | None = None  # 当前活跃的 WebSocket 连接

        # 线程控制
        self._stop_event = threading.Event()
        self._ws_thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ------------------------------------------------------------------
    # WebSocket 服务端
    # ------------------------------------------------------------------

    async def _handle_client(self, websocket):
        """处理单个客户端连接（仅允许一个活跃连接，新连接会踢掉旧连接）"""
        client_addr = websocket.remote_address
        logger.info("心跳客户端已连接: %s", client_addr)

        with self._lock:
            old_ws = self._active_ws
            self._active_ws = websocket

            was_alerted = self.alert_sent
            old_last_heartbeat = self.last_heartbeat

            self.client_connected = True
            self.last_heartbeat = time.time()
            self.alert_sent = False

        if old_ws is not None:
            logger.warning("踢掉旧的心跳客户端连接，仅保留最新连接: %s", client_addr)
            await old_ws.close(1000, "replaced by new client")

        if was_alerted:
            self._send_recovery_notification(old_last_heartbeat)

        try:
            async for message in websocket:
                if message == "ping":
                    with self._lock:
                        self.last_heartbeat = time.time()
                    await websocket.send("pong")
                    logger.debug("收到心跳 ping，已回复 pong")
        except Exception as e:
            logger.warning("WebSocket 连接异常: %s", e)
        finally:
            with self._lock:
                if self._active_ws is websocket:
                    self._active_ws = None
                    self.client_connected = False
            logger.info("心跳客户端已断开: %s", client_addr)

    async def _run_ws_server(self):
        """启动 WebSocket 服务端"""
        import websockets

        async with websockets.serve(self._handle_client, "0.0.0.0", self.ws_port):
            logger.info("心跳 WebSocket 服务端已启动，监听端口 %s", self.ws_port)
            while not self._stop_event.is_set():
                await asyncio.sleep(1)

    def _ws_thread_target(self):
        """WebSocket 服务端线程入口"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_ws_server())
        except Exception as e:
            logger.error("WebSocket 服务端线程异常退出: %s", e)
        finally:
            self._loop.close()

    # ------------------------------------------------------------------
    # 心跳超时监控
    # ------------------------------------------------------------------

    def _monitor_thread_target(self):
        """心跳超时监控线程"""
        logger.info(
            "心跳监控线程已启动 (超时=%ds, 检查间隔=%ds, 报警冷却=%ds)",
            self.timeout_seconds, self.check_interval, self.alert_cooldown,
        )

        while not self._stop_event.is_set():
            self._stop_event.wait(self.check_interval)
            if self._stop_event.is_set():
                break

            with self._lock:
                last_hb = self.last_heartbeat
                already_alerted = self.alert_sent
                last_alert_t = self.last_alert_time

            if last_hb is None:
                continue

            elapsed = time.time() - last_hb

            if elapsed > self.timeout_seconds and not already_alerted:
                can_alert = (
                    last_alert_t is None
                    or (time.time() - last_alert_t) > self.alert_cooldown
                )
                if can_alert:
                    self._send_timeout_alert(elapsed, last_hb)
                    with self._lock:
                        self.alert_sent = True
                        self.last_alert_time = time.time()

        logger.info("心跳监控线程已停止")

    # ------------------------------------------------------------------
    # 钉钉通知
    # ------------------------------------------------------------------

    def _send_timeout_alert(self, elapsed_seconds: float, last_hb: float):
        """发送心跳超时报警，last_hb 为监控线程快照的最后心跳时间戳"""
        from utils.dingtalk import send_dingtalk_message

        last_hb_time = datetime.fromtimestamp(last_hb, tz=JST).strftime("%Y-%m-%d %H:%M:%S")
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)

        msg = (
            f"⚠️ 【日本养殖基地网络告警】\n"
            f"检测到 ai_japan 客户端心跳超时！\n"
            f"最后心跳时间: {last_hb_time} (JST)\n"
            f"已超时: {minutes}分{seconds}秒\n"
            f"可能原因: 网络断开 / 设备断电 / 程序异常退出\n"
            f"请及时检查！"
        )

        logger.warning("心跳超时，发送钉钉报警: elapsed=%.0fs", elapsed_seconds)
        send_dingtalk_message(msg, is_at_all=True)

    def _send_recovery_notification(self, old_last_heartbeat: float | None):
        """发送连接恢复通知，old_last_heartbeat 为断线前最后一次心跳时间戳"""
        from utils.dingtalk import send_dingtalk_message

        now = time.time()
        now_str = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S")

        offline_duration = ""
        if old_last_heartbeat is not None:
            duration = now - old_last_heartbeat
            minutes = int(duration // 60)
            offline_duration = f"\n断线持续时长: 约{minutes}分钟"

        msg = (
            f"✅ 【日本养殖基地网络恢复】\n"
            f"ai_japan 客户端已重新连接！\n"
            f"恢复时间: {now_str} (JST)"
            f"{offline_duration}"
        )

        logger.info("客户端重连，发送恢复通知")
        send_dingtalk_message(msg, is_at_all=True)

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self):
        """启动心跳 WebSocket 服务（非阻塞）"""
        if self._ws_thread and self._ws_thread.is_alive():
            logger.warning("心跳 WebSocket 服务已在运行，跳过重复启动")
            return

        self._stop_event.clear()

        self._ws_thread = threading.Thread(target=self._ws_thread_target, name="heartbeat-ws", daemon=True)
        self._ws_thread.start()

        self._monitor_thread = threading.Thread(target=self._monitor_thread_target, name="heartbeat-monitor", daemon=True)
        self._monitor_thread.start()

        logger.info("心跳监控服务已启动 (ws_port=%s)", self.ws_port)

    def stop(self):
        """停止心跳 WebSocket 服务"""
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("心跳监控服务已停止")
