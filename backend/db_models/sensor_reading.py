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
    传感器读数记录表 (核心数据表) 
    符合数据处理计划要求，包含批次、池号、时间戳、质量标记等字段
    """ 
    __tablename__ = "sensor_readings" 
    __table_args__ = ( 
        # 为最常见的查询（查询某个传感器在一段时间内的数据）建立复合索引 
        Index("idx_sensor_id_recorded_at", "sensor_id", "recorded_at"), 
        Index("idx_sr_batch_metric_ts", "batch_id", "metric", "ts_utc"),
    ) 
     
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False) 
     
    # 外键，关联到具体的传感器设备 
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), comment="传感器设备ID") 
    
    # 批次ID（FK，关联到batches表）
    batch_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        comment="批次ID（FK）",
        init=False
    )
    
    # 池号/分区标识（冗余便于查询）
    pool_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="池号/分区（冗余便于查询）",
        init=False
    )
     
    # 记录的数值，使用浮点数以兼容各种类型的数据 
    value: Mapped[float] = mapped_column(Float, comment="传感器读数值") 
     
    # 数据记录的时间戳（保留原有字段以兼容）
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, 
        default=datetime.now(timezone.utc), 
        comment="数据记录时间",
        init=False
    )
    
    # UTC时间戳（毫秒精度）
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="UTC时间戳",
        init=False
    )
    
    # 本地时间戳（日本时区）
    ts_local: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="本地时间戳（日本时区）",
        init=False
    )
    
    # 指标名称（如：do, ph, temp等）
    metric: Mapped[Optional[str]] = mapped_column(
        String(32),
        comment="指标名称",
        init=False
    )
    
    # 类型名称
    type_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="类型名称",
        init=False
    )
    
    # 描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="描述",
        init=False
    )
    
    # 计量单位
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="计量单位",
        init=False
    )
    
    # 质量标记（ok/missing/anomaly）
    quality_flag: Mapped[str] = mapped_column(
        Enum('ok', 'missing', 'anomaly', name='quality_flag_enum'),
        default='ok',
        nullable=False,
        comment="质量标记",
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
    sensor: Mapped["Sensor"] = relationship(back_populates="readings", init=False)