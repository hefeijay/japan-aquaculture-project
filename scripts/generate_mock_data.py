#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成Mock数据脚本
根据数据库表设计生成测试数据，包括：
- 用户（gmm, admin, fish）
- 养殖池、批次
- 设备类型、传感器类型
- 设备（传感器、喂食机、摄像头）
- 传感器读数
- 喂食机记录
- 摄像头图片和健康检查
- 预警规则和预警记录
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
import uuid
import hashlib

# 添加 backend 目录到 Python 路径
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app_factory import create_app
from db_models import (
    db, Pond, Batch, DeviceType, SensorType, Device, 
    SensorReading, FeederLog, CameraImage, CameraHealth, User,
    AlertRule, AlertNotification
)


# 8种传感器类型配置（匹配数据库表结构）
SENSOR_TYPES_CONFIG = [
    {
        "type_name": "dissolved_oxygen_aturation",
        "metric": "do",
        "unit": "mg/L",
        "valid_min": 4.0,
        "valid_max": 9.0,
        "description": "溶解氧饱和度"
    },
    {
        "type_name": "liquid_level",
        "metric": "water_level",
        "unit": "mm",
        "valid_min": 980,
        "valid_max": 1000,
        "description": "液位"
    },
    {
        "type_name": "PH",
        "metric": "PH",
        "unit": "pH",
        "valid_min": 7.4,
        "valid_max": 8.6,
        "description": "PH"
    },
    {
        "type_name": "temperature",
        "metric": "temperature",
        "unit": "°C",
        "valid_min": 22.0,
        "valid_max": 34.0,
        "description": "温度"
    },
    {
        "type_name": "turbidity",
        "metric": "turbidity",
        "unit": "NTU",
        "valid_min": 0.0,
        "valid_max": 200.0,
        "description": "浊度"
    },
    {
        "type_name": "ammonia",
        "metric": "ammonia",
        "unit": "mg/L",
        "valid_min": 0.0,
        "valid_max": 0.5,
        "description": "氨氮浓度"
    },
    {
        "type_name": "nitrite",
        "metric": "nitrite",
        "unit": "mg/L",
        "valid_min": 0.0,
        "valid_max": 0.5,
        "description": "亚硝酸盐浓度"
    },
    {
        "type_name": "circulation",
        "metric": "circulation",
        "unit": "unknown",
        "valid_min": 0.0,
        "valid_max": 100.0,
        "description": "Auto-created sensor type for circulation"
    }
]

# 需要创建设备的传感器类型（只创建5个设备）
SENSOR_DEVICE_METRICS = ["do", "water_level", "PH", "temperature", "turbidity"]

# 传感器设备中文名称映射
SENSOR_DEVICE_NAMES = {
    "do": "溶解氧传感器",
    "water_level": "液位传感器",
    "PH": "PH传感器",
    "temperature": "温度传感器",
    "turbidity": "浊度传感器",
    "ammonia": "氨氮传感器",
    "nitrite": "亚硝酸盐传感器",
    "circulation": "循环传感器"
}

# 设备类型配置
DEVICE_TYPES_CONFIG = [
    {"category": "sensor", "name": "传感器", "description": "各类传感器设备"},
    {"category": "feeder", "name": "自动喂食机", "description": "自动投喂设备"},
    {"category": "camera", "name": "监控摄像头", "description": "视频监控设备"},
    {"category": "water_pump", "name": "循环水泵", "description": "水循环设备"},
    {"category": "air_blower", "name": "鼓风机", "description": "增氧设备"},
    {"category": "water_switch", "name": "水龙头开关", "description": "水龙头控制设备"},
    {"category": "solar_heater_pump", "name": "太阳能加热器循环泵", "description": "太阳能加热循环设备"},
]


def generate_connection_info(device_counter: int) -> dict:
    """生成设备连接信息（所有设备类型通用）"""
    return {
        "url": f"http://192.168.1.{100 + (device_counter % 50)}",
        "username": "admin",
        "password": f"password{device_counter:04d}"
    }


