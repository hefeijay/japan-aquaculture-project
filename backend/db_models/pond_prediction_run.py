from typing import Optional
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PondPredictionRun(Base):
    """
    养殖池预测结果表
    一条记录保存某个池一次完整预测结果，所有传感器预测明细存入 output_payload。
    """

    __tablename__ = "pond_prediction_runs"
    __table_args__ = (
        Index("idx_prediction_pond_created", "pond_id", "created_at"),
        Index("idx_prediction_pond_signature", "pond_id", "input_signature"),
        Index("idx_prediction_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        init=False,
        comment="主键ID",
    )

    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="养殖池ID",
    )

    input_signature: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="预测输入签名，用于判定最近五条是否变化",
    )

    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        comment="预测生成时间",
    )

    weather_cache_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("weather_cache.id"),
        nullable=True,
        default=None,
        comment="关联天气缓存ID",
    )

    predicted_for_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
        comment="预测目标时间",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        comment="预测状态：pending/processing/ready/failed",
    )

    output_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="预测结果(JSON)",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="错误信息",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        init=False,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        init=False,
        comment="更新时间",
    )

    pond = relationship("Pond", init=False)
    weather_cache = relationship("WeatherCache", init=False)
