#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由蓝图
包含所有API端点的路由定义
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging
import time
import uuid
import random
from urllib.parse import unquote
from sqlalchemy.exc import ProgrammingError
from sqlalchemy import or_
from werkzeug.security import check_password_hash
import hashlib

# 取消模拟数据：移除 DataGeneratorService 的使用
# CameraService 延迟在端点内部导入，避免外部依赖影响启动
from config.settings import Config, SENSOR_TYPES
from services.sensor_service import SensorService
from services.ai_decision_service import AIDecisionService
from services.pond_service import PondService
from utils.auth import auth_required
from db_models import Session, Tool, Model, KnowledgeBase, KnowledgeDocument, Device, DeviceType, User
from db_models.db_session import db_session_factory

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 配置日志
logger = logging.getLogger(__name__)


def generate_device_id(device_type_category: str, session) -> str:
    """
    生成设备ID：{category}_{数字}
    例如：feeder_3445435, sensor_5656, camera_3798455
    
    Args:
        device_type_category: 设备类型类别（如：sensor, feeder, camera等）
        session: 数据库会话对象
    
    Returns:
        唯一的设备ID字符串
    """
    # 设备类型前缀映射
    category_prefix_map = {
        'sensor': 'sensor',
        'feeder': 'feeder',
        'camera': 'camera',
        'water_pump': 'water_pump',
        'air_blower': 'air_blower',
        'water_switch': 'water_switch',
        'solar_heater_pump': 'solar_heater_pump'
    }
    
    prefix = category_prefix_map.get(device_type_category, 'device')
    
    # 生成唯一ID（最多重试10次）
    max_retries = 10
    for _ in range(max_retries):
        # 使用随机数（6-8位数字）
        number = random.randint(100000, 99999999)  # 6-8位随机数
        device_id = f"{prefix}_{number}"
        
        # 检查是否已存在
        existing = session.query(Device).filter_by(device_id=device_id).first()
        if not existing:
            return device_id
    
    # 如果随机数都冲突，使用时间戳+随机数
    timestamp = int(time.time() * 1000) % 100000000  # 取后8位
    number = random.randint(1000, 9999)
    device_id = f"{prefix}_{timestamp}{number}"
    
    # 最后检查
    existing = session.query(Device).filter_by(device_id=device_id).first()
    if existing:
        # 如果还是冲突，使用UUID作为后备（去掉横线，取前12位）
        uuid_str = str(uuid.uuid4()).replace('-', '')[:12]
        device_id = f"{prefix}_{uuid_str}"
    
    return device_id


