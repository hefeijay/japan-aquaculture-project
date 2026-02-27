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
from db_models.sensor_type import SensorType
from db_models.device import Device
from db_models.pond import Pond
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
                 pond_id: Optional[int] = None):
        """
        执行一次聚合任务：读取传感器与虾图像分析结果，按养殖池写入消息队列。
        若不指定 pond_id，则自动从传感器数据中发现所有有数据的池，分别生成消息；
        若时间窗口内无传感器数据，则回退到 default_pond_id。
        """
        win_mins = window_minutes or self.default_window_minutes
        # 使用 UTC naive 时间与数据库 DATETIME 对齐，避免时区比较偏差
        end_ts = datetime.utcnow()
        start_ts = end_ts - timedelta(minutes=win_mins)

        with db_session_factory() as session:
            # 确保 message_types 中存在 sensor_data 类型
            self._ensure_message_type(session, msg_type="sensor_data", icon="🛰️", color="#20B2AA", description="传感器与虾统计聚合")

            # 按 ponds.id 分组获取传感器数据，同时返回 ponds.id → Pond.pond_id（业务ID）映射
            pond_sensor_map, pond_id_map = self._fetch_sensor_payload_by_pond(session, start_ts, end_ts)

            if pond_id is not None:
                # 外部指定时按业务ID过滤（Pond.pond_id 字符串）
                target_db_ids = [db_id for db_id, biz_id in pond_id_map.items() if biz_id == str(pond_id)]
                if not target_db_ids:
                    logger.warning(f"指定的 pond_id={pond_id} 在传感器数据中未找到，跳过本次聚合")
                    return
            elif pond_sensor_map:
                target_db_ids = sorted(pond_sensor_map.keys())
            else:
                # 无传感器数据时回退到默认池，仍写入消息队列（sensors 为空列表）
                target_db_ids = [int(self.default_pond_id)]

            for p_db_id in target_db_ids:
                # 优先使用业务 pond_id（Pond.pond_id 字符串），无法取到时退化为整型主键字符串
                p_biz_id = pond_id_map.get(p_db_id, str(p_db_id))
                sensor_payload = pond_sensor_map.get(p_db_id, [])
                shrimp_payload = self._fetch_shrimp_payload(session, start_ts, end_ts, p_db_id)

                combined = {
                    "time_window": {
                        "start": start_ts.isoformat(),
                        "end": end_ts.isoformat(),
                        "minutes": win_mins
                    },
                    "pond_id": p_biz_id,
                    "sensors": sensor_payload,
                    "shrimp_stats": shrimp_payload
                }

                message_id = f"agg_{p_biz_id}_{int(time.time() * 1000)}"
                metadata = {
                    "source": "aggregator_service",
                    "window_minutes": win_mins,
                    "pond_id": p_biz_id
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
                logger.info(f"Aggregator 写入 message_queue: {message_id} (pond_id={p_biz_id})")

            session.commit()

    def _fetch_sensor_payload_by_pond(
        self, session: Session, start_ts: datetime, end_ts: datetime
    ) -> tuple[Dict[int, List[Dict[str, Any]]], Dict[int, str]]:
        """
        查询时间窗口内的所有传感器读数，JOIN Pond 表获取业务 pond_id。
        返回：
          sensor_map  — ponds.id（整型PK） → 读数列表
          pond_id_map — ponds.id（整型PK） → Pond.pond_id（业务字符串ID）
        """
        interval_minutes = int((end_ts - start_ts).total_seconds() // 60)
        readings = (
            session.query(SensorReading, Device, SensorType, Pond)
            .join(Device, SensorReading.device_id == Device.id)
            .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)
            .join(Pond, SensorReading.pond_id == Pond.id)
            .filter(and_(
                SensorReading.recorded_at >= func.date_sub(func.now(), text(f"INTERVAL {interval_minutes} MINUTE")),
                SensorReading.recorded_at <= func.now()
            ))
            .order_by(SensorReading.recorded_at.asc())
            .all()
        )
        sensor_map: Dict[int, List[Dict[str, Any]]] = {}
        pond_id_map: Dict[int, str] = {}
        logger.info(f"传感器查询原始结果: 共 {len(readings)} 条记录，时间窗口 {interval_minutes} 分钟")
        for sr, device, st, pond in readings:
            p_db_id: int = sr.pond_id
            p_biz_id: str = pond.pond_id
            pond_id_map[p_db_id] = p_biz_id
            sensor_map.setdefault(p_db_id, []).append({
                "device_id": sr.device_id,
                "device_name": getattr(device, "name", None),
                "sensor_type": st.type_name if st else None,
                "metric": sr.metric,
                "unit": sr.unit or (st.unit if st else None),
                "pond_id": p_biz_id,
                "value": sr.value,
                "recorded_at": sr.recorded_at.isoformat() if getattr(sr, "recorded_at", None) else None
            })
        logger.info(f"传感器分组结果: pond_db_id→业务id = {pond_id_map}, 各池读数条数 = { {k: len(v) for k, v in sensor_map.items()} }")
        return sensor_map, pond_id_map

    def _fetch_shrimp_payload(self, session: Session, start_ts: datetime, end_ts: datetime, pond_id: int) -> List[Dict[str, Any]]:
        interval_minutes = int((end_ts - start_ts).total_seconds() // 60)
        rows = (
            session.query(ShrimpStats)
            .filter(and_(
                ShrimpStats.pond_id == pond_id,
                ShrimpStats.created_at_source >= func.date_sub(func.now(), text(f"INTERVAL {interval_minutes} MINUTE")),
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