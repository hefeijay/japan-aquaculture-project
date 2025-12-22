#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息队列管理API路由
提供消息队列的CRUD操作和管理功能
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
import logging
import time

from japan_server.services.message_queue_service import message_queue_service

# 创建蓝图
message_queue_bp = Blueprint('message_queue', __name__, url_prefix='/api/messages')

# 配置日志
logger = logging.getLogger(__name__)


@message_queue_bp.route('/', methods=['POST'])
def create_message():
    """
    接收客户端推送的消息并存储到消息队列
    
    Request Body:
        {
            "message_type": "text|json|notification|command|data|general|sensor_data|user_input|system_alert",
            "content": "消息内容",
            "priority": "low|normal|high|urgent" 或 0-10的整数 (可选),
            "source": "消息来源" (可选),
            "metadata": {} (可选)
        }
    
    Returns:
        JSON格式的响应，包含操作结果和消息ID
    """
    try:
        # 获取请求数据
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "请求必须是JSON格式",
                "timestamp": int(time.time() * 1000)
            }), 400
            
        message_data = request.get_json()
        
        if not message_data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "timestamp": int(time.time() * 1000)
            }), 400
        
        # 调用服务层创建消息
        success, message, message_id = message_queue_service.create_message(message_data)
        
        if success:
            logger.info(f"成功接收并存储客户端消息: {message_id}")
            return jsonify({
                "success": True,
                "message": message,
                "message_id": message_id,
                "timestamp": int(time.time() * 1000)
            }), 201
        else:
            logger.warning(f"消息存储失败: {message}")
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": int(time.time() * 1000)
            }), 400
            
    except Exception as e:
        logger.error(f"处理消息推送请求时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"创建消息失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/', methods=['GET'])
def get_pending_messages():
    """
    获取待处理的消息列表
    
    Query Parameters:
        limit: 返回消息数量限制 (默认10，最大100)
        
    Returns:
        JSON格式的待处理消息列表
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', 10, type=int)
        if limit <= 0 or limit > 100:
            limit = 10
            
        success, message, messages = message_queue_service.get_pending_messages(limit)
        
        return jsonify({
            "success": True,
            "message": message,
            "data": messages,
            "count": len(messages),
            "timestamp": int(time.time() * 1000)
        }), 200
        
    except Exception as e:
        logger.error(f"获取待处理消息时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取消息列表失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/<string:message_id>', methods=['GET'])
def get_message_status(message_id):
    """
    获取指定消息的状态信息
    
    Args:
        message_id: 消息ID
        
    Returns:
        JSON格式的消息状态信息
    """
    try:
        success, message, status_data = message_queue_service.get_message_status(message_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "data": status_data,
                "timestamp": int(time.time() * 1000)
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": int(time.time() * 1000)
            }), 404
            
    except Exception as e:
        logger.error(f"获取消息状态时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取消息状态失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/<string:message_id>/status', methods=['PUT'])
def update_message_status(message_id):
    """
    更新消息状态
    
    Args:
        message_id: 消息ID
        
    Request Body:
        {
            "status": "pending|processing|completed|failed|expired",
            "error_message": "错误信息" (可选)
        }
        
    Returns:
        JSON格式的更新结果
    """
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "请求必须是JSON格式",
                "timestamp": int(time.time() * 1000)
            }), 400
            
        update_data = request.get_json()
        
        if not update_data or 'status' not in update_data:
            return jsonify({
                "success": False,
                "error": "缺少必需的status字段",
                "timestamp": int(time.time() * 1000)
            }), 400
            
        # 验证状态值
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'expired']
        if update_data['status'] not in valid_statuses:
            return jsonify({
                "success": False,
                "error": f"无效的状态值，支持的状态: {', '.join(valid_statuses)}",
                "timestamp": int(time.time() * 1000)
            }), 400
            
        status = update_data['status']
        error_message = update_data.get('error_message')
        
        success, message = message_queue_service.update_message_status(
            message_id, status, error_message
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "timestamp": int(time.time() * 1000)
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": int(time.time() * 1000)
            }), 400
            
    except Exception as e:
        logger.error(f"更新消息状态时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"更新消息状态失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/statistics', methods=['GET'])
def get_queue_statistics():
    """
    获取消息队列统计信息
    
    Returns:
        JSON格式的队列统计数据，包含：
        - 总消息数量
        - 各状态消息数量统计
        - 各类型消息数量统计
        - 队列健康状况指标
    """
    try:
        success, message, stats = message_queue_service.get_queue_statistics()
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "data": stats,
                "timestamp": int(time.time() * 1000)
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": int(time.time() * 1000)
            }), 500
            
    except Exception as e:
        logger.error(f"获取队列统计时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取队列统计失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/cleanup', methods=['POST'])
def cleanup_expired_messages():
    """
    清理过期的消息
    
    Request Body (可选):
        {
            "max_age_hours": 24  # 清理超过指定小时数的消息，默认24小时
        }
        
    Returns:
        JSON格式的清理结果
    """
    try:
        # 获取清理参数
        max_age_hours = 24  # 默认24小时
        if request.is_json:
            data = request.get_json()
            if data and 'max_age_hours' in data:
                max_age_hours = data['max_age_hours']
        
        # 这里可以扩展message_queue_service来支持清理功能
        # 目前返回一个占位响应
        return jsonify({
            "success": True,
            "message": "清理功能待实现",
            "cleaned_count": 0,
            "timestamp": int(time.time() * 1000)
        }), 200
        
    except Exception as e:
        logger.error(f"清理过期消息时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"清理过期消息失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500


@message_queue_bp.route('/health', methods=['GET'])
def get_queue_health():
    """
    获取消息队列健康状态
    
    Returns:
        JSON格式的队列健康状态信息
    """
    try:
        # 获取统计信息来评估健康状态
        success, message, stats = message_queue_service.get_queue_statistics()
        
        if success:
            # 基于统计信息计算健康状态
            health_status = "healthy"
            if stats['queue_health']['failure_rate'] > 10:
                health_status = "warning"
            if stats['queue_health']['failure_rate'] > 25:
                health_status = "critical"
                
            return jsonify({
                "success": True,
                "health_status": health_status,
                "active_messages": stats['queue_health']['active_messages'],
                "completion_rate": stats['queue_health']['completion_rate'],
                "failure_rate": stats['queue_health']['failure_rate'],
                "timestamp": int(time.time() * 1000)
            }), 200
        else:
            return jsonify({
                "success": False,
                "health_status": "unknown",
                "error": message,
                "timestamp": int(time.time() * 1000)
            }), 500
            
    except Exception as e:
        logger.error(f"获取队列健康状态时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "health_status": "error",
            "error": f"获取队列健康状态失败: {str(e)}",
            "timestamp": int(time.time() * 1000)
        }), 500