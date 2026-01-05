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
from sqlalchemy.exc import ProgrammingError

# 取消模拟数据：移除 DataGeneratorService 的使用
# CameraService 延迟在端点内部导入，避免外部依赖影响启动
from config.settings import Config, SENSOR_TYPES
from services.sensor_service import SensorService
from services.ai_decision_service import AIDecisionService
from services.pond_service import PondService
from utils.auth import auth_required
from db_models import Session, Tool, Model, KnowledgeBase, KnowledgeDocument
from db_models.db_session import db_session_factory

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 配置日志
logger = logging.getLogger(__name__)


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
            
            for metric, readings in grouped_readings.items():
                # 先尝试直接匹配，再尝试小写匹配
                key = metric_map.get(metric, metric_map.get(metric.lower() if metric else "", metric.lower() if metric else ""))
                if key not in allowed_ids:
                    # 跳过未在配置中的传感器类型
                    logger.debug(f"跳过未配置的 metric: {metric} -> {key}")
                    continue
                
                # 获取该类型的阈值范围，用于过滤异常值
                sensor_config = next((s for s in SENSOR_TYPES if s["id"] == key), None)
                threshold = sensor_config["threshold"] if sensor_config else None
                
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
                    
                    # 数据验证：如果配置了阈值，过滤掉明显异常的值
                    # 注意：对于level类型，由于实际数据可能不在阈值范围内，使用更宽松的过滤
                    if threshold:
                        min_val, max_val = threshold
                        # 对于level类型，使用更宽松的容差（10倍范围），其他类型使用2倍
                        tolerance_multiplier = 10 if key == "level" else 2
                        tolerance = (max_val - min_val) * tolerance_multiplier
                        # 对于level，只过滤明显异常的值（负值或超大值）
                        if key == "level":
                            if val < 0 or val > 10:  # 液位不应该超过10米
                                logger.warning(f"过滤异常值: {metric} -> {key}, value={val}")
                                continue
                        else:
                            if val < min_val - tolerance or val > max_val + tolerance:
                                logger.warning(f"过滤异常值: {metric} -> {key}, value={val}, threshold={threshold}")
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
    
    Returns:
        JSON格式的设备状态数据，包含设备名称、状态、参数等信息
    """
    try:
        # 已取消模拟数据逻辑，设备状态无真实数据源则返回500
        logger.error("设备状态数据不可用，返回500")
        return jsonify({
            "success": False,
            "error": "设备状态数据不可用",
            "timestamp": datetime.now().isoformat()
        }), 500
    except Exception as e:
        logger.error(f"设备状态数据接口异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


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


@api_bp.route('/cameras/<int:camera_id>/status', methods=['GET'])
def get_camera_status(camera_id):
    """
    获取摄像头状态数据接口
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        JSON格式的摄像头状态数据
    """
    try:
        # 延迟导入，避免外部依赖导致应用无法启动
        from services.camera_service import CameraService
        # 从数据库获取摄像头状态数据
        camera_data = CameraService.get_camera_status(camera_id)
        if camera_data is None:
            logger.error(f"摄像头{camera_id}状态数据不可用，返回500")
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
        logger.error(f"摄像头{camera_id}状态获取失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/<int:camera_id>/image', methods=['GET'])
def get_camera_image(camera_id):
    """
    获取摄像头图片接口
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        JSON格式的摄像头图片数据
    """
    try:
        from services.camera_service import CameraService
        # 从数据库获取摄像头图片数据
        image_data = CameraService.get_camera_image(camera_id)
        if image_data is None:
            logger.error(f"摄像头{camera_id}图片数据不可用，返回500")
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
        logger.error(f"摄像头{camera_id}图片获取失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/cameras/<int:camera_id>/health', methods=['GET'])
def get_camera_health(camera_id):
    """
    获取摄像头健康状态接口
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        JSON格式的摄像头健康状态数据
    """
    try:
        from services.camera_service import CameraService
        # 从数据库获取摄像头健康状态数据
        health_data = CameraService.get_camera_health(camera_id)
        if health_data is None:
            logger.error(f"摄像头{camera_id}健康检查数据不可用，返回500")
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
        logger.error(f"摄像头{camera_id}健康检查失败: {str(e)}")
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