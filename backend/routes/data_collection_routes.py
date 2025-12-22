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

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_reading import SensorReading
from japan_server.db_models.camera import CameraImage
from japan_server.db_models.feeder_log import FeederLog
from japan_server.db_models.operation_log import OperationLog
from japan_server.services.data_cleaning_service import DataCleaningService

# 创建蓝图
data_collection_bp = Blueprint('data_collection', __name__, url_prefix='/api/data')

# 配置日志
logger = logging.getLogger(__name__)


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


def ensure_batch_exists(session, batch_id: Optional[int], pool_id: Optional[str] = None) -> Optional[int]:
    """
    确保批次记录存在，如果不存在则自动创建
    
    Args:
        session: 数据库会话
        batch_id: 批次ID
        pool_id: 池号（用于创建新批次时使用）
        
    Returns:
        Optional[int]: 批次ID（如果创建失败则返回 None）
    """
    if batch_id is None:
        return None
    
    from japan_server.db_models.batch import Batch
    from datetime import date
    
    batch = session.query(Batch).filter(Batch.batch_id == batch_id).first()
    if batch:
        return batch_id
    
    # 如果批次不存在，自动创建一个
    logger.info(f"批次记录不存在，自动创建: batch_id={batch_id}")
    try:
        # 尝试使用原始 SQL 插入指定 batch_id 的批次记录
        session.execute(
            text("""
                INSERT INTO batches (batch_id, pool_id, start_date, created_at, updated_at)
                VALUES (:batch_id, :pool_id, :start_date, NOW(), NOW())
            """),
            {
                "batch_id": batch_id,
                "pool_id": pool_id or "4",  # 使用提供的 pool_id 或默认值
                "start_date": date.today()  # 使用当前日期作为开始日期
            }
        )
        session.flush()  # 刷新以获取插入的记录
        # 重新查询确认
        batch = session.query(Batch).filter(Batch.batch_id == batch_id).first()
        if batch:
            logger.info(f"成功创建指定 batch_id 的批次记录: batch_id={batch.batch_id}, pool_id={batch.pool_id}")
            return batch_id
        else:
            raise Exception("批次创建后查询失败")
    except Exception as e:
        logger.warning(f"无法创建指定 batch_id 的批次记录，尝试使用自动 id: {e}")
        # 如果无法创建指定 batch_id 的批次，创建新批次并使用其 batch_id
        try:
            # 使用 SQL 插入，让数据库自动分配 batch_id
            session.execute(
                text("""
                    INSERT INTO batches (pool_id, start_date, created_at, updated_at)
                    VALUES (:pool_id, :start_date, NOW(), NOW())
                """),
                {
                    "pool_id": pool_id or "4",
                    "start_date": date.today()
                }
            )
            session.flush()  # 刷新以获取插入的记录
            # 获取自动生成的 batch_id
            batch = session.query(Batch).filter(
                Batch.pool_id == (pool_id or "4"),
                Batch.start_date == date.today()
            ).order_by(Batch.batch_id.desc()).first()
            if batch:
                logger.warning(f"使用自动生成的批次 batch_id: {batch.batch_id} (原始 batch_id: {batch_id})")
                return batch.batch_id
            else:
                raise Exception("批次创建后查询失败")
        except Exception as e2:
            logger.error(f"创建批次记录失败: {e2}")
            # 如果批次创建失败，返回 None，避免外键约束错误
            return None


