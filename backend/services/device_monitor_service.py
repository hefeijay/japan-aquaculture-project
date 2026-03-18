#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备连接状态监控服务

在后台线程中定期探测所有可监控设备的连接状态，自动管理 device.status 字段。
- MAC 设备（水泵、鼓风机等）：通过已有 MQTTService 连接发送 status 查询
- API 设备（feeder）：通过 HTTP 连接测试
- Camera / Sensor：不参与监控，保持默认 online

状态机：online → offline → disabled（超时报警）→ online（恢复通知）
"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm.attributes import flag_modified

from config.settings import Config
from db_models.db_session import db_session_factory
from db_models.device import Device, DeviceType

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=Config.LOCAL_TIMEZONE_OFFSET))

MAC_CATEGORIES = (
    "water_pump", "air_blower", "water_switch",
    "solar_heater_pump", "air_pump", "physical_filter",
)

STATUS_LABELS = {
    "online": "在线",
    "offline": "离线",
    "disabled": "已禁用",
}


class DeviceMonitorService:
    """设备连接状态监控服务"""

    def __init__(
        self,
        mqtt_check_interval: int = 30,
        mqtt_timeout: int = 600,
        mqtt_probe_wait: int = 10,
        api_check_interval: int = 120,
        api_connect_timeout: int = 10,
        alert_cooldown: int = 3600,
        heartbeat_service=None,
    ):
        self.mqtt_check_interval = mqtt_check_interval
        self.mqtt_timeout = mqtt_timeout
        self.mqtt_probe_wait = mqtt_probe_wait
        self.api_check_interval = api_check_interval
        self.api_connect_timeout = api_connect_timeout
        self.alert_cooldown = alert_cooldown
        self._heartbeat_service = heartbeat_service

        # 每个设备的上次报警时间 {device.id: timestamp}
        self._last_alert_time: Dict[int, float] = {}

        self._stop_event = threading.Event()
        self._mqtt_thread: Optional[threading.Thread] = None
        self._api_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self):
        if self._mqtt_thread and self._mqtt_thread.is_alive():
            logger.warning("设备监控服务已在运行，跳过重复启动")
            return

        self._stop_event.clear()

        self._mqtt_thread = threading.Thread(
            target=self._monitor_mqtt_devices,
            name="device-monitor-mqtt",
            daemon=True,
        )
        self._mqtt_thread.start()

        self._api_thread = threading.Thread(
            target=self._monitor_api_devices,
            name="device-monitor-api",
            daemon=True,
        )
        self._api_thread.start()

        logger.info(
            "设备监控服务已启动 (mqtt_interval=%ds, mqtt_timeout=%ds, "
            "api_interval=%ds, alert_cooldown=%ds)",
            self.mqtt_check_interval, self.mqtt_timeout,
            self.api_check_interval, self.alert_cooldown,
        )

    def stop(self):
        self._stop_event.set()
        logger.info("设备监控服务已停止")

    # ------------------------------------------------------------------
    # 整站断网判断
    # ------------------------------------------------------------------

    def _is_site_offline(self) -> bool:
        if self._heartbeat_service is None:
            return False
        with self._heartbeat_service._lock:
            return self._heartbeat_service.alert_sent

    # ------------------------------------------------------------------
    # MAC 设备监控线程
    # ------------------------------------------------------------------

    def _monitor_mqtt_devices(self):
        logger.info("MAC 设备监控线程已启动")

        # 等待 MQTT 连接就绪后立刻做第一轮探测
        from services.mqtt_service import MQTTService
        for _ in range(30):
            if self._stop_event.is_set():
                return
            if MQTTService.is_connected():
                break
            self._stop_event.wait(1)

        if not self._stop_event.is_set() and MQTTService.is_connected():
            logger.info("MQTT 已就绪，执行首轮 MAC 设备探测")
            try:
                self._probe_mqtt_devices()
            except Exception as e:
                logger.error(f"首轮 MAC 设备探测异常: {e}", exc_info=True)

        while not self._stop_event.is_set():
            self._stop_event.wait(self.mqtt_check_interval)
            if self._stop_event.is_set():
                break

            if self._is_site_offline():
                logger.debug("整站断网中，跳过 MAC 设备探测")
                continue

            try:
                self._probe_mqtt_devices()
            except Exception as e:
                logger.error(f"MAC 设备探测异常: {e}", exc_info=True)

        logger.info("MAC 设备监控线程已停止")

    def _probe_mqtt_devices(self):
        from services.mqtt_service import MQTTService

        if not MQTTService.is_connected():
            logger.debug("MQTT 未连接，跳过本轮 MAC 设备探测")
            return

        # 第 1 步：查出所有 MAC 类设备（含无 mac_address 的）
        with db_session_factory() as session:
            rows = (
                session.query(Device, DeviceType)
                .join(DeviceType, Device.device_type_id == DeviceType.id)
                .filter(DeviceType.category.in_(MAC_CATEGORIES))
                .filter(Device.is_deleted == False)
                .all()
            )

            if not rows:
                logger.info("当前无 MAC 设备，跳过 MAC 设备探测")
                return

            # 分离：有 MAC 地址的可探测，没有的直接设 offline
            probeable: List[Tuple[int, str]] = []
            for device, dt in rows:
                conn = device.connection_info or {}
                mac = conn.get("mac_address")
                if mac:
                    mac = mac.replace(":", "").replace("-", "").lower()
                    probeable.append((device.id, mac))
                else:
                    if device.status != "offline":
                        device.status = "offline"
                        flag_modified(device, "device_specific_config")

            session.commit()

        if not probeable:
            logger.info("当前无带 MAC 地址的设备，跳过 MAC 设备探测")
            return

        logger.info("正在探测 %d 台 MAC 设备连接状态", len(probeable))
        # 第 2 步：发探测指令
        for _device_id, mac in probeable:
            MQTTService.publish_status_query(mac)

        # 第 3 步：等待设备回复
        self._stop_event.wait(self.mqtt_probe_wait)
        if self._stop_event.is_set():
            return

        # 第 4 步：检查结果
        now = time.time()
        with db_session_factory() as session:
            device_ids = [did for did, _ in probeable]
            devices = (
                session.query(Device)
                .filter(Device.id.in_(device_ids))
                .all()
            )
            for device in devices:
                config = device.device_specific_config or {}
                last_ts = config.get("last_heartbeat_ts")

                if last_ts is not None and (now - last_ts) < (self.mqtt_probe_wait + 5):
                    probe_success = True
                else:
                    probe_success = False

                self._update_device_status(session, device, probe_success, now)
                status_label = "online" if probe_success else "offline"
                logger.info("设备 %s (%s) MAC 探测: %s", device.name, device.id, status_label)

            session.commit()

    # ------------------------------------------------------------------
    # API 设备 (feeder) 监控线程
    # ------------------------------------------------------------------

    def _monitor_api_devices(self):
        logger.info("API 设备监控线程已启动")

        # 启动后立刻做第一轮探测
        if not self._stop_event.is_set():
            logger.info("执行首轮 API 设备探测")
            try:
                self._probe_api_devices()
            except Exception as e:
                logger.error(f"首轮 API 设备探测异常: {e}", exc_info=True)

        while not self._stop_event.is_set():
            self._stop_event.wait(self.api_check_interval)
            if self._stop_event.is_set():
                break

            if self._is_site_offline():
                logger.debug("整站断网中，跳过 API 设备探测")
                continue

            try:
                self._probe_api_devices()
            except Exception as e:
                logger.error(f"API 设备探测异常: {e}", exc_info=True)

        logger.info("API 设备监控线程已停止")

    def _probe_api_devices(self):
        from services.device_service import DeviceConnectionTester

        with db_session_factory() as session:
            rows = (
                session.query(Device, DeviceType)
                .join(DeviceType, Device.device_type_id == DeviceType.id)
                .filter(DeviceType.category == "feeder")
                .filter(Device.is_deleted == False)
                .all()
            )

            if not rows:
                logger.info("当前无 API 设备，跳过 API 设备探测")
                return

            logger.info("正在探测 %d 台 API 设备连接状态", len(rows))
            now = time.time()
            results: Dict[int, bool] = {}

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for device, dt in rows:
                    future = executor.submit(
                        DeviceConnectionTester.test_connection,
                        dt.category,
                        device.connection_info or {},
                        self.api_connect_timeout,
                    )
                    futures[future] = device.id

                for future in as_completed(futures):
                    device_id = futures[future]
                    try:
                        result = future.result()
                        results[device_id] = result.get("success", False)
                    except Exception:
                        results[device_id] = False

            for device, dt in rows:
                probe_success = results.get(device.id, False)
                self._update_device_status(session, device, probe_success, now)
                status_label = "online" if probe_success else "offline"
                logger.info("设备 %s (%s) API 探测: %s", device.name, device.id, status_label)

            session.commit()

    # ------------------------------------------------------------------
    # 状态转换核心逻辑
    # ------------------------------------------------------------------

    def _update_device_status(self, session, device: Device, probe_success: bool, now: float):
        config = device.device_specific_config or {}
        last_ts = config.get("last_heartbeat_ts")
        now_iso = datetime.now(tz=JST).isoformat()
        old_status = device.status

        if probe_success:
            device.status = "online"
            config.pop("disabled_reason", None)
            config["last_connection_check"] = now_iso

            if old_status == "disabled":
                self._send_recovery_alert(device, config, last_ts, now)

            config["last_heartbeat_ts"] = now

        else:
            config["last_connection_check"] = now_iso

            if last_ts is None:
                device.status = "offline"
            else:
                elapsed = now - last_ts
                if elapsed >= self.mqtt_timeout:
                    if old_status != "disabled":
                        device.status = "disabled"
                        config["disabled_reason"] = f"超过{int(elapsed)}秒无响应"
                        self._send_offline_alert(device, config, elapsed, last_ts)
                else:
                    device.status = "offline"

        device.device_specific_config = config
        flag_modified(device, "device_specific_config")

    # ------------------------------------------------------------------
    # 钉钉通知
    # ------------------------------------------------------------------

    def _can_alert(self, device_id: int, now: float) -> bool:
        last = self._last_alert_time.get(device_id)
        if last is None:
            return True
        return (now - last) > self.alert_cooldown

    def _send_offline_alert(self, device: Device, config: dict, elapsed: float, last_ts: float):
        now = time.time()
        if not self._can_alert(device.id, now):
            logger.debug(f"设备 {device.name} 报警冷却中，跳过")
            return

        from utils.dingtalk import send_dingtalk_message

        last_online = datetime.fromtimestamp(last_ts, tz=JST).strftime("%Y-%m-%d %H:%M:%S")
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        pond_name = self._get_pond_name(device.pond_id)
        device_type_name = self._get_device_type_name(device.device_type_id)

        msg = (
            f"⚠️ 【设备连接异常报警】\n"
            f"设备名称: {device.name}\n"
            f"设备ID: {device.device_id}\n"
            f"所属养殖池: {pond_name}\n"
            f"设备类型: {device_type_name}\n"
            f"最后在线时间: {last_online} (JST)\n"
            f"已超时: {minutes}分{seconds}秒无响应\n"
            f"状态已设为: 已禁用（不再重复报警，持续检测中）\n"
            f"请及时检查设备！"
        )

        logger.warning(f"设备 {device.name} 连接超时，发送钉钉报警: elapsed={elapsed:.0f}s")
        send_dingtalk_message(msg, is_at_all=True)
        self._last_alert_time[device.id] = now

    def _send_recovery_alert(self, device: Device, config: dict, last_ts: Optional[float], now: float):
        from utils.dingtalk import send_dingtalk_message

        now_str = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S")
        pond_name = self._get_pond_name(device.pond_id)

        offline_duration = ""
        if last_ts is not None:
            duration = now - last_ts
            minutes = int(duration // 60)
            offline_duration = f"\n离线持续时长: 约{minutes}分钟"

        msg = (
            f"✅ 【设备连接恢复】\n"
            f"设备名称: {device.name}\n"
            f"设备ID: {device.device_id}\n"
            f"所属养殖池: {pond_name}\n"
            f"恢复时间: {now_str} (JST)"
            f"{offline_duration}\n"
            f"设备状态已恢复为: 在线"
        )

        logger.info(f"设备 {device.name} 连接恢复，发送钉钉通知")
        send_dingtalk_message(msg, is_at_all=True)
        self._last_alert_time.pop(device.id, None)

    # ------------------------------------------------------------------
    # 辅助查询
    # ------------------------------------------------------------------

    @staticmethod
    def _get_pond_name(pond_id: int) -> str:
        try:
            from db_models.pond import Pond
            with db_session_factory() as session:
                pond = session.query(Pond).filter(Pond.id == pond_id).first()
                return pond.name if pond else f"养殖池{pond_id}"
        except Exception:
            return f"养殖池{pond_id}"

    @staticmethod
    def _get_device_type_name(device_type_id: int) -> str:
        try:
            with db_session_factory() as session:
                dt = session.query(DeviceType).filter(DeviceType.id == device_type_id).first()
                return dt.name if dt else "未知类型"
        except Exception:
            return "未知类型"
