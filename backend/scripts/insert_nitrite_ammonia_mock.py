#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
往sensor_readings表中插入亚硝酸盐浓度和氨氮浓度的mock数据各一条
"""

import sys
import os
from datetime import datetime, timezone

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
parent_root = os.path.dirname(project_root)
if parent_root not in sys.path:
    sys.path.insert(0, parent_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_reading import SensorReading
from japan_server.db_models.sensor_type import SensorType
from japan_server.db_models.sensor import Sensor
from japan_server.db_models.pond import Pond

def insert_nitrite_ammonia_mock():
    """插入亚硝酸盐浓度和氨氮浓度的mock数据"""
    print("=" * 80)
    print("插入亚硝酸盐浓度和氨氮浓度的mock数据")
    print("=" * 80)
    
    try:
        with db_session_factory() as session:
            # 获取当前时间
            now_utc = datetime.now(timezone.utc)
            
            # 查找亚硝酸盐浓度和氨氮浓度的sensor_type
            nitrite_type = session.query(SensorType).filter(
                SensorType.metric == "nitrite"
            ).first()
            
            ammonia_type = session.query(SensorType).filter(
                SensorType.metric == "ammonia"
            ).first()
            
            if not nitrite_type:
                print("✗ 错误: 未找到亚硝酸盐浓度类型 (nitrite)")
                return False
            
            if not ammonia_type:
                print("✗ 错误: 未找到氨氮浓度类型 (ammonia)")
                return False
            
            print(f"✓ 找到传感器类型:")
            print(f"  - 亚硝酸盐浓度: ID={nitrite_type.id}, metric={nitrite_type.metric}, 单位={nitrite_type.unit}")
            print(f"  - 氨氮浓度: ID={ammonia_type.id}, metric={ammonia_type.metric}, 单位={ammonia_type.unit}")
            
            # 查找或创建对应的传感器
            # 先查找是否有使用这些类型的传感器
            nitrite_sensor = session.query(Sensor).filter(
                Sensor.sensor_type_id == nitrite_type.id
            ).first()
            
            ammonia_sensor = session.query(Sensor).filter(
                Sensor.sensor_type_id == ammonia_type.id
            ).first()
            
            # 如果没有找到对应的传感器，创建一个通用的传感器
            if not nitrite_sensor:
                print("\n⚠ 警告: 未找到亚硝酸盐传感器，正在创建...")
                pond = session.query(Pond).first()
                if not pond:
                    print("✗ 错误: ponds表为空，无法创建传感器")
                    return False
                
                nitrite_sensor = Sensor(
                    name="Mock Nitrite Sensor",
                    sensor_id=f"nitrite_sensor_{int(now_utc.timestamp())}",
                    pond_id=pond.id,
                    sensor_type_id=nitrite_type.id,
                    model="Mock Model",
                    installed_at=now_utc,
                    status="active"
                )
                session.add(nitrite_sensor)
                session.flush()
                print(f"  ✓ 已创建亚硝酸盐传感器，id={nitrite_sensor.id}")
            
            if not ammonia_sensor:
                print("\n⚠ 警告: 未找到氨氮传感器，正在创建...")
                pond = session.query(Pond).first()
                if not pond:
                    print("✗ 错误: ponds表为空，无法创建传感器")
                    return False
                
                ammonia_sensor = Sensor(
                    name="Mock Ammonia Sensor",
                    sensor_id=f"ammonia_sensor_{int(now_utc.timestamp())}",
                    pond_id=pond.id,
                    sensor_type_id=ammonia_type.id,
                    model="Mock Model",
                    installed_at=now_utc,
                    status="active"
                )
                session.add(ammonia_sensor)
                session.flush()
                print(f"  ✓ 已创建氨氮传感器，id={ammonia_sensor.id}")
            
            # 插入亚硝酸盐浓度的mock数据
            # 正常范围：0-0.1 mg/L，mock数据使用0.05 mg/L
            nitrite_reading = SensorReading(
                sensor_id=nitrite_sensor.id,
                value=0.05
            )
            nitrite_reading.recorded_at = now_utc
            nitrite_reading.ts_utc = now_utc
            nitrite_reading.metric = nitrite_type.metric
            nitrite_reading.type_name = nitrite_type.type_name
            nitrite_reading.description = "Mock data for nitrite concentration"
            nitrite_reading.unit = nitrite_type.unit
            nitrite_reading.quality_flag = "ok"
            session.add(nitrite_reading)
            
            # 插入氨氮浓度的mock数据
            # 正常范围：0-0.5 mg/L，mock数据使用0.2 mg/L
            ammonia_reading = SensorReading(
                sensor_id=ammonia_sensor.id,
                value=0.2
            )
            ammonia_reading.recorded_at = now_utc
            ammonia_reading.ts_utc = now_utc
            ammonia_reading.metric = ammonia_type.metric
            ammonia_reading.type_name = ammonia_type.type_name
            ammonia_reading.description = "Mock data for ammonia concentration"
            ammonia_reading.unit = ammonia_type.unit
            ammonia_reading.quality_flag = "ok"
            session.add(ammonia_reading)
            
            # 提交事务
            session.commit()
            
            print("\n" + "=" * 80)
            print("✓ 成功插入2条mock记录:")
            print("=" * 80)
            print(f"1. 亚硝酸盐浓度:")
            print(f"   - sensor_id: {nitrite_sensor.id}")
            print(f"   - metric: {nitrite_reading.metric}")
            print(f"   - value: {nitrite_reading.value} {nitrite_reading.unit}")
            print(f"   - timestamp: {nitrite_reading.ts_utc}")
            print(f"\n2. 氨氮浓度:")
            print(f"   - sensor_id: {ammonia_sensor.id}")
            print(f"   - metric: {ammonia_reading.metric}")
            print(f"   - value: {ammonia_reading.value} {ammonia_reading.unit}")
            print(f"   - timestamp: {ammonia_reading.ts_utc}")
            
            return True
            
    except Exception as e:
        print(f"✗ 插入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_insertion():
    """验证插入结果"""
    print("\n" + "=" * 80)
    print("验证插入结果 - 查询最新的sensor_readings记录（包含nitrite和ammonia）")
    print("=" * 80)
    
    try:
        with db_session_factory() as session:
            # 查询最新的包含nitrite或ammonia的记录
            from sqlalchemy import or_
            latest = session.query(SensorReading).filter(
                or_(
                    SensorReading.metric == "nitrite",
                    SensorReading.metric == "ammonia"
                )
            ).order_by(SensorReading.id.desc()).limit(5).all()
            
            if latest:
                print(f"\n找到 {len(latest)} 条相关记录:\n")
                print(f"{'ID':<8} {'传感器ID':<10} {'Metric':<15} {'数值':<12} {'单位':<10} {'时间戳':<25}")
                print("-" * 85)
                for reading in latest:
                    timestamp = reading.ts_utc or reading.recorded_at or ""
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else ""
                    print(f"{reading.id:<8} {reading.sensor_id:<10} {(reading.metric or ''):<15} {reading.value:<12.4f} {(reading.unit or ''):<10} {timestamp_str:<25}")
            else:
                print("⚠ 未找到相关记录")
                
    except Exception as e:
        print(f"验证查询失败: {str(e)}")

if __name__ == "__main__":
    success = insert_nitrite_ammonia_mock()
    if success:
        verify_insertion()