@api_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口
    验证用户名和密码，返回用户信息
    
    Request Body:
        {
            "username": "用户名",
            "password": "密码"
        }
    
    Returns:
        JSON格式的登录结果，包含用户信息
    """
    try:
        # 获取请求数据
        if not request.is_json:
            return jsonify({
                "code": 400,
                "msg": "请求格式错误，需要JSON格式",
                "data": {}
            }), 400
        
        data = request.get_json()
        username = data.get('username') or data.get('user_name')
        password = data.get('password') or data.get('pass_word')
        
        if not username or not password:
            return jsonify({
                "code": 400,
                "msg": "缺少用户名或密码",
                "data": {}
            }), 400
        
        # 从数据库查询用户
        with db_session_factory() as session:
            user = session.query(User).filter_by(username=username).first()
            
            if not user:
                logger.warning(f"登录失败：用户 {username} 不存在")
                return jsonify({
                    "code": 401,
                    "msg": "用户名或密码错误",
                    "data": {}
                }), 401
            
            # 检查用户状态
            if user.status and user.status.lower() == 'deactive':
                logger.warning(f"登录失败：用户 {username} 已被禁用")
                return jsonify({
                    "code": 403,
                    "msg": "用户已被禁用",
                    "data": {}
                }), 403
            
            # 验证密码（支持明文、MD5哈希和werkzeug哈希）
            password_match = False
            
            # 1. 尝试明文密码匹配
            if user.password_hash == password:
                password_match = True
            else:
                # 2. 尝试MD5哈希匹配
                password_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
                if user.password_hash == password_md5:
                    password_match = True
                else:
                    # 3. 尝试werkzeug密码哈希验证
                    try:
                        password_match = check_password_hash(user.password_hash, password)
                    except Exception as e:
                        logger.warning(f"密码哈希验证异常: {str(e)}")
            
            if not password_match:
                logger.warning(f"登录失败：用户 {username} 密码错误")
                return jsonify({
                    "code": 401,
                    "msg": "用户名或密码错误",
                    "data": {}
                }), 401
            
            # 生成JWT token（如果启用了JWT）
            import os
            enable_auth = os.getenv('ENABLE_AUTH', 'false').lower() in ('true', '1', 'yes')
            
            token = None
            if enable_auth:
                try:
                    from flask_jwt_extended import create_access_token
                    # 创建token，包含用户ID和角色信息
                    additional_claims = {"role": user.role}
                    token = create_access_token(
                        identity=user.user_id,
                        additional_claims=additional_claims
                    )
                except ImportError:
                    logger.warning("flask_jwt_extended 未安装，无法生成JWT token")
                except Exception as e:
                    logger.error(f"生成JWT token失败: {str(e)}")
            
            # 返回登录成功信息
            response_data = {
                "user_id": user.user_id,
                "user_name": user.username,
                "role": user.role,
            }
            
            if token:
                response_data["token"] = token
            
            logger.info(f"用户 {username} 登录成功")
            return jsonify({
                "code": 200,
                "msg": "登录成功",
                "data": response_data
            }), 200
            
    except Exception as e:
        logger.error(f"登录接口异常: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "msg": f"服务器内部错误: {str(e)}",
            "data": {}
        }), 500


@api_bp.route('/ai/decisions/recent', methods=['GET'])
def get_ai_decisions():
    """
    获取AI决策消息接口
    
    Returns:
        JSON格式的AI决策消息数据
    """
    try:
        # 从数据库获取AI决策消息
        decisions = AIDecisionService.get_recent_decisions()
        if not decisions:
            logger.error("AI决策消息为空或获取失败，返回500")
            return jsonify({
                "success": False,
                "error": "AI决策消息不可用",
                "timestamp": int(time.time() * 1000)
            }), 500

        return jsonify({
            "success": True,
            "data": decisions,
            "timestamp": int(time.time() * 1000),
            "count": len(decisions)
        }), 200
    except Exception as e:
        logger.error(f"AI决策消息获取异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }), 500


@api_bp.route('/sensors/realtime', methods=['GET'])
def get_sensor_data():
    """
    获取所有传感器的实时数据
    从 sensor_types 表中每个 metric 在 sensor_readings 表中相同 metric 值的最新 N 条记录
    
    Returns:
        JSON格式的传感器数据，包含所有传感器类型的历史数据点
    """
    try:
        # 从配置中获取每个 metric 的最新记录数
        limit = Config.SENSOR_REALTIME_LIMIT
        
        # 从数据库获取每个 metric 的最新 N 条记录
        grouped_readings = SensorService.get_latest_sensor_readings_by_metric(limit=limit)
        
        sensor_data = {}
        
        # 映射 metric 到接口ID（统一小写，支持大小写不敏感匹配）
        metric_map = {
            "temperature": "temperature",
            "ph": "ph",
            "do": "oxygen",  # dissolved oxygen
            "water_level": "level",
            "liquid_level": "level",
            "turbidity": "turbidity",
            "ammonia": "ammonia",
            "nitrite": "nitrite",
            "light": "light",
            "flow": "flow",
        }
        allowed_ids = {s["id"] for s in SENSOR_TYPES}
        
        # 如果有数据，处理数据
        if grouped_readings:
            # 转换为接口格式：每类型最多 limit 个点，包含timestamp/value/time
            from datetime import datetime as dtmod
            def parse_dt(s: str):
                if not s:
                    return dtmod.now()
                try:
                    return dtmod.fromisoformat(s)
                except Exception:
                    try:
                        return dtmod.strptime(s, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        return dtmod.now()
            
            for metric, metric_data in grouped_readings.items():
                # 先尝试直接匹配，再尝试小写匹配
                key = metric_map.get(metric, metric_map.get(metric.lower() if metric else "", metric.lower() if metric else ""))
                if key not in allowed_ids:
                    # 跳过未在配置中的传感器类型
                    logger.debug(f"跳过未配置的 metric: {metric} -> {key}")
                    continue
                
                # 从数据库获取该类型的阈值范围，用于过滤异常值
                readings = metric_data.get("readings", [])
                valid_min = metric_data.get("valid_min")
                valid_max = metric_data.get("valid_max")
                
                # 排序为时间升序，并截取最近 limit 条
                readings_sorted = sorted(readings, key=lambda r: parse_dt(r["recorded_at"]) if r.get("recorded_at") else dtmod.min)
                points = []
                for r in readings_sorted[-limit:]:
                    recorded_at = r.get("recorded_at")
                    if not recorded_at:
                        continue
                    d = parse_dt(recorded_at)
                    ts = int(d.timestamp() * 1000)
                    val = r.get("value")
                    if val is None:
                        continue
                    
                    # 单位转换：液位mm -> m（在验证之前转换，以便使用正确的阈值）
                    if metric and metric.lower() in ("water_level", "liquid_level") and key == "level":
                        try:
                            val = float(val) / 1000.0
                        except Exception:
                            pass
                    
                    # 数据验证：如果数据库配置了阈值，过滤掉明显异常的值
                    # 注意：对于level类型，由于实际数据可能不在阈值范围内，使用更宽松的过滤
                    if valid_min is not None and valid_max is not None:
                        # 对于level类型，使用更宽松的容差（10倍范围），其他类型使用2倍
                        tolerance_multiplier = 10 if key == "level" else 2
                        tolerance = (valid_max - valid_min) * tolerance_multiplier
                        # 对于level，只过滤明显异常的值（负值或超大值）
                        if key == "level":
                            if val < 0 or val > 10:  # 液位不应该超过10米
                                logger.warning(f"过滤异常值: {metric} -> {key}, value={val}")
                                continue
                        else:
                            if val < valid_min - tolerance or val > valid_max + tolerance:
                                logger.warning(f"过滤异常值: {metric} -> {key}, value={val}, valid_min={valid_min}, valid_max={valid_max}")
                                continue
                    
                    points.append({
                        "timestamp": ts,
                        "value": round(float(val), 2),
                        "time": d.strftime("%H:%M")
                    })
                
                # 如果该类型已有数据，合并（去重相同时间戳）
                if key in sensor_data:
                    # 合并并去重（按时间戳）
                    existing_points = {p["timestamp"]: p for p in sensor_data[key]}
                    for p in points:
                        if p["timestamp"] not in existing_points:
                            existing_points[p["timestamp"]] = p
                    sensor_data[key] = sorted(existing_points.values(), key=lambda x: x["timestamp"])
                else:
                    sensor_data[key] = points
        
        # 为所有配置的传感器类型填充数据（缺失的填充空数组）
        for s in SENSOR_TYPES:
            sensor_data.setdefault(s["id"], [])
        
        logger.info(f"传感器数据请求成功，返回{len(sensor_data)}个类型的实时数据，每个metric最多{limit}条记录")
        return jsonify({
            "success": True,
            "data": sensor_data,
            "timestamp": int(time.time() * 1000)
        }), 200
        
    except Exception as e:
        logger.error(f"传感器数据获取失败: {str(e)}", exc_info=True)
        # 即使出错，也返回空数据结构，避免前端报错
        sensor_data = {}
        for s in SENSOR_TYPES:
            sensor_data[s["id"]] = []
        return jsonify({
            "success": True,
            "data": sensor_data,
            "timestamp": int(time.time() * 1000),
            "warning": f"数据获取异常: {str(e)}"
        }), 200


@api_bp.route('/devices/status', methods=['GET'])
def get_device_status():
    """
    获取所有设备的状态信息
    从数据库 devices 表获取所有设备及其状态信息
    
    Returns:
        JSON格式的设备状态数据，包含设备名称、状态、参数等信息
    """
    try:
        # 从数据库获取设备状态
        from services.device_service import DeviceService
        devices_data = DeviceService.get_all_devices_status()
        
        logger.info(f"设备状态请求成功，返回{len(devices_data)}个设备的状态")
        return jsonify({
            "success": True,
            "data": devices_data,
            "timestamp": int(time.time() * 1000)
        }), 200
        
    except Exception as e:
        logger.error(f"设备状态数据获取失败: {str(e)}", exc_info=True)
        # 即使出错，也返回空数据结构，避免前端报错
        return jsonify({
            "success": True,
            "data": [],
            "timestamp": int(time.time() * 1000),
            "warning": f"数据获取异常: {str(e)}"
        }), 200


@api_bp.route('/location/data', methods=['GET'])
def get_location_data():
    """
    获取地理位置数据接口
    
    Returns:
        JSON格式的地理位置数据，包含养殖场各区域的位置信息
    """
    try:
        # 已取消模拟数据逻辑，地理位置数据无真实数据源则返回500
        logger.error("地理位置数据不可用，返回500")
        return jsonify({
            "success": False,
            "error": "地理位置数据不可用",
            "timestamp": datetime.now().isoformat()
        }), 500
    except Exception as e:
        logger.error(f"地理位置数据接口异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/list', methods=['GET'])
def get_camera_list():
    """
    获取所有摄像头设备列表
    
    Returns:
        JSON格式的摄像头列表，包含 id、name、location
    """
    try:
        from services.camera_service import CameraService
        # 从数据库获取摄像头列表
        camera_list = CameraService.get_camera_list()
        
        logger.info(f"摄像头列表请求成功，返回{len(camera_list)}个摄像头")
        return jsonify({
            "success": True,
            "data": camera_list
        }), 200
        
    except Exception as e:
        logger.error(f"获取摄像头列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/<int:device_id>/status', methods=['GET'])
def get_camera_status(device_id):
    """
    获取摄像头状态数据接口
    
    Args:
        device_id: 摄像头设备ID（devices.id）
        
    Returns:
        JSON格式的摄像头状态数据
    """
    try:
        # 延迟导入，避免外部依赖导致应用无法启动
        from services.camera_service import CameraService
        # 从数据库获取摄像头状态数据
        camera_data = CameraService.get_camera_status(device_id)
        if camera_data is None:
            logger.error(f"摄像头设备{device_id}状态数据不可用，返回500")
            return jsonify({
                "success": False,
                "error": "摄像头状态数据不可用",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        return jsonify({
            "success": True,
            "data": camera_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"摄像头设备{device_id}状态获取失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/<int:device_id>/image', methods=['GET'])
def get_camera_image(device_id):
    """
    获取摄像头图片接口
    
    Args:
        device_id: 摄像头设备ID（devices.id）
        
    Returns:
        JSON格式的摄像头图片数据
    """
    try:
        from services.camera_service import CameraService
        # 从数据库获取摄像头图片数据
        image_data = CameraService.get_camera_image(device_id)
        if image_data is None:
            logger.error(f"摄像头设备{device_id}图片数据不可用，返回500")
            return jsonify({
                "success": False,
                "error": "摄像头图片数据不可用",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        return jsonify({
            "success": True,
            "data": image_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"摄像头设备{device_id}图片获取失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/<int:device_id>/health', methods=['GET'])
def get_camera_health(device_id):
    """
    获取摄像头健康状态接口
    
    Args:
        device_id: 摄像头设备ID（devices.id）
        
    Returns:
        JSON格式的摄像头健康状态数据
    """
    try:
        from services.camera_service import CameraService
        # 从数据库获取摄像头健康状态数据
        health_data = CameraService.get_camera_health(device_id)
        if health_data is None:
            logger.error(f"摄像头设备{device_id}健康检查数据不可用，返回500")
            return jsonify({
                "success": False,
                "error": "摄像头健康检查数据不可用",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        return jsonify({
            "success": True,
            "data": health_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"摄像头设备{device_id}健康检查失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    
    Returns:
        系统健康状态信息
    """
    import time
    return jsonify({
        "status": "healthy",
        "service": Config.SERVICE_NAME,
        "version": Config.VERSION,
        "timestamp": int(time.time() * 1000)
    }), 200


