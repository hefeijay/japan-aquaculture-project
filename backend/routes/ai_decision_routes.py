#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI决策管理API路由
提供AI决策的CRUD操作和管理功能
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
import logging

from japan_server.services.ai_decision_service import AIDecisionService, DecisionRuleEngine

# 创建蓝图
ai_decision_bp = Blueprint('ai_decision', __name__, url_prefix='/api/ai-decisions')

# 配置日志
logger = logging.getLogger(__name__)


@ai_decision_bp.route('/', methods=['GET'])
def get_decisions():
    """
    获取AI决策消息列表
    
    Query Parameters:
        - num_messages: 消息数量限制
        - max_age_hours: 最大消息年龄（小时）
    """
    try:
        # 获取查询参数
        num_messages = request.args.get('num_messages', type=int)
        max_age_hours = request.args.get('max_age_hours', default=24, type=int)
        
        # 获取决策消息
        decisions = AIDecisionService.get_recent_decisions(
            num_messages=num_messages,
            max_age_hours=max_age_hours
        )
        
        return jsonify({
            "success": True,
            "data": decisions,
            "count": len(decisions),
            "timestamp": AIDecisionService.format_japanese_time()
        })
        
    except Exception as e:
        logger.error(f"获取AI决策消息失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/', methods=['POST'])
def create_decision():
    """
    创建新的AI决策消息
    
    Request Body:
        - type: 决策类型 (analysis/warning/action/optimization)
        - message: 消息内容
        - action: 建议操作 (可选)
        - priority: 优先级 0-10 (可选，默认0)
        - source: 数据源类型 (可选)
        - source_id: 数据源ID (可选)
        - confidence: 置信度 0-100 (可选)
        - expires_hours: 过期时间小时数 (可选)
    """
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data or 'type' not in data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必需字段: type, message"
            }), 400
        
        # 验证决策类型
        valid_types = ['analysis', 'warning', 'action', 'optimization', 'maintenance', 'security']
        if data['type'] not in valid_types:
            return jsonify({
                "success": False,
                "error": f"无效的决策类型，支持的类型: {', '.join(valid_types)}"
            }), 400
        
        # 创建决策
        decision_id = AIDecisionService.create_decision(
            decision_type=data['type'],
            message=data['message'],
            action=data.get('action'),
            priority=data.get('priority', 0),
            source=data.get('source'),
            source_id=data.get('source_id'),
            confidence=data.get('confidence'),
            expires_hours=data.get('expires_hours')
        )
        
        if decision_id:
            return jsonify({
                "success": True,
                "decision_id": decision_id,
                "message": "AI决策创建成功",
                "timestamp": AIDecisionService.format_japanese_time()
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "创建AI决策失败",
                "timestamp": AIDecisionService.format_japanese_time()
            }), 500
            
    except Exception as e:
        logger.error(f"创建AI决策失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/<decision_id>/status', methods=['PUT'])
def update_decision_status(decision_id: str):
    """
    更新决策状态
    
    Request Body:
        - status: 新状态 (active/processed/expired)
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必需字段: status"
            }), 400
        
        # 验证状态值
        valid_statuses = ['active', 'processed', 'expired']
        if data['status'] not in valid_statuses:
            return jsonify({
                "success": False,
                "error": f"无效的状态值，支持的状态: {', '.join(valid_statuses)}"
            }), 400
        
        # 更新状态
        success = AIDecisionService.update_decision_status(
            decision_id=decision_id,
            status=data['status']
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "决策状态更新成功",
                "timestamp": AIDecisionService.format_japanese_time()
            })
        else:
            return jsonify({
                "success": False,
                "error": "决策不存在或更新失败",
                "timestamp": AIDecisionService.format_japanese_time()
            }), 404
            
    except Exception as e:
        logger.error(f"更新决策状态失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/cleanup', methods=['POST'])
def cleanup_expired():
    """清理过期的决策消息"""
    try:
        cleaned_count = AIDecisionService.cleanup_expired_decisions()
        
        return jsonify({
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"已清理 {cleaned_count} 条过期决策",
            "timestamp": AIDecisionService.format_japanese_time()
        })
        
    except Exception as e:
        logger.error(f"清理过期决策失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取决策统计信息"""
    try:
        stats = AIDecisionService.get_decision_statistics()
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": AIDecisionService.format_japanese_time()
        })
        
    except Exception as e:
        logger.error(f"获取决策统计信息失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/rules', methods=['GET'])
def get_rules():
    """获取决策规则列表"""
    try:
        # 这里可以实现获取规则列表的逻辑
        return jsonify({
            "success": True,
            "data": [],
            "message": "规则管理功能待实现",
            "timestamp": AIDecisionService.format_japanese_time()
        })
        
    except Exception as e:
        logger.error(f"获取决策规则失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/rules', methods=['POST'])
def create_rule():
    """
    创建新的决策规则
    
    Request Body:
        - name: 规则名称
        - condition_type: 条件类型
        - condition_config: 条件配置(JSON字符串)
        - message_template: 消息模板
        - decision_type: 决策类型
        - action_template: 操作模板 (可选)
        - priority: 优先级 (可选，默认0)
    """
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['name', 'condition_type', 'condition_config', 'message_template', 'decision_type']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必需字段: {field}"
                }), 400
        
        # 创建规则
        rule_id = DecisionRuleEngine.create_rule(
            name=data['name'],
            condition_type=data['condition_type'],
            condition_config=data['condition_config'],
            message_template=data['message_template'],
            decision_type=data['decision_type'],
            action_template=data.get('action_template'),
            priority=data.get('priority', 0)
        )
        
        if rule_id:
            return jsonify({
                "success": True,
                "rule_id": rule_id,
                "message": "决策规则创建成功",
                "timestamp": AIDecisionService.format_japanese_time()
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "创建决策规则失败",
                "timestamp": AIDecisionService.format_japanese_time()
            }), 500
            
    except Exception as e:
        logger.error(f"创建决策规则失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500


@ai_decision_bp.route('/evaluate', methods=['POST'])
def evaluate_data():
    """
    基于规则评估数据并生成决策
    
    Request Body:
        - data_type: 数据类型 (sensor/performance/etc.)
        - data: 数据内容
    """
    try:
        data = request.get_json()
        
        if not data or 'data_type' not in data or 'data' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必需字段: data_type, data"
            }), 400
        
        # 根据数据类型评估
        decision_ids = []
        if data['data_type'] == 'sensor':
            decision_ids = DecisionRuleEngine.evaluate_sensor_data(data['data'])
        
        return jsonify({
            "success": True,
            "generated_decisions": decision_ids,
            "count": len(decision_ids),
            "timestamp": AIDecisionService.format_japanese_time()
        })
        
    except Exception as e:
        logger.error(f"评估数据失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": AIDecisionService.format_japanese_time()
        }), 500