def generate_device_specific_config(category: str, device_counter: int) -> dict:
    """根据设备类型生成设备专属配置"""
    if category == "sensor":
        # 传感器不需要在device_specific_config中存储特殊字段
        return None
    
    elif category == "feeder":
        # 喂食机配置
        return {
            "feed_count": random.randint(1, 5),  # 默认喂食份数
            "timezone": 9,  # 时区（UTC+9，日本时区）
            "network_type": random.choice([0, 1]),  # 0=WiFi, 1=4G
            "group_id": f"GROUP-{chr(65 + (device_counter % 26))}",  # 设备分组ID
            "feed_portion_weight": round(random.uniform(15.0, 25.0), 1),  # 每份饲料重量（克）
            "capacity_kg": round(random.uniform(50.0, 200.0), 1),  # 饲料容量（千克）
            "feed_type": random.choice(["虾料A型", "虾料B型", "虾料C型", "通用饲料"])
        }
    
    elif category == "camera":
        # 摄像头配置
        return {
            "quality": random.choice(["高", "中", "低"]),
            "resolution": random.choice(["1920x1080", "1280x720", "2560x1440"]),
            "notes": f"摄像头设备{device_counter}的备注信息"
        }
    
    elif category == "water_pump":
        # 循环水泵配置
        return {
            "flow_rate": round(random.uniform(10.0, 50.0), 2),  # 循环量（L/min）
            "power": round(random.uniform(0.5, 3.0), 2),  # 功率（kW）
            "notes": f"循环水泵设备{device_counter}的备注信息"
        }
    
    elif category == "air_blower":
        # 鼓风机配置
        return {
            "air_flow": round(random.uniform(50.0, 200.0), 2),  # 气量（L/min）
            "power": round(random.uniform(0.3, 2.0), 2),  # 功率（kW）
            "notes": f"鼓风机设备{device_counter}的备注信息"
        }
    
    elif category == "water_switch":
        # 水龙头开关配置
        return {
            "notes": f"水龙头开关设备{device_counter}的备注信息"
        }
    
    elif category == "solar_heater_pump":
        # 太阳能加热器循环泵配置
        return {
            "flow_rate": round(random.uniform(8.0, 30.0), 2),  # 循环量（L/min）
            "power": round(random.uniform(0.4, 2.5), 2),  # 功率（kW）
            "notes": f"太阳能加热器循环泵设备{device_counter}的备注信息"
        }
    
    else:
        return None


def generate_sensor_value(metric: str, base_time: datetime) -> float:
    """根据传感器类型生成合理的读数值"""
    hour = base_time.hour
    metric_lower = metric.lower()  # 统一转小写处理
    
    if metric_lower == "do":
        # 溶解氧：白天高，夜间低，范围5-12 mg/L
        base = 8.5 + 2.5 * (1 if 6 <= hour <= 18 else -1) * 0.5
        return round(base + random.uniform(-1.0, 1.0), 2)
    
    elif metric_lower == "ph":
        # pH值：相对稳定，范围7.0-8.5
        return round(7.5 + random.uniform(-0.3, 0.8), 2)
    
    elif metric_lower == "temperature":
        # 温度：白天高，夜间低，范围22-28°C
        base = 25.0 + 2.0 * (1 if 10 <= hour <= 16 else -1) * 0.3
        return round(base + random.uniform(-1.0, 1.0), 2)
    
    elif metric_lower == "turbidity":
        # 浊度：范围0-30 NTU
        return round(random.uniform(2.0, 25.0), 2)
    
    elif metric_lower == "water_level":
        # 液位：范围1500-3000 mm
        return round(random.uniform(1800.0, 2800.0), 2)
    
    elif metric_lower == "ammonia":
        # 氨氮：范围0-0.5 mg/L
        return round(random.uniform(0.05, 0.35), 3)
    
    elif metric_lower == "nitrite":
        # 亚硝酸盐：范围0-0.1 mg/L
        return round(random.uniform(0.01, 0.08), 3)
    
    elif metric_lower == "circulation":
        # 循环：范围0-100
        return round(random.uniform(0.0, 100.0), 2)
    
    else:
        return round(random.uniform(0.0, 100.0), 2)