@api_bp.route('/v1/get_pond_list', methods=['GET'])
def get_pond_list():
    """
    获取池塘列表
    从数据库获取所有池塘的基本信息
    
    Returns:
        JSON格式的池塘列表数据
    """
    try:
        # 从数据库获取真实数据
        pond_list = PondService.get_pond_list()
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": pond_list
        }), 200
            
    except Exception as e:
        logger.error(f"获取池塘列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": []
        }), 500


@api_bp.route('/v1/get_pond_detail', methods=['GET'])
def get_pond_detail():
    """
    获取池塘详细信息
    从数据库获取真实数据，包括池塘信息、传感器数据、批次信息等
    
    Returns:
        JSON格式的池塘详情数据
    """
    try:
        pond_id = request.args.get("pond_id")
        if not pond_id:
            return jsonify({
                "code": 400,
                "message": "缺少参数 pond_id",
                "data": None
            }), 400
        
        # 从数据库获取真实数据
        pond_detail = PondService.get_pond_detail(pond_id)
        
        if pond_detail:
            return jsonify({
                "code": 200,
                "message": "success",
                "data": pond_detail
            }), 200
        else:
            # 如果获取失败，返回错误信息
            return jsonify({
                "code": 404,
                "message": f"池塘 {pond_id} 不存在或数据获取失败",
                "data": None
            }), 404
            
    except Exception as e:
        logger.error(f"获取池塘详情失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@api_bp.route('/v1/update_pond_detail', methods=['POST'])
def update_pond_detail():
    """
    更新池塘详细信息
    支持部分或全部更新，包括池塘信息、传感器数据、环境数据、统计图像路径等
    
    Returns:
        JSON格式的更新结果
    """
    try:
        pond_id = request.args.get("pond_id") or (request.json.get("pond_id") if request.is_json else None)
        if not pond_id:
            return jsonify({
                "code": 400,
                "message": "缺少参数 pond_id",
                "data": None
            }), 400
        
        # 获取请求体数据
        if request.is_json:
            detail_data = request.json.get("detail", request.json)
        else:
            detail_data = request.form.to_dict()
            # 尝试解析 JSON 字符串
            if "detail" in detail_data:
                import json
                try:
                    detail_data = json.loads(detail_data["detail"])
                except json.JSONDecodeError:
                    detail_data = {}
        
        if not detail_data:
            return jsonify({
                "code": 400,
                "message": "缺少更新数据",
                "data": None
            }), 400
        
        # 调用服务更新数据
        success, message, updated_data = PondService.update_pond_detail(pond_id, detail_data)
        
        if success:
            return jsonify({
                "code": 200,
                "message": message,
                "data": updated_data
            }), 200
        else:
            status_code = 400 if "不存在" in message else 500
            return jsonify({
                "code": status_code,
                "message": message,
                "data": updated_data
            }), status_code
            
    except Exception as e:
        logger.error(f"更新池塘详情失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@api_bp.route('/v1/get_session_list', methods=['GET'])
@auth_required
def get_session_list(user_id, role):
    """
    获取会话列表
    根据用户ID获取该用户的所有会话
    
    Args:
        user_id: 用户ID（从认证装饰器获取）
        role: 用户角色（从认证装饰器获取）
    
    Returns:
        JSON格式的会话列表数据
    """
    try:
        # 从数据库查询该用户的所有会话，按创建时间倒序
        with db_session_factory() as session:
            session_list = session.query(Session).filter_by(
                user_id=user_id
            ).order_by(Session.create_at.desc()).all()
            
            # 构建返回数据
            data = [
                {
                    "session_name": s.session_name,
                    "session_id": s.session_id,
                    "timestamp": int(s.create_at.timestamp()) if s.create_at else 0
                }
                for s in session_list
            ]
        
        response = {
            "code": 200,
            "msg": "success",
            "data": data
        }
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "msg": f"服务器内部错误: {str(e)}",
            "data": []
        }), 500


