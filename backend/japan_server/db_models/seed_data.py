#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小测试数据填充脚本
在当前数据库中插入一个传感器类型（temperature）、一个养殖池、一个传感器设备，
并写入最近一小时的若干条读数，以使 /api/sensors/realtime 能返回 200 与真实数据。
"""

from datetime import datetime, timedelta
from typing import Optional

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_type import SensorType
from japan_server.db_models.pond import Pond
from japan_server.db_models.sensor import Sensor
from japan_server.db_models.sensor_reading import SensorReading


def _get_or_create(session, model, defaults: Optional[dict] = None, **kwargs):
    obj = session.query(model).filter_by(**kwargs).first()
    if obj:
        return obj, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    obj = model(**params)  # type: ignore
    session.add(obj)
    return obj, True


def seed_minimal_sensor_data():
    """
    插入最小传感器数据：
    - SensorType: temperature
    - Pond: 1号养殖池
    - Sensor: 温度传感器 temp-001
    - SensorReading: 最近一小时的多条水温读数
    """
    with db_session_factory() as session:
        # 1) 传感器类型：temperature
        temp_type, created_type = _get_or_create(
            session,
            SensorType,
            defaults={"unit": "°C", "description": "水温"},
            type_name="temperature",
        )

        # 2) 养殖池
        pond, created_pond = _get_or_create(
            session,
            Pond,
            defaults={"location": "Tokyo", "description": "示例池塘"},
            name="1号养殖池",
        )

        # 3) 传感器设备
        sensor, created_sensor = _get_or_create(
            session,
            Sensor,
            defaults={
                "name": "温度-1号",
                "model": "TMP-100",
                "status": "active",
                "pond_id": pond.id,
                "sensor_type_id": temp_type.id,
            },
            sensor_id="temp-001",
        )

        # 若首次创建传感器，确保外键已填充
        if created_sensor:
            sensor.pond_id = pond.id
            sensor.sensor_type_id = temp_type.id

        # 4) 最近一小时的读数（例如每5分钟一条，共12条）
        now = datetime.now()
        existing_count = (
            session.query(SensorReading)
            .filter(SensorReading.sensor_id == sensor.id)
            .filter(SensorReading.recorded_at >= now - timedelta(hours=1))
            .count()
        )

        if existing_count == 0:
            readings = []
            base_value = 22.5
            for i in range(12):
                ts = now - timedelta(minutes=5 * (11 - i))
                # 生成一些轻微波动的数据
                val = base_value + (i % 3) * 0.2
                readings.append(
                    SensorReading(sensor_id=sensor.id, value=float(val), recorded_at=ts)
                )
            session.add_all(readings)

        session.commit()

        print(
            f"Seed完成: type={'created' if created_type else 'exists'}, "
            f"pond={'created' if created_pond else 'exists'}, "
            f"sensor={'created' if created_sensor else 'exists'}, "
            f"readings_added={'yes' if existing_count == 0 else 'no'}"
        )


if __name__ == "__main__":
    seed_minimal_sensor_data()