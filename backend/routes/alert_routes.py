#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警管理路由蓝图
包含预警规则和预警通知的所有API端点
"""

from flask import Blueprint, jsonify, request
import logging

from services.alert_service import AlertService

# 创建蓝图
alert_bp = Blueprint('alert', __name__, url_prefix='/api')

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 预警规则接口 ====================

@alert_bp.route('/alert-rules', methods=['GET'])
def search_alert_rules():
    """
    搜索预警规则
    
    Query Parameters:
        - search: 搜索关键词（设备名称或规则ID）
        - device_id: 设备ID筛选
        - severity_level: 严重级别筛选（info/warning/critical）
        - is_enabled: 是否启用筛选（默认true）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
    
    Returns:
        JSON格式的规则列表和分页信息
    """
    try:
        # 获取查询参数
        search = request.args.get('search')
        device_id = request.args.get('device_id', type=int)
        severity_level = request.args.get('severity_level')
        is_enabled_str = request.args.get('is_enabled', 'true')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 处理 is_enabled 参数
        if is_enabled_str.lower() == 'false':
            is_enabled = False
        elif is_enabled_str.lower() == 'all':
            is_enabled = None
        else:
            is_enabled = True
        
        # 参数校验
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # 调用服务
        items, pagination = AlertService.search_rules(
            search=search,
            device_id=device_id,
            severity_level=severity_level,
            is_enabled=is_enabled,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "items": items,
                "pagination": pagination
            }
        })
        
    except Exception as e:
        logger.error(f"搜索预警规则失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@alert_bp.route('/alert-rules', methods=['POST'])
def create_alert_rule():
    """
    新增预警规则
    
    Request Body:
        {
            "device_id": 1,
            "metric": "do",
            "severity_level": "critical",
            "trigger_condition": "below",
            "threshold": "5.0",
            "check_interval": 5,
            "check_interval_unit": "minute"
        }
    
    Returns:
        JSON格式的创建结果
    """
    try:
        # 获取请求数据
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "请求格式错误，需要JSON格式",
                "data": None
            }), 400
        
        data = request.get_json()
        
        # 参数校验
        required_fields = ['device_id', 'metric', 'severity_level', 'trigger_condition', 'threshold']
        missing_fields = [f for f in required_fields if f not in data or data[f] is None]
        
        if missing_fields:
            return jsonify({
                "code": 400,
                "message": f"缺少必填字段: {', '.join(missing_fields)}",
                "data": None
            }), 400
        
        # 校验枚举值
        valid_severity_levels = ['info', 'warning', 'critical']
        if data['severity_level'] not in valid_severity_levels:
            return jsonify({
                "code": 400,
                "message": f"无效的严重级别，可选值: {', '.join(valid_severity_levels)}",
                "data": None
            }), 400
        
        valid_trigger_conditions = ['below', 'above']
        if data['trigger_condition'] not in valid_trigger_conditions:
            return jsonify({
                "code": 400,
                "message": f"无效的触发条件，可选值: {', '.join(valid_trigger_conditions)}",
                "data": None
            }), 400
        
        valid_metrics = ['do', 'ph', 'temperature', 'turbidity', 'water_level', 'ammonia', 'nitrite']
        if data['metric'] not in valid_metrics:
            return jsonify({
                "code": 400,
                "message": f"无效的检测指标，可选值: {', '.join(valid_metrics)}",
                "data": None
            }), 400
        
        # 校验检测间隔单位（如果提供）
        check_interval = data.get('check_interval', 5)
        check_interval_unit = data.get('check_interval_unit', 'minute')
        
        valid_interval_units = ['minute', 'hour', 'day']
        if check_interval_unit not in valid_interval_units:
            return jsonify({
                "code": 400,
                "message": f"无效的检测间隔单位，可选值: {', '.join(valid_interval_units)}",
                "data": None
            }), 400
        
        # 校验检测间隔数值
        if not isinstance(check_interval, int) or check_interval < 1:
            return jsonify({
                "code": 400,
                "message": "检测间隔必须是大于0的整数",
                "data": None
            }), 400
        
        # 调用服务
        result = AlertService.create_rule(
            device_id=data['device_id'],
            metric=data['metric'],
            severity_level=data['severity_level'],
            trigger_condition=data['trigger_condition'],
            threshold=str(data['threshold']),
            check_interval=check_interval,
            check_interval_unit=check_interval_unit
        )
        
        return jsonify({
            "code": 200,
            "message": "预警规则创建成功",
            "data": result
        }), 201
        
    except ValueError as e:
        return jsonify({
            "code": 400,
            "message": str(e),
            "data": None
        }), 400
        
    except Exception as e:
        logger.error(f"创建预警规则失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@alert_bp.route('/alert-rules/<int:rule_id>', methods=['PUT'])
def update_alert_rule(rule_id: int):
    """
    修改预警规则
    
    Path Parameters:
        - rule_id: 规则主键ID
    
    Request Body (支持部分更新):
        {
            "device_id": 1,
            "metric": "do",
            "severity_level": "warning",
            "trigger_condition": "below",
            "threshold": "6.0",
            "check_interval": 10,
            "check_interval_unit": "minute",
            "is_enabled": true
        }
    
    Returns:
        JSON格式的更新结果
    """
    try:
        # 获取请求数据
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "请求格式错误，需要JSON格式",
                "data": None
            }), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                "code": 400,
                "message": "缺少更新数据",
                "data": None
            }), 400
        
        # 校验枚举值（如果提供）
        if 'severity_level' in data and data['severity_level']:
            valid_severity_levels = ['info', 'warning', 'critical']
            if data['severity_level'] not in valid_severity_levels:
                return jsonify({
                    "code": 400,
                    "message": f"无效的严重级别，可选值: {', '.join(valid_severity_levels)}",
                    "data": None
                }), 400
        
        if 'trigger_condition' in data and data['trigger_condition']:
            valid_trigger_conditions = ['below', 'above']
            if data['trigger_condition'] not in valid_trigger_conditions:
                return jsonify({
                    "code": 400,
                    "message": f"无效的触发条件，可选值: {', '.join(valid_trigger_conditions)}",
                    "data": None
                }), 400
        
        if 'metric' in data and data['metric']:
            valid_metrics = ['do', 'ph', 'temperature', 'turbidity', 'water_level', 'ammonia', 'nitrite']
            if data['metric'] not in valid_metrics:
                return jsonify({
                    "code": 400,
                    "message": f"无效的检测指标，可选值: {', '.join(valid_metrics)}",
                    "data": None
                }), 400
        
        # 校验检测间隔单位（如果提供）
        if 'check_interval_unit' in data and data['check_interval_unit']:
            valid_interval_units = ['minute', 'hour', 'day']
            if data['check_interval_unit'] not in valid_interval_units:
                return jsonify({
                    "code": 400,
                    "message": f"无效的检测间隔单位，可选值: {', '.join(valid_interval_units)}",
                    "data": None
                }), 400
        
        # 校验检测间隔数值（如果提供）
        if 'check_interval' in data and data['check_interval'] is not None:
            if not isinstance(data['check_interval'], int) or data['check_interval'] < 1:
                return jsonify({
                    "code": 400,
                    "message": "检测间隔必须是大于0的整数",
                    "data": None
                }), 400
        
        # 处理阈值
        if 'threshold' in data:
            data['threshold'] = str(data['threshold'])
        
        # 调用服务
        result = AlertService.update_rule(rule_id, **data)
        
        return jsonify({
            "code": 200,
            "message": "预警规则更新成功",
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "code": 404,
            "message": str(e),
            "data": None
        }), 404
        
    except Exception as e:
        logger.error(f"更新预警规则失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@alert_bp.route('/alert-rules/<int:rule_id>', methods=['DELETE'])
def delete_alert_rule(rule_id: int):
    """
    删除预警规则
    
    Path Parameters:
        - rule_id: 规则主键ID
    
    Returns:
        JSON格式的删除结果
    """
    try:
        result = AlertService.delete_rule(rule_id)
        
        return jsonify({
            "code": 200,
            "message": "预警规则删除成功",
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "code": 404,
            "message": str(e),
            "data": None
        }), 404
        
    except Exception as e:
        logger.error(f"删除预警规则失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


# ==================== 预警通知接口 ====================

@alert_bp.route('/alert-rules/<int:rule_id>/notifications', methods=['GET'])
def get_alert_rule_notifications(rule_id: int):
    """
    获取指定规则的预警历史
    
    Path Parameters:
        - rule_id: 规则主键ID
    
    Query Parameters:
        - status: 状态筛选（pending/resolved）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
    
    Returns:
        JSON格式的规则信息和预警通知列表
    """
    try:
        # 获取查询参数
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 校验状态值
        if status and status not in ['pending', 'resolved']:
            return jsonify({
                "code": 400,
                "message": "无效的状态值，可选值: pending, resolved",
                "data": None
            }), 400
        
        # 参数校验
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # 调用服务
        rule_info, items, pagination = AlertService.get_rule_notifications(
            rule_pk_id=rule_id,
            status=status,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "rule": rule_info,
                "items": items,
                "pagination": pagination
            }
        })
        
    except ValueError as e:
        return jsonify({
            "code": 404,
            "message": str(e),
            "data": None
        }), 404
        
    except Exception as e:
        logger.error(f"获取预警历史失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@alert_bp.route('/alert-notifications/<int:notification_id>/resolve', methods=['POST'])
def resolve_alert_notification(notification_id: int):
    """
    标记预警为已处理
    
    Path Parameters:
        - notification_id: 预警通知主键ID
    
    Returns:
        JSON格式的处理结果
    """
    try:
        result = AlertService.resolve_notification(notification_id)
        
        return jsonify({
            "code": 200,
            "message": "预警已标记为已解决",
            "data": result
        })
        
    except ValueError as e:
        error_msg = str(e)
        if "不存在" in error_msg:
            return jsonify({
                "code": 404,
                "message": error_msg,
                "data": None
            }), 404
        else:
            return jsonify({
                "code": 400,
                "message": error_msg,
                "data": None
            }), 400
        
    except Exception as e:
        logger.error(f"标记预警处理失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500