@api_bp.route('/v1/get_tool_list', methods=['GET'])
@auth_required
def get_tool_list(user_id, role):
    """
    获取工具和模型列表
    返回所有可用的工具和模型信息
    
    Args:
        user_id: 用户ID（从认证装饰器获取）
        role: 用户角色（从认证装饰器获取）
    
    Returns:
        JSON格式的工具和模型列表数据
    """
    try:
        with db_session_factory() as session:
            # 查询工具列表
            tools_query = session.query(Tool).filter_by(
                ownership='public'  # 或者根据用户权限过滤
            )
            
            # 如果用户是管理员，也可以获取私有工具
            if role in ['admin', 'super_admin']:
                tools_query = session.query(Tool)
            
            tools = tools_query.all()
            
            tool_list = [
                {
                    "tool_id": tool.tool_id,
                    "tool_name": tool.name,
                    "description": tool.description,
                    "status": "activate",  # 可以根据实际需求设置
                    "perm": tool.ownership
                }
                for tool in tools
            ]
            
            # 查询模型列表
            models_query = session.query(Model).filter_by(
                perm='public'  # 或者根据用户权限过滤
            )
            
            # 如果用户是管理员，也可以获取私有模型
            if role in ['admin', 'super_admin']:
                models_query = session.query(Model)
            
            models = models_query.all()
            
            model_list = [
                {
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "description": model.description,
                    "status": model.status,
                    "perm": model.perm
                }
                for model in models
            ]
        
        data = {
            "model_list": model_list,
            "tool_list": tool_list
        }
        
        response = {
            "code": 200,
            "msg": "success",
            "data": data
        }
        return jsonify(response), 200
        
    except ProgrammingError as e:
        # 如果表不存在，返回模拟数据（与原项目保持一致）
        if "doesn't exist" in str(e):
            logger.info("数据库表不存在，返回模拟数据")
            tool_mock = [
                {"tool_id": "60dc063e-b2ee-4ec2-b5ff-8bb9e0331d61", "tool_name": "文件分析", "description": "用于分析指定路径中的文件内容", "status": "activate", "perm": "public"},
                {"tool_id": "fa5d4e87-8f47-44a4-b525-986726004e47", "tool_name": "科学计算器", "description": "用于分析并计算复杂的科学工具", "status": "activate", "perm": "private"},
            ]
            model_mock = [
                {"model_id": "2bf21219-0a53-485b-835e-b5e71b9e4185", "model_name": "gpt-4o", "description": "标准模型", "status": "activate", "perm": "public"},
                {"model_id": "81a0678e-9de3-45ca-99b7-60b19cf975f6", "model_name": "gpt-4o-mini", "description": "轻量模型", "status": "activate", "perm": "private"},
                {"model_id": "81a0678e-9de3-45ca-99b7-60b19cf975f6", "model_name": "gpt-5", "description": "先进模型", "status": "activate", "perm": "private"},
            ]
            data = {
                "model_list": model_mock,
                "tool_list": tool_mock
            }
            response = {
                "code": 200,
                "msg": "success",
                "data": data
            }
            return jsonify(response), 200
        else:
            raise
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "msg": f"服务器内部错误: {str(e)}",
            "data": {
                "model_list": [],
                "tool_list": []
            }
        }), 500


