#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShrimpStats ORM 模型
对应图像识别统计结果表 `shrimp_stats`
符合数据处理计划要求，包含帧ID、时间戳、检测结果、模型信息等字段
常见查询：按池子查时间范围、按批次查时间范围、按模型版本统计
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
    ForeignKey,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ShrimpStats(Base):
    """
    图像识别统计结果表
    常见查询：按池子查时间范围、按批次查时间范围、按模型版本统计
    """
    __tablename__ = "shrimp_stats"
    __table_args__ = (
        Index("idx_ss_frame", "frame_id"),
        Index("idx_ss_ts", "ts_utc"),
        Index("idx_shrimp_stats_pond_ts", "pond_id", "ts_utc"),
        Index("idx_id_modelver", "model_name", "model_version"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 图像帧ID（FK -> camera_images）
    frame_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("camera_images.id"),
        comment="图像帧ID（FK -> camera_images）",
        init=False
    )
    
    # UTC时间戳（推理时间）
    ts_utc: Mapped[datetime] = mapped_column(
        DATETIME(3),
        nullable=False,
        comment="UTC时间戳（推理时间）"
    )
    
    uuid: Mapped[Optional[str]] = mapped_column(
        String(36),
        comment="UUID",
        init=False
    )
    
    # 所属养殖池ID（FK）
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）"
    )
    
    input_subdir: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="输入子目录",
        init=False
    )
    output_dir: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="输出目录",
        init=False
    )
    created_at_source_iso: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="源创建时间ISO",
        init=False
    )
    created_at_source: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        comment="源创建时间",
        init=False
    )
    
    # 置信度（原有字段）
    conf: Mapped[Optional[float]] = mapped_column(
        Float,
        comment="置信度（原有字段）",
        init=False
    )
    
    # 平均置信度
    confidence_avg: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 4),
        comment="平均置信度",
        init=False
    )
    
    iou: Mapped[Optional[float]] = mapped_column(Float, comment="IOU", init=False)
    total_live: Mapped[Optional[int]] = mapped_column(Integer, comment="活虾总数", init=False)
    
    # 检测数量
    count: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="检测数量",
        init=False
    )
    
    total_dead: Mapped[Optional[int]] = mapped_column(Integer, comment="死虾总数", init=False)
    size_min_cm: Mapped[Optional[float]] = mapped_column(Float, comment="最小尺寸(cm)", init=False)
    size_max_cm: Mapped[Optional[float]] = mapped_column(Float, comment="最大尺寸(cm)", init=False)
    size_mean_cm: Mapped[Optional[float]] = mapped_column(Float, comment="平均尺寸(cm)", init=False)
    size_median_cm: Mapped[Optional[float]] = mapped_column(Float, comment="中位数尺寸(cm)", init=False)
    
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
    
    weight_min_g: Mapped[Optional[float]] = mapped_column(Float, comment="最小体重(g)", init=False)
    weight_max_g: Mapped[Optional[float]] = mapped_column(Float, comment="最大体重(g)", init=False)
    weight_mean_g: Mapped[Optional[float]] = mapped_column(Float, comment="平均体重(g)", init=False)
    weight_median_g: Mapped[Optional[float]] = mapped_column(Float, comment="中位数体重(g)", init=False)
    
    # 平均估算体重（克）
    est_weight_g_avg: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 3),
        comment="平均估算体重（克）",
        init=False
    )
    
    # 是否存在饲料
    feed_present: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否存在饲料",
        init=False
    )
    
    # 是否存在虾皮
    shrimp_shell_present: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否存在虾皮",
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
    
    source_file: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="源文件",
        init=False
    )
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="创建时间",
        init=False
    )
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="更新时间",
        init=False
    )
    
    # ORM 关系
    frame: Mapped[Optional["CameraImage"]] = relationship(init=False)
    pond: Mapped["Pond"] = relationship(back_populates="shrimp_stats", init=False)