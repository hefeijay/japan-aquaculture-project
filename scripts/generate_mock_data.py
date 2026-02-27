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
import csv
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
from config.settings import Config
from db_models import (
    db, Pond, Batch, DeviceType, SensorType, Device, 
    SensorReading, FeederLog, CameraImage, User,
    AlertRule, AIDecision, Prompt
)


def get_local_timezone():
    """获取本地时区（从配置中读取）"""
    return timezone(timedelta(hours=Config.LOCAL_TIMEZONE_OFFSET))


def _parse_datetime(s: str, default_tz=timezone.utc):
    """解析 CSV 中的时间字符串，支持多种格式，返回 timezone-aware datetime"""
    if not s or not str(s).strip():
        return datetime.now(default_tz)
    s = str(s).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s[:26], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=default_tz)
            return dt
        except (ValueError, TypeError):
            continue
    return datetime.now(default_tz)


# ==================== 可配置参数 ====================
# 每个传感器设备生成的读数条数（仅在没有 CSV 时使用）
SENSOR_READINGS_PER_DEVICE = 5
# 喂食机/摄像头/传感器数据：若存在 CSV 则从 scripts/db_datas 导入，否则生成 mock
DB_DATAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_datas")
FEEDERS_LOGS_CSV = os.path.join(DB_DATAS_DIR, "feeders_logs.csv")
CAMERA_IMAGES_CSV = os.path.join(DB_DATAS_DIR, "camera_images.csv")
SENSOR_READINGS_CSV = os.path.join(DB_DATAS_DIR, "sensor_readings.csv")
AI_DECISIONS_CSV = os.path.join(DB_DATAS_DIR, "ai_decisions.csv")
PROMPTS_CSV = os.path.join(DB_DATAS_DIR, "prompts.csv")

# CSV 导入开关：控制是否从 CSV 导入数据（True=导入CSV，False=生成mock数据）
ENABLE_CSV_IMPORT = {
    "sensor_readings": True,    # 传感器读数
    "feeders_logs": True,        # 喂食机记录
    "camera_images": False,      # 摄像头图片（已禁用，不导入CSV也不生成mock）
    "ai_decisions": True,        # AI决策
    "prompts": True,             # Prompts
}