@data_collection_bp.route('/sensors', methods=['POST'])
def receive_sensor_data():
    """
    接收传感器数据接口
    
    请求体格式：
    {
        "sensor_id": 1,
        "batch_id": 123,  // 可选
        "pool_id": "pool-001",  // 可选
        "value": 25.5,
        "metric": "temperature",
        "unit": "°C",
        "timestamp": 1234567890000,  // Unix时间戳（毫秒），可选
        "type_name": "温度传感器",  // 可选
        "description": "1号池温度"  // 可选
    }
    """
    try:
        data = request.get_json()
        print(f"data: {data}")
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
        sensor_id = data['sensor_id']
        value = float(data['value'])
        metric = data.get('metric')
        unit = data.get('unit')
        batch_id = data.get('batch_id')
        pool_id = data.get('pool_id')
        timestamp = data.get('timestamp')
        type_name = data.get('type_name')
        description = data.get('description')
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 异常值检测
        threshold = data.get('threshold')
        is_anomaly = False
        if metric:
            is_anomaly = DataCleaningService.detect_anomaly(value, metric, threshold)
        
        # 确定质量标记
        quality_flag = 'anomaly' if is_anomaly else 'ok'
        
        # 生成校验和
        checksum_data = {
            'sensor_id': sensor_id,
            'value': value,
            'metric': metric,
            'ts_utc': ts_utc.isoformat() if ts_utc else None
        }
        checksum = DataCleaningService.generate_checksum(checksum_data)
        
        # 保存到数据库
        with db_session_factory() as session:
            # 检查并确保传感器记录存在
            from japan_server.db_models.sensor import Sensor
            
            sensor = session.query(Sensor).filter(Sensor.id == sensor_id).first()
            if not sensor:
                # 如果传感器不存在，自动创建一个
                logger.info(f"传感器记录不存在，自动创建: sensor_id={sensor_id}")
                try:
                    # 首先确保有默认的养殖池（id=1）
                    pond_result = session.execute(
                        text("SELECT id FROM ponds WHERE id = 1")
                    ).first()
                    if not pond_result:
                        # 创建默认养殖池
                        session.execute(
                            text("""
                                INSERT INTO ponds (id, name, location, description, created_at, updated_at)
                                VALUES (1, '默认养殖池', '未知位置', '系统自动创建', NOW(), NOW())
                                ON DUPLICATE KEY UPDATE name = name
                            """)
                        )
                        session.flush()
                    
                    # 查找或创建默认传感器类型（根据 metric 或 type_name 判断）
                    # 优先使用 type_name，如果没有则使用 metric
                    sensor_type_name = type_name or (metric if metric else "unknown")
                    sensor_type_result = session.execute(
                        text("SELECT id FROM sensor_types WHERE type_name = :type_name"),
                        {"type_name": sensor_type_name}
                    ).first()
                    
                    if not sensor_type_result:
                        # 创建默认传感器类型（如果提供了 metric，也设置到 metric 字段）
                        session.execute(
                            text("""
                                INSERT INTO sensor_types (type_name, metric, unit, description)
                                VALUES (:type_name, :metric, :unit, :description)
                            """),
                            {
                                "type_name": sensor_type_name,
                                "metric": metric if metric else None,
                                "unit": unit or "",
                                "description": description or f"{sensor_type_name}传感器"
                            }
                        )
                        session.flush()
                        sensor_type_result = session.execute(
                            text("SELECT id FROM sensor_types WHERE type_name = :type_name"),
                            {"type_name": sensor_type_name}
                        ).first()
                    
                    sensor_type_id = sensor_type_result[0] if sensor_type_result else 1
                    
                    # 使用原始 SQL 插入指定 id 的传感器记录
                    session.execute(
                        text("""
                            INSERT INTO sensors (id, sensor_id, name, pond_id, sensor_type_id, status, created_at, updated_at)
                            VALUES (:id, :sensor_id, :name, :pond_id, :sensor_type_id, :status, NOW(), NOW())
                        """),
                        {
                            "id": sensor_id,
                            "sensor_id": f"sensor_{sensor_id}",
                            "name": f"传感器 {sensor_id}",
                            "pond_id": 1,
                            "sensor_type_id": sensor_type_id,
                            "status": "active"
                        }
                    )
                    session.flush()
                    # 重新查询确认
                    sensor = session.query(Sensor).filter(Sensor.id == sensor_id).first()
                    if sensor:
                        logger.info(f"成功创建传感器记录: id={sensor.id}, sensor_id={sensor.sensor_id}")
                    else:
                        raise Exception("传感器创建后查询失败")
                except Exception as e:
                    logger.error(f"创建传感器记录失败: {e}")
                    return jsonify({
                        "success": False,
                        "error": f"无法创建传感器记录: {str(e)}"
                    }), 500
            
            # 检查并确保批次记录存在（如果提供了 batch_id）
            if batch_id is not None:
                batch_id = ensure_batch_exists(session, batch_id, pool_id)
            
            # 创建对象（只传入 init=True 的字段）
            reading = SensorReading(
                sensor_id=sensor_id,
                value=value
            )
            # 设置 init=False 的字段（通过属性赋值）
            if batch_id is not None:
                reading.batch_id = batch_id
            if pool_id is not None:
                reading.pool_id = pool_id
            if ts_utc is not None:
                reading.recorded_at = ts_utc
                reading.ts_utc = ts_utc
            if ts_local is not None:
                reading.ts_local = ts_local
            # 设置 metric 和 type_name
            if metric is not None:
                reading.metric = metric
                # 如果还没有 type_name，从数据库查询映射
                if not type_name:
                    mapping_result = get_type_name_from_metric(session, metric)
                    if mapping_result:
                        type_name = mapping_result[0]
                        logger.debug(f"从数据库获取 type_name: {metric} -> {type_name}")
                    else:
                        # 如果数据库中没有找到，使用 metric 作为 type_name（向后兼容）
                        type_name = metric
                        logger.debug(f"使用 metric 作为 type_name: {metric}")
            
            # 设置 type_name
            if type_name is not None:
                reading.type_name = type_name
            if description is not None:
                reading.description = description
            if unit is not None:
                reading.unit = unit
            if quality_flag is not None:
                reading.quality_flag = quality_flag
            if checksum is not None:
                reading.checksum = checksum
            
            session.add(reading)
            session.commit()
            
            logger.info(f"传感器数据接收成功: sensor_id={sensor_id}, value={value}, metric={metric}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": reading.id,
                    "sensor_id": reading.sensor_id,
                    "value": reading.value,
                    "quality_flag": reading.quality_flag
                },
                "timestamp": int(time.time() * 1000)
            }), 201
            
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
        "feeder_id": 1,
        "batch_id": 123,  // 可选
        "pool_id": "pool-001",  // 可选
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
        feeder_id_raw = data['feeder_id']
        # 处理feeder_id：如果是字符串，尝试转换为整数；如果无法转换，使用字符串的hash值
        try:
            feeder_id = int(feeder_id_raw) if isinstance(feeder_id_raw, str) and feeder_id_raw.isdigit() else feeder_id_raw
            if not isinstance(feeder_id, int):
                # 如果仍然不是整数，使用hash值（取绝对值，确保为正数）
                feeder_id = abs(hash(feeder_id_raw)) % (10 ** 9)  # 限制在合理范围内
        except (ValueError, TypeError):
            # 如果转换失败，使用hash值
            feeder_id = abs(hash(str(feeder_id_raw))) % (10 ** 9)
        
        batch_id = data.get('batch_id')
        pool_id = data.get('pool_id')
        feed_amount_g = data.get('feed_amount_g')
        run_time_s = data.get('run_time_s')
        status = data.get('status', 'ok')
        leftover_estimate_g = data.get('leftover_estimate_g')
        timestamp = data.get('timestamp')
        notes = data.get('notes')
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 生成校验和
        checksum_data = {
            'feeder_id': feeder_id,
            'feed_amount_g': feed_amount_g,
            'ts_utc': ts_utc.isoformat() if ts_utc else None
        }
        checksum = DataCleaningService.generate_checksum(checksum_data)
        
        # 保存到数据库
        with db_session_factory() as session:
            # 检查并确保设备记录存在
            from japan_server.db_models.device import Device
            
            # 首先尝试通过 id 查找设备
            device = session.query(Device).filter(Device.id == feeder_id).first()
            
            # 如果通过 id 找不到，尝试通过 device_id 查找
            if not device:
                device = session.query(Device).filter(Device.device_id == str(feeder_id)).first()
                if device:
                    # 如果通过 device_id 找到了，使用其 id
                    logger.info(f"通过 device_id 找到设备: device_id={feeder_id}, id={device.id}")
                    feeder_id = device.id
            
            # 如果仍然找不到，自动创建一个新设备
            if not device:
                logger.info(f"设备记录不存在，自动创建: feeder_id={feeder_id}")
                try:
                    # 先尝试使用原始 SQL 插入指定 id 的设备记录
                    # 注意：这需要数据库允许手动指定自增主键的值（需要 SET sql_mode 或类似设置）
                    session.execute(
                        text("""
                            INSERT INTO devices (id, device_id, name, ownership, status, switch_status, priority, created_at, updated_at)
                            VALUES (:id, :device_id, :name, :ownership, :status, :switch_status, :priority, NOW(), NOW())
                        """),
                        {
                            "id": feeder_id,
                            "device_id": f"feeder_{feeder_id}",
                            "name": f"喂食机 {feeder_id}",
                            "ownership": "系统自动创建",
                            "status": "active",
                            "switch_status": "off",
                            "priority": "medium"
                        }
                    )
                    session.flush()  # 刷新以获取插入的记录
                    # 重新查询确认
                    device = session.query(Device).filter(Device.id == feeder_id).first()
                    if device:
                        logger.info(f"成功创建指定 id 的设备记录: id={device.id}, device_id={device.device_id}")
                    else:
                        raise Exception("设备创建后查询失败")
                except Exception as e:
                    logger.warning(f"无法创建指定 id 的设备记录，尝试使用自动 id: {e}")
                    # 如果无法创建指定 id 的设备，尝试使用 SQL 创建新设备（让数据库自动分配 id）
                    try:
                        # 使用 SQL 插入，让数据库自动分配 id
                        result = session.execute(
                            text("""
                                INSERT INTO devices (device_id, name, ownership, status, switch_status, priority, created_at, updated_at)
                                VALUES (:device_id, :name, :ownership, :status, :switch_status, :priority, NOW(), NOW())
                            """),
                            {
                                "device_id": f"feeder_{feeder_id}",
                                "name": f"喂食机 {feeder_id}",
                                "ownership": "系统自动创建",
                                "status": "active",
                                "switch_status": "off",
                                "priority": "medium"
                            }
                        )
                        session.flush()  # 刷新以获取插入的记录
                        # 获取自动生成的 id
                        device = session.query(Device).filter(Device.device_id == f"feeder_{feeder_id}").first()
                        if device:
                            logger.warning(f"使用自动生成的设备 id: {device.id} (原始 feeder_id: {feeder_id})")
                            feeder_id = device.id
                        else:
                            raise Exception("设备创建后查询失败")
                    except Exception as e2:
                        logger.error(f"创建设备记录失败: {e2}")
                        return jsonify({
                            "success": False,
                            "error": f"无法创建设备记录: {str(e2)}"
                        }), 500
            
            # 检查并确保批次记录存在（如果提供了 batch_id）
            if batch_id is not None:
                batch_id = ensure_batch_exists(session, batch_id, pool_id)
            
            # 创建对象（只传入 init=True 的字段）
            feeder_log = FeederLog(
                feeder_id=feeder_id,
                ts_utc=ts_utc,
                status=status  # status 有默认值，但可以传入
            )
            # 设置 init=False 的字段（通过属性赋值）
            if batch_id is not None:
                feeder_log.batch_id = batch_id
            if pool_id is not None:
                feeder_log.pool_id = pool_id
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
            
            logger.info(f"喂食机数据接收成功: feeder_id={feeder_id}, feed_amount_g={feed_amount_g}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": feeder_log.id,
                    "feeder_id": feeder_log.feeder_id,
                    "status": feeder_log.status
                },
                "timestamp": int(time.time() * 1000)
            }), 201
            
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
        "operator_id": "user001",
        "batch_id": 123,  // 可选
        "pool_id": "pool-001",  // 可选
        "action_type": "投料",
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
        if 'operator_id' not in data or 'action_type' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: operator_id, action_type"
            }), 400
        
        # 提取数据
        operator_id = data['operator_id']
        action_type = data['action_type']
        batch_id = data.get('batch_id')
        pool_id = data.get('pool_id')
        remarks = data.get('remarks')
        attachment_uri = data.get('attachment_uri')
        timestamp = data.get('timestamp')
        
        # 时间标准化
        if timestamp:
            ts_utc, ts_local = DataCleaningService.standardize_time(timestamp)
        else:
            ts_utc, ts_local = DataCleaningService.standardize_time(datetime.now())
        
        # 保存到数据库
        with db_session_factory() as session:
            # 检查并确保批次记录存在（如果提供了 batch_id）
            if batch_id is not None:
                batch_id = ensure_batch_exists(session, batch_id, pool_id)
            
            # 创建对象（只传入 init=True 的字段）
            operation_log = OperationLog(
                operator_id=operator_id,
                ts_utc=ts_utc,
                action_type=action_type
            )
            # 设置 init=False 的字段（通过属性赋值）
            if batch_id is not None:
                operation_log.batch_id = batch_id
            if pool_id is not None:
                operation_log.pool_id = pool_id
            if ts_local is not None:
                operation_log.ts_local = ts_local
            if remarks is not None:
                operation_log.remarks = remarks
            if attachment_uri is not None:
                operation_log.attachment_uri = attachment_uri
            
            session.add(operation_log)
            session.commit()
            
            logger.info(f"操作日志接收成功: operator_id={operator_id}, action_type={action_type}")
            
            return jsonify({
                "success": True,
                "data": {
                    "id": operation_log.id,
                    "operator_id": operation_log.operator_id,
                    "action_type": operation_log.action_type
                },
                "timestamp": int(time.time() * 1000)
            }), 201
            
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
            # 检查并确保批次记录存在（如果提供了 batch_id）
            if batch_id is not None:
                batch_id = ensure_batch_exists(session, batch_id, pool_id)
            
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
            }), 201
            
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
        
        # 确保批次存在
        if batch_id:
            ensure_batch_exists(db_session_factory(), batch_id, pond_id)
        
        # 创建 ShrimpStats 记录
        from japan_server.db_models.shrimp_stats import ShrimpStats
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
            }), 201
            
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
            from japan_server.db_models.shrimp_stats import ShrimpStats
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
                # 确保批次存在
                if batch_id:
                    ensure_batch_exists(session, batch_id, pool_id)
                
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