def generate_mock_data():
    """生成所有mock数据"""
    print("=" * 60)
    print("开始生成Mock数据")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # 0. 创建用户
        print("\n[0/9] 创建用户...")
        users_config = [
            {"username": "gmm", "user_id": "USER_GMM", "role": "admin"},
            {"username": "admin", "user_id": "USER_ADMIN", "role": "admin"},
            {"username": "fish", "user_id": "USER_FISH", "role": "user"}
        ]
        password = "123456"
        # 使用MD5哈希（32字符），符合password_hash字段String(128)的限制
        # 系统支持MD5哈希验证（见backend/routes/api_routes.py）
        password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        
        for user_config in users_config:
            existing = db.session.query(User).filter_by(username=user_config["username"]).first()
            if existing:
                print(f"  ✓ 用户已存在: {user_config['username']}")
            else:
                user = User(
                    user_id=user_config["user_id"],
                    username=user_config["username"],
                    password_hash=password_hash,
                    role=user_config["role"],
                    status="active"
                )
                db.session.add(user)
                print(f"  ✓ 创建用户: {user_config['username']} (密码: {password})")
        
        db.session.commit()
        
        # 1. 创建设备类型
        print("\n[1/9] 创建设备类型...")
        device_type_map = {}
        for dt_config in DEVICE_TYPES_CONFIG:
            existing = db.session.query(DeviceType).filter_by(name=dt_config["name"]).first()
            if existing:
                device_type_map[dt_config["category"]] = existing
                print(f"  ✓ 设备类型已存在: {dt_config['name']}")
            else:
                device_type = DeviceType(
                    category=dt_config["category"],
                    name=dt_config["name"],
                    description=dt_config["description"]
                )
                db.session.add(device_type)
                db.session.flush()
                device_type_map[dt_config["category"]] = device_type
                print(f"  ✓ 创建设备类型: {dt_config['name']}")
        
        db.session.commit()
        
        # 2. 创建传感器类型
        print("\n[2/9] 创建传感器类型...")
        sensor_type_map = {}
        for st_config in SENSOR_TYPES_CONFIG:
            existing = db.session.query(SensorType).filter_by(metric=st_config["metric"]).first()
            if existing:
                sensor_type_map[st_config["metric"]] = existing
                print(f"  ✓ 传感器类型已存在: {st_config['type_name']}")
            else:
                sensor_type = SensorType(
                    type_name=st_config["type_name"],
                    metric=st_config["metric"],
                    unit=st_config["unit"],
                    valid_min=st_config["valid_min"],
                    valid_max=st_config["valid_max"],
                    description=st_config["description"]
                )
                db.session.add(sensor_type)
                db.session.flush()
                sensor_type_map[st_config["metric"]] = sensor_type
                print(f"  ✓ 创建传感器类型: {st_config['type_name']}")
        
        db.session.commit()
        
        # 3. 创建养殖池
        print("\n[3/9] 创建养殖池...")
        ponds = []
        pond_names = ["1号池", "2号池", "3号池", "4号池"]
        for i, name in enumerate(pond_names, 1):
            existing = db.session.query(Pond).filter_by(pond_id=f"POND_{i:03d}").first()
            if existing:
                ponds.append(existing)
                print(f"  ✓ 养殖池已存在: {name}")
            else:
                pond = Pond(
                    pond_id=f"POND_{i:03d}",
                    name=name,
                    location=f"车间A-{i}区",
                    area=round(random.uniform(50.0, 200.0), 2),
                    count=random.randint(5000, 20000),
                    description=f"{name}的养殖池，位于车间A-{i}区"
                )
                db.session.add(pond)
                db.session.flush()
                ponds.append(pond)
                print(f"  ✓ 创建养殖池: {name}")
        
        db.session.commit()
        
        # 4. 创建批次
        print("\n[4/9] 创建批次...")
        batches = []
        # 只创建2个批次
        for j in range(1, 3):
            batch_id = f"BATCH_2024_{j:02d}"
            existing = db.session.query(Batch).filter_by(batch_id=batch_id).first()
            if existing:
                batches.append(existing)
                print(f"  ✓ 批次已存在: {batch_id}")
            else:
                # 批次1关联到1号池，批次2关联到4号池
                if j == 1:
                    pond = ponds[0]  # 1号池
                else:
                    pond = ponds[3]  # 4号池
                start_date = datetime.now().date() - timedelta(days=random.randint(30, 180))
                end_date = None if random.random() > 0.3 else (start_date + timedelta(days=random.randint(60, 120)))
                
                # 创建对象，只传递可以在构造函数中使用的字段
                batch = Batch(
                    batch_id=batch_id,
                    pond_id=pond.id,
                    start_date=start_date
                )
                # 设置其他字段（这些字段设置了 init=False）
                batch.species = "Litopenaeus vannamei"
                batch.end_date = end_date
                batch.location = f"车间A-{j}区"
                batch.seed_origin = "育苗场A"
                batch.stocking_density = Decimal(str(round(random.uniform(50.0, 150.0), 2)))
                
                db.session.add(batch)
                db.session.flush()
                batches.append(batch)
                print(f"  ✓ 创建批次: {batch_id}")
        
        db.session.commit()
        
        # 5. 创建设备（传感器、喂食机、摄像头）
        print("\n[5/9] 创建设备...")
        sensor_devices = []
        feeder_devices = []
        camera_devices = []
        
        device_counter = 1
        
        # 只创建5个传感器设备（指定类型），全部放在4号池
        pond_4 = ponds[3]  # 4号池（索引为3）
        for metric in SENSOR_DEVICE_METRICS:
            sensor_type = sensor_type_map.get(metric)
            if not sensor_type:
                continue
            # 使用中文名称作为设备名称
            device_name = SENSOR_DEVICE_NAMES.get(metric, f"{sensor_type.type_name}传感器")
            device_id = f"sensor_{device_counter:04d}"
            existing = db.session.query(Device).filter_by(device_id=device_id).first()
            if existing:
                if existing.device_type.category == "sensor":
                    sensor_devices.append(existing)
            else:
                device = Device(
                    device_id=device_id,
                    name=f"{device_name}-{pond_4.name}",
                    ownership="养殖场",
                    device_type_id=device_type_map["sensor"].id,
                    sensor_type_id=sensor_type.id,
                    pond_id=pond_4.id,
                    model=f"Model-{sensor_type.metric.upper()}",
                    manufacturer="传感器制造公司",
                    serial_number=f"SN-{device_counter:06d}",
                    location=f"{pond_4.name}-{device_name}",
                    status="online",
                    control_mode="hybrid",
                    connection_info=generate_connection_info(device_counter),
                    device_specific_config=generate_device_specific_config("sensor", device_counter)
                )
                db.session.add(device)
                db.session.flush()
                sensor_devices.append(device)
                device_counter += 1
        
        # 只创建2个喂食机，group_id分别为AI和AI2
        feeder_group_ids = ["AI", "AI2"]
        feeder_connection_info = {
            "url": "https://ffish.huaeran.cn:8081/commonRequest",
            "password": "123456789",
            "username": "8619034657726"
        }
        for i, group_id in enumerate(feeder_group_ids, 1):
            device_id = f"feeder_{device_counter:04d}"
            existing = db.session.query(Device).filter_by(device_id=device_id).first()
            if existing:
                if existing.device_type.category == "feeder":
                    feeder_devices.append(existing)
            else:
                # 关联到4号池
                pond = ponds[3]
                
                # 生成喂食机专属配置，覆盖group_id
                feeder_config = {
                    "feed_count": 1,  # 默认1份
                    "timezone": 9,
                    "network_type": random.choice([0, 1]),
                    "group_id": group_id,  # 使用指定的group_id
                    "feed_portion_weight": 17.0,  # 每份17克
                    "capacity_kg": round(random.uniform(50.0, 200.0), 1),
                    "feed_type": random.choice(["虾料A型", "虾料B型", "虾料C型", "通用饲料"])
                }
                
                device = Device(
                    device_id=device_id,
                    name=f"自动喂食机-{pond.name}-{i}号",
                    ownership="养殖场",
                    device_type_id=device_type_map["feeder"].id,
                    sensor_type_id=None,
                    pond_id=pond.id,
                    model="AutoFeeder-Pro",
                    manufacturer="喂食机制造公司",
                    serial_number=f"SN-FEED-{device_counter:06d}",
                    location=f"{pond.name}-喂食区{i}",
                    status="online" if random.random() > 0.1 else "offline",
                    control_mode="hybrid",
                    connection_info=feeder_connection_info,
                    device_specific_config=feeder_config
                )
                db.session.add(device)
                db.session.flush()
                feeder_devices.append(device)
                device_counter += 1
        
        # 只为4号池创建摄像头（1-2个）
        for pond in [ponds[3]]:
            for i in range(1, random.randint(2, 3)):
                device_id = f"camera_{device_counter:04d}"
                existing = db.session.query(Device).filter_by(device_id=device_id).first()
                if existing:
                    if existing.device_type.category == "camera":
                        camera_devices.append(existing)
                else:
                    device = Device(
                        device_id=device_id,
                        name=f"监控摄像头-{pond.name}-{i}号",
                        ownership="养殖场",
                        device_type_id=device_type_map["camera"].id,
                        sensor_type_id=None,
                        pond_id=pond.id,
                        model="Camera-HD-1080P",
                        manufacturer="摄像头制造公司",
                        serial_number=f"SN-CAM-{device_counter:06d}",
                        location=f"{pond.name}-监控点{i}",
                        status="online" if random.random() > 0.1 else "offline",
                        control_mode="hybrid",
                        connection_info=generate_connection_info(device_counter),
                        device_specific_config=generate_device_specific_config("camera", device_counter)
                    )
                    db.session.add(device)
                    db.session.flush()
                    camera_devices.append(device)
                    device_counter += 1
        
        # 只为4号池创建其他设备类型（循环水泵、鼓风机、水龙头开关、太阳能加热器循环泵）
        # 确保每个设备类型都至少创建一个设备
        other_devices = []
        other_device_categories = ["water_pump", "air_blower", "water_switch", "solar_heater_pump"]
        
        for pond in [ponds[3]]:
            for category in other_device_categories:
                if category in device_type_map:
                    # 每个池每种类型创建1个设备（确保每个类型都有）
                    device_id = f"{category}_{device_counter:04d}"
                    existing = db.session.query(Device).filter_by(device_id=device_id).first()
                    if existing:
                        if existing.device_type.category == category:
                            other_devices.append(existing)
                    else:
                        device_names = {
                            "water_pump": "循环水泵",
                            "air_blower": "鼓风机",
                            "water_switch": "水龙头开关",
                            "solar_heater_pump": "太阳能加热器循环泵"
                        }
                        device_models = {
                            "water_pump": "WaterPump-2000",
                            "air_blower": "AirBlower-1500",
                            "water_switch": "WaterSwitch-Pro",
                            "solar_heater_pump": "SolarPump-3000"
                        }
                        device_manufacturers = {
                            "water_pump": "水泵制造公司",
                            "air_blower": "鼓风机制造公司",
                            "water_switch": "开关制造公司",
                            "solar_heater_pump": "太阳能设备公司"
                        }
                        
                        device = Device(
                            device_id=device_id,
                            name=f"{device_names[category]}-{pond.name}",
                            ownership="养殖场",
                            device_type_id=device_type_map[category].id,
                            sensor_type_id=None,
                            pond_id=pond.id,
                            model=device_models[category],
                            manufacturer=device_manufacturers[category],
                            serial_number=f"SN-{category.upper()}-{device_counter:06d}",
                            location=f"{pond.name}-{device_names[category]}",
                            status="online" if random.random() > 0.1 else "offline",
                            control_mode="hybrid",
                            connection_info=generate_connection_info(device_counter),
                            device_specific_config=generate_device_specific_config(category, device_counter)
                        )
                        db.session.add(device)
                        db.session.flush()
                        other_devices.append(device)
                        device_counter += 1
        
        db.session.commit()
        print(f"  ✓ 创建传感器设备: {len(sensor_devices)} 个")
        print(f"  ✓ 创建喂食机设备: {len(feeder_devices)} 个")
        print(f"  ✓ 创建摄像头设备: {len(camera_devices)} 个")
        print(f"  ✓ 创建其他设备: {len(other_devices)} 个")
        
        # 6. 生成传感器读数（最近30天，每小时1条）
        print("\n[6/9] 生成传感器读数...")
        reading_count = 0
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        for device in sensor_devices:
            if device.sensor_type is None:
                continue
            
            metric = device.sensor_type.metric
            current_time = start_time
            
            # 为每个设备生成最近30天的数据，每小时1条
            while current_time <= end_time:
                # 随机跳过一些时间点，模拟真实采集
                if random.random() > 0.05:  # 95%的数据点
                    value = generate_sensor_value(metric, current_time)
                    
                    # 随机选择一个批次
                    batch = random.choice(batches) if batches else None
                    
                    # 创建对象，只传递可以在构造函数中使用的字段
                    reading = SensorReading(
                        device_id=device.id,
                        pond_id=device.pond_id,
                        value=value
                    )
                    # 设置其他字段（这些字段设置了 init=False）
                    reading.batch_id = batch.id if batch else None
                    reading.unit = device.sensor_type.unit
                    reading.metric = metric
                    reading.recorded_at = current_time
                    reading.ts_utc = current_time
                    reading.ts_local = current_time.astimezone(timezone(timedelta(hours=9)))  # 日本时区
                    reading.quality_flag = "ok" if random.random() > 0.05 else random.choice(["missing", "anomaly"])
                    
                    db.session.add(reading)
                    reading_count += 1
                    
                    # 每1000条提交一次
                    if reading_count % 1000 == 0:
                        db.session.commit()
                        print(f"  ✓ 已生成 {reading_count} 条传感器读数...")
                
                current_time += timedelta(hours=1)
        
        db.session.commit()
        print(f"  ✓ 传感器读数生成完成，共 {reading_count} 条")
        
        # 7. 生成喂食机记录（最近30天，每天2-4次）
        print("\n[7/9] 生成喂食机记录...")
        feeder_log_count = 0
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        for device in feeder_devices:
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                # 每天2-4次投喂
                feed_times = random.randint(2, 4)
                feed_hours = sorted(random.sample(range(6, 20), feed_times))
                
                for hour in feed_hours:
                    feed_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                    feed_time = feed_time.replace(tzinfo=timezone.utc)
                    
                    # 随机选择一个批次
                    batch = random.choice(batches) if batches else None
                    
                    feed_amount = round(random.uniform(100.0, 500.0), 3)  # 克
                    run_time = random.randint(30, 120)  # 秒
                    leftover = round(random.uniform(500.0, 2000.0), 3)  # 克
                    
                    # 创建对象，只传递可以在构造函数中使用的字段
                    log = FeederLog(
                        device_id=device.id,
                        pond_id=device.pond_id,
                        ts_utc=feed_time,
                        status="ok" if random.random() > 0.05 else random.choice(["warning", "error"])
                    )
                    # 设置其他字段（这些字段设置了 init=False）
                    log.batch_id = batch.id if batch else None
                    log.ts_local = feed_time.astimezone(timezone(timedelta(hours=9)))
                    log.feed_amount_g = Decimal(str(feed_amount))
                    log.run_time_s = run_time
                    log.leftover_estimate_g = Decimal(str(leftover))
                    
                    db.session.add(log)
                    feeder_log_count += 1
                
                current_date += timedelta(days=1)
        
        db.session.commit()
        print(f"  ✓ 喂食机记录生成完成，共 {feeder_log_count} 条")
        
        # 8. 生成摄像头图片和健康检查（最近30天）
        print("\n[8/9] 生成摄像头数据...")
        image_count = 0
        health_count = 0
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        for device in camera_devices:
            # 生成图片（每天10-20张）
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                image_times = random.randint(10, 20)
                for _ in range(image_times):
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    img_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    img_time = img_time.replace(tzinfo=timezone.utc)
                    
                    # 随机选择一个批次
                    batch = random.choice(batches) if batches else None
                    
                    # 创建对象，只传递可以在构造函数中使用的字段
                    image = CameraImage(
                        device_id=device.id,
                        pond_id=device.pond_id,
                        image_url=f"https://storage.example.com/images/{device.device_id}/{img_time.strftime('%Y%m%d_%H%M%S')}.jpg",
                        ts_utc=img_time,
                        timestamp_str=img_time.strftime("%Y-%m-%d %H:%M:%S"),
                        width=1920,
                        height=1080,
                        format="jpg",
                        size=random.randint(500000, 2000000)
                    )
                    # 设置其他字段（这些字段设置了 init=False）
                    image.batch_id = batch.id if batch else None
                    image.storage_uri = f"images/{device.device_id}/{img_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                    image.ts_local = img_time.astimezone(timezone(timedelta(hours=9)))
                    image.quality_flag = "ok" if random.random() > 0.05 else "anomaly"
                    
                    db.session.add(image)
                    image_count += 1
                
                # 每天生成1次健康检查
                health_time = datetime.combine(current_date, datetime.min.time().replace(hour=12))
                health_time = health_time.replace(tzinfo=timezone.utc)
                health_timestamp = int(health_time.timestamp() * 1000)
                
                overall_score = round(random.uniform(70.0, 100.0), 2)
                connectivity_score = random.randint(80, 100)
                image_quality_score = random.randint(75, 100)
                hardware_score = random.randint(70, 100)
                storage_score = random.randint(80, 100)
                
                status_map = {
                    (90, 100): "优秀",
                    (80, 89): "良好",
                    (70, 79): "一般",
                    (60, 69): "需要维护",
                    (0, 59): "离线"
                }
                
                def get_status(score):
                    for (low, high), status in status_map.items():
                        if low <= score <= high:
                            return status
                    return "一般"
                
                # 创建对象，只传递可以在构造函数中使用的字段
                health = CameraHealth(
                    device_id=device.id,
                    pond_id=device.pond_id,
                    health_status=get_status(overall_score),
                    overall_score=Decimal(str(overall_score)),
                    connectivity_status=get_status(connectivity_score),
                    connectivity_score=connectivity_score,
                    connectivity_message="连接正常" if connectivity_score >= 90 else "连接不稳定",
                    image_quality_status=get_status(image_quality_score),
                    image_quality_score=image_quality_score,
                    image_quality_message="图像清晰" if image_quality_score >= 90 else "图像质量一般",
                    hardware_status=get_status(hardware_score),
                    hardware_score=hardware_score,
                    hardware_message="硬件正常" if hardware_score >= 90 else "硬件需要检查",
                    storage_status=get_status(storage_score),
                    storage_score=storage_score,
                    storage_message="存储空间充足" if storage_score >= 90 else "存储空间紧张",
                    timestamp=health_timestamp,
                    last_check=health_time.strftime("%Y-%m-%d %H:%M:%S")
                )
                # 设置其他字段（这些字段设置了 init=False）
                health.temperature = Decimal(str(round(random.uniform(20.0, 35.0), 2)))
                health.uptime_hours = random.randint(100, 5000)
                
                db.session.add(health)
                health_count += 1
                
                current_date += timedelta(days=1)
        
        db.session.commit()
        print(f"  ✓ 摄像头图片生成完成，共 {image_count} 条")
        print(f"  ✓ 摄像头健康检查生成完成，共 {health_count} 条")
        
        # 9. 生成预警规则和预警记录
        print("\n[9/9] 生成预警规则和预警记录...")
        alert_rules = []
        alert_notifications_list = []
        
        # 预警规则配置（为传感器设备创建预警规则）
        alert_rules_config = [
            {
                "metric": "do",
                "severity_level": "critical",
                "trigger_condition": "below",
                "threshold": "5.0",
                "check_interval": 5,
                "check_interval_unit": "minute",
                "description": "溶解氧浓度过低预警"
            },
            {
                "metric": "temperature",
                "severity_level": "warning",
                "trigger_condition": "above",
                "threshold": "32.0",
                "check_interval": 10,
                "check_interval_unit": "minute",
                "description": "温度过高预警"
            },
            {
                "metric": "PH",
                "severity_level": "warning",
                "trigger_condition": "below",
                "threshold": "7.0",
                "check_interval": 15,
                "check_interval_unit": "minute",
                "description": "pH值过低预警"
            }
        ]
        
        rule_counter = 1
        for rule_config in alert_rules_config:
            # 找到对应 metric 的传感器设备
            target_device = None
            for device in sensor_devices:
                if device.sensor_type and device.sensor_type.metric == rule_config["metric"]:
                    target_device = device
                    break
            
            if not target_device:
                print(f"  ⚠ 未找到 {rule_config['metric']} 类型的传感器设备，跳过创建规则")
                continue
            
            rule_id = f"AT-{rule_counter:03d}"
            existing = db.session.query(AlertRule).filter_by(rule_id=rule_id).first()
            
            if existing:
                alert_rules.append(existing)
                print(f"  ✓ 预警规则已存在: {rule_id}")
            else:
                # 创建预警规则
                rule = AlertRule(
                    device_id=target_device.id,
                    rule_id=rule_id,
                    metric=rule_config["metric"],
                    severity_level=rule_config["severity_level"],
                    trigger_condition=rule_config["trigger_condition"],
                    threshold=rule_config["threshold"]
                )
                # 设置检测间隔（init=False 的字段）
                rule.check_interval = rule_config["check_interval"]
                rule.check_interval_unit = rule_config["check_interval_unit"]
                rule.is_enabled = True
                
                db.session.add(rule)
                db.session.flush()
                alert_rules.append(rule)
                print(f"  ✓ 创建预警规则: {rule_id} - {rule_config['description']}")
            
            rule_counter += 1
        
        db.session.commit()
        
        # 为每个预警规则生成2-3条预警记录
        notification_counter = 1
        for rule in alert_rules:
            # 每个规则生成2-3条预警记录
            notification_count_per_rule = random.randint(2, 3)
            
            # 获取关联设备
            device = db.session.query(Device).filter_by(id=rule.device_id).first()
            device_name = device.name if device else "未知设备"
            
            for i in range(notification_count_per_rule):
                notification_id = f"REC-{notification_counter:03d}"
                existing = db.session.query(AlertNotification).filter_by(notification_id=notification_id).first()
                
                if existing:
                    alert_notifications_list.append(existing)
                else:
                    # 生成随机触发时间（最近7天内）
                    triggered_time = datetime.now(timezone.utc) - timedelta(
                        days=random.randint(0, 7),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    # 根据规则生成预警内容和当前值
                    if rule.metric == "do":
                        current_val = round(random.uniform(3.5, 4.9), 2)
                        content = f"溶解氧浓度低于阈值{rule.threshold}mg/L，当前值: {current_val}mg/L"
                    elif rule.metric == "temperature":
                        current_val = round(random.uniform(32.1, 35.0), 2)
                        content = f"温度高于阈值{rule.threshold}°C，当前值: {current_val}°C"
                    elif rule.metric == "PH":
                        current_val = round(random.uniform(6.0, 6.9), 2)
                        content = f"pH值低于阈值{rule.threshold}，当前值: {current_val}"
                    else:
                        current_val = round(random.uniform(0, 100), 2)
                        content = f"{rule.metric}异常，当前值: {current_val}"
                    
                    # 创建预警记录
                    notification = AlertNotification(
                        notification_id=notification_id,
                        alert_rule_id=rule.id,
                        device_id=rule.device_id,
                        content=content,
                        triggered_at=triggered_time
                    )
                    # 设置其他字段（init=False 的字段）
                    notification.current_value = str(current_val)
                    
                    # 随机设置状态（70%待处理，30%已解决）
                    if random.random() > 0.7:
                        notification.status = "resolved"
                        notification.resolved_at = triggered_time + timedelta(hours=random.randint(1, 24))
                    else:
                        notification.status = "pending"
                    
                    db.session.add(notification)
                    alert_notifications_list.append(notification)
                
                notification_counter += 1
        
        db.session.commit()
        print(f"  ✓ 预警规则生成完成，共 {len(alert_rules)} 条")
        print(f"  ✓ 预警记录生成完成，共 {len(alert_notifications_list)} 条")
        
        print("\n" + "=" * 60)
        print("Mock数据生成完成！")
        print("=" * 60)
        print(f"统计信息：")
        print(f"  - 养殖池: {len(ponds)} 个")
        print(f"  - 批次: {len(batches)} 个")
        print(f"  - 传感器设备: {len(sensor_devices)} 个")
        print(f"  - 喂食机设备: {len(feeder_devices)} 个")
        print(f"  - 摄像头设备: {len(camera_devices)} 个")
        print(f"  - 其他设备: {len(other_devices)} 个")
        print(f"  - 传感器读数: {reading_count} 条")
        print(f"  - 喂食机记录: {feeder_log_count} 条")
        print(f"  - 摄像头图片: {image_count} 条")
        print(f"  - 健康检查: {health_count} 条")
        print(f"  - 预警规则: {len(alert_rules)} 条")
        print(f"  - 预警记录: {len(alert_notifications_list)} 条")
        print("=" * 60)


if __name__ == "__main__":
    try:
        generate_mock_data()
    except Exception as e:
        print(f"❌ 生成Mock数据失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

