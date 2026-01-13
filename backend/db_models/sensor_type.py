from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Float,
    TIMESTAMP,
    Index,
    text,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class SensorType(Base): 
    """ 
    传感器类型字典表
    定义传感器的测量类型和数据规格。与device_types表配合使用：
    device_types定义设备大类（category=sensor），sensor_types定义具体的测量类型
    """ 
    __tablename__ = "sensor_types"
    __table_args__ = (
        Index("idx_sensor_type_metric", "metric"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False) 
    
    # 传感器类型名称（如：溶解氧饱和度传感器）
    type_name: Mapped[str] = mapped_column(
        String(128), 
        unique=True,
        nullable=False,
        comment="传感器类型名称（如：溶解氧饱和度传感器）"
    ) 
    
    # metric 标识符（do/ph/temperature/turbidity/liquid_level/ammonia/nitrite/circulation）
    metric: Mapped[Optional[str]] = mapped_column(
        String(64), 
        unique=True, 
        comment="metric 标识符（do/ph/temperature/turbidity/liquid_level/ammonia/nitrite/circulation）"
    )
    
    # 数据单位（%/mm/°C/NTU/mg/L）
    unit: Mapped[Optional[str]] = mapped_column(
        String(50), 
        comment="数据单位（%/mm/°C/NTU/mg/L）"
    ) 
    
    # 有效值下限
    valid_min: Mapped[Optional[float]] = mapped_column(
        Float,
        comment="有效值下限"
    )
    
    # 有效值上限
    valid_max: Mapped[Optional[float]] = mapped_column(
        Float,
        comment="有效值上限"
    )
    
    # 传感器类型描述/备注
    description: Mapped[Optional[str]] = mapped_column(
        TEXT, 
        comment="传感器类型描述/备注"
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

    # ORM 关系：一个类型可以对应多个传感器设备 
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="sensor_type", init=False)