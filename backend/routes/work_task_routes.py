#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理中心路由蓝图
包含业务任务的创建、编辑、撤销和查询API端点
"""

from flask import Blueprint, jsonify, request
import logging

from services.work_task_service import WorkTaskService
from utils.auth import token_required

work_task_bp = Blueprint('work_task', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)


@work_task_bp.route('/work-tasks', methods=['GET'])
@token_required
def get_work_task_list():
    """
    查询任务列表

    Query Parameters:
        - status: 状态筛选（pending/in_progress/completed）
        - priority: 优先级筛选（high/medium/low）
        - search: 搜索关键词（按 topic、task_id、负责人 username 模糊搜索）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
    """
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        if status and status not in ('pending', 'in_progress', 'completed'):
            return jsonify({
                "code": 400,
                "message": "无效的状态值，可选值: pending, in_progress, completed",
                "data": None
            }), 400

        if priority and priority not in ('high', 'medium', 'low'):
            return jsonify({
                "code": 400,
                "message": "无效的优先级，可选值: high, medium, low",
                "data": None
            }), 400

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        items, pagination = WorkTaskService.get_task_list(
            status=status,
            priority=priority,
            search=search,
            page=page,
            page_size=page_size,
        )

        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "items": items,
                "pagination": pagination
            }
        }), 200

    except Exception as e:
        logger.error(f"查询任务列表失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@work_task_bp.route('/work-tasks', methods=['POST'])
@token_required
def create_work_task():
    """
    创建新任务

    Request Body:
        {
            "topic": "检查1号池溶解氧设备",
            "priority": "high",
            "creator_name": "张三",
            "assignee_id": 2,
            "pond_id": 1,            // 可选
            "deadline": "...",        // 可选，ISO 8601
            "status": "pending",     // 可选，默认 pending
            "description": "...",    // 可选
            "execute_immediately": false  // 可选，默认 false
        }
    """
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "请求格式错误，需要JSON格式",
                "data": None
            }), 400

        data = request.get_json()

        required_fields = ['topic', 'priority', 'creator_name', 'assignee_id']
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            return jsonify({
                "code": 400,
                "message": f"缺少必填字段: {', '.join(missing)}",
                "data": None
            }), 400

        valid_priorities = ('high', 'medium', 'low')
        if data['priority'] not in valid_priorities:
            return jsonify({
                "code": 400,
                "message": f"无效的优先级，可选值: {', '.join(valid_priorities)}",
                "data": None
            }), 400

        status = data.get('status', 'pending')
        if status not in ('pending', 'in_progress'):
            return jsonify({
                "code": 400,
                "message": "创建任务时状态只能是 pending 或 in_progress",
                "data": None
            }), 400

        result = WorkTaskService.create_task(
            topic=data['topic'],
            priority=data['priority'],
            creator_name=data['creator_name'],
            assignee_id=data['assignee_id'],
            pond_id=data.get('pond_id'),
            deadline=data.get('deadline'),
            status=status,
            description=data.get('description'),
            execute_immediately=data.get('execute_immediately', False),
        )

        msg = "任务创建成功"
        if data.get('execute_immediately'):
            msg = "任务创建成功（已立即执行）"

        return jsonify({
            "code": 200,
            "message": msg,
            "data": result
        }), 200

    except ValueError as e:
        return jsonify({
            "code": 400,
            "message": str(e),
            "data": None
        }), 400

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@work_task_bp.route('/work-tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_work_task(task_id: int):
    """
    编辑任务（支持部分更新）

    Path Parameters:
        - task_id: 任务主键ID

    Request Body (支持部分更新):
        {
            "topic": "...",
            "priority": "medium",
            "assignee_id": 3,
            "pond_id": 2,
            "deadline": "...",
            "status": "in_progress",
            "description": "...",
            "execute_immediately": false
        }
    """
    try:
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

        if 'priority' in data and data['priority']:
            if data['priority'] not in ('high', 'medium', 'low'):
                return jsonify({
                    "code": 400,
                    "message": "无效的优先级，可选值: high, medium, low",
                    "data": None
                }), 400

        if 'status' in data and data['status']:
            if data['status'] not in ('pending', 'in_progress', 'completed'):
                return jsonify({
                    "code": 400,
                    "message": "无效的状态值，可选值: pending, in_progress, completed",
                    "data": None
                }), 400

        result = WorkTaskService.update_task(task_id, **data)

        return jsonify({
            "code": 200,
            "message": "任务更新成功",
            "data": result
        }), 200

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
        logger.error(f"更新任务失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@work_task_bp.route('/work-tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_work_task(task_id: int):
    """
    撤销（删除）任务

    Path Parameters:
        - task_id: 任务主键ID

    仅 pending / in_progress 状态的任务可撤销，completed 不可撤销
    """
    try:
        result = WorkTaskService.delete_task(task_id)

        return jsonify({
            "code": 200,
            "message": "任务已撤销",
            "data": result
        }), 200

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
        logger.error(f"撤销任务失败: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500
