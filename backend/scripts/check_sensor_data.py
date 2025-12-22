#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查传感器数据脚本
用于诊断数据库中的数据情况
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
# 添加项目根目录的父目录（/srv）到路径
parent_root = os.path.dirname(project_root)
if parent_root not in sys.path:
    sys.path.insert(0, parent_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor import Sensor
from japan_server.db_models.sensor_reading import SensorReading
from japan_server.db_models.sensor_type import SensorType
from japan_server.config.settings import Config
from sqlalchemy import text

def check_database_connection():
    """检查数据库连接"""
    print("=" * 60)
    print("1. 检查数据库连接")
    print("=" * 60)
    try:
        print(f"数据库URI: {Config.SQLALCHEMY_DATABASE_URI[:50]}...")
        with db_session_factory() as session:
            # 执行简单查询测试连接
            result = session.execute(text("SELECT 1")).scalar()
            print(f"✓ 数据库连接成功: {result}")
            return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        return False

def check_sensor_types():
    """检查传感器类型表"""
    print("\n" + "=" * 60)
    print("2. 检查传感器类型表 (sensor_types)")
    print("=" * 60)
    try:
        with db_session_factory() as session:
            types = session.query(SensorType).all()
            print(f"传感器类型总数: {len(types)}")
            if types:
                print("\n传感器类型列表:")
                for st in types:
                    print(f"  - ID: {st.id}, 名称: {st.type_name}, 单位: {st.unit}")
            else:
                print("⚠ 警告: 传感器类型表为空")
            return len(types)
    except Exception as e:
        print(f"✗ 查询传感器类型失败: {str(e)}")
        return 0

def check_sensors():
    """检查传感器表"""
    print("\n" + "=" * 60)
    print("3. 检查传感器表 (sensors)")
    print("=" * 60)
    try:
        with db_session_factory() as session:
            sensors = session.query(Sensor).all()
            print(f"传感器总数: {len(sensors)}")
            if sensors:
                print("\n传感器列表:")
                for sensor in sensors:
                    type_name = sensor.sensor_type.type_name if sensor.sensor_type else "未知"
                    print(f"  - ID: {sensor.id}, 名称: {sensor.name}, 类型: {type_name}, 状态: {sensor.status}")
            else:
                print("⚠ 警告: 传感器表为空")
            return len(sensors)
    except Exception as e:
        print(f"✗ 查询传感器失败: {str(e)}")
        return 0

def check_sensor_readings():
    """检查传感器读数表"""
    print("\n" + "=" * 60)
    print("4. 检查传感器读数表 (sensor_readings)")
    print("=" * 60)
    try:
        with db_session_factory() as session:
            # 总数据量
            total_count = session.query(SensorReading).count()
            print(f"传感器读数总数: {total_count}")
            
            if total_count == 0:
                print("⚠ 警告: 传感器读数表为空，没有数据")
                return 0
            
            # 最近1小时的数据
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            recent_count = session.query(SensorReading)\
                .filter(SensorReading.recorded_at >= start_time)\
                .filter(SensorReading.recorded_at <= end_time)\
                .count()
            print(f"最近1小时内的数据量: {recent_count}")
            
            # 最近24小时的数据
            start_time_24h = end_time - timedelta(hours=24)
            recent_24h_count = session.query(SensorReading)\
                .filter(SensorReading.recorded_at >= start_time_24h)\
                .filter(SensorReading.recorded_at <= end_time)\
                .count()
            print(f"最近24小时内的数据量: {recent_24h_count}")
            
            # 最早和最晚的数据时间
            earliest = session.query(SensorReading)\
                .order_by(SensorReading.recorded_at.asc())\
                .first()
            latest = session.query(SensorReading)\
                .order_by(SensorReading.recorded_at.desc())\
                .first()
            
            if earliest:
                print(f"最早数据时间: {earliest.recorded_at}")
            if latest:
                print(f"最新数据时间: {latest.recorded_at}")
            
            # 按传感器类型分组统计
            print("\n按传感器类型分组统计:")
            readings_with_types = session.query(SensorReading, Sensor, SensorType)\
                .join(Sensor, SensorReading.sensor_id == Sensor.id)\
                .join(SensorType, Sensor.sensor_type_id == SensorType.id)\
                .filter(SensorReading.recorded_at >= start_time)\
                .filter(SensorReading.recorded_at <= end_time)\
                .all()
            
            type_counts = {}
            for reading, sensor, sensor_type in readings_with_types:
                type_name = sensor_type.type_name
                if type_name not in type_counts:
                    type_counts[type_name] = 0
                type_counts[type_name] += 1
            
            if type_counts:
                for type_name, count in sorted(type_counts.items()):
                    print(f"  - {type_name}: {count} 条")
            else:
                print("  ⚠ 最近1小时内没有数据")
            
            return total_count
    except Exception as e:
        print(f"✗ 查询传感器读数失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

def check_api_query():
    """模拟API查询逻辑"""
    print("\n" + "=" * 60)
    print("5. 模拟API查询逻辑")
    print("=" * 60)
    try:
        from japan_server.services.sensor_service import SensorService
        
        # 获取最近1小时的数据
        grouped_readings = SensorService.get_all_sensor_readings(hours=1)
        
        print(f"查询结果: {len(grouped_readings)} 个传感器类型有数据")
        if grouped_readings:
            print("\n各类型数据量:")
            for type_name, readings in grouped_readings.items():
                print(f"  - {type_name}: {len(readings)} 条")
        else:
            print("⚠ 警告: 查询返回空结果")
        
        return len(grouped_readings)
    except Exception as e:
        print(f"✗ API查询失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("传感器数据诊断工具")
    print("=" * 60)
    
    # 检查数据库连接
    if not check_database_connection():
        print("\n✗ 数据库连接失败，无法继续检查")
        return
    
    # 检查各表
    type_count = check_sensor_types()
    sensor_count = check_sensors()
    reading_count = check_sensor_readings()
    
    # 模拟API查询
    api_result_count = check_api_query()
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    print(f"传感器类型数: {type_count}")
    print(f"传感器设备数: {sensor_count}")
    print(f"传感器读数总数: {reading_count}")
    print(f"API查询返回类型数: {api_result_count}")
    
    if reading_count == 0:
        print("\n⚠ 问题: 传感器读数表为空，需要插入数据")
    elif api_result_count == 0:
        print("\n⚠ 问题: 最近1小时内没有数据，可能是:")
        print("  1. 数据采集服务未运行")
        print("  2. 数据时间戳不在最近1小时内")
        print("  3. 传感器类型名称不匹配")
    else:
        print("\n✓ 数据正常，API应该可以返回数据")

if __name__ == '__main__':
    main()

