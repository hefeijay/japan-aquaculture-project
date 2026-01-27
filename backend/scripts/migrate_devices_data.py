#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备数据综合迁移脚本
迁移 devices.csv, sensors.csv 到新的统一设备管理表结构
"""

import sys
import os
import csv
from datetime import datetime
from decimal import Decimal

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
import db_models  # 导入所有模型
from db_models.device import Device, DeviceType
from db_models.sensor import Sensor
from db_models.sensor_type import SensorType
from db_models.feeder import Feeder
from db_models.pond import Pond
from sqlalchemy import text


def migrate_sensor_types_csv(session):
    """迁移 sensor_types.csv 数据"""
    print("=" * 60)
    print("步骤 1: 迁移 sensor_types.csv 数据")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/sensor_types.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    success_count = 0
    skip_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                sensor_type_id = int(row['id'])
                
                # 检查是否已存在
                existing = session.query(SensorType).filter(SensorType.id == sensor_type_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 使用原生 SQL 插入以指定 id
                session.execute(text("""
                    INSERT INTO sensor_types (id, type_name, metric, unit, description)
                    VALUES (:id, :type_name, :metric, :unit, :description)
                """), {
                    "id": sensor_type_id,
                    "type_name": row['type_name'],
                    "metric": row['metric'] if row['metric'] else None,
                    "unit": row['unit'] if row['unit'] else None,
                    "description": row['description'] if row['description'] else None
                })
                success_count += 1
                    
            except Exception as e:
                print(f"  ❌ 处理记录失败 (id={row.get('id')}): {str(e)}")
                session.rollback()  # 回滚以继续处理下一条
                continue
    
    session.commit()
    print(f"  ✓ sensor_types.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print()
    
    return success_count


def ensure_device_types(session):
    """确保设备类型基础数据存在"""
    print("=" * 60)
    print("步骤 2: 检查并创建设备类型基础数据")
    print("=" * 60)
    
    # 需要的设备类型
    required_types = [
        {"id": 1, "category": "misc", "name": "通用设备", "description": "通用设备类型"},
        {"id": 2, "category": "camera", "name": "摄像头", "description": "监控摄像头"},
        {"id": 3, "category": "sensor", "name": "传感器", "description": "各类传感器设备"},
        {"id": 4, "category": "feeder", "name": "喂食机", "description": "自动喂食设备"},
    ]
    
    for type_data in required_types:
        existing = session.query(DeviceType).filter(DeviceType.id == type_data["id"]).first()
        if not existing:
            # 使用原生 SQL 插入以指定 id
            session.execute(text("""
                INSERT INTO device_types (id, category, name, description)
                VALUES (:id, :category, :name, :description)
            """), {
                "id": type_data["id"],
                "category": type_data["category"],
                "name": type_data["name"],
                "description": type_data["description"]
            })
            print(f"  ✓ 创建设备类型: {type_data['name']} (category={type_data['category']}, id={type_data['id']})")
        else:
            print(f"  ✓ 设备类型已存在: {existing.name} (category={existing.category}, id={existing.id})")
    
    session.commit()
    print()


def migrate_devices_csv(session):
    """迁移 devices.csv 数据"""
    print("=" * 60)
    print("步骤 3: 迁移 devices.csv 数据")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/devices.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                device_id = row['device_id'].strip()
                
                # 检查是否已存在
                existing = session.query(Device).filter(Device.device_id == device_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 映射 device_type_id（喂食机使用 id=4）
                type_id = int(row['device_type_id']) if row['device_type_id'] else 4
                
                # 确定设备名称
                name = row['name'] if row['name'] else row['type']
                if not name:
                    name = f"设备_{row['id']}"
                
                # 创建 device 记录（必须在构造函数中提供所有字段）
                device = Device(
                    device_id=device_id,
                    name=name,
                    description=row['description'] if row['description'] else None,
                    ownership=row['ownership'] if row['ownership'] else "系统",
                    device_type_id=type_id,
                    model=row['model'] if row['model'] else None,
                    manufacturer=row['manufacturer'] if row['manufacturer'] else None,
                    serial_number=row['serial_number'] if row['serial_number'] else None,
                    location=row['location'] if row['location'] else None,
                    pond_id=int(row['pond_id']) if row['pond_id'] else None,
                    firmware_version=row['firmware_version'] if row['firmware_version'] else None,
                    hardware_version=row['hardware_version'] if row['hardware_version'] else None,
                    ip_address=row['ip_address'] if row['ip_address'] else None,
                    mac_address=row['mac_address'] if row['mac_address'] else None,
                    config_json=None,  # JSON字段，暂时设为None
                    tags=row['tags'] if row['tags'] else None,
                    status=row['status'] if row['status'] else 'offline'
                )
                
                session.add(device)
                success_count += 1
                
                if success_count % 10 == 0:
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ 处理记录失败 (device_id={row.get('device_id')}): {str(e)}")
                session.rollback()  # 回滚以继续处理下一条
                continue
    
    session.commit()
    print(f"\n  ✓ devices.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    print()
    
    return success_count


def migrate_sensors_csv(session):
    """迁移 sensors.csv 数据
    每个传感器需要创建: 1个device记录 + 1个sensor记录
    """
    print("=" * 60)
    print("步骤 4: 迁移 sensors.csv 数据")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/sensors.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                sensor_id_str = row['sensor_id'].strip()
                
                # 检查device是否已存在
                existing_device = session.query(Device).filter(Device.device_id == sensor_id_str).first()
                if existing_device:
                    skip_count += 1
                    continue
                
                # 确定传感器名称
                sensor_name = row['name'].strip() if row['name'] else f"传感器_{row['id']}"
                
                # 1. 创建 Device 记录（必须在构造函数中提供所有字段）
                device = Device(
                    device_id=sensor_id_str,
                    name=sensor_name,
                    description=f"传感器设备 - {sensor_name}",
                    ownership="系统",
                    device_type_id=3,  # sensor类型
                    model=row['model'] if row['model'] else None,
                    manufacturer=None,
                    serial_number=None,
                    location=None,
                    pond_id=int(row['pond_id']) if row['pond_id'] else None,
                    firmware_version=None,
                    hardware_version=None,
                    ip_address=None,
                    mac_address=None,
                    config_json=None,
                    tags=None,
                    status='online' if row['status'] == 'activate' else (row['status'] if row['status'] else 'online')
                )
                
                session.add(device)
                session.flush()  # 获取device.id
                
                # 2. 创建 Sensor 记录
                sensor = Sensor(
                    device_id=device.id,
                    sensor_type_id=int(row['sensor_type_id'])
                )
                
                session.add(sensor)
                success_count += 1
                
                if success_count % 5 == 0:
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ 处理记录失败 (sensor_id={row.get('sensor_id')}): {str(e)}")
                session.rollback()  # 回滚以继续处理下一条
                continue
    
    session.commit()
    print(f"\n  ✓ sensors.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条 (device + sensor)")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    print()
    
    return success_count


def create_feeders_for_devices(session):
    """为 devices.csv 中的喂食机创建 feeder 扩展记录"""
    print("=" * 60)
    print("步骤 5: 为喂食机设备创建 feeder 扩展记录")
    print("=" * 60)
    
    # 查找所有喂食机类型的设备（device_type_id=4）
    feeder_devices = session.query(Device).filter(
        Device.device_type_id == 4
    ).all()
    
    success_count = 0
    skip_count = 0
    
    for device in feeder_devices:
        # 检查是否已有 feeder 记录
        existing_feeder = session.query(Feeder).filter(Feeder.device_id == device.id).first()
        if existing_feeder:
            skip_count += 1
            continue
        
        # 创建 feeder 记录
        feeder = Feeder(
            device_id=device.id,
            feed_count=1,  # 默认值
            feed_portion_weight=Decimal('17.0')  # 默认每份17克
        )
        
        session.add(feeder)
        success_count += 1
    
    session.commit()
    print(f"\n  ✓ 喂食机扩展记录创建完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print()
    
    return success_count


def verify_migration(session):
    """验证迁移结果"""
    print("=" * 60)
    print("步骤 6: 验证迁移结果")
    print("=" * 60)
    
    # 统计各类数据
    device_count = session.query(Device).count()
    sensor_count = session.query(Sensor).count()
    feeder_count = session.query(Feeder).count()
    device_type_count = session.query(DeviceType).count()
    sensor_type_count = session.query(SensorType).count()
    
    print(f"  ✓ 数据统计:")
    print(f"    - 设备类型 (device_types): {device_type_count} 条")
    print(f"    - 传感器类型 (sensor_types): {sensor_type_count} 条")
    print(f"    - 设备 (devices): {device_count} 条")
    print(f"    - 传感器扩展 (sensors): {sensor_count} 条")
    print(f"    - 喂食机扩展 (feeders): {feeder_count} 条")
    
    # 按类型统计设备
    print(f"\n  ✓ 设备类型分布:")
    for device_type in session.query(DeviceType).all():
        count = session.query(Device).filter(Device.device_type_id == device_type.id).count()
        print(f"    - {device_type.name} (id={device_type.id}): {count} 台")
    
    print()


def main():
    """主函数"""
    print("=" * 60)
    print("设备数据综合迁移脚本")
    print("=" * 60)
    print()
    
    try:
        with db_session_factory() as session:
            # 步骤 1: 迁移 sensor_types.csv
            sensor_types_count = migrate_sensor_types_csv(session)
            
            # 步骤 2: 确保设备类型基础数据
            ensure_device_types(session)
            
            # 步骤 3: 迁移 devices.csv
            devices_count = migrate_devices_csv(session)
            
            # 步骤 4: 迁移 sensors.csv
            sensors_count = migrate_sensors_csv(session)
            
            # 步骤 5: 为喂食机创建扩展记录
            feeders_count = create_feeders_for_devices(session)
            
            # 步骤 6: 验证迁移结果
            verify_migration(session)
            
            print("=" * 60)
            print("✓ 所有迁移任务完成！")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