@api_bp.route('/v1/get_knowledge_base_list', methods=['GET'])
@auth_required
def get_knowledge_base_list(user_id, role):
    """
    获取知识库列表
    返回所有知识库及其文档列表
    
    Args:
        user_id: 用户ID（从认证装饰器获取）
        role: 用户角色（从认证装饰器获取）
    
    Returns:
        JSON格式的知识库列表数据
    """
    try:
        with db_session_factory() as session:
            # 查询所有知识库
            knowledge_bases = session.query(KnowledgeBase).all()
            
            # 构建返回数据
            data = []
            for kb in knowledge_bases:
                # 查询该知识库的所有文档
                documents = session.query(KnowledgeDocument).filter_by(
                    knowledge_base_id=kb.knowledge_base_id
                ).all()
                
                document_list = [doc.document_name for doc in documents]
                
                kb_data = {
                    "knowledge_base_name": kb.knowledge_base_name,
                    "knowledge_base_id": kb.knowledge_base_id,
                    "document_list": document_list
                }
                data.append(kb_data)
        
        response = {
            "code": 200,
            "msg": "success",
            "data": data
        }
        return jsonify(response), 200
        
    except ProgrammingError as e:
        # 如果表不存在，返回模拟数据（与原项目保持一致）
        if "doesn't exist" in str(e):
            logger.info("数据库表不存在，返回模拟数据")
            mock = [
                {
                    "knowledge_base_name": "陆上养殖",
                    "knowledge_base_id": "25241d69-33fd-465d-8fd1-18d34865248c",
                    "document_list": [
                        "2025_06_27.txt",
                        "2025_07_08.txt",
                        "2025_07_14.txt",
                        "2025_06_16.txt",
                        "2025_06_24.txt",
                        "2025_07_21.txt",
                        "2025_07_07.txt",
                        "2025_06_12.txt",
                        "循环水南美白对虾养殖系统设计及操作手册张驰v3.0.pdf",
                        "2025_07_25.txt",
                        "2025_07_17.txt",
                        "2025_07_15.txt",
                        "2025_07_03.txt",
                        "2025_07_24.txt",
                        "2025_06_17.txt",
                        "2025_07_16.txt",
                        "2025_07_23.txt",
                        "2025_06_23.txt",
                        "2025_06_20.txt",
                        "2025_07_09.txt",
                        "2025_06_25.txt",
                        "2025_07_11.txt",
                        "2025_06_30.txt",
                        "2025_07_10.txt",
                        "2025_07_18.txt",
                        "2025_07_01.txt",
                        "2025_07_04.txt",
                        "2025_07_02.txt",
                        "2025_07_22.txt"
                    ],
                },
            ]
            response = {
                "code": 200,
                "msg": "success",
                "data": mock
            }
            return jsonify(response), 200
        else:
            raise
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "msg": f"服务器内部错误: {str(e)}",
            "data": []
        }), 500

#设备管理接口
@api_bp.route('/get_device_type_list', methods=['GET'])
def get_device_type_list():
    """
    获取设备类型列表（轻量接口，只返回id、category、name）
    
    Returns:
        JSON格式的设备类型列表数据
    """
    try:        
        with db_session_factory() as session:
            device_types = session.query(DeviceType).order_by(DeviceType.id).all()
            
            device_type_list = []
            for dt in device_types:
                type_info = {
                    "id": dt.id,
                    "category": dt.category,
                    "name": dt.name
                }
                device_type_list.append(type_info)
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": device_type_list
        }), 200
        
    except Exception as e:
        logger.error(f"获取设备类型列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": []
        }), 500

@api_bp.route('/get_sensor_type_list', methods=['GET'])
def get_sensor_type_list():
    """
    获取传感器类型列表（轻量接口，只返回id和type_name）
    
    Returns:
        JSON格式的传感器类型列表数据
    """
    try:
        from db_models.sensor_type import SensorType
        
        with db_session_factory() as session:
            sensor_types = session.query(SensorType).order_by(SensorType.id).all()
            
            sensor_type_list = []
            for st in sensor_types:
                type_info = {
                    "id": st.id,
                    "type_name": st.type_name
                }
                sensor_type_list.append(type_info)
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": sensor_type_list
        }), 200
        
    except Exception as e:
        logger.error(f"获取传感器类型列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": []
        }), 500