# 数据生成开关：控制是否需要该类型的数据（True=需要，False=完全跳过）
ENABLE_DATA_GENERATION = {
    "sensor_readings": True,     # 传感器读数
    "feeders_logs": True,         # 喂食机记录
    "camera_images": False,       # 摄像头图片（完全不需要）
    "ai_decisions": True,         # AI决策
    "prompts": True,              # Prompts
}
# ====================================================

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
        # 摄像头配置：固定 1920x1080，notes 为空
        return {
            "quality": "高",
            "resolution": "1920x1080",
            "notes": ""
        }
    
    elif category == "water_pump":
        # 循环水泵：3.5吨/小时 ≈ 58.33 L/min，50w = 0.05 kW，24小时运行
        return {
            "flow_rate": 58.33,  # 3.5吨/小时（L/min）
            "power": 0.05,       # 50W（kW）
            "notes": "24小时运行"
        }
    
    elif category == "air_blower":
        # 鼓风机：100L/min，100w = 0.1 kW，24小时运行
        return {
            "air_flow": 100.0,   # 气量（L/min）
            "power": 0.1,        # 100W（kW）
            "notes": "24小时运行"
        }
    
    elif category == "water_switch":
        # 水龙头开关：电磁阀控制，液位传感器低于980mm开启，达到1000mm停止
        return {
            "notes": "电磁阀控制，液位传感器低于980mm开启，达到1000mm停止"
        }
    
    elif category == "solar_heater_pump":
        # 太阳能加热器循环泵：1吨/小时 ≈ 16.67 L/min，20w = 0.02 kW，需要手动开启关闭
        return {
            "flow_rate": 16.67,  # 1吨/小时（L/min）
            "power": 0.02,       # 20W（kW）
            "notes": "需要手动开启关闭"
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
            {"username": "fish", "user_id": "USER_FISH", "role": "user"},
            {"username": "henry", "user_id": "USER_HENRY", "role": "user"} 
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
        
        # 3. 创建养殖池（五个：1号池～5号池，日本茨城县筑波市，面积 20/20/7/7/7 平方米）
        print("\n[3/9] 创建养殖池...")
        ponds = []
        pond_names = ["1号池", "2号池", "3号池", "4号池", "5号池"]
        pond_areas = [20.0, 20.0, 7.0, 7.0, 7.0]  # 平方米
        location_tsukuba = "日本茨城县筑波市"
        for i, name in enumerate(pond_names, 1):
            existing = db.session.query(Pond).filter_by(pond_id=f"POND_{i:03d}").first()
            if existing:
                ponds.append(existing)
                print(f"  ✓ 养殖池已存在: {name}")
            else:
                pond = Pond(
                    pond_id=f"POND_{i:03d}",
                    name=name,
                    location=location_tsukuba,
                    area=pond_areas[i - 1],
                    count=random.randint(5000, 20000),
                    description=f"{name}的养殖池，位于{location_tsukuba}"
                )
                db.session.add(pond)
                db.session.flush()
                ponds.append(pond)
                print(f"  ✓ 创建养殖池: {name}")
        
        db.session.commit()
        
        # 4. 创建批次（两个批次均在四号池，物种/来源/放养密度一致）
        print("\n[4/9] 创建批次...")
        batches = []
        pond_4 = ponds[3]  # 四号池
        batch_configs = [
            {
                "batch_id": "BATCH_2024_01",
                "start_date": datetime(2024, 3, 1).date(),
                "end_date": datetime(2025, 9, 12).date(),
            },
            {
                "batch_id": "BATCH_2025_02",
                "start_date": datetime(2025, 9, 12).date(),
                "end_date": None,
            },
        ]
        species = "Litopenaeus vannamei"
        batch_location = "四号池"
        seed_origin = "日本"
        stocking_density = Decimal("500")
        for cfg in batch_configs:
            existing = db.session.query(Batch).filter_by(batch_id=cfg["batch_id"]).first()
            if existing:
                batches.append(existing)
                print(f"  ✓ 批次已存在: {cfg['batch_id']}")
            else:
                batch = Batch(
                    batch_id=cfg["batch_id"],
                    pond_id=pond_4.id,
                    start_date=cfg["start_date"]
                )
                batch.species = species
                batch.end_date = cfg["end_date"]
                batch.location = batch_location
                batch.seed_origin = seed_origin
                batch.stocking_density = stocking_density
                db.session.add(batch)
                db.session.flush()
                batches.append(batch)
                print(f"  ✓ 创建批次: {cfg['batch_id']}")
        
        db.session.commit()
        
        # 5. 创建设备（传感器、喂食机、摄像头）
        print("\n[5/9] 创建设备...")
        sensor_devices = []
        feeder_devices = []
        camera_devices = []
        
        device_counter = 1
        
        # 只创建5个传感器设备（device_id 1～5），全部放在4号池；描述=水质探头，归属=日本养殖基地，制造商=普瑞森社中国山东
        pond_4 = ponds[3]  # 4号池（索引为3）
        sensor_ownership = "日本养殖基地"
        sensor_manufacturer = "普瑞森社中国山东"
        sensor_description = "水质探头"
        for metric in SENSOR_DEVICE_METRICS:
            sensor_type = sensor_type_map.get(metric)
            if not sensor_type:
                continue
            device_name = SENSOR_DEVICE_NAMES.get(metric, f"{sensor_type.type_name}传感器")
            # 液位传感器安装位置为池底，其余为水池液面以下
            sensor_location = "池底" if metric == "water_level" else "水池液面以下"
            device_id = f"sensor_{device_counter:04d}"
            existing = db.session.query(Device).filter_by(device_id=device_id).first()
            if existing:
                if existing.device_type.category == "sensor":
                    sensor_devices.append(existing)
            else:
                device = Device(
                    device_id=device_id,
                    name=f"{device_name}-{pond_4.name}",
                    ownership=sensor_ownership,
                    device_type_id=device_type_map["sensor"].id,
                    sensor_type_id=sensor_type.id,
                    pond_id=pond_4.id,
                    model=f"Model-{sensor_type.metric.upper()}",
                    manufacturer=sensor_manufacturer,
                    serial_number=f"SN-{device_counter:06d}",
                    location=sensor_location,
                    description=sensor_description,
                    status="online",
                    control_mode="hybrid",
                    connection_info=generate_connection_info(device_counter),
                    device_specific_config=generate_device_specific_config("sensor", device_counter)
                )
                db.session.add(device)
                db.session.flush()
                sensor_devices.append(device)
                device_counter += 1
        
        # 摄像头2个：device_id 6→摄像头2（水下），7→摄像头3（距水面约41cm）；描述与归属一致，关联4号池
        camera_description = (
            "具备 IP66 防水性能，能够在长期高湿、高盐（或高有机负荷）环境下稳定运行。"
            "镜头选用 2.8 mm 定焦广角镜头，视角约为 120°，成像无明显畸变。"
        )
        camera_locations = [
            "水下",
            "距离水面约 41 cm，视角向下，采用水平固定方式进行布设，以减少视角变化对图像分析结果的影响。",
        ]
        camera_names = ["摄像头2", "摄像头3"]
        for i, cam_name in enumerate(camera_names):
            device_counter = 6 + i
            device_id = f"camera_{device_counter:04d}"
            existing = db.session.query(Device).filter_by(device_id=device_id).first()
            if existing:
                if existing.device_type.category == "camera":
                    camera_devices.append(existing)
            else:
                device = Device(
                    device_id=device_id,
                    name=cam_name,
                    ownership="日本养殖基地",
                    device_type_id=device_type_map["camera"].id,
                    sensor_type_id=None,
                    pond_id=pond_4.id,
                    model="Camera-HD-1080P",
                    manufacturer="摄像头制造公司",
                    serial_number=f"SN-CAM-{device_counter:06d}",
                    location=camera_locations[i],
                    description=camera_description,
                    status="offline" if i == 0 else "online",  # 摄像头2 设为非在线
                    control_mode="hybrid",
                    connection_info=generate_connection_info(device_counter),
                    device_specific_config=generate_device_specific_config("camera", device_counter)
                )
                db.session.add(device)
                db.session.flush()
                camera_devices.append(device)
        device_counter = 8  # 喂食机从 8 开始
        
        # 喂食机2个：device_id 8→喂食机AI（group_id AI），9→AI2（group_id AI2）；归属/型号/制造商/location/配置一致
        feeder_names = ["喂食机AI", "喂食机AI2"]
        feeder_group_ids = ["AI", "AI2"]
        feeder_connection_info = {
            "url": "https://ffish.huaeran.cn:8081/commonRequest",
            "password": "123456789",
            "username": "8619034657726"
        }
        # 两台喂食机共用：描述、归属、型号、制造商、location、device_specific_config
        feeder_common = {
            "description": "自动喂食机",
            "ownership": "日本养殖基地",
            "model": "EV800W",
            "manufacturer": "依华莱斯（EVNICE）",
            "location": "水池上方",
        }
        feeder_config_common = {
            "feed_count": 1,
            "timezone": 9,
            "network_type": 0,
            "feed_portion_weight": 17.0,
            "capacity_kg": 5,
            "feed_type": "颗粒",
        }
        for i, group_id in enumerate(feeder_group_ids):
            device_id = f"feeder_{device_counter:04d}"
            existing = db.session.query(Device).filter_by(device_id=device_id).first()
            if existing:
                if existing.device_type.category == "feeder":
                    feeder_devices.append(existing)
            else:
                feeder_config = {**feeder_config_common, "group_id": group_id}
                device = Device(
                    device_id=device_id,
                    name=feeder_names[i],
                    ownership=feeder_common["ownership"],
                    device_type_id=device_type_map["feeder"].id,
                    sensor_type_id=None,
                    pond_id=pond_4.id,
                    model=feeder_common["model"],
                    manufacturer=feeder_common["manufacturer"],
                    serial_number=f"SN-FEED-{device_counter:06d}",
                    location=feeder_common["location"],
                    description=feeder_common["description"],
                    status="online",
                    control_mode="hybrid",
                    connection_info=feeder_connection_info,
                    device_specific_config=feeder_config
                )
                db.session.add(device)
                db.session.flush()
                feeder_devices.append(device)
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
                            ownership="日本养殖基地",
                            device_type_id=device_type_map[category].id,
                            sensor_type_id=None,
                            pond_id=pond.id,
                            model=device_models[category],
                            manufacturer=device_manufacturers[category],
                            serial_number=f"SN-{category.upper()}-{device_counter:06d}",
                            location=f"{pond.name}-{device_names[category]}",
                            status="online",
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
        
        # 构建 CSV 导入用映射：device_id 字符串 -> devices.id；batch_id/pond_id 数字 -> 主键
        device_id_str_to_pk = {}
        for d in sensor_devices + feeder_devices + camera_devices:
            device_id_str_to_pk[d.device_id] = d.id
        batch_id_map = {}
        for idx, b in enumerate(batches, 1):
            batch_id_map[idx] = b.id
        pond_id_map = {4: pond_4.id}
        # 传感器按 (pond_id, metric) 解析，因 CSV 中 device_id 可能为源库主键
        sensor_metric_pond_to_device = {}
        for d in sensor_devices:
            if d.sensor_type and d.pond_id:
                sensor_metric_pond_to_device[(d.pond_id, d.sensor_type.metric)] = d.id
        
        # 6. 传感器读数：有 CSV 则从 scripts/db_datas/sensor_readings.csv 导入，否则生成
        reading_count = 0
        if ENABLE_CSV_IMPORT.get("sensor_readings", True) and os.path.exists(SENSOR_READINGS_CSV):
            print(f"\n[6/9] 从 CSV 导入传感器读数: {SENSOR_READINGS_CSV}")
            with open(SENSOR_READINGS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        pond_pk = pond_id_map.get(int(row["pond_id"])) if row.get("pond_id") else None
                        if not pond_pk:
                            continue
                        metric = (row.get("metric") or "").strip()
                        device_pk = sensor_metric_pond_to_device.get((pond_pk, metric))
                        if not device_pk:
                            csv_did = row.get("device_id")
                            if csv_did:
                                try:
                                    n = int(csv_did)
                                    device_pk = device_id_str_to_pk.get(f"sensor_{n:04d}")
                                except (ValueError, TypeError):
                                    pass
                        if not device_pk:
                            continue
                        batch_pk = None
                        if row.get("batch_id"):
                            try:
                                batch_pk = batch_id_map.get(int(row["batch_id"]))
                            except (ValueError, TypeError):
                                pass
                        ts_utc = _parse_datetime(row.get("ts_utc") or row.get("recorded_at"))
                        value = float(row["value"]) if row.get("value") else 0.0
                        reading = SensorReading(
                            device_id=device_pk,
                            pond_id=pond_pk,
                            value=value
                        )
                        reading.batch_id = batch_pk
                        reading.unit = (row.get("unit") or "").strip() or None
                        reading.metric = metric or None
                        reading.recorded_at = ts_utc
                        reading.ts_utc = ts_utc
                        reading.ts_local = ts_utc.astimezone(get_local_timezone())
                        reading.quality_flag = (row.get("quality_flag") or "ok").strip() or "ok"
                        if row.get("description"):
                            reading.description = row["description"].strip()
                        if row.get("checksum"):
                            reading.checksum = row["checksum"].strip()
                        db.session.add(reading)
                        reading_count += 1
                        if reading_count % 5000 == 0:
                            db.session.flush()
                            print(f"  进度: {reading_count} 条...")
                    except Exception as e:
                        if reading_count < 3:
                            print(f"  ⚠ 跳过行: {e}")
            db.session.commit()
            print(f"  ✓ 传感器读数导入完成，共 {reading_count} 条")
        else:
            print(f"\n[6/9] 生成传感器读数（每设备 {SENSOR_READINGS_PER_DEVICE} 条）...")
            end_time = datetime.now(timezone.utc)
            for device in sensor_devices:
                if device.sensor_type is None:
                    continue
                metric = device.sensor_type.metric
                for i in range(SENSOR_READINGS_PER_DEVICE):
                    hours_ago = (SENSOR_READINGS_PER_DEVICE - 1 - i) * (24 / max(SENSOR_READINGS_PER_DEVICE, 1))
                    random_offset_minutes = random.randint(-30, 30)
                    current_time = end_time - timedelta(hours=hours_ago, minutes=random_offset_minutes)
                    value = generate_sensor_value(metric, current_time)
                    batch = random.choice(batches) if batches else None
                    reading = SensorReading(
                        device_id=device.id,
                        pond_id=device.pond_id,
                        value=value
                    )
                    reading.batch_id = batch.id if batch else None
                    reading.unit = device.sensor_type.unit
                    reading.metric = metric
                    reading.recorded_at = current_time
                    reading.ts_utc = current_time
                    reading.ts_local = current_time.astimezone(get_local_timezone())
                    reading.quality_flag = "ok" if random.random() > 0.05 else random.choice(["missing", "anomaly"])
                    db.session.add(reading)
                    reading_count += 1
            db.session.commit()
            print(f"  ✓ 传感器读数生成完成，共 {reading_count} 条")
        
        # 7. 喂食机记录：有 CSV 则从 scripts/db_datas/feeders_logs.csv 导入，否则生成
        feeder_log_count = 0
        if ENABLE_CSV_IMPORT.get("feeders_logs", True) and os.path.exists(FEEDERS_LOGS_CSV):
            print(f"\n[7/9] 从 CSV 导入喂食机记录: {FEEDERS_LOGS_CSV}")
            with open(FEEDERS_LOGS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        csv_did = row.get("device_id")
                        if not csv_did:
                            continue
                        device_pk = device_id_str_to_pk.get(f"feeder_{int(csv_did):04d}")
                        if not device_pk:
                            continue
                        pond_pk = pond_id_map.get(int(row["pond_id"])) if row.get("pond_id") else pond_4.id
                        batch_pk = None
                        if row.get("batch_id"):
                            try:
                                batch_pk = batch_id_map.get(int(row["batch_id"]))
                            except (ValueError, TypeError):
                                pass
                        ts_utc = _parse_datetime(row.get("ts_utc") or row.get("ts_local"))
                        log = FeederLog(
                            device_id=device_pk,
                            pond_id=pond_pk,
                            ts_utc=ts_utc,
                            status=(row.get("status") or "ok").strip() or "ok"
                        )
                        log.batch_id = batch_pk
                        log.ts_local = ts_utc.astimezone(get_local_timezone())
                        if row.get("feed_amount_g"):
                            try:
                                log.feed_amount_g = Decimal(str(row["feed_amount_g"]))
                            except Exception:
                                pass
                        if row.get("run_time_s"):
                            try:
                                log.run_time_s = int(row["run_time_s"])
                            except Exception:
                                pass
                        if row.get("leftover_estimate_g"):
                            try:
                                log.leftover_estimate_g = Decimal(str(row["leftover_estimate_g"]))
                            except Exception:
                                pass
                        if row.get("notes"):
                            log.notes = row["notes"].strip()
                        if row.get("checksum"):
                            log.checksum = row["checksum"].strip()
                        db.session.add(log)
                        feeder_log_count += 1
                        if feeder_log_count % 500 == 0:
                            db.session.flush()
                            print(f"  进度: {feeder_log_count} 条...")
                    except Exception as e:
                        if feeder_log_count < 3:
                            print(f"  ⚠ 跳过行: {e}")
            db.session.commit()
            print(f"  ✓ 喂食机记录导入完成，共 {feeder_log_count} 条")
        else:
            print("\n[7/9] 生成喂食机记录...")
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            for device in feeder_devices:
                current_date = start_time.date()
                end_date = end_time.date()
                while current_date <= end_date:
                    feed_times = random.randint(2, 4)
                    feed_hours = sorted(random.sample(range(6, 20), feed_times))
                    for hour in feed_hours:
                        feed_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                        feed_time = feed_time.replace(tzinfo=timezone.utc)
                        batch = random.choice(batches) if batches else None
                        feed_amount = round(random.uniform(100.0, 500.0), 3)
                        run_time = random.randint(30, 120)
                        leftover = round(random.uniform(500.0, 2000.0), 3)
                        log = FeederLog(
                            device_id=device.id,
                            pond_id=device.pond_id,
                            ts_utc=feed_time,
                            status="ok" if random.random() > 0.05 else random.choice(["warning", "error"])
                        )
                        log.batch_id = batch.id if batch else None
                        log.ts_local = feed_time.astimezone(get_local_timezone())
                        log.feed_amount_g = Decimal(str(feed_amount))
                        log.run_time_s = run_time
                        log.leftover_estimate_g = Decimal(str(leftover))
                        db.session.add(log)
                        feeder_log_count += 1
                    current_date += timedelta(days=1)
            db.session.commit()
            print(f"  ✓ 喂食机记录生成完成，共 {feeder_log_count} 条")
        
        # 8. 摄像头图片：有 CSV 则从 scripts/db_datas/camera_images.csv 导入；健康检查仍按需生成
        image_count = 0
        health_count = 0
        if not ENABLE_DATA_GENERATION.get("camera_images", True):
            print("\n[8/9] 跳过摄像头图片数据生成（已配置为不需要）")
        elif ENABLE_CSV_IMPORT.get("camera_images", True) and os.path.exists(CAMERA_IMAGES_CSV):
            print(f"\n[8/9] 从 CSV 导入摄像头图片: {CAMERA_IMAGES_CSV}")
            with open(CAMERA_IMAGES_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        csv_did = row.get("device_id")
                        if not csv_did:
                            continue
                        device_pk = device_id_str_to_pk.get(f"camera_{int(csv_did):04d}")
                        if not device_pk:
                            continue
                        pond_pk = pond_id_map.get(int(row["pond_id"])) if row.get("pond_id") else pond_4.id
                        batch_pk = None
                        if row.get("batch_id"):
                            try:
                                batch_pk = batch_id_map.get(int(row["batch_id"]))
                            except (ValueError, TypeError):
                                pass
                        ts_utc = _parse_datetime(row.get("ts_utc") or row.get("ts_local") or row.get("timestamp_str"))
                        image_url = (row.get("image_url") or "").strip()
                        if not image_url:
                            continue
                        try:
                            w = int(row.get("width") or 1920)
                        except (TypeError, ValueError):
                            w = 1920
                        try:
                            h = int(row.get("height") or 1080)
                        except (TypeError, ValueError):
                            h = 1080
                        image = CameraImage(
                            device_id=device_pk,
                            pond_id=pond_pk,
                            image_url=image_url,
                            ts_utc=ts_utc,
                            timestamp_str=(row.get("timestamp_str") or ts_utc.strftime("%Y-%m-%d %H:%M:%S")).strip(),
                            width=w,
                            height=h,
                            format=(row.get("format") or "jpg").strip() or "jpg",
                            size=int(row.get("size") or 0),
                            fps=int(row.get("fps") or 0)
                        )
                        image.batch_id = batch_pk
                        if row.get("storage_uri"):
                            image.storage_uri = row["storage_uri"].strip()
                        image.ts_local = ts_utc.astimezone(get_local_timezone())
                        image.quality_flag = (row.get("quality_flag") or "ok").strip() or "ok"
                        if row.get("checksum"):
                            image.checksum = row["checksum"].strip()
                        db.session.add(image)
                        image_count += 1
                        if image_count % 500 == 0:
                            db.session.flush()
                            print(f"  进度: {image_count} 条...")
                    except Exception as e:
                        if image_count < 3:
                            print(f"  ⚠ 跳过行: {e}")
            db.session.commit()
            print(f"  ✓ 摄像头图片导入完成，共 {image_count} 条")
        else:
            print("\n[8/9] 生成摄像头数据...")
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
                        batch = random.choice(batches) if batches else None
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
                        image.batch_id = batch.id if batch else None
                        image.storage_uri = f"images/{device.device_id}/{img_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.ts_local = img_time.astimezone(get_local_timezone())
                        image.quality_flag = "ok" if random.random() > 0.05 else "anomaly"
                        db.session.add(image)
                        image_count += 1
                    current_date += timedelta(days=1)
            db.session.commit()
            print(f"  ✓ 摄像头图片生成完成，共 {image_count} 条")
        
        # 9. 生成预警规则（不生成预警记录 mock 数据）
        print("\n[9/9] 生成预警规则...")
        alert_rules = []
        
        # 预警规则配置（为传感器设备创建预警规则）
        alert_rules_config = [
            {
                "metric": "do",
                "severity_level": "critical",
                "trigger_condition": "below",
                "threshold": "5.0",
                "check_interval": 10,
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
                "check_interval": 10,
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
                # 设置上次检查时间（模拟调度器已运行）
                last_check_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 30))
                rule.last_checked_at = last_check_time
                rule.last_checked_at_local = last_check_time.astimezone(get_local_timezone())
                
                db.session.add(rule)
                db.session.flush()
                alert_rules.append(rule)
                print(f"  ✓ 创建预警规则: {rule_id} - {rule_config['description']}")
            
            rule_counter += 1
        
        db.session.commit()
        print(f"  ✓ 预警规则生成完成，共 {len(alert_rules)} 条")
        
        # 10. 从 CSV 导入 AI 决策（ai_decisions.csv）
        ai_decision_count = 0
        if ENABLE_CSV_IMPORT.get("ai_decisions", True) and os.path.exists(AI_DECISIONS_CSV):
            print(f"\n[10/11] 从 CSV 导入 AI 决策: {AI_DECISIONS_CSV}")
            with open(AI_DECISIONS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        decision_id = (row.get("decision_id") or "").strip()
                        if not decision_id:
                            continue
                        if db.session.query(AIDecision).filter_by(decision_id=decision_id).first():
                            continue
                        msg_type = (row.get("type") or "analysis").strip()
                        message = (row.get("message") or "").strip()
                        if not message:
                            continue
                        action = (row.get("action") or "").strip() or None
                        source = (row.get("source") or "").strip() or None
                        source_id = (row.get("source_id") or "").strip() or None
                        expires_at = None
                        if row.get("expires_at"):
                            expires_at = _parse_datetime(row["expires_at"])
                        try:
                            priority = int(row.get("priority") or 0)
                        except (TypeError, ValueError):
                            priority = 0
                        try:
                            confidence = Decimal(str(row.get("confidence") or 0))
                        except Exception:
                            confidence = Decimal("0")
                        status = (row.get("status") or "active").strip() or "active"
                        if status not in ("active", "processed", "expired"):
                            status = "active"
                        rec = AIDecision(
                            decision_id=decision_id,
                            type=msg_type,
                            message=message,
                            action=action,
                            source=source,
                            source_id=source_id,
                            expires_at=expires_at,
                            priority=priority,
                            confidence=confidence,
                            status=status
                        )
                        db.session.add(rec)
                        ai_decision_count += 1
                        if ai_decision_count % 500 == 0:
                            db.session.flush()
                            print(f"  进度: {ai_decision_count} 条...")
                    except Exception as e:
                        if ai_decision_count < 3:
                            print(f"  ⚠ 跳过行: {e}")
            db.session.commit()
            print(f"  ✓ AI 决策导入完成，共 {ai_decision_count} 条")
        else:
            print(f"\n[10/11] 跳过 AI 决策导入（文件不存在: {AI_DECISIONS_CSV}）")
        
        # 11. 从 CSV 导入 Prompts（prompts.csv）
        prompt_count = 0
        if ENABLE_CSV_IMPORT.get("prompts", True) and os.path.exists(PROMPTS_CSV):
            print(f"\n[11/11] 从 CSV 导入 Prompts: {PROMPTS_CSV}")
            with open(PROMPTS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        agent_name = (row.get("agent_name") or "").strip()
                        if not agent_name:
                            continue
                        template_key = (row.get("template_key") or "").strip() or None
                        template = (row.get("template") or "").strip()
                        if not template:
                            continue
                        # 检查是否已存在（根据唯一约束：agent_name + template_key）
                        existing = db.session.query(Prompt).filter_by(
                            agent_name=agent_name,
                            template_key=template_key
                        ).first()
                        if existing:
                            continue
                        description = (row.get("description") or "").strip() or None
                        version = (row.get("version") or "").strip() or None
                        prompt = Prompt(
                            agent_name=agent_name,
                            template_key=template_key,
                            description=description,
                            version=version,
                            template=template
                        )
                        db.session.add(prompt)
                        prompt_count += 1
                        if prompt_count % 100 == 0:
                            db.session.flush()
                            print(f"  进度: {prompt_count} 条...")
                    except Exception as e:
                        if prompt_count < 3:
                            print(f"  ⚠ 跳过行: {e}")
            db.session.commit()
            print(f"  ✓ Prompts 导入完成，共 {prompt_count} 条")
        else:
            print(f"\n[11/11] 跳过 Prompts 导入（文件不存在: {PROMPTS_CSV}）")
        
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
        print(f"  - 预警规则: {len(alert_rules)} 条")
        print(f"  - AI 决策: {ai_decision_count} 条")
        print(f"  - Prompts: {prompt_count} 条")
        print("=" * 60)


if __name__ == "__main__":
    try:
        generate_mock_data()
    except Exception as e:
        print(f"❌ 生成Mock数据失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

