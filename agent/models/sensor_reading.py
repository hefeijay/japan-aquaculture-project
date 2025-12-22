#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器读数模型 - 参考 db_models/sensor_reading.py
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Float, TIMESTAMP, ForeignKey, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from .base import Base


class QualityFlag(enum.Enum):
    """质量标记枚举 - 注意：数据库存储小写，这里使用小写值"""
    OK = "ok"
    MISSING = "missing"
    ANOMALY = "anomaly"
    
    # 为了兼容，也支持大写值
    @classmethod
    def _missing_(cls, value):
        """处理大小写不匹配的情况"""
        if isinstance(value, str):
            value_lower = value.lower()
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
        return None


class SensorReading(Base):
    """传感器读数（窄表设计）"""
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("idx_sr_batch_metric_ts", "batch_id", "metric", "ts_utc"),
    )
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 注意：实际数据库表使用 sensor_id 而不是 device_id
    # 如果需要使用 device_id，需要执行数据库迁移脚本
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id"), nullable=False)
    batch_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("batches.batch_id"), nullable=True)
    pool_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # 表中有 recorded_at 和 ts_utc 两个字段，优先使用 ts_utc
    recorded_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    ts_utc: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    ts_local: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    metric: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    # 表中有 unit 字段（varchar(50)）和 type_name, description 快照字段
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    type_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quality_flag: Mapped[QualityFlag] = mapped_column(
        Enum(QualityFlag, values_callable=lambda x: [e.value for e in QualityFlag]),
        nullable=False,
        default=QualityFlag.OK
    )
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # 为了兼容性，添加 device_id 属性（映射到 sensor_id）
    @property
    def device_id(self) -> int:
        """兼容属性：将 sensor_id 映射为 device_id"""
        return self.sensor_id

