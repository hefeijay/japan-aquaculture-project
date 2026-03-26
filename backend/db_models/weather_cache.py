from typing import Optional
from datetime import datetime

from sqlalchemy import Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WeatherCache(Base):
    """
    天气缓存表
    按 location_key 缓存未来天气，避免高频重复调用天气 API。
    """

    __tablename__ = "weather_cache"
    __table_args__ = (
        Index("idx_weather_cache_location_expires", "location_key", "expires_at"),
        Index("idx_weather_cache_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        init=False,
        comment="主键ID",
    )

    location_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="地点标识，如 Tsukuba",
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="天气缓存内容(JSON)",
    )

    fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        comment="抓取时间",
    )

    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        comment="过期时间",
    )

    source: Mapped[str] = mapped_column(
        String(64),
        default="openweather",
        nullable=False,
        comment="天气来源",
    )

    forecast_type: Mapped[str] = mapped_column(
        String(32),
        default="forecast",
        nullable=False,
        comment="缓存类型，如 current/forecast",
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
