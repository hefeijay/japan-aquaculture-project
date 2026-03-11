#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
养殖池实时监控服务模块
提供养殖池下传感器、摄像头、设备列表、AI决策的实时数据查询，
以及设备开关控制功能。
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import Session

from config.settings import Config
from db_models.db_session import db_session_factory
from db_models.device import Device, DeviceType
from db_models.sensor_type import SensorType
from db_models.sensor_reading import SensorReading
from db_models.camera import CameraImage
from db_models.pond import Pond
from db_models.ai_decision import AIDecision
from db_models.message_queue import MessageQueue

logger = logging.getLogger(__name__)

_LOCAL_TZ = timezone(timedelta(hours=Config.LOCAL_TIMEZONE_OFFSET))


class PondRealtimeService:
    """养殖池实时监控服务类"""

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _utc_to_local(dt: Optional[datetime]) -> Optional[str]:
        """UTC datetime -> 本地时间 ISO 8601 字符串（带时区偏移）"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(_LOCAL_TZ)
        return local_dt.isoformat()

    @staticmethod
    def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, Decimal):
            return float(val)
        return float(val)

    @staticmethod
    def _get_pond_or_none(session: Session, pond_id: int) -> Optional[Pond]:
        return session.query(Pond).filter(Pond.id == pond_id).first()

    # ------------------------------------------------------------------
    # API 4: GET /v1/ponds/<pond_id>/devices
    # ------------------------------------------------------------------

    @classmethod
    def get_pond_devices(
        cls, pond_id: int, category: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        获取养殖池设备列表

        Returns:
            (data_dict, error_message)  error_message 非 None 时表示失败
        """
        try:
            with db_session_factory() as session:
                pond = cls._get_pond_or_none(session, pond_id)
                if not pond:
                    return None, "养殖池不存在"

                query = (
                    session.query(Device, DeviceType)
                    .join(DeviceType, Device.device_type_id == DeviceType.id)
                    .filter(Device.pond_id == pond_id)
                    .filter(Device.is_deleted == False)
                )
                if category:
                    query = query.filter(DeviceType.category == category)

                query = query.order_by(Device.id)
                rows = query.all()

                devices = []
                for device, device_type in rows:
                    config = device.device_specific_config or {}
                    cat = device_type.category
                    is_running = bool(config.get("is_running", False))

                    can_control = (
                        device.status == "online"
                        and device.control_mode != "ai_only"
                        and cat != "sensor"
                    )

                    devices.append(
                        {
                            "device_id": device.id,
                            "name": device.name,
                            "category": cat,
                            "category_name": device_type.name,
                            "status": device.status,
                            "is_running": is_running,
                            "control_mode": device.control_mode,
                            "can_control": can_control,
                            "location": device.location,
                        }
                    )

                data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "devices": devices,
                }
                return data, None

        except Exception as e:
            logger.error(f"获取养殖池设备列表失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}"

    # ------------------------------------------------------------------
    # API 1: GET /v1/ponds/<pond_id>/sensors/realtime
    # ------------------------------------------------------------------

    @classmethod
    def get_pond_sensors_realtime(
        cls, pond_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            with db_session_factory() as session:
                pond = cls._get_pond_or_none(session, pond_id)
                if not pond:
                    return None, "养殖池不存在"

                sensor_devices = (
                    session.query(Device, DeviceType, SensorType)
                    .join(DeviceType, Device.device_type_id == DeviceType.id)
                    .join(SensorType, Device.sensor_type_id == SensorType.id)
                    .filter(Device.pond_id == pond_id)
                    .filter(Device.is_deleted == False)
                    .filter(DeviceType.category == "sensor")
                    .order_by(Device.id)
                    .all()
                )

                sensors: List[Dict[str, Any]] = []
                for device, _dt, sensor_type in sensor_devices:
                    latest = (
                        session.query(SensorReading)
                        .filter(SensorReading.device_id == device.id)
                        .order_by(desc(SensorReading.created_at))
                        .first()
                    )

                    value = cls._safe_float(latest.value) if latest else None
                    valid_min = cls._safe_float(sensor_type.valid_min)
                    valid_max = cls._safe_float(sensor_type.valid_max)
                    recorded_at = latest.recorded_at if latest else None

                    status = "normal"
                    if value is not None:
                        if valid_min is not None and value < valid_min:
                            status = "abnormal_low"
                        elif valid_max is not None and value > valid_max:
                            status = "abnormal_high"

                    sensors.append(
                        {
                            "device_id": device.id,
                            "name": device.name,
                            "metric": sensor_type.metric,
                            "value": value,
                            "unit": sensor_type.unit,
                            "valid_min": valid_min,
                            "valid_max": valid_max,
                            "status": status,
                            "recorded_at": cls._utc_iso(recorded_at),
                            "recorded_at_local": cls._utc_to_local(recorded_at),
                        }
                    )

                data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "sensors": sensors,
                }
                return data, None

        except Exception as e:
            logger.error(f"获取传感器实时数据失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}"

    # ------------------------------------------------------------------
    # API 2: GET /v1/ponds/<pond_id>/cameras/realtime
    # ------------------------------------------------------------------

    @classmethod
    def get_pond_cameras_realtime(
        cls, pond_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            with db_session_factory() as session:
                pond = cls._get_pond_or_none(session, pond_id)
                if not pond:
                    return None, "养殖池不存在"

                camera_devices = (
                    session.query(Device, DeviceType)
                    .join(DeviceType, Device.device_type_id == DeviceType.id)
                    .filter(Device.pond_id == pond_id)
                    .filter(Device.is_deleted == False)
                    .filter(DeviceType.category == "camera")
                    .order_by(Device.id)
                    .all()
                )

                cameras: List[Dict[str, Any]] = []
                for device, _dt in camera_devices:
                    latest_img = (
                        session.query(CameraImage)
                        .filter(CameraImage.device_id == device.id)
                        .order_by(desc(CameraImage.ts_utc))
                        .first()
                    )
                    captured_at = latest_img.ts_utc if latest_img else None

                    cameras.append(
                        {
                            "device_id": device.id,
                            "name": device.name,
                            "location": device.location,
                            "status": device.status,
                            "captured_at": cls._utc_iso(captured_at),
                            "captured_at_local": cls._utc_to_local(captured_at),
                        }
                    )

                data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "cameras": cameras,
                }
                return data, None

        except Exception as e:
            logger.error(f"获取摄像头实时数据失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}"

    # ------------------------------------------------------------------
    # API 3: GET /v1/ponds/<pond_id>/cameras/<device_id>/image
    # ------------------------------------------------------------------

    @classmethod
    def get_camera_image_meta(
        cls, pond_id: int, device_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        获取摄像头最新图片的元数据（storage_url / image_url / format 等）

        Returns:
            (meta_dict, error_message, http_status_code)
        """
        try:
            with db_session_factory() as session:
                pond = cls._get_pond_or_none(session, pond_id)
                if not pond:
                    return None, "养殖池不存在", 404

                device = (
                    session.query(Device)
                    .join(DeviceType, Device.device_type_id == DeviceType.id)
                    .filter(Device.id == device_id)
                    .filter(Device.pond_id == pond_id)
                    .filter(Device.is_deleted == False)
                    .filter(DeviceType.category == "camera")
                    .first()
                )
                if not device:
                    return None, "摄像头不存在或不属于该养殖池", 404

                latest_image = (
                    session.query(CameraImage)
                    .filter(CameraImage.device_id == device_id)
                    .order_by(desc(CameraImage.ts_utc))
                    .first()
                )
                if not latest_image:
                    return None, "该摄像头暂无图片数据", 404

                meta = {
                    "storage_url": latest_image.storage_url,
                    "image_url": latest_image.image_url,
                    "format": latest_image.format or "jpeg",
                }
                return meta, None, 200

        except Exception as e:
            logger.error(f"获取摄像头图片元数据失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}", 500

    # ------------------------------------------------------------------
    # API 5: GET /v1/ponds/<pond_id>/ai-decisions/realtime
    # ------------------------------------------------------------------

    @classmethod
    def get_pond_ai_decisions_realtime(
        cls, pond_id: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            with db_session_factory() as session:
                pond = cls._get_pond_or_none(session, pond_id)
                if not pond:
                    return None, "养殖池不存在"

                pond_id_str = str(pond_id)

                # 通过 message_queue 的 message_metadata 中的 pond_id 找到关联的 message_id
                all_mq = (
                    session.query(MessageQueue.message_id, MessageQueue.message_metadata)
                    .filter(MessageQueue.message_metadata.isnot(None))
                    .all()
                )

                matching_message_ids: List[str] = []
                for msg_id, metadata_raw in all_mq:
                    try:
                        if isinstance(metadata_raw, str):
                            metadata = json.loads(metadata_raw)
                        elif isinstance(metadata_raw, dict):
                            metadata = metadata_raw
                        else:
                            continue
                        mq_pond_id = metadata.get("pond_id")
                        if str(mq_pond_id) == pond_id_str:
                            matching_message_ids.append(msg_id)
                    except (json.JSONDecodeError, TypeError):
                        continue

                decisions_list: List[Dict[str, Any]] = []

                if matching_message_ids:
                    decisions = (
                        session.query(AIDecision)
                        .filter(
                            and_(
                                AIDecision.status == "active",
                                or_(
                                    AIDecision.expires_at.is_(None),
                                    AIDecision.expires_at > datetime.now(timezone.utc),
                                ),
                                AIDecision.source_id.in_(matching_message_ids),
                            )
                        )
                        .order_by(desc(AIDecision.priority), desc(AIDecision.created_at))
                        .all()
                    )
                    for d in decisions:
                        decisions_list.append(
                            {
                                "id": d.id,
                                "decision_id": d.decision_id,
                                "type": d.type,
                                "message": d.message,
                                "action": d.action,
                                "priority": d.priority,
                                "confidence": cls._safe_float(d.confidence),
                                "status": d.status,
                                "created_at": cls._utc_iso(d.created_at),
                                "created_at_local": cls._utc_to_local(d.created_at),
                                "expires_at": cls._utc_iso(d.expires_at),
                            }
                        )

                data = {
                    "pond_id": pond.id,
                    "pond_name": pond.name,
                    "decisions": decisions_list,
                }
                return data, None

        except Exception as e:
            logger.error(f"获取AI决策实时数据失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}"

    # ------------------------------------------------------------------
    # API 6: POST /v1/devices/<device_id>/control
    # ------------------------------------------------------------------

    @classmethod
    def control_device(
        cls, device_id: int, action: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Returns:
            (data, error_message, http_status_code)
        """
        if action not in ("start", "stop"):
            return None, "action 只允许 start 或 stop", 400

        try:
            with db_session_factory() as session:
                result = (
                    session.query(Device, DeviceType)
                    .join(DeviceType, Device.device_type_id == DeviceType.id)
                    .filter(Device.id == device_id)
                    .filter(Device.is_deleted == False)
                    .first()
                )

                if not result:
                    return None, "设备不存在或已删除", 404

                device, device_type = result

                if device.status != "online":
                    return None, "设备当前离线，无法控制", 400

                if device_type.category == "sensor":
                    return None, "该设备类型不支持开关控制", 400

                if device.control_mode == "ai_only":
                    return None, "该设备为仅AI控制模式，不支持手动操作", 400

                config = device.device_specific_config or {}
                is_running = action == "start"
                config["is_running"] = is_running
                device.device_specific_config = config

                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(device, "device_specific_config")

                session.commit()

                data = {
                    "device_id": device.id,
                    "name": device.name,
                    "action": action,
                    "is_running": is_running,
                }
                return data, None, 200

        except Exception as e:
            logger.error(f"设备控制失败: {e}", exc_info=True)
            return None, f"服务器内部错误: {e}", 500
