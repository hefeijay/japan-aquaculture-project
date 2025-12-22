#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShrimpStats ORM 模型
对应图像识别统计结果表 `shrimp_stats`
符合数据处理计划要求，包含帧ID、时间戳、检测结果、模型信息等字段
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import (
    Integer, 
    String, 
    TIMESTAMP, 
    BIGINT, 
    Float, 
    DECIMAL,
    Boolean,
    Text,
    Index,
    BigInteger,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ShrimpStats(Base):
    __tablename__ = "shrimp_stats"
    __table_args__ = (
        Index("idx_id_frame", "frame_id"),
        Index("idx_id_ts", "ts_utc"),
        Index("idx_id_modelver", "model_name", "model_version"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True, init=False)
    
    # 图像帧ID（FK，关联到camera_images或image_frames表）
    frame_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        comment="图像帧ID（FK）",
        init=False
    )
    
    # UTC时间戳（推理时间）
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="UTC时间戳（推理）",
        init=False
    )
    
    uuid: Mapped[Optional[str]] = mapped_column(String(36))
    pond_id: Mapped[str] = mapped_column(String(255))
    input_subdir: Mapped[str] = mapped_column(String(255))
    output_dir: Mapped[str] = mapped_column(String(512))
    created_at_source_iso: Mapped[str] = mapped_column(String(64))
    created_at_source: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    
    # 置信度（保留原有字段）
    conf: Mapped[Optional[float]] = mapped_column(Float)
    
    # 平均置信度
    confidence_avg: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 4),
        comment="平均置信度",
        init=False
    )
    
    iou: Mapped[Optional[float]] = mapped_column(Float)
    total_live: Mapped[int] = mapped_column(Integer)
    
    # 检测数量
    count: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="检测数量",
        init=False
    )
    
    total_dead: Mapped[int] = mapped_column(Integer)
    size_min_cm: Mapped[Optional[float]] = mapped_column(Float)
    size_max_cm: Mapped[Optional[float]] = mapped_column(Float)
    size_mean_cm: Mapped[Optional[float]] = mapped_column(Float)
    
    # 平均长度（毫米）
    avg_length_mm: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 3),
        comment="平均长度（毫米）",
        init=False
    )
    
    # 平均高度（毫米）
    avg_height_mm: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 3),
        comment="平均高度（毫米）",
        init=False
    )
    
    size_median_cm: Mapped[Optional[float]] = mapped_column(Float)
    weight_min_g: Mapped[Optional[float]] = mapped_column(Float)
    weight_max_g: Mapped[Optional[float]] = mapped_column(Float)
    weight_mean_g: Mapped[Optional[float]] = mapped_column(Float)
    
    # 平均估算体重（克）
    est_weight_g_avg: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 3),
        comment="平均估算体重（克）",
        init=False
    )
    
    # 是否存在饲料（布尔）
    feed_present: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否存在饲料（布尔）",
        init=False
    )
    
    # 是否存在虾皮（布尔）
    shrimp_shell_present: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否存在虾皮（布尔）",
        init=False
    )
    
    # 模型名称
    model_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="模型名称",
        init=False
    )
    
    # 模型版本
    model_version: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="模型版本",
        init=False
    )
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="备注",
        init=False
    )
    
    weight_median_g: Mapped[Optional[float]] = mapped_column(Float)
    source_file: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)