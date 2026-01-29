#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据收集路由
提供数据接收API端点，包括传感器、图像、喂食机等数据
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Optional
import logging
import time
import os
from werkzeug.utils import secure_filename
from sqlalchemy import text

from db_models.db_session import db_session_factory
from db_models.sensor_reading import SensorReading
from db_models.camera import CameraImage
from db_models.feeder_log import FeederLog
from db_models.operation_log import OperationLog
from services.data_cleaning_service import DataCleaningService

# 创建蓝图
data_collection_bp = Blueprint('data_collection', __name__, url_prefix='/api/data')

# 配置日志
logger = logging.getLogger(__name__)

# sensor_id 映射表：用户输入的ID -> 实际数据库中的设备ID
# 请根据实际情况修改映射关系
SENSOR_ID_MAPPING = {
    1: 1,   # 用户输入1 -> 映射到设备ID 23
    2: 2,   # 用户输入2 -> 映射到设备ID 24
    3: 3,   # 用户输入3 -> 映射到设备ID 25
    4: 4,   # 用户输入4 -> 映射到设备ID 26
    5: 5,   # 用户输入5 -> 映射到设备ID 27
}


def get_type_name_from_metric(session, metric: str) -> Optional[tuple]:
    """
    从数据库查询 metric 对应的 type_name、unit 和 description
    
    Args:
        session: 数据库会话
        metric: metric 标识符
        
    Returns:
        tuple: (type_name, unit, description) 或 None（如果未找到）
    """
    if not metric:
        return None
    
    result = session.execute(
        text("""
            SELECT type_name, unit, description 
            FROM sensor_types 
            WHERE metric = :metric OR LOWER(metric) = LOWER(:metric)
            LIMIT 1
        """),
        {"metric": metric}
    ).first()
    
    if result:
        return result[0], result[1], result[2]
    return None


def ensure_batch_exists(session, batch_business_id: Optional[str], pond_id: Optional[int] = None) -> Optional[int]:
    """
    确保批次记录存在，如果不存在则自动创建
    
    Args:
        session: 数据库会话
        batch_business_id: 批次业务ID（字符串，如 "BATCH_2024_001"）
        pond_id: 养殖池ID（整数，数据库主键，用于创建新批次时使用）
        
    Returns:
        Optional[int]: 批次数据库主键ID（batches.id，如果创建失败则返回 None）
    """
    if batch_business_id is None:
        return None
    
    from db_models.batch import Batch
    from datetime import date
    
    # 查询批次是否存在（通过业务ID查询）
    batch = session.query(Batch).filter(Batch.batch_id == batch_business_id).first()
    if batch:
        return batch.id  # 返回数据库主键
    
    # 如果批次不存在，自动创建一个
    logger.info(f"批次记录不存在，自动创建: batch_id={batch_business_id}, pond_id={pond_id}")
    
    if pond_id is None:
        logger.error(f"创建批次时必须提供 pond_id: batch_id={batch_business_id}")
        return None
    
    try:
        # 使用原生 SQL 插入新批次记录
        # 注意：id 字段会自动生成，batch_id 是业务ID字符串
        session.execute(
            text("""
                INSERT INTO batches (batch_id, pond_id, start_date, created_at, updated_at)
                VALUES (:batch_id, :pond_id, :start_date, NOW(), NOW())
            """),
            {
                "batch_id": batch_business_id,  # 业务ID（字符串）
                "pond_id": pond_id,              # 养殖池数据库主键（整数）
                "start_date": date.today()       # 使用当前日期作为开始日期
            }
        )
        session.flush()  # 刷新以获取插入的记录
        
        # 重新查询确认（通过业务ID查询）
        batch = session.query(Batch).filter(Batch.batch_id == batch_business_id).first()
        if batch:
            logger.info(f"成功创建批次记录: id={batch.id}, batch_id={batch.batch_id}, pond_id={batch.pond_id}")
            return batch.id  # 返回数据库主键
        else:
            raise Exception("批次创建后查询失败")
            
    except Exception as e:
        logger.error(f"创建批次记录失败: {e}")
        # 如果批次创建失败，返回 None，避免外键约束错误
        return None


