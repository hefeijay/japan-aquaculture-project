#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合数据迁移脚本 - 一次性完成所有数据迁移
按照依赖关系正确顺序执行迁移，确保外键关系和ID映射正确
"""

import sys
import os
import csv
import json
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
import db_models  # 导入所有模型
from db_models.pond import Pond
from db_models.batch import Batch
from db_models.device import Device, DeviceType
from db_models.sensor_type import SensorType
from db_models.camera import CameraImage, CameraHealth
from db_models.feeder_log import FeederLog
from db_models.sensor_reading import SensorReading
from db_models.shrimp_stats import ShrimpStats
from sqlalchemy import text


class DataMigrator:
    """数据迁移器 - 管理所有迁移流程和ID映射"""
    
    def __init__(self, session):
        self.session = session
        self.backend_dir = backend_dir
        
        # ID映射字典
        self.pond_id_map = {}  # 旧id -> 新id
        self.batch_id_map = {}  # 旧id -> 新batch_id(整数，数据库主键)
        self.device_id_map = {}  # device_id(UUID) -> devices.id
        # 旧传感器ID -> device_id(UUID) -> devices.id 的映射链
        self.old_sensor_id_to_device_id = {}  # 旧sensor.id -> device_id(UUID)
        # 旧喂食机编号 -> device_id(UUID) -> devices.id 的映射链
        self.old_feeder_num_to_device_id = {}  # 旧feeder编号 -> device_id(UUID)
        # 旧摄像头ID -> device_id(UUID) -> devices.id 的映射链
        self.old_camera_id_to_device_id = {}  # 旧camera_id -> device_id(UUID)
        
        # 统计信息
        self.stats = defaultdict(lambda: {'success': 0, 'skip': 0, 'error': 0})
    
    def print_section(self, title, step=None):
        """打印章节标题"""
        print("\n" + "=" * 70)
        if step:
            print(f"步骤 {step}: {title}")
        else:
            print(title)
        print("=" * 70)
    
    def migrate_ponds(self):
        """步骤1: 迁移池子数据"""
        self.print_section("迁移池子数据 (ponds.csv)", 1)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/ponds.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_id = int(row['id'])
                    
                    # 生成业务ID: POND_001, POND_002, ...
                    pond_id = f"POND_{old_id:03d}"
                    
                    # 使用原生SQL插入，保留原ID
                    self.session.execute(text("""
                        INSERT INTO ponds (id, pond_id, name, location, area, count, description)
                        VALUES (:id, :pond_id, :name, :location, :area, :count, :description)
                        ON DUPLICATE KEY UPDATE name=VALUES(name)
                    """), {
                        'id': old_id,
                        'pond_id': pond_id,
                        'name': row['name'],
                        'location': row.get('location'),
                        'area': Decimal(row['area']) if row.get('area') else None,
                        'count': int(row['count']) if row.get('count') else 0,
                        'description': row.get('description')
                    })
                    
                    self.pond_id_map[old_id] = old_id
                    self.stats['ponds']['success'] += 1
                    
                except Exception as e:
                    self.stats['ponds']['error'] += 1
                    print(f"  ❌ 错误 (id={row.get('id')}): {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['ponds']['success']} 成功, {self.stats['ponds']['error']} 失败")
    
    def migrate_batches(self):
        """步骤2: 迁移批次数据"""
        self.print_section("迁移批次数据 (batches.csv)", 2)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/batches.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_batch_id = int(row['batch_id'])
                    old_pool_id = int(row['pool_id'])
                    
                    # 映射 pond_id (pool_id=4 -> pond_id=1)
                    new_pond_id = 1 if old_pool_id == 4 else self.pond_id_map.get(old_pool_id, 1)
                    
                    # 映射数据库ID (旧的2 -> 新的1)
                    new_db_id = 1 if old_batch_id == 2 else old_batch_id
                    
                    # 生成业务ID: BATCH_2024_001, BATCH_2024_002, ...
                    # 从 start_date 提取年份，如果没有则使用 2024
                    year = '2024'
                    if row.get('start_date'):
                        try:
                            year = row['start_date'][:4]
                        except:
                            pass
                    business_batch_id = f"BATCH_{year}_{new_db_id:03d}"
                    
                    self.session.execute(text("""
                        INSERT INTO batches (
                            id, batch_id, pond_id, start_date, species, location,
                            seed_origin, stocking_density, end_date, notes
                        ) VALUES (
                            :id, :batch_id, :pond_id, :start_date, :species, :location,
                            :seed_origin, :stocking_density, :end_date, :notes
                        )
                        ON DUPLICATE KEY UPDATE species=VALUES(species)
                    """), {
                        'id': new_db_id,
                        'batch_id': business_batch_id,
                        'pond_id': new_pond_id,
                        'start_date': row.get('start_date'),
                        'species': row.get('species'),
                        'location': row.get('location'),
                        'seed_origin': row.get('seed_origin'),
                        'stocking_density': Decimal(row['stocking_density']) if row.get('stocking_density') else None,
                        'end_date': row.get('end_date'),
                        'notes': row.get('notes')
                    })
                    
                    self.batch_id_map[old_batch_id] = new_db_id  # 存储数据库主键ID（整数）
                    self.stats['batches']['success'] += 1
                    
                except Exception as e:
                    self.stats['batches']['error'] += 1
                    print(f"  ❌ 错误 (batch_id={row.get('batch_id')}): {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['batches']['success']} 成功, {self.stats['batches']['error']} 失败")
    
    def migrate_device_types(self):
        """步骤3: 迁移设备类型"""
        self.print_section("初始化设备类型 (device_types)", 3)
        
        device_types = [
            (2, 'camera', '摄像头', '监控摄像头'),
            (3, 'sensor', '传感器', '各类传感器设备'),
            (4, 'feeder', '喂食机', '自动喂食设备'),
            (5, 'water_pump', '循环水泵', '循环水泵设备'),
            (6, 'air_blower', '鼓风机', '鼓风机设备'),
            (7, 'water_switch', '水龙头开关', '水龙头开关设备'),
            (8, 'solar_heater_pump', '太阳能加热器循环泵', '太阳能加热器循环泵设备'),
        ]
        
        for type_id, category, name, description in device_types:
            try:
                self.session.execute(text("""
                    INSERT INTO device_types (id, category, name, description)
                    VALUES (:id, :category, :name, :description)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), description=VALUES(description)
                """), {
                    'id': type_id,
                    'category': category,
                    'name': name,
                    'description': description
                })
                self.stats['device_types']['success'] += 1
            except Exception as e:
                self.stats['device_types']['error'] += 1
                print(f"  ❌ 错误 (id={type_id}): {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['device_types']['success']} 成功")
    
    def migrate_sensor_types(self):
        """步骤4: 迁移传感器类型"""
        self.print_section("迁移传感器类型 (sensor_types.csv)", 4)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/sensor_types.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.session.execute(text("""
                        INSERT INTO sensor_types (
                            id, type_name, metric, unit, valid_min, valid_max, description
                        ) VALUES (
                            :id, :type_name, :metric, :unit, :valid_min, :valid_max, :description
                        )
                        ON DUPLICATE KEY UPDATE type_name=VALUES(type_name)
                    """), {
                        'id': int(row['id']),
                        'type_name': row['type_name'],
                        'metric': row.get('metric'),
                        'unit': row.get('unit'),
                        'valid_min': Decimal(row['valid_min']) if row.get('valid_min') else None,
                        'valid_max': Decimal(row['valid_max']) if row.get('valid_max') else None,
                        'description': row.get('description')
                    })
                    self.stats['sensor_types']['success'] += 1
                except Exception as e:
                    self.stats['sensor_types']['error'] += 1
                    print(f"  ❌ 错误 (id={row.get('id')}): {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['sensor_types']['success']} 成功")
    
    def migrate_devices_and_extensions(self):
        """步骤5: 迁移设备及扩展（传感器、喂食机、摄像头）"""
        self.print_section("迁移设备及扩展数据", 5)
        
        # 5.1 迁移传感器设备
        print("\n  5.1 迁移传感器设备...")
        self._migrate_sensors()
        
        # 5.2 迁移喂食机设备
        print("\n  5.2 迁移喂食机设备...")
        self._migrate_feeders()
        
        # 5.3 迁移摄像头设备
        print("\n  5.3 迁移摄像头设备...")
        self._migrate_cameras()
        
        self.session.commit()
        print(f"\n  ✓ 设备迁移完成:")
        print(f"    - 传感器: {self.stats['sensors']['success']} 成功")
        print(f"    - 喂食机: {self.stats['feeders']['success']} 成功")
        print(f"    - 摄像头: {self.stats['cameras']['success']} 成功")
    
    def _migrate_sensors(self):
        """迁移传感器设备（只创建Device记录，不再创建Sensor扩展表）"""
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/sensors.csv')
        if not os.path.exists(csv_path):
            return
        
        # 状态值转换函数
        def normalize_status(status):
            if not status:
                return 'online'
            status_lower = str(status).lower()
            if status_lower in ['activate', 'active', '在线', '正常']:
                return 'online'
            elif status_lower in ['deactivate', 'inactive', '离线', '异常']:
                return 'offline'
            return 'online'  # 默认值
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_sensor_id = int(row['id'])
                    sensor_uuid = row['sensor_id']
                    sensor_type_id = int(row['sensor_type_id']) if row.get('sensor_type_id') and row['sensor_type_id'].strip() else None
                    
                    # 创建 Device（传感器类型，device_type_id=3）
                    # 如果sensor_type_id为None，使用NULL
                    if sensor_type_id is not None:
                        self.session.execute(text("""
                            INSERT INTO devices (
                                device_id, name, device_type_id, sensor_type_id, model, location, 
                                pond_id, status, ownership, control_mode, is_deleted
                            ) VALUES (
                                :device_id, :name, 3, :sensor_type_id, :model, :location, 
                                1, :status, 'own', 'hybrid', 0
                            )
                            ON DUPLICATE KEY UPDATE name=VALUES(name), sensor_type_id=VALUES(sensor_type_id)
                        """), {
                            'device_id': sensor_uuid,
                            'name': row.get('name', f'传感器-{old_sensor_id}').strip(),
                            'sensor_type_id': sensor_type_id,
                            'model': row.get('model', 'sensor') or 'sensor',
                            'location': row.get('location'),
                            'status': normalize_status(row.get('status'))
                        })
                    else:
                        self.session.execute(text("""
                            INSERT INTO devices (
                                device_id, name, device_type_id, model, location, 
                                pond_id, status, ownership, control_mode, is_deleted
                            ) VALUES (
                                :device_id, :name, 3, :model, :location, 
                                1, :status, 'own', 'hybrid', 0
                            )
                            ON DUPLICATE KEY UPDATE name=VALUES(name)
                        """), {
                            'device_id': sensor_uuid,
                            'name': row.get('name', f'传感器-{old_sensor_id}').strip(),
                            'model': row.get('model', 'sensor') or 'sensor',
                            'location': row.get('location'),
                            'status': normalize_status(row.get('status'))
                        })
                    self.session.flush()
                    
                    # 获取 device.id
                    device = self.session.query(Device).filter(Device.device_id == sensor_uuid).first()
                    if not device:
                        continue
                    
                    # 保存映射：旧sensor.id -> device_id(UUID) -> devices.id
                    self.device_id_map[sensor_uuid] = device.id
                    self.old_sensor_id_to_device_id[old_sensor_id] = sensor_uuid
                    self.stats['sensors']['success'] += 1
                    
                except Exception as e:
                    self.stats['sensors']['error'] += 1
                    if self.stats['sensors']['error'] <= 5:
                        print(f"    ❌ 传感器错误 (id={row.get('id')}): {e}")
    
    def _migrate_feeders(self):
        """迁移喂食机设备（只创建Device记录，不再创建Feeder扩展表）"""
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/devices.csv')
        if not os.path.exists(csv_path):
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    device_uuid = row['device_id']
                    device_name = row.get('name', '').lower()
                    
                    # 喂食机的标识：
                    # 1. device_id 以 'feeder_' 开头
                    # 2. name 包含 'feed' 或 'robot'
                    is_feeder = (device_uuid and device_uuid.startswith('feeder_')) or \
                                ('feed' in device_name) or ('robot' in device_name)
                    
                    if not is_feeder:
                        continue
                    
                    # 状态值转换函数
                    def normalize_status(status):
                        if not status:
                            return 'online'
                        status_lower = str(status).lower()
                        if status_lower in ['activate', 'active', '在线', '正常']:
                            return 'online'
                        elif status_lower in ['deactivate', 'inactive', '离线', '异常']:
                            return 'offline'
                        return 'online'  # 默认值
                    
                    # 创建 Device（喂食机类型，device_type_id=4）
                    self.session.execute(text("""
                        INSERT INTO devices (
                            device_id, name, device_type_id, model, manufacturer,
                            location, pond_id, status, control_mode, ownership, is_deleted
                        ) VALUES (
                            :device_id, :name, 4, :model, :manufacturer,
                            :location, 1, :status, :control_mode, 'own', 0
                        )
                        ON DUPLICATE KEY UPDATE name=VALUES(name)
                    """), {
                        'device_id': device_uuid,
                        'name': row.get('name', 'Feeder'),
                        'model': row.get('model') or None,
                        'manufacturer': row.get('manufacturer') or None,
                        'location': row.get('location') or None,
                        'status': normalize_status(row.get('status')),
                        'control_mode': row.get('control_mode', 'hybrid')
                    })
                    self.session.flush()
                    
                    # 获取 device.id
                    device = self.session.query(Device).filter(Device.device_id == device_uuid).first()
                    if not device:
                        continue
                    
                    # 保存映射
                    self.device_id_map[device_uuid] = device.id
                    
                    # 提取喂食机编号并保存映射
                    feeder_num = None
                    if device_uuid.startswith('feeder_'):
                        try:
                            feeder_num = int(device_uuid.replace('feeder_', ''))
                            self.old_feeder_num_to_device_id[str(feeder_num)] = device_uuid
                        except:
                            pass
                    
                    self.stats['feeders']['success'] += 1
                    
                except Exception as e:
                    self.stats['feeders']['error'] += 1
                    if self.stats['feeders']['error'] <= 5:
                        print(f"    ❌ 喂食机错误: {e}")
    
    def _migrate_cameras(self):
        """迁移摄像头设备（只创建Device记录，不再创建Camera扩展表）"""
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/camera_status.csv')
        if not os.path.exists(csv_path):
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_camera_id = int(row['camera_id'])
                    camera_uuid = f"camera_{old_camera_id}"
                    
                    # 创建 Device（摄像头类型，device_type_id=2）
                    # 摄像头专属配置可以存储在 device_specific_config JSON 字段中
                    device_config = {}
                    if row.get('connectivity'):
                        device_config['connectivity'] = int(row['connectivity'])
                    if row.get('fps'):
                        device_config['fps'] = int(row['fps'])
                    if row.get('recording'):
                        device_config['recording'] = row.get('recording', '').lower() == 'true'
                    if row.get('night_vision'):
                        device_config['night_vision'] = row.get('night_vision', '').lower() == 'true'
                    if row.get('motion_detection'):
                        device_config['motion_detection'] = row.get('motion_detection', '').lower() == 'true'
                    if row.get('quality'):
                        device_config['quality'] = row['quality']
                    if row.get('temperature'):
                        device_config['temperature'] = float(row['temperature'])
                    if row.get('resolution'):
                        device_config['resolution'] = row['resolution']
                    
                    config_json = json.dumps(device_config) if device_config else None
                    
                    # 状态值转换函数
                    def normalize_status(status):
                        if not status:
                            return 'online'
                        status_lower = str(status).lower()
                        if status_lower in ['activate', 'active', '在线', '正常']:
                            return 'online'
                        elif status_lower in ['deactivate', 'inactive', '离线', '异常']:
                            return 'offline'
                        return 'online'  # 默认值
                    
                    self.session.execute(text("""
                        INSERT INTO devices (
                            device_id, name, device_type_id, location, pond_id, 
                            status, ownership, control_mode, device_specific_config, is_deleted
                        ) VALUES (
                            :device_id, :name, 2, :location, 1, 
                            :status, 'own', 'hybrid', :device_specific_config, 0
                        )
                        ON DUPLICATE KEY UPDATE name=VALUES(name), device_specific_config=VALUES(device_specific_config)
                    """), {
                        'device_id': camera_uuid,
                        'name': row.get('name', f'摄像头-{old_camera_id}'),
                        'location': row.get('location'),
                        'status': normalize_status(row.get('status')),
                        'device_specific_config': config_json
                    })
                    self.session.flush()
                    
                    # 获取 device.id
                    device = self.session.query(Device).filter(Device.device_id == camera_uuid).first()
                    if not device:
                        continue
                    
                    # 保存映射：旧camera_id -> device_id(UUID) -> devices.id
                    self.device_id_map[camera_uuid] = device.id
                    self.old_camera_id_to_device_id[old_camera_id] = camera_uuid
                    self.stats['cameras']['success'] += 1
                    
                except Exception as e:
                    self.stats['cameras']['error'] += 1
                    if self.stats['cameras']['error'] <= 5:
                        print(f"    ❌ 摄像头错误 (camera_id={row.get('camera_id')}): {e}")
    
    def migrate_sensor_readings(self):
        """步骤6: 迁移传感器读数（使用device_id而不是sensor_id）"""
        self.print_section("迁移传感器读数 (sensor_readings.csv)", 6)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/sensor_readings.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        print(f"  📊 传感器设备映射: {len(self.old_sensor_id_to_device_id)} 个")
        
        # 建立 device_id -> metric 的映射（从Device和SensorType获取）
        device_to_metric = {}
        devices = self.session.query(Device).filter(Device.device_type_id == 3).all()  # 只查询传感器设备
        for device in devices:
            if device.sensor_type_id:
                sensor_type = self.session.query(SensorType).filter(SensorType.id == device.sensor_type_id).first()
                if sensor_type and sensor_type.metric:
                    device_to_metric[device.id] = sensor_type.metric
        
        print(f"  📊 设备metric映射: {len(device_to_metric)} 个")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_sensor_id = int(row['sensor_id'])
                    # 通过旧sensor_id找到device_id，再找到devices.id
                    device_uuid = self.old_sensor_id_to_device_id.get(old_sensor_id)
                    if not device_uuid:
                        self.stats['sensor_readings']['error'] += 1
                        continue
                    
                    device_db_id = self.device_id_map.get(device_uuid)
                    if not device_db_id:
                        self.stats['sensor_readings']['error'] += 1
                        continue
                    
                    # 解析时间
                    ts_utc = None
                    if row.get('ts_utc'):
                        try:
                            ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S.%f')
                        except:
                            try:
                                ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S')
                            except:
                                ts_utc = datetime.utcnow()
                    
                    if not ts_utc:
                        ts_utc = datetime.utcnow()
                    
                    value = float(row['value']) if row.get('value') else 0.0
                    
                    reading = SensorReading(
                        device_id=device_db_id,  # 使用device_id而不是sensor_id
                        pond_id=1,
                        value=value
                    )
                    
                    if self.batch_id_map:
                        # 使用第一个批次的数据库主键ID（整数）
                        reading.batch_id = list(self.batch_id_map.values())[0]
                    reading.ts_utc = ts_utc
                    
                    # 填充 metric（快照字段，从 sensor_types 同步）
                    metric = device_to_metric.get(device_db_id)
                    if metric:
                        reading.metric = metric
                    
                    if row.get('unit'):
                        reading.unit = row['unit']
                    if row.get('quality_flag'):
                        reading.quality_flag = row['quality_flag']
                    
                    self.session.add(reading)
                    self.stats['sensor_readings']['success'] += 1
                    
                    if self.stats['sensor_readings']['success'] % 5000 == 0:
                        self.session.flush()
                        print(f"  进度: {self.stats['sensor_readings']['success']} 条...")
                    
                except Exception as e:
                    self.stats['sensor_readings']['error'] += 1
                    if self.stats['sensor_readings']['error'] <= 5:
                        print(f"  ❌ 错误: {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['sensor_readings']['success']} 成功, {self.stats['sensor_readings']['error']} 失败")
    
    def migrate_feeder_logs(self):
        """步骤7: 迁移喂食机日志（使用device_id而不是feeder_id）"""
        self.print_section("迁移喂食机日志 (feeders_logs.csv)", 7)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/feeders_logs.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        print(f"  📊 喂食机设备映射: {len(self.old_feeder_num_to_device_id)} 个")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    feeder_id_str = str(row['feeder_id'])
                    # 通过旧feeder编号找到device_id，再找到devices.id
                    device_uuid = self.old_feeder_num_to_device_id.get(feeder_id_str)
                    if not device_uuid:
                        self.stats['feeder_logs']['error'] += 1
                        continue
                    
                    device_db_id = self.device_id_map.get(device_uuid)
                    if not device_db_id:
                        self.stats['feeder_logs']['error'] += 1
                        continue
                    
                    # 解析时间
                    ts_utc = None
                    if row.get('ts_utc'):
                        try:
                            ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S.%f')
                        except:
                            try:
                                ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S')
                            except:
                                ts_utc = datetime.utcnow()
                    
                    if not ts_utc:
                        ts_utc = datetime.utcnow()
                    
                    log = FeederLog(
                        device_id=device_db_id,  # 使用device_id而不是feeder_id
                        pond_id=1,
                        ts_utc=ts_utc,
                        status=row.get('status', 'ok')
                    )
                    
                    if self.batch_id_map:
                        # 使用第一个批次的数据库主键ID（整数）
                        log.batch_id = list(self.batch_id_map.values())[0]
                    if row.get('feed_amount_g'):
                        log.feed_amount_g = Decimal(row['feed_amount_g'])
                    if row.get('notes'):
                        log.notes = row['notes']
                    
                    self.session.add(log)
                    self.stats['feeder_logs']['success'] += 1
                    
                    if self.stats['feeder_logs']['success'] % 500 == 0:
                        self.session.flush()
                        print(f"  进度: {self.stats['feeder_logs']['success']} 条...")
                    
                except Exception as e:
                    self.stats['feeder_logs']['error'] += 1
                    if self.stats['feeder_logs']['error'] <= 5:
                        print(f"  ❌ 错误: {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['feeder_logs']['success']} 成功, {self.stats['feeder_logs']['error']} 失败")
    
    def migrate_camera_images(self):
        """步骤8: 迁移摄像头图片（使用device_id而不是camera_id）"""
        self.print_section("迁移摄像头图片 (camera_images.csv)", 8)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/camera_images.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        print(f"  📊 摄像头设备映射: {len(self.old_camera_id_to_device_id)} 个")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    old_camera_id = int(row['camera_id'])
                    # 通过旧camera_id找到device_id，再找到devices.id
                    device_uuid = self.old_camera_id_to_device_id.get(old_camera_id)
                    if not device_uuid:
                        self.stats['camera_images']['error'] += 1
                        continue
                    
                    device_db_id = self.device_id_map.get(device_uuid)
                    if not device_db_id:
                        self.stats['camera_images']['error'] += 1
                        continue
                    
                    # 解析时间
                    ts_utc = datetime.utcnow()
                    if row.get('timestamp'):
                        try:
                            ts_ms = int(row['timestamp'])
                            ts_utc = datetime.fromtimestamp(ts_ms / 1000.0)
                        except:
                            pass
                    
                    image = CameraImage(
                        device_id=device_db_id,  # 使用device_id而不是camera_id
                        pond_id=1,
                        image_url=row.get('image_url', ''),
                        ts_utc=ts_utc,
                        timestamp_str=row.get('timestamp_str', ''),
                        width=int(row['width']) if row.get('width') and int(row['width']) > 0 else 1920,
                        height=int(row['height']) if row.get('height') and int(row['height']) > 0 else 1080,
                        format=row.get('format', 'jpg'),
                        size=int(row.get('size', 0)),
                        fps=int(row.get('fps', 0))
                    )
                    
                    if self.batch_id_map:
                        # 使用第一个批次的数据库主键ID（整数）
                        image.batch_id = list(self.batch_id_map.values())[0]
                    
                    self.session.add(image)
                    self.stats['camera_images']['success'] += 1
                    
                    if self.stats['camera_images']['success'] % 1000 == 0:
                        self.session.flush()
                        print(f"  进度: {self.stats['camera_images']['success']} 条...")
                    
                except Exception as e:
                    self.stats['camera_images']['error'] += 1
                    if self.stats['camera_images']['error'] <= 5:
                        print(f"  ❌ 错误: {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['camera_images']['success']} 成功, {self.stats['camera_images']['error']} 失败")
    
    def migrate_shrimp_stats(self):
        """步骤9: 迁移虾统计数据"""
        self.print_section("迁移虾统计数据 (shrimp_stats.csv)", 9)
        
        csv_path = os.path.join(self.backend_dir, 'db_models/db_datas/shrimp_stats.csv')
        if not os.path.exists(csv_path):
            print("  ⚠️  文件不存在，跳过")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # 解析时间
                    ts_utc = datetime.utcnow()
                    if row.get('created_at_source'):
                        try:
                            ts_utc = datetime.strptime(row['created_at_source'], '%Y-%m-%d %H:%M:%S.%f')
                        except:
                            pass
                    
                    stat = ShrimpStats(
                        ts_utc=ts_utc,
                        pond_id=1
                    )
                    
                    if self.batch_id_map:
                        # 使用第一个批次的数据库主键ID（整数）
                        stat.batch_id = list(self.batch_id_map.values())[0]
                    
                    if row.get('count'):
                        try:
                            stat.count = int(row['count'])
                        except:
                            pass
                    if row.get('size_mean_cm'):
                        try:
                            stat.size_mean_cm = float(row['size_mean_cm'])
                        except:
                            pass
                    if row.get('weight_mean_g'):
                        try:
                            stat.weight_mean_g = float(row['weight_mean_g'])
                        except:
                            pass
                    
                    self.session.add(stat)
                    self.stats['shrimp_stats']['success'] += 1
                    
                except Exception as e:
                    self.stats['shrimp_stats']['error'] += 1
                    if self.stats['shrimp_stats']['error'] <= 5:
                        print(f"  ❌ 错误: {e}")
        
        self.session.commit()
        print(f"  ✓ 完成: {self.stats['shrimp_stats']['success']} 成功, {self.stats['shrimp_stats']['error']} 失败")
    
    def print_summary(self):
        """打印迁移汇总"""
        self.print_section("迁移汇总报告")
        
        print("\n📊 各表迁移统计:")
        print(f"{'表名':<20} {'成功':>8} {'跳过':>8} {'失败':>8}")
        print("-" * 50)
        
        for table, stats in sorted(self.stats.items()):
            print(f"{table:<20} {stats['success']:>8} {stats['skip']:>8} {stats['error']:>8}")
        
        total_success = sum(s['success'] for s in self.stats.values())
        total_error = sum(s['error'] for s in self.stats.values())
        
        print("-" * 50)
        print(f"{'总计':<20} {total_success:>8} {0:>8} {total_error:>8}")
        
        print(f"\n✅ 迁移完成! 成功: {total_success}, 失败: {total_error}")


def main():
    """主函数"""
    print("=" * 70)
    print("综合数据迁移脚本 - 一次性完成所有数据迁移")
    print("=" * 70)
    print("\n⚠️  警告: 此脚本将按依赖顺序迁移所有数据")
    print("建议在运行前备份数据库\n")
    
    try:
        with db_session_factory() as session:
            migrator = DataMigrator(session)
            
            # 按依赖顺序执行迁移
            migrator.migrate_ponds()              # 1. 基础：池子
            migrator.migrate_batches()            # 2. 依赖池子：批次
            migrator.migrate_device_types()       # 3. 基础：设备类型
            migrator.migrate_sensor_types()       # 4. 基础：传感器类型
            migrator.migrate_devices_and_extensions()  # 5. 设备+扩展（传感器/喂食机/摄像头）
            migrator.migrate_sensor_readings()    # 6. 依赖传感器：传感器读数
            migrator.migrate_feeder_logs()        # 7. 依赖喂食机：喂食机日志
            migrator.migrate_camera_images()      # 8. 依赖摄像头：摄像头图片
            migrator.migrate_shrimp_stats()       # 9. 依赖图片：虾统计
            
            # 打印汇总
            migrator.print_summary()
            
            return True
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

