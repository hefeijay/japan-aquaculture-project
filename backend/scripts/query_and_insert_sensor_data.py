#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询sensor_types和sensor_readings表的最新20条记录
并插入sensor_id为6和7的mock记录各一条
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
from sqlalchemy import text, desc

def query_sensor_types_latest():
    """查询sensor_types表的最新20条记录"""
    print("=" * 80)
    print("查询 sensor_types 表的最新20条记录")
    print("=" * 80)
    try:
        with db_session_factory() as session:
            # 查询最新20条记录（按id降序）
            types = session.query(SensorType).order_by(desc(SensorType.id)).limit(20).all()
            print(f"\n找到 {len(types)} 条记录:\n")
            
            if types:
                print(f"{'ID':<5} {'类型名称':<30} {'Metric':<20} {'单位':<15} {'描述':<30}")
                print("-" * 100)
                for st in types:
                    type_name = st.type_name or ""
                    metric = st.metric or ""
                    unit = st.unit or ""
                    description = (st.description or "")[:28] + ".." if st.description and len(st.description) > 30 else (st.description or "")
                    print(f"{st.id:<5} {type_name:<30} {metric:<20} {unit:<15} {description:<30}")
            else:
                print("⚠ 警告: sensor_types 表为空")
            
            return types
    except Exception as e:
        print(f"✗ 查询 sensor_types 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def query_sensor_readings_latest():
    """查询sensor_readings表的最新20条记录"""
    print("\n" + "=" * 80)
    print("查询 sensor_readings 表的最新20条记录")
    print("=" * 80)
    try:
        with db_session_factory() as session:
            # 查询最新20条记录（按id降序）
            readings = session.query(SensorReading).order_by(desc(SensorReading.id)).limit(20).all()
            print(f"\n找到 {len(readings)} 条记录:\n")
            
            if readings:
                print(f"{'ID':<8} {'传感器ID':<10} {'批次ID':<10} {'池号':<10} {'Metric':<15} {'数值':<10} {'单位':<10} {'时间戳':<25} {'质量标记':<10}")
                print("-" * 120)
                for reading in readings:
                    reading_id = reading.id
                    sensor_id = reading.sensor_id
                    batch_id = reading.batch_id or ""
                    pool_id = reading.pool_id or ""
                    metric = reading.metric or ""
                    value = reading.value
                    unit = reading.unit or ""
                    timestamp = reading.ts_utc or reading.recorded_at or ""
                    quality_flag = reading.quality_flag or ""
                    
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else ""
                    
                    print(f"{reading_id:<8} {sensor_id:<10} {str(batch_id):<10} {pool_id:<10} {metric:<15} {value:<10.2f} {unit:<10} {timestamp_str:<25} {quality_flag:<10}")
            else:
                print("⚠ 警告: sensor_readings 表为空")
            
            return readings
    except Exception as e:
        print(f"✗ 查询 sensor_readings 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def insert_mock_sensor_readings():
    """插入sensor_id为6和7的mock记录各一条"""
    print("\n" + "=" * 80)
    print("插入 sensor_id 为 6 和 7 的 mock 记录")
    print("=" * 80)
    
    try:
        with db_session_factory() as session:
            # 获取当前时间
            now_utc = datetime.now(timezone.utc)
            
            # 检查sensor_id 6和7是否存在（注意：Sensor.id是主键，Sensor.sensor_id是唯一标识符）
            from japan_server.db_models.sensor import Sensor
            from japan_server.db_models.pond import Pond
            
            # 查找id=6和id=7的传感器
            sensor6 = session.query(Sensor).filter(Sensor.id == 6).first()
            sensor7 = session.query(Sensor).filter(Sensor.id == 7).first()
            
            # 如果sensor_id 6或7不存在，创建它们
            if not sensor6:
                print("⚠ 警告: sensor_id=6 不存在，正在创建...")
                # 获取一个存在的pond_id和sensor_type_id
                pond = session.query(Pond).first()
                if not pond:
                    print("✗ 错误: ponds表为空，无法创建传感器")
                    return False
                
                sensor_type = session.query(SensorType).first()
                if not sensor_type:
                    print("✗ 错误: sensor_types表为空，无法创建传感器")
                    return False
                
                # 创建sensor_id=6的传感器
                sensor6 = Sensor(
                    name="Mock Sensor 6",
                    sensor_id=f"sensor_6_{int(now_utc.timestamp())}",
                    pond_id=pond.id,
                    sensor_type_id=sensor_type.id,
                    model="Mock Model",
                    installed_at=now_utc,
                    status="active"
                )
                session.add(sensor6)
                session.flush()  # 刷新以获取生成的id
                print(f"   ✓ 已创建传感器，id={sensor6.id}")
            
            if not sensor7:
                print("⚠ 警告: sensor_id=7 不存在，正在创建...")
                # 获取一个存在的pond_id和sensor_type_id
                pond = session.query(Pond).first()
                if not pond:
                    print("✗ 错误: ponds表为空，无法创建传感器")
                    return False
                
                sensor_type = session.query(SensorType).first()
                if not sensor_type:
                    print("✗ 错误: sensor_types表为空，无法创建传感器")
                    return False
                
                # 创建sensor_id=7的传感器
                sensor7 = Sensor(
                    name="Mock Sensor 7",
                    sensor_id=f"sensor_7_{int(now_utc.timestamp())}",
                    pond_id=pond.id,
                    sensor_type_id=sensor_type.id,
                    model="Mock Model",
                    installed_at=now_utc,
                    status="active"
                )
                session.add(sensor7)
                session.flush()  # 刷新以获取生成的id
                print(f"   ✓ 已创建传感器，id={sensor7.id}")
            
            sensor6_id = sensor6.id
            sensor7_id = sensor7.id
            
            # 获取一些sensor_types信息用于mock数据
            sensor_types = session.query(SensorType).limit(5).all()
            if not sensor_types:
                print("⚠ 警告: sensor_types 表为空，将使用默认值")
            
            # 插入sensor_id=6的记录（使用sensor6.id）
            reading6 = SensorReading(
                sensor_id=sensor6_id,
                value=25.5
            )
            # 设置其他字段（init=False的字段通过属性赋值）
            reading6.recorded_at = now_utc
            reading6.ts_utc = now_utc
            reading6.metric = sensor_types[0].metric if sensor_types else "temperature"
            reading6.type_name = sensor_types[0].type_name if sensor_types else "温度"
            reading6.description = "Mock data for sensor 6"
            reading6.unit = sensor_types[0].unit if sensor_types else "°C"
            reading6.quality_flag = "ok"
            session.add(reading6)
            
            # 插入sensor_id=7的记录（使用sensor7.id）
            reading7 = SensorReading(
                sensor_id=sensor7_id,
                value=7.2
            )
            # 设置其他字段（init=False的字段通过属性赋值）
            reading7.recorded_at = now_utc
            reading7.ts_utc = now_utc
            reading7.metric = sensor_types[1].metric if len(sensor_types) > 1 else "ph"
            reading7.type_name = sensor_types[1].type_name if len(sensor_types) > 1 else "pH值"
            reading7.description = "Mock data for sensor 7"
            reading7.unit = sensor_types[1].unit if len(sensor_types) > 1 else "pH"
            reading7.quality_flag = "ok"
            session.add(reading7)
            
            # 提交事务
            session.commit()
            
            print(f"\n✓ 成功插入2条mock记录:")
            print(f"  - sensor_id={sensor6_id}: {reading6.metric}={reading6.value} {reading6.unit}")
            print(f"  - sensor_id={sensor7_id}: {reading7.metric}={reading7.value} {reading7.unit}")
            
            return True
    except Exception as e:
        print(f"✗ 插入mock记录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("传感器数据查询和插入脚本")
    print("=" * 80)
    
    # 1. 查询sensor_types表的最新20条记录
    sensor_types = query_sensor_types_latest()
    
    # 2. 查询sensor_readings表的最新20条记录
    sensor_readings = query_sensor_readings_latest()
    
    # 3. 插入mock记录
    success = insert_mock_sensor_readings()
    
    if success:
        print("\n" + "=" * 80)
        print("操作完成！")
        print("=" * 80)
        
        # 再次查询最新记录以验证插入
        print("\n验证插入结果 - 查询最新的5条sensor_readings记录:")
        try:
            with db_session_factory() as session:
                latest = session.query(SensorReading).order_by(desc(SensorReading.id)).limit(5).all()
                print(f"\n{'ID':<8} {'传感器ID':<10} {'Metric':<15} {'数值':<10} {'单位':<10} {'时间戳':<25}")
                print("-" * 80)
                for reading in latest:
                    timestamp = reading.ts_utc or reading.recorded_at or ""
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else ""
                    print(f"{reading.id:<8} {reading.sensor_id:<10} {(reading.metric or ''):<15} {reading.value:<10.2f} {(reading.unit or ''):<10} {timestamp_str:<25}")
        except Exception as e:
            print(f"验证查询失败: {str(e)}")

if __name__ == "__main__":
    main()

