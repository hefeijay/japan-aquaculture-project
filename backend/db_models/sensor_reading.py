from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import ( 
    Column, 
    Integer, 
    Float, 
    TIMESTAMP, 
    ForeignKey, 
    Index, 
    BigInteger,
    String,
    Enum,
    Text,
    text,
) 
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship, Mapped, mapped_column 
 
from .base import Base 
 
 
class SensorReading(Base): 
    """ 
    传感器读数表
    直接关联devices.id，metric为快照字段便于按类型查询。
    pond_id为快照字段，记录数据产生时的池位
    """ 
    __tablename__ = "sensor_readings" 
    __table_args__ = ( 
        # 为最常见的查询建立复合索引 
        Index("idx_sensor_reading_device_ts", "device_id", "recorded_at"),
        Index("idx_sensor_reading_pond_ts", "pond_id", "ts_utc"),
        Index("idx_sensor_reading_metric_ts", "metric", "ts_utc"),
        Index("idx_sensor_reading_batch_ts", "batch_id", "ts_utc"),
    ) 
     
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True, 
        autoincrement=True, 
        init=False,
        comment="主键ID"
    ) 
     
    # 设备ID（FK → devices.id）- 直接关联统一设备表
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id）"
    ) 
    
    # 所属养殖池ID（FK）- 快照字段，记录数据产生时的池位
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）- 快照字段，记录数据产生时的池位"
    )
    
    # 批次ID（FK，关联到batches表的主键id）
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("batches.id"),
        comment="批次ID（FK，关联到batches.id主键）",
        init=False
    )
     
    # 读数数据
    # 记录的数值，使用浮点数以兼容各种类型的数据 
    value: Mapped[float] = mapped_column(
        Float, 
        nullable=False,
        comment="读数值"
    ) 
    
    # 计量单位
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="单位（%/mm/°C/NTU/mg/L等）",
        init=False
    )
    
    # metric标识符（快照字段，从sensor_types同步，便于查询）
    metric: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="metric标识符（快照字段，从sensor_types同步，便于查询）",
        init=False
    )
    
    # 描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="描述",
        init=False
    )
    
    # 时间戳
    # 数据记录的时间戳
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, 
        comment="数据记录时间",
        init=False
    )
    
    # UTC时间戳（毫秒精度）
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="UTC时间戳（毫秒精度）",
        init=False
    )
    
    # 本地时间戳（日本时区）
    ts_local: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="本地时间戳（日本时区）",
        init=False
    )
    
    # 质量控制
    # 质量标记（ok/missing/anomaly）
    quality_flag: Mapped[str] = mapped_column(
        String(20),
        default='ok',
        nullable=False,
        comment="质量标记（ok/missing/anomaly）",
        init=False
    )
    
    # 完整性校验
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="完整性校验",
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
    device: Mapped["Device"] = relationship(back_populates="sensor_readings", init=False)
    pond: Mapped["Pond"] = relationship(back_populates="sensor_readings", init=False)
    batch: Mapped[Optional["Batch"]] = relationship(init=False)