@api_bp.route('/get_device_list', methods=['GET'])
def get_device_list():
    """
    获取设备列表（支持分页和搜索）
    返回设备完整信息，传感器类型信息放在info字段，其他设备类型从device_specific_config获取
    
    Query Parameters:
        status: 设备状态（online/offline，可选）
        pond_id: 养殖池ID（可选）
        control_mode: 控制权限模式（manual_only/ai_only/hybrid，可选）
        category: 设备类别（sensor/feeder/camera等，可选）
        search: 搜索关键词（按设备名称或device_id模糊搜索，可选）
        page: 当前页码（默认1）
        page_size: 每页数量（默认5，最大100）
    
    Returns:
        JSON格式的设备列表数据，包含：
        - items: 设备列表（每个设备包含device表的所有字段 + info字段）
        - pagination: 分页信息
    """
    try:
        from db_models.sensor_type import SensorType
        
        # 获取查询参数
        status = request.args.get('status')  # online 或 offline
        pond_id = request.args.get('pond_id', type=int)
        control_mode = request.args.get('control_mode')  # manual_only, ai_only, hybrid
        category = request.args.get('category')  # sensor, feeder, camera, water_pump, air_blower等
        search = request.args.get('search')  # 搜索关键词（设备名称或device_id）
        
        # 修复编码问题：处理客户端错误编码的情况（容错处理）
        original_search = search  # 保存原始值用于日志
        if search:
            try:
                # 检查是否是 Latin-1 错误解码的 UTF-8 字节
                # 特征：包含 Latin-1 范围外的字符（>127），且可以重新编码为 UTF-8
                if any(ord(c) > 127 for c in search):
                    try:
                        # 将 Latin-1 字符串重新编码为字节，然后按 UTF-8 解码
                        fixed_search = search.encode('latin-1').decode('utf-8')
                        # 验证修复后的字符串是否包含中文字符（或其他合理的 Unicode 字符）
                        if any('\u4e00' <= c <= '\u9fff' for c in fixed_search):
                            search = fixed_search
                            logger.info(f"修复搜索参数编码: '{original_search}' -> '{search}'")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # 编码修复失败，尝试从原始 query_string 重新解析
                        try:
                            raw_query = request.query_string.decode('latin-1')
                            for param in raw_query.split('&'):
                                if param.startswith('search='):
                                    encoded_value = param[7:]  # 去掉 'search='
                                    # 尝试 URL 解码
                                    decoded = unquote(encoded_value, encoding='utf-8')
                                    if decoded != search and any('\u4e00' <= c <= '\u9fff' for c in decoded):
                                        search = decoded
                                        logger.info(f"从 query_string 重新解析搜索参数: '{original_search}' -> '{search}'")
                                        break
                        except Exception:
                            pass  # 如果所有修复方法都失败，使用原始值
            except Exception as e:
                logger.warning(f"搜索参数编码处理异常: {e}, 使用原始值: {search}")
        
        # 记录最终使用的搜索参数（如果是修复后的，会显示正确的中文）
        if search:
            logger.info(f"设备列表搜索请求 - 搜索关键词: '{search}'")
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 5, type=int)
        
        # 参数验证
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 5
        if page_size > 100:  # 限制最大每页数量
            page_size = 100
        
        with db_session_factory() as session:
            # 构建查询（过滤已软删除的设备）
            query = session.query(Device).filter(Device.is_deleted == False)
            
            # 如果需要按category筛选，需要join device_types表
            if category:
                query = query.join(DeviceType).filter(DeviceType.category == category)
            
            # 应用其他过滤条件
            if status:
                query = query.filter(Device.status == status)
            if pond_id:
                query = query.filter(Device.pond_id == pond_id)
            if control_mode:
                query = query.filter(Device.control_mode == control_mode)
            
            # 搜索功能：按设备名称或device_id模糊搜索
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        Device.name.like(search_pattern),
                        Device.device_id.like(search_pattern)
                    )
                )
            
            # 计算总数（在分页之前）
            total = query.count()
            
            # 计算总页数
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 分页查询（按创建时间倒序排列）
            devices = query.order_by(Device.created_at.desc())\
                          .limit(page_size)\
                          .offset(offset)\
                          .all()
            
            # 批量查询设备类型信息
            device_type_ids = [d.device_type_id for d in devices if d.device_type_id]
            device_types = {}
            if device_type_ids:
                types = session.query(DeviceType).filter(DeviceType.id.in_(device_type_ids)).all()
                device_types = {dt.id: dt for dt in types}
            
            # 批量查询传感器类型信息（仅对传感器设备）
            sensor_type_ids = [d.sensor_type_id for d in devices if d.sensor_type_id]
            sensor_types_dict = {}
            if sensor_type_ids:
                sensor_types = session.query(SensorType).filter(SensorType.id.in_(sensor_type_ids)).all()
                sensor_types_dict = {st.id: st for st in sensor_types}
            
            # 构建返回数据
            device_list = []
            for device in devices:
                device_type = device_types.get(device.device_type_id) if device.device_type_id else None
                device_category = device_type.category if device_type else None
                
                # 构建基础设备信息（device表的所有字段）
                device_info = {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name,
                    "description": device.description,
                    "ownership": device.ownership,
                    "device_type_id": device.device_type_id,
                    "sensor_type_id": device.sensor_type_id,
                    "device_type_name": device_type.name if device_type else None,
                    "device_category": device_category,
                    "model": device.model,
                    "manufacturer": device.manufacturer,
                    "serial_number": device.serial_number,
                    "location": device.location,
                    "pond_id": device.pond_id,
                    "connection_info": device.connection_info,
                    "device_specific_config": device.device_specific_config,
                    "tags": device.tags,
                    "status": device.status,
                    "control_mode": device.control_mode,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None,
                }
                
                # 构建info字段
                info = None
                if device_category == 'sensor' and device.sensor_type_id:
                    # 传感器设备：从sensor_types表获取传感器类型信息
                    sensor_type = sensor_types_dict.get(device.sensor_type_id)
                    if sensor_type:
                        info = {
                            "sensor_type_id": sensor_type.id,
                            "sensor_type_name": sensor_type.type_name,
                            "metric": sensor_type.metric,
                            "unit": sensor_type.unit,
                            "valid_min": float(sensor_type.valid_min) if sensor_type.valid_min is not None else None,
                            "valid_max": float(sensor_type.valid_max) if sensor_type.valid_max is not None else None,
                            "description": sensor_type.description,
                        }
                else:
                    # 其他设备：直接使用device_specific_config
                    info = device.device_specific_config
                
                device_info["info"] = info
                device_list.append(device_info)
            
            # 构建分页信息
            pagination = {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "items": device_list,
                "pagination": pagination
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@api_bp.route('/device', methods=['POST'])
def create_device():
    """
    创建新设备（统一设备表架构）
    
    所有设备都存储在统一的devices表中。
    - 如果是传感器设备（device_type.category='sensor'），必须提供sensor_type_id
    - 其他设备的特有配置统一存储在device_specific_config字段中
    
    必填字段（后端必须接收）：
        - name: 设备名称
        - device_type_id: 设备类型ID
        - sensor_type_id: 传感器类型ID（仅当设备类型为sensor时必填）
        - pond_id: 养殖池ID
        - location: 设备安装位置
        - control_mode: 权限分配（manual_only/ai_only/hybrid）
    
    可选字段：
        - ownership: 设备归属
        - description: 设备描述
        - model: 设备型号
        - manufacturer: 制造商
        - serial_number: 序列号（唯一）
        - connection_info: 设备连接信息（JSON格式）
        - status: 设备状态（默认：online）
        - device_specific_config: 设备专属配置（JSON格式）
        - tags: 标签（逗号分隔）
    
    Returns:
        JSON格式的创建结果
    """
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "请求必须是JSON格式",
                "data": None
            }), 400
        
        data = request.get_json()
        
        # 验证必填字段
        required_fields = {
            'name': '设备名称',
            'device_type_id': '设备类型ID',
            'pond_id': '养殖池ID',
            'location': '设备安装位置',
            'control_mode': '权限分配'
        }
        
        for field, field_name in required_fields.items():
            if not data.get(field):
                return jsonify({
                    "code": 400,
                    "message": f"缺少必填字段: {field_name}（{field}）",
                    "data": None
                }), 400
        
        # 验证 control_mode 的值
        valid_control_modes = ['manual_only', 'ai_only', 'hybrid']
        if data['control_mode'] not in valid_control_modes:
            return jsonify({
                "code": 400,
                "message": f"control_mode 必须是以下值之一: {', '.join(valid_control_modes)}",
                "data": None
            }), 400
        
        with db_session_factory() as session:
            # 验证设备类型是否存在
            device_type = session.query(DeviceType).filter_by(
                id=data['device_type_id']
            ).first()
            if not device_type:
                return jsonify({
                    "code": 400,
                    "message": f"设备类型ID {data['device_type_id']} 不存在",
                    "data": None
                }), 400
            
            # 如果是传感器设备，sensor_type_id是必填的
            sensor_type_id = data.get('sensor_type_id')
            if device_type.category == 'sensor':
                if not sensor_type_id:
                    return jsonify({
                        "code": 400,
                        "message": "传感器设备必须提供 sensor_type_id",
                        "data": None
                    }), 400
                
                from db_models.sensor_type import SensorType
                sensor_type = session.query(SensorType).filter_by(id=sensor_type_id).first()
                if not sensor_type:
                    return jsonify({
                        "code": 400,
                        "message": f"传感器类型ID {sensor_type_id} 不存在",
                        "data": None
                    }), 400
            else:
                # 非传感器设备，sensor_type_id应该为空
                sensor_type_id = None
            
            # 验证 pond_id 是否存在
            from db_models.pond import Pond
            pond = session.query(Pond).filter_by(id=data['pond_id']).first()
            if not pond:
                return jsonify({
                    "code": 400,
                    "message": f"养殖池ID {data['pond_id']} 不存在",
                    "data": None
                }), 400
            
            # 生成唯一的device_id（业务格式：{category}_{数字}）
            # 例如：feeder_3445435, sensor_5656, camera_3798455
            device_id = generate_device_id(device_type.category, session)
            
            # 检查序列号是否已存在（如果提供了）
            if data.get('serial_number'):
                existing_serial = session.query(Device).filter_by(
                    serial_number=data['serial_number']
                ).first()
                if existing_serial:
                    return jsonify({
                        "code": 400,
                        "message": f"序列号 {data['serial_number']} 已存在",
                        "data": None
                    }), 400
            
            # 处理JSON字段：如果没有提供，使用空JSON {}
            connection_info = data.get('connection_info')
            if connection_info is None:
                connection_info = {}
            
            device_specific_config = data.get('device_specific_config')
            if device_specific_config is None:
                device_specific_config = {}
            
            # 创建设备对象（所有设备都存储在devices表）
            device = Device(
                device_id=device_id,
                name=data['name'],
                ownership=data.get('ownership'),  # 可选字段
                device_type_id=data['device_type_id'],
                sensor_type_id=sensor_type_id,  # 仅传感器设备有值，其他为None
                pond_id=data['pond_id'],  # 必填字段
                location=data['location'],  # 必填字段
                model=data.get('model'),
                manufacturer=data.get('manufacturer'),
                serial_number=data.get('serial_number'),
                connection_info=connection_info,  # JSON字段，没有提供则为空JSON
                status=data.get('status', 'online'),  # 默认online
                control_mode=data['control_mode'],  # 必填字段
                device_specific_config=device_specific_config,  # JSON字段，没有提供则为空JSON
                tags=data.get('tags'),
                description=data.get('description'),
            )
            
            session.add(device)
            session.commit()
            
            logger.info(f"成功创建设备: {device_id} - {data['name']}")
            
            return jsonify({
                "code": 200,
                "message": "设备创建成功",
                "data": {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name
                }
            }), 200
            
    except ValueError as e:
        logger.error(f"创建设备失败（数据格式错误）: {str(e)}")
        return jsonify({
            "code": 400,
            "message": f"数据格式错误: {str(e)}",
            "data": None
        }), 400
    except Exception as e:
        logger.error(f"创建设备失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500

@api_bp.route('/device/<device_id>', methods=['PUT'])
def update_device(device_id):
    """
    更新设备信息（支持部分更新）
    
    只允许更新以下字段：
    - name: 设备名称
    - description: 设备描述
    - location: 设备位置
    - status: 设备状态（online/offline）
    - device_specific_config: 设备专属配置JSON
    - connection_info: 设备连接信息JSON（包含连接地址、账户名、密码等）
    - pond_id: 养殖池ID
    - control_mode: 权限分配（manual_only/ai_only/hybrid）
    
    Args:
        device_id: 设备ID（可以是数据库主键id或device_id业务ID）
    
    Request Body:
        支持部分更新，只需提供要更新的字段
        {
            "name": "更新后的设备名称",
            "description": "更新后的设备描述",
            "location": "更新后的设备位置",
            "status": "online",
            "connection_info": {
                "url": "http://192.168.1.100",
                "username": "admin",
                "password": "password"
            },
            "device_specific_config": {
                "sampling_rate": 60,
                "alert_threshold": 5.0
            },
            "pond_id": 1,
            "control_mode": "hybrid"
        }
    
    Returns:
        JSON格式的更新结果
    """
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "请求必须是JSON格式",
                "data": None
            }), 400
        
        data = request.get_json()
        
        # 检查请求体是否为空
        if not data:
            return jsonify({
                "code": 400,
                "message": "请求体不能为空",
                "data": None
            }), 400
        
        with db_session_factory() as session:
            # 查找设备（排除已软删除的设备）
            try:
                device_id_int = int(device_id)
                device = session.query(Device).filter(
                    Device.id == device_id_int,
                    Device.is_deleted == False
                ).first()
            except ValueError:
                device = session.query(Device).filter(
                    Device.device_id == device_id,
                    Device.is_deleted == False
                ).first()
            
            if not device:
                return jsonify({
                    "code": 404,
                    "message": f"设备 {device_id} 不存在或已删除",
                    "data": None
                }), 404
            
            # 只允许更新以下字段
            allowed_fields = ['description', 'name', 'location', 'status', 'device_specific_config', 'connection_info', 'pond_id', 'control_mode']
            
            # 检查是否有不允许更新的字段
            invalid_fields = [field for field in data.keys() if field not in allowed_fields]
            if invalid_fields:
                return jsonify({
                    "code": 400,
                    "message": f"不允许更新以下字段: {', '.join(invalid_fields)}。只允许更新: {', '.join(allowed_fields)}",
                    "data": None
                }), 400
            
            # 验证name字段（如果提供了）
            if 'name' in data:
                name = data['name']
                if not name or not isinstance(name, str):
                    return jsonify({
                        "code": 400,
                        "message": "name 必须是非空字符串",
                        "data": None
                    }), 400
                if len(name) < 1 or len(name) > 128:
                    return jsonify({
                        "code": 400,
                        "message": "name 长度必须在1-128个字符之间",
                        "data": None
                    }), 400
            
            # 验证status字段（如果提供了）
            if 'status' in data:
                if data['status'] not in ['online', 'offline']:
                    return jsonify({
                        "code": 400,
                        "message": "status 必须是 'online' 或 'offline'",
                        "data": None
                    }), 400
            
            # 验证control_mode字段（如果提供了）
            if 'control_mode' in data:
                if data['control_mode'] not in ['manual_only', 'ai_only', 'hybrid']:
                    return jsonify({
                        "code": 400,
                        "message": "control_mode 必须是 'manual_only', 'ai_only' 或 'hybrid'",
                        "data": None
                    }), 400
            
            # 验证pond_id字段（如果提供了）
            if 'pond_id' in data and data['pond_id'] is not None:
                from db_models.pond import Pond
                pond = session.query(Pond).filter_by(id=data['pond_id']).first()
                if not pond:
                    return jsonify({
                        "code": 400,
                        "message": f"养殖池ID {data['pond_id']} 不存在",
                        "data": None
                    }), 400
            
            # 处理JSON字段：验证类型并处理空值
            if 'connection_info' in data:
                if data['connection_info'] is None:
                    data['connection_info'] = {}
                elif not isinstance(data['connection_info'], dict):
                    return jsonify({
                        "code": 400,
                        "message": "connection_info 必须是JSON对象",
                        "data": None
                    }), 400
            
            if 'device_specific_config' in data:
                if data['device_specific_config'] is None:
                    data['device_specific_config'] = {}
                elif not isinstance(data['device_specific_config'], dict):
                    return jsonify({
                        "code": 400,
                        "message": "device_specific_config 必须是JSON对象",
                        "data": None
                    }), 400
            
            # 更新允许的字段
            for field in allowed_fields:
                if field in data:
                    setattr(device, field, data[field])
            
            session.commit()
            
            logger.info(f"成功更新设备: {device_id} - {device.name}")
            
            return jsonify({
                "code": 200,
                "message": "设备更新成功",
                "data": {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name
                }
            }), 200
            
    except ValueError as e:
        logger.error(f"更新设备失败（数据格式错误）: {str(e)}")
        return jsonify({
            "code": 400,
            "message": f"数据格式错误: {str(e)}",
            "data": None
        }), 400
    except Exception as e:
        logger.error(f"更新设备失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500

@api_bp.route('/device/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """
    删除设备（软删除，设置is_deleted字段）
    
    Args:
        device_id: 设备ID（可以是数据库主键id或device_id UUID）
    
    Returns:
        JSON格式的删除结果
    """
    try:
        with db_session_factory() as session:
            # 查找设备
            try:
                device_id_int = int(device_id)
                device = session.query(Device).filter(Device.id == device_id_int).first()
            except ValueError:
                device = session.query(Device).filter(Device.device_id == device_id).first()
            
            if not device:
                return jsonify({
                    "code": 404,
                    "message": f"设备 {device_id} 不存在",
                    "data": None
                }), 404
            
            if device.is_deleted:
                return jsonify({
                    "code": 400,
                    "message": f"设备 {device_id} 已被删除",
                    "data": None
                }), 400
            
            # 软删除：设置is_deleted为True
            device.is_deleted = True
            device.status = 'offline'
            
            session.commit()
            
            logger.info(f"成功删除设备: {device_id} - {device.name}")
            
            return jsonify({
                "code": 200,
                "message": "设备删除成功",
                "data": {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name
                }
            }), 200
            
    except Exception as e:
        logger.error(f"删除设备失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500