#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT 设备控制服务模块
负责与 MQTT Broker 通信，实现设备控制指令下发、设备状态接收与同步。
ESP32 设备通过 MAC 地址标识，MAC 存储在 devices.connection_info["mac_address"] 中。
"""

import json
import logging
import uuid
import threading
from typing import Optional

import paho.mqtt.client as mqtt

from config.settings import Config
from db_models.db_session import db_session_factory
from db_models.device import Device

logger = logging.getLogger(__name__)


class MQTTService:
    """MQTT 客户端服务 - 单例，随 Flask 应用启动"""

    _client: Optional[mqtt.Client] = None
    _connected = False
    _lock = threading.Lock()

    @classmethod
    def init(cls):
        """初始化并启动 MQTT 客户端（异步连接，后台线程维护）"""
        broker = Config.MQTT_BROKER_HOST
        port = Config.MQTT_BROKER_PORT
        if not broker:
            logger.warning("MQTT_BROKER_HOST 未配置，MQTT 服务未启动")
            return

        cls._client = mqtt.Client(
            client_id="flask-backend",
            protocol=mqtt.MQTTv311,
        )
        cls._client.username_pw_set(Config.MQTT_USER, Config.MQTT_PASSWORD)
        cls._client.on_connect = cls._on_connect
        cls._client.on_message = cls._on_message
        cls._client.on_disconnect = cls._on_disconnect

        cls._client.connect_async(broker, port, keepalive=60)
        cls._client.loop_start()
        logger.info(f"MQTT 客户端正在连接 {broker}:{port}")

    # ----------------------------------------------------------------
    # 连接回调
    # ----------------------------------------------------------------

    @classmethod
    def _on_connect(cls, client, userdata, flags, rc):
        if rc == 0:
            cls._connected = True
            logger.info("MQTT 连接成功")
            client.subscribe("aqua/devices/+/status")
            client.subscribe("aqua/devices/+/response")
            client.subscribe("aqua/devices/+/online")
        else:
            logger.error(f"MQTT 连接失败, rc={rc}")

    @classmethod
    def _on_disconnect(cls, client, userdata, rc):
        cls._connected = False
        logger.warning(f"MQTT 断开连接, rc={rc}")

    # ----------------------------------------------------------------
    # 消息路由
    # ----------------------------------------------------------------

    @classmethod
    def _on_message(cls, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            parts = topic.split("/")
            # topic 格式: aqua/devices/{mac}/{type}
            if len(parts) != 4:
                return
            mac = parts[2]
            msg_type = parts[3]

            if msg_type == "online":
                cls._handle_online(mac, payload)
            elif msg_type == "status":
                cls._handle_status(mac, payload)
            elif msg_type == "response":
                cls._handle_response(mac, payload)
        except Exception as e:
            logger.error(f"处理 MQTT 消息异常: {e}", exc_info=True)

    # ----------------------------------------------------------------
    # 通过 MAC 查找设备
    # ----------------------------------------------------------------

    @classmethod
    def _find_device_by_mac(cls, session, mac: str) -> Optional[Device]:
        """
        在 devices 表中查找 connection_info->>'mac_address' == mac 的设备。
        MySQL JSON 查询: JSON_UNQUOTE(JSON_EXTRACT(connection_info, '$.mac_address'))
        """
        from sqlalchemy import func

        device = (
            session.query(Device)
            .filter(
                func.json_unquote(
                    func.json_extract(Device.connection_info, "$.mac_address")
                ) == mac,
                Device.is_deleted == False,
            )
            .first()
        )
        return device

    # ----------------------------------------------------------------
    # 处理设备上线/离线
    # ----------------------------------------------------------------

    @classmethod
    def _handle_online(cls, mac: str, payload: dict):
        online = payload.get("online", False)
        state = "connected" if online else "disconnected"
        try:
            with db_session_factory() as session:
                device = cls._find_device_by_mac(session, mac)
                if device:
                    config = device.device_specific_config or {}
                    config["mqtt_connected"] = online
                    device.device_specific_config = config

                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(device, "device_specific_config")
                    session.commit()
                    logger.info(f"设备 MAC={mac} ({device.name}) MQTT {state}")
                else:
                    logger.warning(f"收到未注册设备的上线消息: MAC={mac}")
        except Exception as e:
            logger.error(f"更新设备MQTT连接状态失败: {e}", exc_info=True)

    # ----------------------------------------------------------------
    # 处理设备周期状态上报
    # ----------------------------------------------------------------

    @classmethod
    def _handle_status(cls, mac: str, payload: dict):
        try:
            with db_session_factory() as session:
                device = cls._find_device_by_mac(session, mac)
                if not device:
                    return

                config = device.device_specific_config or {}
                config["ip"] = payload.get("ip", "")
                config["rssi"] = payload.get("rssi", 0)
                config["uptime_s"] = payload.get("uptime_s", 0)
                config["last_heartbeat"] = payload.get("uptime_s", 0)
                device.device_specific_config = config

                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(device, "device_specific_config")
                session.commit()
        except Exception as e:
            logger.error(f"处理状态上报失败: {e}", exc_info=True)

    # ----------------------------------------------------------------
    # 处理控制指令回复
    # ----------------------------------------------------------------

    @classmethod
    def _handle_response(cls, mac: str, payload: dict):
        request_id = payload.get("request_id", "")
        success = payload.get("success", False)
        message = payload.get("message", "")

        logger.info(
            f"设备 MAC={mac} 回复: request_id={request_id}, "
            f"success={success}, message={message}"
        )

        if success:
            try:
                with db_session_factory() as session:
                    device = cls._find_device_by_mac(session, mac)
                    if device:
                        config = device.device_specific_config or {}
                        last_command = config.get("last_command", "")
                        is_running = (last_command == "start")
                        config["is_running"] = is_running
                        device.device_specific_config = config
                        device.status = "online" if is_running else "offline"

                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(device, "device_specific_config")
                        session.commit()
                        logger.info(
                            f"设备 MAC={mac} 控制确认: "
                            f"is_running={is_running}, status={device.status}"
                        )
            except Exception as e:
                logger.error(f"更新控制结果失败: {e}", exc_info=True)

    # ----------------------------------------------------------------
    # 发布控制指令
    # ----------------------------------------------------------------

    @classmethod
    def publish_control(cls, mac: str, action: str) -> Optional[str]:
        """
        向指定 MAC 的设备发布控制指令。

        Args:
            mac: 设备 MAC 地址（去冒号小写，如 aabbccddeeff）
            action: 控制动作 (start/stop)

        Returns:
            request_id: 请求ID，用于追踪回复；None 表示发送失败
        """
        if not cls._client or not cls._connected:
            logger.error("MQTT 未连接，无法发送控制指令")
            return None

        request_id = uuid.uuid4().hex[:8]
        payload = {
            "action": action,
            "request_id": request_id,
        }
        topic = f"aqua/devices/{mac}/control"
        cls._client.publish(topic, json.dumps(payload), qos=1)
        logger.info(f"已发布: {topic} → {payload}")
        return request_id

    # ----------------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------------

    @classmethod
    def is_connected(cls) -> bool:
        return cls._connected

    @classmethod
    def shutdown(cls):
        if cls._client:
            cls._client.loop_stop()
            cls._client.disconnect()
            logger.info("MQTT 客户端已关闭")
