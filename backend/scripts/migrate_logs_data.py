#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志数据迁移脚本
迁移 feeders_logs.csv 和 sensor_readings.csv 到新的表结构
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
from db_models.feeder_log import FeederLog
from db_models.sensor_reading import SensorReading
from db_models.device import Device
from db_models.sensor import Sensor
from db_models.feeder import Feeder
from sqlalchemy import text


def migrate_feeder_logs(session):
    """迁移 feeders_logs.csv 数据"""
    print("=" * 60)
    print("步骤 1: 迁移 feeders_logs.csv 数据")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/feeders_logs.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    # 先构建 feeder_id(CSV中的字符串) -> feeders.id 的映射（不是devices.id！）
    print("  正在构建喂食机ID映射...")
    feeder_id_map = {}
    feeders = session.query(Feeder).all()
    for feeder in feeders:
        # 获取该喂食机对应的设备
        device = session.query(Device).filter(Device.id == feeder.device_id).first()
        if device and device.device_id.startswith('feeder_'):
            # device_id 格式如 "feeder_126437392"，提取数字部分
            feeder_num = device.device_id.replace('feeder_', '')
            feeder_id_map[feeder_num] = feeder.id  # 映射到 feeders.id，不是 devices.id
    
    print(f"  ✓ 映射关系已建立: {len(feeder_id_map)} 个喂食机")
    
    # 检查 batch_id=1 是否存在
    from db_models.batch import Batch
    batch_exists = session.query(Batch).filter(Batch.batch_id == 1).first() is not None
    if not batch_exists:
        print(f"  ⚠️  警告: batches 表中不存在 batch_id=1，将跳过 batch_id 字段")
    else:
        print(f"  ✓ 批次数据已就绪: batch_id=1")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 检查是否已存在（根据 id）
                log_id = int(row['id'])
                existing = session.query(FeederLog).filter(FeederLog.id == log_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 获取 feeder_id 对应的 device.id
                feeder_id_str = str(row['feeder_id'])
                device_id = feeder_id_map.get(feeder_id_str)
                
                if not device_id:
                    error_count += 1
                    if error_count <= 5:  # 只显示前5个错误
                        print(f"  ⚠️  未找到 feeder_id={feeder_id_str} 对应的设备")
                    continue
                
                # 解析时间
                ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S.%f') if row['ts_utc'] else None
                ts_local = datetime.strptime(row['ts_local'], '%Y-%m-%d %H:%M:%S.%f') if row['ts_local'] else None
                
                # 创建 FeederLog 记录（只传必需参数）
                feeder_log = FeederLog(
                    feeder_id=device_id,  # 使用 feeders.id
                    pond_id=1,  # pool_id=4 映射到 pond_id=1
                    ts_utc=ts_utc,
                    status=row['status'] if row['status'] else 'ok'
                )
                
                # 设置可选字段（这些都标记了 init=False）
                if row['batch_id'] and batch_exists:
                    # 映射 batch_id: CSV中的2 -> 数据库中的1
                    csv_batch_id = int(row['batch_id'])
                    feeder_log.batch_id = 1 if csv_batch_id == 2 else csv_batch_id
                if row['ts_local']:
                    feeder_log.ts_local = ts_local
                if row['feed_amount_g']:
                    feeder_log.feed_amount_g = Decimal(row['feed_amount_g'])
                if row['run_time_s']:
                    feeder_log.run_time_s = int(row['run_time_s'])
                if row['leftover_estimate_g']:
                    feeder_log.leftover_estimate_g = Decimal(row['leftover_estimate_g'])
                if row['notes']:
                    feeder_log.notes = row['notes']
                if row['checksum']:
                    feeder_log.checksum = row['checksum']
                
                session.add(feeder_log)
                success_count += 1
                
                if success_count % 500 == 0:
                    session.flush()  # 定期刷新
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只显示前5个错误
                    print(f"  ❌ 处理记录失败 (id={row.get('id')}): {str(e)}")
                session.rollback()
                continue
    
    session.commit()
    print(f"\n  ✓ feeders_logs.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    print()
    
    return success_count


def migrate_sensor_readings(session):
    """迁移 sensor_readings.csv 数据"""
    print("=" * 60)
    print("步骤 2: 迁移 sensor_readings.csv 数据")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/sensor_readings.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    # 检查 batch_id=1 是否存在
    from db_models.batch import Batch
    batch_exists = session.query(Batch).filter(Batch.batch_id == 1).first() is not None
    if not batch_exists:
        print(f"  ⚠️  警告: batches 表中不存在 batch_id=1，将跳过 batch_id 字段")
    else:
        print(f"  ✓ 批次数据已就绪: batch_id=1")
    
    # 构建 sensor_id(CSV中的整数) -> sensor表的id 的映射
    # CSV中的 sensor_id 是旧表的 sensors.id
    # 需要通过 device_id 来找到新表中的 sensor.id
    print("  正在构建传感器ID映射...")
    
    # 由于 sensors.csv 中的 id 字段可以作为映射关键
    # 我们需要查询所有 sensors 和对应的 devices
    sensor_id_map = {}
    
    # 从 sensors.csv 读取旧的 id -> sensor_id(UUID) 映射
    sensors_csv = os.path.join(backend_dir, 'db_models/db_datas/sensors.csv')
    old_sensor_map = {}  # old_id -> device_id(UUID)
    if os.path.exists(sensors_csv):
        with open(sensors_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_sensor_map[int(row['id'])] = row['sensor_id']
    
    # 查询新表中的 sensors 和对应的 devices
    sensors = session.query(Sensor).join(Device).all()
    for sensor in sensors:
        device_id_uuid = sensor.device.device_id
        # 在旧映射中找到对应的 old_id
        for old_id, uuid in old_sensor_map.items():
            if uuid == device_id_uuid:
                sensor_id_map[old_id] = sensor.id
                break
    
    print(f"  ✓ 映射关系已建立: {len(sensor_id_map)} 个传感器")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    unmapped_sensors = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 检查是否已存在（根据 id）
                reading_id = int(row['id'])
                existing = session.query(SensorReading).filter(SensorReading.id == reading_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 获取 sensor_id 对应的新 sensor.id
                old_sensor_id = int(row['sensor_id'])
                new_sensor_id = sensor_id_map.get(old_sensor_id)
                
                if not new_sensor_id:
                    unmapped_sensors.add(old_sensor_id)
                    error_count += 1
                    continue
                
                # 解析时间
                ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S.%f') if row['ts_utc'] else None
                ts_local = datetime.strptime(row['ts_local'], '%Y-%m-%d %H:%M:%S.%f') if row['ts_local'] else None
                
                # 创建 SensorReading 记录（只传必需参数）
                sensor_reading = SensorReading(
                    sensor_id=new_sensor_id,
                    pond_id=1,  # pool_id=4 映射到 pond_id=1
                    value=float(row['value']) if row['value'] else 0.0
                )
                
                # 设置可选字段（这些都标记了 init=False）
                if row['batch_id'] and batch_exists:
                    # 映射 batch_id: CSV中的2 -> 数据库中的1
                    csv_batch_id = int(row['batch_id'])
                    sensor_reading.batch_id = 1 if csv_batch_id == 2 else csv_batch_id
                if row['ts_utc']:
                    sensor_reading.ts_utc = ts_utc
                if row['ts_local']:
                    sensor_reading.ts_local = ts_local
                if row['unit']:
                    sensor_reading.unit = row['unit']
                if row['quality_flag']:
                    sensor_reading.quality_flag = row['quality_flag']
                if row['checksum']:
                    sensor_reading.checksum = row['checksum']
                
                session.add(sensor_reading)
                success_count += 1
                
                if success_count % 5000 == 0:
                    session.flush()  # 定期刷新
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只显示前5个错误
                    print(f"  ❌ 处理记录失败 (id={row.get('id')}): {str(e)}")
                session.rollback()
                continue
    
    session.commit()
    
    if unmapped_sensors:
        print(f"\n  ⚠️  未映射的传感器ID: {sorted(unmapped_sensors)}")
    
    print(f"\n  ✓ sensor_readings.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    print()
    
    return success_count


def verify_migration(session):
    """验证迁移结果"""
    print("=" * 60)
    print("步骤 3: 验证迁移结果")
    print("=" * 60)
    
    # 统计各类数据
    feeder_log_count = session.query(FeederLog).count()
    sensor_reading_count = session.query(SensorReading).count()
    
    print(f"  ✓ 数据统计:")
    print(f"    - 喂食机日志 (feeder_logs): {feeder_log_count} 条")
    print(f"    - 传感器读数 (sensor_readings): {sensor_reading_count} 条")
    
    # 按日期范围统计
    print(f"\n  ✓ 数据时间范围:")
    
    # 喂食机日志时间范围
    result = session.execute(text("""
        SELECT MIN(ts_utc) as min_date, MAX(ts_utc) as max_date 
        FROM feeder_logs 
        WHERE ts_utc IS NOT NULL
    """)).first()
    if result and result[0]:
        print(f"    - 喂食机日志: {result[0]} ~ {result[1]}")
    
    # 传感器读数时间范围
    result = session.execute(text("""
        SELECT MIN(ts_utc) as min_date, MAX(ts_utc) as max_date 
        FROM sensor_readings 
        WHERE ts_utc IS NOT NULL
    """)).first()
    if result and result[0]:
        print(f"    - 传感器读数: {result[0]} ~ {result[1]}")
    
    print()


def main():
    """主函数"""
    print("=" * 60)
    print("日志数据迁移脚本")
    print("=" * 60)
    print()
    
    try:
        with db_session_factory() as session:
            # 步骤 1: 迁移 feeders_logs
            feeder_logs_count = migrate_feeder_logs(session)
            
            # 步骤 2: 迁移 sensor_readings
            sensor_readings_count = migrate_sensor_readings(session)
            
            # 步骤 3: 验证迁移结果
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

