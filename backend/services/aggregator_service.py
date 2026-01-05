#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周期聚合服务
任务：
- 周期性查询 sensor_readings 在指定时间窗口内的各类型传感器数据，结合 sensor_types 的类型映射与单位信息，按 pond 聚合生成易理解的结构化输入；
- 同时查询 shrimp_stats 在同一时间窗口内的指定养殖池（可指定，默认 0）的图像识别统计结果；
- 将两组数据拼接为一条消息，插入 message_queue，并确保 message_types 有对应类型（如 sensor_data）。
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from config.settings import Config
from db_models.db_session import db_session_factory
from db_models.sensor_reading import SensorReading
from db_models.sensor import Sensor
from db_models.sensor_type import SensorType
from db_models.message_queue import MessageQueue
from db_models.ai_decision import MessageType as MessageTypeModel
from db_models.shrimp_stats import ShrimpStats

logger = logging.getLogger(__name__)


class AggregatorService:
    def __init__(self,
                 interval_seconds: int,
                 default_window_minutes: int,
                 default_pond_id: str):
        self.interval_seconds = interval_seconds
        self.default_window_minutes = default_window_minutes
        self.default_pond_id = default_pond_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.info("AggregatorService 已在运行")
            return
        self._thread = threading.Thread(target=self._run_loop, name="AggregatorServiceThread", daemon=True)
        self._thread.start()
        logger.info(f"AggregatorService 启动，周期 {self.interval_seconds}s")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("AggregatorService 已停止")

    def _run_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Aggregator 执行异常: {e}", exc_info=True)
            # 控制周期
            elapsed = time.time() - start_time
            sleep_sec = max(0.0, self.interval_seconds - elapsed)
            if self._stop_event.wait(timeout=sleep_sec):
                break

    def run_once(self,
                 window_minutes: Optional[int] = None,
                 pond_id: Optional[str] = None):
        """
        执行一次聚合任务：读取传感器与虾图像分析结果，写入消息队列。
        """
        win_mins = window_minutes or self.default_window_minutes
        pond = pond_id or self.default_pond_id
        # 使用 UTC naive 时间与数据库 DATETIME 对齐，避免时区比较偏差
        end_ts = datetime.utcnow()
        start_ts = end_ts - timedelta(minutes=win_mins)

        with db_session_factory() as session:
            # 确保 message_types 中存在 sensor_data 类型
            self._ensure_message_type(session, msg_type="sensor_data", icon="🛰️", color="#20B2AA", description="传感器与虾统计聚合")

            sensor_payload = self._fetch_sensor_payload(session, start_ts, end_ts)
            shrimp_payload = self._fetch_shrimp_payload(session, start_ts, end_ts, pond)

            combined = {
                "time_window": {
                    "start": start_ts.isoformat(),
                    "end": end_ts.isoformat(),
                    "minutes": win_mins
                },
                "pond_id": pond,
                "sensors": sensor_payload,
                "shrimp_stats": shrimp_payload
            }

            message_id = f"agg_{int(time.time() * 1000)}"
            metadata = {
                "source": "aggregator_service",
                "window_minutes": win_mins,
                "pond_id": pond
            }

            msg = MessageQueue(
                message_id=message_id,
                content=json.dumps(combined, ensure_ascii=False),
                message_type="sensor_data",
                priority=5,
                status='pending',
                retry_count=0,
                max_retries=3,
                message_metadata=json.dumps(metadata, ensure_ascii=False),
                consumed_at=None,
                completed_at=None,
                error_message=None,
                expires_at=None
            )
            session.add(msg)
            session.commit()
            logger.info(f"Aggregator 写入 message_queue: {message_id}")

    def _fetch_sensor_payload(self, session: Session, start_ts: datetime, end_ts: datetime) -> List[Dict[str, Any]]:
        # 查询窗口内的读数，联表拿到类型与池塘信息，直接返回原始记录列表
        readings = (
            session.query(SensorReading, Sensor, SensorType)
            .join(Sensor, SensorReading.sensor_id == Sensor.id)
            .join(SensorType, Sensor.sensor_type_id == SensorType.id)
            .filter(and_(
                SensorReading.recorded_at >= func.date_sub(func.now(), text(f"INTERVAL {int((end_ts - start_ts).total_seconds() // 60)} MINUTE")),
                SensorReading.recorded_at <= func.now()
            ))
            .order_by(SensorReading.recorded_at.asc())
            .all()
        )
        payload: List[Dict[str, Any]] = []
        for sr, sensor, st in readings:
            payload.append({
                "sensor_id": sr.sensor_id,
                "sensor_name": getattr(sensor, "name", None),
                "sensor_type": st.type_name,
                "unit": st.unit,
                "pond_id": str(getattr(sensor, "pond_id", "")),
                "value": sr.value,
                "recorded_at": sr.recorded_at.isoformat() if getattr(sr, "recorded_at", None) else None
            })
        return payload

    def _fetch_shrimp_payload(self, session: Session, start_ts: datetime, end_ts: datetime, pond_id: str) -> List[Dict[str, Any]]:
        rows = (
            session.query(ShrimpStats)
            .filter(and_(
                ShrimpStats.pond_id == pond_id,
                ShrimpStats.created_at_source >= func.date_sub(func.now(), text(f"INTERVAL {int((end_ts - start_ts).total_seconds() // 60)} MINUTE")),
                ShrimpStats.created_at_source <= func.now()
            ))
            .order_by(ShrimpStats.created_at_source.asc())
            .all()
        )
        payload = []
        for r in rows:
            payload.append({
                "created_at_source": r.created_at_source.isoformat() if r.created_at_source else None,
                "total_live": r.total_live,
                "total_dead": r.total_dead,
                "size_mean_cm": r.size_mean_cm,
                "weight_mean_g": r.weight_mean_g,
                "source_file": r.source_file,
                "conf": r.conf,
                "iou": r.iou
            })
        return payload

    def _ensure_message_type(self, session: Session, msg_type: str, icon: str, color: str, description: str):
        try:
            existing = session.query(MessageTypeModel).filter(MessageTypeModel.type == msg_type).first()
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    session.commit()
                return
            mt = MessageTypeModel(type=msg_type, icon=icon, color=color, description=description, is_active=True)
            session.add(mt)
            session.commit()
        except Exception as e:
            logger.warning(f"确保 message_types 存在失败: {e}")


# 全局实例，供主入口启动
aggregator_service = AggregatorService(
    interval_seconds=Config.AGGREGATOR_INTERVAL_SECONDS,
    default_window_minutes=Config.AGGREGATOR_DEFAULT_WINDOW_MINUTES,
    default_pond_id=Config.AGGREGATOR_DEFAULT_POND_ID,
)