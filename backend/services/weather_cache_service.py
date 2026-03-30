#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气缓存服务
定时刷新天气缓存，供预测服务读取，避免在 SSE 请求链路中直接调用天气 API。
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from config.settings import Config
from db_models.base import Base
from db_models.db_session import db_session_factory, get_engine
from db_models.pond import Pond
from db_models.weather_cache import WeatherCache

logger = logging.getLogger(__name__)


class WeatherCacheService:
    """天气缓存服务"""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def ensure_tables(self) -> None:
        """确保天气缓存表存在。"""
        try:
            Base.metadata.create_all(get_engine(), tables=[WeatherCache.__table__])
        except Exception as exc:
            logger.error(f"创建天气缓存表失败: {exc}", exc_info=True)

    def start(self) -> None:
        """启动后台定时刷新线程。"""
        self.ensure_tables()
        if self._thread and self._thread.is_alive():
            logger.info("WeatherCacheService 已在运行")
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            name="WeatherCacheServiceThread",
            daemon=True,
        )
        self._thread.start()
        logger.info("WeatherCacheService 已启动")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        # 启动后先刷新一次，之后按固定周期刷新
        self.refresh_all_locations()
        interval_seconds = max(300, Config.WEATHER_UPDATE_INTERVAL_HOURS * 3600)
        while not self._stop_event.wait(interval_seconds):
            self.refresh_all_locations()

    def get_weather_for_pond(self, pond: Optional[Pond]) -> Optional[Dict[str, Any]]:
        """获取池塘对应的最新有效天气缓存，必要时同步刷新一次。"""
        self.ensure_tables()
        location_key = self._resolve_location_key(pond)
        with db_session_factory() as session:
            cache = self._get_latest_valid_cache(session, location_key)
            if cache:
                return self._serialize_cache(cache)

        refreshed = self.refresh_location(location_key)
        if refreshed:
            return self._serialize_cache(refreshed)

        with db_session_factory() as session:
            cache = (
                session.query(WeatherCache)
                .filter(WeatherCache.location_key == location_key)
                .order_by(WeatherCache.fetched_at.desc())
                .first()
            )
            return self._serialize_cache(cache) if cache else None

    def refresh_all_locations(self) -> None:
        """当前项目统一只刷新默认养殖地点天气缓存。"""
        self.ensure_tables()
        try:
            self.refresh_location(self._resolve_location_key(None))
        except Exception as exc:
            logger.error(f"刷新天气缓存失败: {exc}", exc_info=True)

    def refresh_location(self, location_key: str, force: bool = False) -> Optional[WeatherCache]:
        """刷新指定地点天气缓存；缓存未过期时默认直接复用。"""
        try:
            with db_session_factory() as session:
                if not force:
                    cache = self._get_latest_valid_cache(session, location_key)
                    if cache:
                        return cache

            payload = self._fetch_forecast(location_key)
            if not payload:
                return None

            fetched_at = datetime.now()
            expires_at = fetched_at + timedelta(hours=Config.WEATHER_CACHE_TTL_HOURS)

            with db_session_factory() as session:
                cache = WeatherCache(
                    location_key=location_key,
                    source="openweather",
                    forecast_type="forecast",
                    payload=payload,
                    fetched_at=fetched_at,
                    expires_at=expires_at,
                )
                session.add(cache)
                session.commit()
                session.refresh(cache)
                logger.info(f"天气缓存已更新: {location_key}")
                return cache
        except Exception as exc:
            logger.error(f"保存天气缓存失败: {exc}", exc_info=True)
            return None

    def _get_latest_valid_cache(self, session, location_key: str) -> Optional[WeatherCache]:
        now = datetime.now()
        return (
            session.query(WeatherCache)
            .filter(WeatherCache.location_key == location_key)
            .filter(WeatherCache.expires_at > now)
            .order_by(WeatherCache.fetched_at.desc())
            .first()
        )

    def _serialize_cache(self, cache: Optional[WeatherCache]) -> Optional[Dict[str, Any]]:
        if not cache:
            return None
        return {
            "id": cache.id,
            "location_key": cache.location_key,
            "payload": cache.payload,
            "fetched_at": cache.fetched_at.isoformat() if cache.fetched_at else None,
            "expires_at": cache.expires_at.isoformat() if cache.expires_at else None,
        }

    def _resolve_location_key(self, pond: Optional[Pond]) -> str:
        # 当前业务统一按筑波天气做预测，不跟随 ponds.location 分散查询。
        return Config.WEATHER_DEFAULT_LOCATION

    def _fetch_forecast(self, location_key: str) -> Optional[Dict[str, Any]]:
        """拉取并整理未来天气数据。"""
        api_key = Config.WEATHER_API_KEY
        if not api_key:
            logger.info("未配置 WEATHER_API_KEY，天气缓存将返回空")
            return None

        try:
            response = httpx.get(
                Config.WEATHER_BASE_URL,
                params={
                    "q": location_key,
                    "appid": api_key,
                    "units": "metric",
                    "lang": Config.WEATHER_LANG,
                },
                timeout=10.0,
            )
            if response.is_success:
                return self._normalize_forecast_payload(response.json(), location_key)

            # OpenWeather 对中文/长地址 q 查询兼容性较差，失败时回退到地理编码查经纬度。
            if response.status_code == 404:
                geo = self._geocode_location(location_key, api_key)
                if geo:
                    fallback_response = httpx.get(
                        Config.WEATHER_BASE_URL,
                        params={
                            "lat": geo["lat"],
                            "lon": geo["lon"],
                            "appid": api_key,
                            "units": "metric",
                            "lang": Config.WEATHER_LANG,
                        },
                        timeout=10.0,
                    )
                    fallback_response.raise_for_status()
                    return self._normalize_forecast_payload(
                        fallback_response.json(),
                        geo.get("name") or location_key,
                    )

            response.raise_for_status()
        except Exception as exc:
            logger.warning(f"获取天气数据失败 {location_key}: {exc}")
            return None

    def _geocode_location(self, location_key: str, api_key: str) -> Optional[Dict[str, Any]]:
        try:
            response = httpx.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params={
                    "q": location_key,
                    "limit": 1,
                    "appid": api_key,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            items = response.json() or []
            if not items:
                return None

            item = items[0]
            lat = item.get("lat")
            lon = item.get("lon")
            if lat is None or lon is None:
                return None

            return {
                "lat": lat,
                "lon": lon,
                "name": item.get("name") or location_key,
            }
        except Exception as exc:
            logger.warning(f"天气地理编码失败 {location_key}: {exc}")
            return None

    def _normalize_forecast_payload(self, data: Dict[str, Any], location_key: str) -> Dict[str, Any]:
        forecast_items = data.get("list", [])[:4]
        normalized_items: List[Dict[str, Any]] = []
        for item in forecast_items:
            main = item.get("main", {})
            weather_list = item.get("weather", [])
            wind = item.get("wind", {})
            normalized_items.append(
                {
                    "forecast_at": item.get("dt_txt"),
                    "temp": main.get("temp"),
                    "feels_like": main.get("feels_like"),
                    "humidity": main.get("humidity"),
                    "condition": weather_list[0].get("description") if weather_list else None,
                    "wind_speed": wind.get("speed"),
                    "rain": item.get("rain", {}),
                }
            )

        return {
            "city": data.get("city", {}).get("name", location_key),
            "forecast_items": normalized_items,
        }


weather_cache_service = WeatherCacheService()