@data_collection_bp.route('/sensors', methods=['POST'])
def receive_sensor_data():
    """
    接收传感器数据接口
    
    请求体格式：
    {
        "sensor_id": "1",            // 必填，传感器设备ID（字符串形式的整数，会通过映射表转换为实际设备ID）
        "value": 25.5,               // 必填，传感器读数值
        "pool_id": "1",              // 可选，养殖池主键ID（字符串形式的整数，对应ponds.id，如未提供则从device获取）
        "batch_id": "1",             // 可选，批次主键ID（字符串形式的整数，对应batches.id）
        "unit": "°C",                // 可选，单位
        "timestamp": 1234567890000,  // 可选，Unix时间戳（毫秒）
        "description": "1号池温度"   // 可选，描述信息
    }
    
    注意：
    - sensor_id 会通过 SENSOR_ID_MAPPING 映射到实际的数据库设备ID
    - metric 将从 device.sensor_type_id 关联的 sensor_types 表自动获取，无需传入
    - 异常值检测使用 sensor_types 表的 valid_min 和 valid_max 字段
    """
    try:
        data = request.get_json()
        logger.debug(f"接收传感器数据: {data}")
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        # 必填字段检查
        if 'sensor_id' not in data or 'value' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: sensor_id, value"
            }), 400
        # 提取数据
        sensor_id_str = str(data['sensor_id'])  # 传感器设备主键ID（字符串）
        value = float(data['value'])
        unit = data.get('unit')
        batch_id_str = data.get('batch_id')  # 批次主键ID（字符串）
        pond_id_str = data.get('pool_id')  # 养殖池主键ID（字符串）
        timestamp = data.get('timestamp')
        description = data.get('description')
        
        # 将 sensor_id 转换为整数
        try:
            sensor_id_input = int(sensor_id_str)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": f"sensor_id 必须是有效的整数: {sensor_id_str}"
            }), 400
        
        # 应用 sensor_id 映射
        if sensor_id_input in SENSOR_ID_MAPPING:
            sensor_id = SENSOR_ID_MAPPING[sensor_id_input]
            logger.debug(f"sensor_id 映射: {sensor_id_input} -> {sensor_id}")
        else:
            # 如果不在映射表中，直接使用原始值
            sensor_id = sensor_id_input
            logger.debug(f"sensor_id 未找到映射，使用原始值: {sensor_id}")
        
        # 将 pool_id 转换为整数（如果提供了）
        pond_id = None
        if pond_id_str is not None:
            try:
                pond_id = int(pond_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"pool_id 必须是有效的整数: {pond_id_str}"
                }), 400
        
        # 将 batch_id 转换为整数（如果提供了）
        batch_id = None
        if batch_id_str is not None:
            try:
                batch_id = int(batch_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"batch_id 必须是有效的整数: {batch_id_str}"
                }), 400
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 保存到数据库
        with db_session_factory() as session:
            # 从统一设备表查找传感器设备（通过主键ID查找，需验证设备类型为sensor）
            from db_models.device import Device, DeviceType
            from db_models.sensor_type import SensorType
            from db_models.pond import Pond
            from db_models.batch import Batch
            
            # 通过主键ID查找设备，并验证是传感器类型
            device = session.query(Device)\
                .join(DeviceType, Device.device_type_id == DeviceType.id)\
                .filter(Device.id == sensor_id)\
                .filter(Device.is_deleted == False)\
                .filter(DeviceType.category == 'sensor')\
                .first()
            
            if not device:
                return jsonify({
                    "success": False,
                    "error": f"传感器设备不存在或已删除: sensor_id={sensor_id}"
                }), 404
            
            # 初始化数据库ID变量
            batch_db_id = None
            
            # 始终使用 device.pond_id 作为最终的 pond_id
            pond_db_id = device.pond_id
            if pond_db_id is None:
                return jsonify({
                    "success": False,
                    "error": f"传感器设备未关联养殖池: sensor_id={sensor_id}"
                }), 400
            
            # 如果用户提供了 pool_id，与 device.pond_id 比较，不一致则记录日志
            if pond_id is not None and pond_id != device.pond_id:
                logger.warning(f"用户提供的 pool_id={pond_id} 与设备关联的 pond_id={device.pond_id} 不一致，将使用设备的 pond_id={device.pond_id}")
            
            # 如果提供了 batch_id（主键ID），验证批次是否存在，并检查 pond_id 是否一致
            if batch_id is not None:
                batch = session.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return jsonify({
                        "success": False,
                        "error": f"批次不存在: batch_id={batch_id}"
                    }), 404
                batch_db_id = batch.id
                # 检查批次的 pond_id 与设备的 pond_id 是否一致
                if batch.pond_id != device.pond_id:
                    logger.warning(f"批次 batch_id={batch_id} 的 pond_id={batch.pond_id} 与设备关联的 pond_id={device.pond_id} 不一致")
            
            # ===== 从 sensor_type 获取类型信息（用于快照字段）=====
            sensor_metric = None
            sensor_unit = None
            is_anomaly = False
            valid_min = None
            valid_max = None
            
            # 通过 device.sensor_type_id 获取传感器类型信息
            if device.sensor_type_id:
                sensor_type = session.query(SensorType).filter(SensorType.id == device.sensor_type_id).first()
                if sensor_type:
                # 获取快照字段数据
                    sensor_metric = sensor_type.metric
                    sensor_unit = sensor_type.unit
                
                # 获取有效范围用于异常检测
                    valid_min = sensor_type.valid_min
                    valid_max = sensor_type.valid_max
                
                # 判断值是否在有效范围内
                if valid_min is not None and value < valid_min:
                    is_anomaly = True
                    logger.warning(f"传感器数据异常（低于最小值）: sensor_id={sensor_id}, value={value}, valid_min={valid_min}")
                elif valid_max is not None and value > valid_max:
                    is_anomaly = True
                    logger.warning(f"传感器数据异常（超过最大值）: sensor_id={sensor_id}, value={value}, valid_max={valid_max}")
            
            # 确定质量标记
            quality_flag = 'anomaly' if is_anomaly else 'ok'
            
            # 生成校验和
            checksum_data = {
                'device_id': device.id,
                'value': value,
                'pond_id': pond_db_id,
                'ts_utc': ts_utc.isoformat() if ts_utc else None
            }
            checksum = DataCleaningService.generate_checksum(checksum_data)
            
            # 创建 SensorReading 对象（直接使用 device.id）
            reading = SensorReading(
                device_id=device.id,  # 直接使用设备主键
                pond_id=pond_db_id,   # 必填字段，使用数据库主键
                value=value
            )
            
            # 设置可选字段（通过属性赋值）
            if batch_db_id is not None:
                reading.batch_id = batch_db_id
            if ts_utc is not None:
                reading.recorded_at = ts_utc
                reading.ts_utc = ts_utc
            if ts_local is not None:
                reading.ts_local = ts_local
            if description is not None:
                reading.description = description
            
            # 设置快照字段（从 sensor_type 获取，如果用户传入则优先使用用户值）
            if unit is not None:
                # 用户传入的 unit 优先
                reading.unit = unit
            elif sensor_unit is not None:
                # 否则使用从 sensor_type 获取的 unit
                reading.unit = sensor_unit
            
            if sensor_metric is not None:
                # 设置 metric 快照字段
                reading.metric = sensor_metric
            
                reading.quality_flag = quality_flag
                reading.checksum = checksum
            
            session.add(reading)
            session.commit()
            
            logger.info(f"传感器数据接收成功: sensor_id={sensor_id}, value={value}, pond_id={pond_db_id}, batch_id={batch_db_id}, metric={sensor_metric}, quality_flag={quality_flag}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": reading.id,
                    "sensor_id": sensor_id,
                    "value": reading.value,
                    "quality_flag": reading.quality_flag
                },
                "timestamp": int(time.time() * 1000)
            }), 200
            
    except ValueError as e:
        logger.error(f"传感器数据接收失败（数据格式错误）: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"数据格式错误: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"传感器数据接收失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@data_collection_bp.route('/feeders', methods=['POST'])
def receive_feeder_data():
    """
    接收喂食机数据接口
    
    请求体格式：
    {
        "feeder_id": "AI",  // 必填，喂食机设备分组ID（对应devices表device_specific_config字段中的group_id，如"AI"、"AI2"）
        "batch_id": "1",  // 可选，批次主键ID（字符串形式的整数，对应batches.id）
        "pool_id": "1",  // 可选，养殖池主键ID（字符串形式的整数，对应ponds.id）
        "feed_amount_g": 500.0,
        "run_time_s": 120,
        "status": "ok",  // ok/warning/error
        "leftover_estimate_g": 50.0,  // 可选
        "timestamp": 1234567890000,  // Unix时间戳（毫秒），可选
        "notes": "正常投喂"  // 可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        # 必填字段检查
        if 'feeder_id' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: feeder_id"
            }), 400
        
        # 提取数据
        feeder_group_id = str(data['feeder_id'])  # 喂食机分组ID（对应device_specific_config中的group_id）
        batch_id_str = data.get('batch_id')  # 批次主键ID（字符串）
        pond_id_str = data.get('pool_id')  # 养殖池主键ID（字符串）
        feed_amount_g = data.get('feed_amount_g')
        run_time_s = data.get('run_time_s')
        status = data.get('status', 'ok')
        leftover_estimate_g = data.get('leftover_estimate_g')
        timestamp = data.get('timestamp')
        notes = data.get('notes')
        
        # 将 pool_id 转换为整数（如果提供了）
        pond_id = None
        if pond_id_str is not None:
            try:
                pond_id = int(pond_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"pool_id 必须是有效的整数: {pond_id_str}"
                }), 400
        
        # 将 batch_id 转换为整数（如果提供了）
        batch_id = None
        if batch_id_str is not None:
            try:
                batch_id = int(batch_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"batch_id 必须是有效的整数: {batch_id_str}"
                }), 400
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 保存到数据库
        with db_session_factory() as session:
            # 从统一设备表查找喂食机设备（通过device_specific_config中的group_id查找）
            from db_models.device import Device, DeviceType
            from db_models.pond import Pond
            from db_models.batch import Batch
            from sqlalchemy import func
            
            # 通过device_specific_config中的group_id查找喂食机设备
            # MySQL JSON函数：JSON_UNQUOTE(JSON_EXTRACT(device_specific_config, '$.group_id'))
            device = session.query(Device)\
                .join(DeviceType, Device.device_type_id == DeviceType.id)\
                .filter(Device.is_deleted == False)\
                .filter(DeviceType.category == 'feeder')\
                .filter(func.json_unquote(func.json_extract(Device.device_specific_config, '$.group_id')) == feeder_group_id)\
                .first()
            
            if not device:
                return jsonify({
                    "success": False,
                    "error": f"喂食机设备不存在或已删除: feeder_id(group_id)={feeder_group_id}"
                }), 404
            
            # 初始化数据库ID变量
            pond_db_id = None
            batch_db_id = None
            
            # 获取 pond_id（如果请求中没有提供，从 device 获取）
            if pond_id is None:
                pond_db_id = device.pond_id
                if pond_db_id is None:
                    return jsonify({
                        "success": False,
                        "error": f"喂食机设备未关联养殖池且请求中未提供 pool_id: feeder_id(group_id)={feeder_group_id}"
                    }), 400
            else:
                # 如果提供了 pond_id（主键ID），验证养殖池是否存在
                pond = session.query(Pond).filter(Pond.id == pond_id).first()
                if not pond:
                    return jsonify({
                        "success": False,
                        "error": f"养殖池不存在: pool_id={pond_id}"
                    }), 404
                pond_db_id = pond.id  # 使用主键ID
            
            # 如果提供了 batch_id（主键ID），验证批次是否存在
            if batch_id is not None:
                batch = session.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return jsonify({
                        "success": False,
                        "error": f"批次不存在: batch_id={batch_id}"
                    }), 404
                batch_db_id = batch.id
            
            # 生成校验和
            checksum_data = {
                'device_id': device.id,
                'feed_amount_g': float(feed_amount_g) if feed_amount_g else None,
                'pond_id': pond_db_id,
                'ts_utc': ts_utc.isoformat() if ts_utc else None
            }
            checksum = DataCleaningService.generate_checksum(checksum_data)
            
            # 创建对象（直接使用 device.id）
            feeder_log = FeederLog(
                device_id=device.id,  # 直接使用设备主键
                pond_id=pond_db_id,   # 必填字段，使用数据库主键
                ts_utc=ts_utc,        # 必填字段
                status=status         # 有默认值，但可以传入
            )

            # 设置 init=False 的字段（通过属性赋值）
            if batch_db_id is not None:
                feeder_log.batch_id = batch_db_id
            if ts_local is not None:
                feeder_log.ts_local = ts_local
            if feed_amount_g is not None:
                feeder_log.feed_amount_g = feed_amount_g
            if run_time_s is not None:
                feeder_log.run_time_s = run_time_s
            if leftover_estimate_g is not None:
                feeder_log.leftover_estimate_g = leftover_estimate_g
            if notes is not None:
                feeder_log.notes = notes
            if checksum is not None:
                feeder_log.checksum = checksum
            
            session.add(feeder_log)
            session.commit()
            
            logger.info(f"喂食机数据接收成功: feeder_id(group_id)={feeder_group_id}, device.id={device.id}, feed_amount_g={feed_amount_g}, pond_id={pond_db_id}, batch_id={batch_db_id}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": feeder_log.id,
                    "feeder_id": feeder_group_id,  # 返回输入的feeder_id（即group_id）
                    "device_id": device.id,  # 返回实际的设备主键ID
                    "status": feeder_log.status
                },
                "timestamp": int(time.time() * 1000)
            }), 200
            
    except ValueError as e:
        logger.error(f"喂食机数据接收失败（数据格式错误）: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"数据格式错误: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"喂食机数据接收失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@data_collection_bp.route('/operations', methods=['POST'])
def receive_operation_data():
    """
    接收操作日志数据接口
    
    请求体格式：
    {
        "user_id": "1",  // 用户主键ID（字符串形式的整数，对应users.id）
        "action_type": "投料",
        "batch_id": "1",  // 可选，批次主键ID（字符串形式的整数，对应batches.id）
        "pool_id": "1",  // 可选，养殖池主键ID（字符串形式的整数，对应ponds.id）
        "remarks": "正常投喂操作",  // 可选
        "attachment_uri": "s3://bucket/file.pdf",  // 可选
        "timestamp": 1234567890000  // Unix时间戳（毫秒），可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        # 必填字段检查
        if 'user_id' not in data or 'action_type' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: user_id, action_type"
            }), 400
        
        # 提取数据
        user_id_str = str(data['user_id'])  # 用户主键ID（字符串）
        action_type = data['action_type']
        batch_id_str = data.get('batch_id')  # 批次主键ID（字符串）
        pond_id_str = data.get('pool_id')  # 养殖池主键ID（字符串）
        remarks = data.get('remarks')
        attachment_uri = data.get('attachment_uri')
        timestamp = data.get('timestamp')
        
        # 将 user_id 转换为整数
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": f"user_id 必须是有效的整数: {user_id_str}"
            }), 400
        
        # 将 pool_id 转换为整数（如果提供了）
        pond_id = None
        if pond_id_str is not None:
            try:
                pond_id = int(pond_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"pool_id 必须是有效的整数: {pond_id_str}"
                }), 400
        
        # 将 batch_id 转换为整数（如果提供了）
        batch_id = None
        if batch_id_str is not None:
            try:
                batch_id = int(batch_id_str)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": f"batch_id 必须是有效的整数: {batch_id_str}"
                }), 400
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 保存到数据库
        with db_session_factory() as session:
            # 验证用户是否存在（通过主键ID查询）
            from db_models.user import User
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({
                    "success": False,
                    "error": f"用户不存在: user_id={user_id}"
                }), 404
            
            # 初始化数据库ID变量
            pond_db_id = None
            batch_db_id = None
            
            # 如果提供了 pond_id（主键ID），验证养殖池是否存在
            if pond_id is not None:
                from db_models.pond import Pond
                pond = session.query(Pond).filter(Pond.id == pond_id).first()
                if not pond:
                    return jsonify({
                        "success": False,
                        "error": f"养殖池不存在: pond_id={pond_id}"
                    }), 404
                pond_db_id = pond.id  # 使用主键ID
            
            # 如果提供了 batch_id（主键ID），验证批次是否存在
            if batch_id is not None:
                from db_models.batch import Batch
                batch = session.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return jsonify({
                        "success": False,
                        "error": f"批次不存在: batch_id={batch_id}"
                    }), 404
                batch_db_id = batch.id
            
            # 创建对象（只传入 init=True 的字段）
            # 使用数据库主键而不是业务ID
            operation_log = OperationLog(
                user_id=user.id,  # 使用查询到的用户数据库ID
                ts_utc=ts_utc,
                action_type=action_type
            )
            # 设置 init=False 的字段（通过属性赋值）
            if batch_db_id is not None:
                operation_log.batch_id = batch_db_id
            if pond_db_id is not None:
                operation_log.pond_id = pond_db_id
            if ts_local is not None:
                operation_log.ts_local = ts_local
            if remarks is not None:
                operation_log.remarks = remarks
            if attachment_uri is not None:
                operation_log.attachment_uri = attachment_uri
            
            session.add(operation_log)
            session.commit()
            
            # 构建返回数据（返回数据库主键ID）
            result_data = {
                "id": operation_log.id,
                "user_id": user.id,  # 返回数据库主键ID
                "action_type": operation_log.action_type
            }
            
            # 如果有批次，返回批次主键ID
            if batch_db_id:
                result_data["batch_id"] = batch_db_id
            
            # 如果有养殖池，返回养殖池主键ID
            if pond_db_id:
                result_data["pond_id"] = pond_db_id
            
            logger.info(f"操作日志接收成功: user_id={user_id}, username={user.username}, action_type={action_type}, pond_id={pond_db_id}, batch_id={batch_db_id}")
            
            return jsonify({
                "success": True,
                "data": result_data,
                "timestamp": int(time.time() * 1000)
            }), 200
            
    except ValueError as e:
        logger.error(f"操作日志接收失败（数据格式错误）: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"数据格式错误: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"操作日志接收失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@data_collection_bp.route('/cameras', methods=['POST'])
def receive_camera_data():
    """
    接收摄像头图像数据接口
    
    请求格式：multipart/form-data
    文件字段：
        - file: 图像文件（必需）
    数据字段：
        - camera_id: 摄像头ID（必需）
        - batch_id: 批次ID（可选）
        - pool_id: 池号（可选）
        - timestamp: Unix时间戳（毫秒，可选）
        - width_px: 图像宽度（像素，可选）
        - height_px: 图像高度（像素，可选）
        - format: 图像格式（jpg/png，可选）
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "缺少文件字段: file"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "文件名为空"
            }), 400
        
        # 获取表单数据
        camera_id = request.form.get('camera_id')
        if not camera_id:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: camera_id"
            }), 400
        
        try:
            camera_id = int(camera_id)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "camera_id 必须是整数"
            }), 400
        
        batch_id = request.form.get('batch_id')
        if batch_id:
            try:
                batch_id = int(batch_id)
            except (ValueError, TypeError):
                batch_id = None
        
        pool_id = request.form.get('pool_id')
        timestamp = request.form.get('timestamp')
        width_px = request.form.get('width_px')
        height_px = request.form.get('height_px')
        format_str = request.form.get('format', 'jpg')
        
        # 处理时间戳
        if timestamp:
            try:
                timestamp_ms = int(timestamp)
                ts_utc, ts_local = DataCleaningService.standardize_time(timestamp_ms)
            except (ValueError, TypeError):
                ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
            timestamp_ms = int(ts_utc.timestamp() * 1000)
        
        # 处理图像尺寸
        if width_px:
            try:
                width_px = int(width_px)
            except (ValueError, TypeError):
                width_px = None
        else:
            width_px = None
            
        if height_px:
            try:
                height_px = int(height_px)
            except (ValueError, TypeError):
                height_px = None
        else:
            height_px = None
        
        # 保存文件（这里简化处理，实际应该保存到对象存储）
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        if not filename:
            # 如果没有文件名，使用时间戳生成
            filename = f"camera_{camera_id}_{timestamp_ms}.{format_str}"
        
        # 创建上传目录（实际应该使用对象存储）
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'cameras')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 如果没有提供尺寸，尝试从文件读取（需要PIL）
        if width_px is None or height_px is None:
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    if width_px is None:
                        width_px = img.width
                    if height_px is None:
                        height_px = img.height
            except ImportError:
                logger.warning("PIL未安装，无法读取图像尺寸")
            except Exception as e:
                logger.warning(f"读取图像尺寸失败: {e}")
        
        # 生成图片URL（实际应该使用对象存储URL）
        image_url = f"/uploads/cameras/{filename}"
        storage_uri = file_path  # 实际应该使用对象存储URI
        
        # 生成校验和
        checksum_data = {
            'camera_id': camera_id,
            'timestamp': timestamp_ms,
            'filename': filename,
            'file_size': file_size
        }
        checksum = DataCleaningService.generate_checksum(checksum_data)
        
        # 确定质量标记（默认 'ok'，可以根据实际情况进行质量检测）
        quality_flag = 'ok'  # TODO: 实现图像质量检测
        
        # 保存到数据库
        with db_session_factory() as session:
            # 创建对象（只传入 init=True 的字段）
            camera_image = CameraImage(
                camera_id=camera_id,
                name=f"摄像头{camera_id}",
                location=pool_id or "未知位置",
                status="在线",
                image_url=image_url,
                last_update=timestamp_ms,
                timestamp=timestamp_ms
            )
            # 设置 init=False 的字段（通过属性赋值）
            if batch_id is not None:
                camera_image.batch_id = batch_id
            if pool_id is not None:
                camera_image.pool_id = pool_id
            if storage_uri is not None:
                camera_image.storage_uri = storage_uri
            if ts_utc is not None:
                camera_image.ts_utc = ts_utc
            if ts_local is not None:
                camera_image.ts_local = ts_local
            if width_px is not None:
                camera_image.width_px = width_px
            if height_px is not None:
                camera_image.height_px = height_px
            if format_str is not None:
                camera_image.format = format_str
            camera_image.quality_flag = quality_flag
            if checksum is not None:
                camera_image.checksum = checksum
            # 设置其他可选字段
            camera_image.timestamp_str = ts_utc.strftime("%Y-%m-%d %H:%M:%S") if ts_utc else ""
            camera_image.width = width_px or 1920
            camera_image.height = height_px or 1080
            camera_image.size = file_size
            
            session.add(camera_image)
            session.commit()
            
            logger.info(f"摄像头图像接收成功: camera_id={camera_id}, filename={filename}, size={file_size}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": camera_image.id,
                    "camera_id": camera_image.camera_id,
                    "image_url": camera_image.image_url,
                    "timestamp": timestamp_ms
                },
                "timestamp": int(time.time() * 1000)
            }), 200
            
    except Exception as e:
        logger.error(f"摄像头图像接收失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@data_collection_bp.route('/shrimp_stats_data', methods=['POST'])
def receive_shrimp_stats_data():
    """
    接收虾类检测统计结果数据
    
    请求体格式（JSON）:
    {
        "uuid": "唯一标识符",
        "pond_id": "池号",
        "input_subdir": "输入子目录",
        "output_dir": "输出目录",
        "created_at": "ISO时间戳",
        "conf": 0.3,
        "iou": 0.5,
        "total_live": 100,
        "total_dead": 5,
        "size_cm": {
            "min": 8.1,
            "max": 17.2,
            "mean": 13.0,
            "median": 13.0
        },
        "weight_g": {
            "min": 3.7,
            "max": 36.2,
            "mean": 16.7,
            "median": 15.5
        },
        "batch_id": 2,  # 可选
        "camera_id": 1,  # 可选
        "frame_id": 123  # 可选，关联到camera_images表
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体为空"
            }), 400
        
        # 从请求中提取数据
        uuid_str = data.get('uuid')
        pond_id = data.get('pond_id', '4')
        input_subdir = data.get('input_subdir', '')
        output_dir = data.get('output_dir', '')
        created_at_source_iso = data.get('created_at', '')
        conf = data.get('conf')
        iou = data.get('iou')
        total_live = data.get('total_live', 0)
        total_dead = data.get('total_dead', 0)
        batch_id = data.get('batch_id')
        camera_id = data.get('camera_id')
        frame_id = data.get('frame_id')
        
        # 提取尺寸和重量统计
        size_cm = data.get('size_cm', {})
        weight_g = data.get('weight_g', {})
        
        size_min_cm = size_cm.get('min')
        size_max_cm = size_cm.get('max')
        size_mean_cm = size_cm.get('mean')
        size_median_cm = size_cm.get('median')
        
        weight_min_g = weight_g.get('min')
        weight_max_g = weight_g.get('max')
        weight_mean_g = weight_g.get('mean')
        weight_median_g = weight_g.get('median')
        
        # 解析时间戳
        from datetime import datetime
        try:
            if created_at_source_iso:
                created_at_source = datetime.fromisoformat(created_at_source_iso.replace('Z', '+00:00'))
            else:
                created_at_source = datetime.now()
        except Exception:
            created_at_source = datetime.now()
        
        # 创建 ShrimpStats 记录
        from db_models.shrimp_stats import ShrimpStats
        from sqlalchemy import text
        
        with db_session_factory() as session:
            # 使用原始 SQL 插入，因为很多字段是 init=False
            session.execute(
                text("""
                    INSERT INTO shrimp_stats (
                        uuid, pond_id, input_subdir, output_dir, created_at_source_iso, created_at_source,
                        conf, iou, total_live, total_dead,
                        size_min_cm, size_max_cm, size_mean_cm, size_median_cm,
                        weight_min_g, weight_max_g, weight_mean_g, weight_median_g,
                        frame_id, ts_utc, created_at, updated_at
                    ) VALUES (
                        :uuid, :pond_id, :input_subdir, :output_dir, :created_at_source_iso, :created_at_source,
                        :conf, :iou, :total_live, :total_dead,
                        :size_min_cm, :size_max_cm, :size_mean_cm, :size_median_cm,
                        :weight_min_g, :weight_max_g, :weight_mean_g, :weight_median_g,
                        :frame_id, :ts_utc, NOW(), NOW()
                    )
                """),
                {
                    "uuid": uuid_str,
                    "pond_id": pond_id,
                    "input_subdir": input_subdir,
                    "output_dir": output_dir,
                    "created_at_source_iso": created_at_source_iso,
                    "created_at_source": created_at_source,
                    "conf": conf,
                    "iou": iou,
                    "total_live": total_live,
                    "total_dead": total_dead,
                    "size_min_cm": size_min_cm,
                    "size_max_cm": size_max_cm,
                    "size_mean_cm": size_mean_cm,
                    "size_median_cm": size_median_cm,
                    "weight_min_g": weight_min_g,
                    "weight_max_g": weight_max_g,
                    "weight_mean_g": weight_mean_g,
                    "weight_median_g": weight_median_g,
                    "frame_id": frame_id,
                    "ts_utc": datetime.now()
                }
            )
            session.commit()
            
            logger.info(f"虾类检测统计结果接收成功: uuid={uuid_str}, pond_id={pond_id}, total_live={total_live}, total_dead={total_dead}")
            
            return jsonify({
                "success": True,
                "message": "虾类检测统计结果已保存",
                "timestamp": int(time.time() * 1000)
            }), 200
            
    except Exception as e:
        logger.error(f"虾类检测统计结果接收失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@data_collection_bp.route('/batch_images', methods=['POST'])
def receive_batch_images():
    """
    接收批量图片数据集并进行 YOLO 检测
    
    请求格式：multipart/form-data
    文件字段：
        - files: 图片文件列表（必需，可以是多个文件）
    数据字段：
        - camera_id: 摄像头ID（必需）
        - batch_id: 批次ID（可选）
        - pool_id: 池号（可选，默认 "4"）
        - conf: 置信度阈值（可选，默认 0.3）
        - iou: IOU阈值（可选，默认 0.5）
        - save_results: 是否保存检测结果图（可选，默认 false）
    """
    import tempfile
    import shutil
    
    temp_input_dir = None
    temp_output_dir = None
    
    try:
        print(f"收到处理图片的请求: {request.files}")
        print(f"request.form: {request.form}")
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({
                "success": False,
                "error": "缺少文件字段: files"
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({
                "success": False,
                "error": "文件列表为空"
            }), 400
        
        # 获取表单数据
        camera_id = request.form.get('camera_id')
        if not camera_id:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: camera_id"
            }), 400
        
        try:
            camera_id = int(camera_id)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "camera_id 必须是整数"
            }), 400
        
        batch_id = request.form.get('batch_id')
        if batch_id:
            try:
                batch_id = int(batch_id)
            except (ValueError, TypeError):
                batch_id = None
        
        pool_id = request.form.get('pool_id', '4')
        
        conf = request.form.get('conf')
        if conf:
            try:
                conf = float(conf)
            except (ValueError, TypeError):
                conf = None
        
        iou = request.form.get('iou')
        if iou:
            try:
                iou = float(iou)
            except (ValueError, TypeError):
                iou = None
        
        save_results = request.form.get('save_results', 'false').lower() in ('true', '1', 'yes')
        
        # 获取 source_video 字段，如果存在则去掉扩展名作为 input_subdir
        source_video = request.form.get('source_video')
        if source_video:
            # 去掉扩展名（.mp4, .avi 等）
            input_subdir = os.path.splitext(source_video)[0]
            logger.info(f"使用 source_video 作为 input_subdir: {input_subdir}")
        else:
            # 如果没有提供 source_video，使用默认格式
            input_subdir = f"camera_{camera_id}_{int(time.time())}"
            logger.info(f"使用默认格式生成 input_subdir: {input_subdir}")
        
        # 创建临时目录
        temp_input_dir = tempfile.mkdtemp(prefix='yolo_input_')
        temp_output_dir = tempfile.mkdtemp(prefix='yolo_output_')
        
        # 保存上传的图片
        image_paths = []
        for file in files:
            if file.filename == '':
                continue
            
            # 检查文件扩展名
            filename = secure_filename(file.filename)
            if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp']):
                logger.warning(f"跳过非图片文件: {filename}")
                continue
            
            file_path = os.path.join(temp_input_dir, filename)
            file.save(file_path)
            image_paths.append(file_path)
            logger.debug(f"保存图片: {file_path}")
        
        if not image_paths:
            return jsonify({
                "success": False,
                "error": "没有有效的图片文件"
            }), 400
        
        logger.info(f"收到 {len(image_paths)} 张图片，开始调用 YOLO 检测服务...")
        
        # 调用 /root/yolo 项目进行检测
        import subprocess
        import json as json_lib
        import shutil
        
        yolo_project_path = '/root/yolo'
        yolo_input_dir = os.path.join(yolo_project_path, 'input_test_images', input_subdir)
        yolo_output_dir = os.path.join(yolo_project_path, 'output_results', input_subdir)
        stats_json_path = os.path.join(yolo_output_dir, 'stats.json')
        
        try:
            # 创建输入目录
            os.makedirs(yolo_input_dir, exist_ok=True)
            
            # 将图片复制到 YOLO 项目的输入目录
            for img_path in image_paths:
                filename = os.path.basename(img_path)
                dest_path = os.path.join(yolo_input_dir, filename)
                shutil.copy2(img_path, dest_path)
                logger.debug(f"复制图片到 YOLO 输入目录: {dest_path}")
            
            # 修改 /root/yolo/main.py 中的 conf 和 iou 参数（如果提供了）
            # 由于 main.py 是硬编码的，我们需要通过环境变量或修改文件来传递参数
            # 这里我们采用修改 main.py 临时文件的方式，或者直接调用并传递参数
            # 但考虑到 main.py 使用 argparse，我们可以直接调用 Python 脚本
            
            # 构建 Python 命令
            python_cmd = ['python3', os.path.join(yolo_project_path, 'main.py'), input_subdir]
            
            # 如果提供了 conf 或 iou，通过命令行参数传递
            if conf is not None:
                python_cmd.extend(['--conf', str(conf)])
            if iou is not None:
                python_cmd.extend(['--iou', str(iou)])
            
            env = os.environ.copy()
            
            # 调用 YOLO 检测脚本
            logger.info(f"调用 YOLO 检测脚本: {' '.join(python_cmd)}")
            result = subprocess.run(
                python_cmd,
                cwd=yolo_project_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"YOLO 检测脚本执行失败: {error_msg}")
                return jsonify({
                    "success": False,
                    "error": f"YOLO 检测失败: {error_msg[:500]}"
                }), 500
            
            # 读取检测结果
            if not os.path.exists(stats_json_path):
                logger.error(f"检测结果文件不存在: {stats_json_path}")
                return jsonify({
                    "success": False,
                    "error": "检测结果文件未生成"
                }), 500
            
            with open(stats_json_path, 'r', encoding='utf-8') as f:
                stats = json_lib.load(f)
            
            # 添加元数据
            stats['camera_id'] = camera_id
            stats['batch_id'] = batch_id
            stats['pool_id'] = pool_id
            stats['input_subdir'] = input_subdir
            stats['output_dir'] = yolo_output_dir if save_results else ""
            
            # 如果 save_results=True，将输出结果复制到临时目录
            if save_results and os.path.exists(yolo_output_dir):
                try:
                    # 复制输出目录内容到临时输出目录
                    if os.path.exists(temp_output_dir):
                        shutil.rmtree(temp_output_dir)
                    shutil.copytree(yolo_output_dir, temp_output_dir)
                    stats['output_dir'] = temp_output_dir
                    logger.info(f"检测结果已复制到临时目录: {temp_output_dir}")
                except Exception as e:
                    logger.warning(f"复制检测结果失败: {e}")
            
            logger.info(f"YOLO 检测完成: total_live={stats.get('total_live', 0)}, total_dead={stats.get('total_dead', 0)}")
            
        except subprocess.TimeoutExpired:
            logger.error("YOLO 检测超时（超过10分钟）")
            return jsonify({
                "success": False,
                "error": "YOLO 检测超时，请稍后重试"
            }), 500
        except FileNotFoundError:
            logger.error(f"YOLO 项目路径不存在: {yolo_project_path}")
            return jsonify({
                "success": False,
                "error": f"YOLO 检测服务未找到: {yolo_project_path}"
            }), 500
        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"YOLO 检测失败: {str(e)}"
            }), 500
        
        # 发送统计结果到数据库
        try:
            from db_models.shrimp_stats import ShrimpStats
            from datetime import datetime
            import uuid as uuid_lib
            
            # 构建统计结果数据
            created_at_source_iso = stats.get("created_at", "")
            try:
                if created_at_source_iso:
                    created_at_source = datetime.fromisoformat(created_at_source_iso.replace('Z', '+00:00'))
                else:
                    created_at_source = datetime.now()
            except Exception:
                created_at_source = datetime.now()
            
            with db_session_factory() as session:
                # 检查 UUID 是否已存在，如果存在则生成新的 UUID
                uuid_value = stats.get("uuid")
                
                # 如果 stats.json 中没有 uuid，或者 uuid 为空，生成新的 UUID
                if not uuid_value:
                    uuid_value = str(uuid_lib.uuid4())
                    stats['uuid'] = uuid_value
                    logger.info(f"stats.json 中没有 uuid，生成新的 UUID: {uuid_value}")
                else:
                    # 如果 uuid 存在，检查是否已在数据库中存在
                    existing = session.execute(
                        text("SELECT id FROM shrimp_stats WHERE uuid = :uuid"),
                        {"uuid": uuid_value}
                    ).first()
                    if existing:
                        logger.warning(f"UUID {uuid_value} 已存在，生成新的 UUID")
                        uuid_value = str(uuid_lib.uuid4())
                        stats['uuid'] = uuid_value
                
                # 使用 INSERT ... ON DUPLICATE KEY UPDATE 来处理重复键
                session.execute(
                    text("""
                        INSERT INTO shrimp_stats (
                            uuid, pond_id, input_subdir, output_dir, created_at_source_iso, created_at_source,
                            conf, iou, total_live, total_dead,
                            size_min_cm, size_max_cm, size_mean_cm, size_median_cm,
                            weight_min_g, weight_max_g, weight_mean_g, weight_median_g,
                            frame_id, ts_utc, created_at, updated_at
                        ) VALUES (
                            :uuid, :pond_id, :input_subdir, :output_dir, :created_at_source_iso, :created_at_source,
                            :conf, :iou, :total_live, :total_dead,
                            :size_min_cm, :size_max_cm, :size_mean_cm, :size_median_cm,
                            :weight_min_g, :weight_max_g, :weight_mean_g, :weight_median_g,
                            :frame_id, :ts_utc, NOW(), NOW()
                        ) ON DUPLICATE KEY UPDATE
                            pond_id = VALUES(pond_id),
                            input_subdir = VALUES(input_subdir),
                            output_dir = VALUES(output_dir),
                            created_at_source_iso = VALUES(created_at_source_iso),
                            created_at_source = VALUES(created_at_source),
                            conf = VALUES(conf),
                            iou = VALUES(iou),
                            total_live = VALUES(total_live),
                            total_dead = VALUES(total_dead),
                            size_min_cm = VALUES(size_min_cm),
                            size_max_cm = VALUES(size_max_cm),
                            size_mean_cm = VALUES(size_mean_cm),
                            size_median_cm = VALUES(size_median_cm),
                            weight_min_g = VALUES(weight_min_g),
                            weight_max_g = VALUES(weight_max_g),
                            weight_mean_g = VALUES(weight_mean_g),
                            weight_median_g = VALUES(weight_median_g),
                            ts_utc = VALUES(ts_utc),
                            updated_at = NOW()
                    """),
                    {
                        "uuid": uuid_value,
                        "pond_id": pool_id,
                        "input_subdir": stats.get("input_subdir", ""),
                        "output_dir": stats.get("output_dir", ""),
                        "created_at_source_iso": created_at_source_iso,
                        "created_at_source": created_at_source,
                        "conf": stats.get("conf"),
                        "iou": stats.get("iou"),
                        "total_live": stats.get("total_live", 0),
                        "total_dead": stats.get("total_dead", 0),
                        "size_min_cm": stats.get("size_cm", {}).get("min") if stats.get("size_cm") else None,
                        "size_max_cm": stats.get("size_cm", {}).get("max") if stats.get("size_cm") else None,
                        "size_mean_cm": stats.get("size_cm", {}).get("mean") if stats.get("size_cm") else None,
                        "size_median_cm": stats.get("size_cm", {}).get("median") if stats.get("size_cm") else None,
                        "weight_min_g": stats.get("weight_g", {}).get("min") if stats.get("weight_g") else None,
                        "weight_max_g": stats.get("weight_g", {}).get("max") if stats.get("weight_g") else None,
                        "weight_mean_g": stats.get("weight_g", {}).get("mean") if stats.get("weight_g") else None,
                        "weight_median_g": stats.get("weight_g", {}).get("median") if stats.get("weight_g") else None,
                        "frame_id": None,
                        "ts_utc": datetime.now()
                    }
                )
                session.commit()
                
                logger.info(f"统计结果已保存到数据库: uuid={uuid_value}")
        
        except Exception as e:
            logger.error(f"保存统计结果失败: {e}", exc_info=True)
            # 不返回错误，因为检测已经完成，只是保存失败
        
        # 返回检测结果
        return jsonify({
            "success": True,
            "message": "批量图片检测完成",
            "data": stats,
            "timestamp": int(time.time() * 1000)
        }), 200
        
    except Exception as e:
        logger.error(f"批量图片接收失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
    finally:
        # 清理临时目录（仅清理本地临时目录，不清理 YOLO 项目的输入输出目录）
        if temp_input_dir and os.path.exists(temp_input_dir):
            try:
                shutil.rmtree(temp_input_dir)
                logger.debug(f"清理临时输入目录: {temp_input_dir}")
            except Exception as e:
                logger.warning(f"清理临时输入目录失败: {e}")
        
        # 如果 save_results=True，temp_output_dir 包含从 YOLO 项目复制的结果，需要清理
        # 如果 save_results=False，temp_output_dir 可能未使用，也需要清理
        if temp_output_dir and os.path.exists(temp_output_dir):
            try:
                shutil.rmtree(temp_output_dir)
                logger.debug(f"清理临时输出目录: {temp_output_dir}")
            except Exception as e:
                logger.warning(f"清理临时输出目录失败: {e}")
        
        # 注意：YOLO 项目的输入输出目录（/root/yolo/input_test_images/ 和 /root/yolo/output_results/）
        # 不会被自动清理，以保留检测结果和历史数据。如需清理，可以后续添加清理策略。

