#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息队列服务层
负责处理客户端推送消息的业务逻辑，包括消息验证、存储和状态管理
"""

import logging
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.message_queue import MessageQueue

logger = logging.getLogger(__name__)


class MessageQueueService:
    """消息队列服务类"""
        
    @classmethod
    def validate_message(cls, message_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证消息数据的有效性
        
        Args:
            message_data: 消息数据字典
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            # 检查必需字段
            required_fields = ['message_type', 'content']
            for field in required_fields:
                if field not in message_data:
                    return False, f"缺少必需字段: {field}"
                    
            # 验证消息类型
            valid_types = ['text', 'json', 'notification', 'command', 'data', 'general', 'sensor_data', 'user_input', 'system_alert']
            if message_data['message_type'] not in valid_types:
                return False, f"无效的消息类型: {message_data['message_type']}"
                
            # 验证内容不为空
            if not message_data['content'] or str(message_data['content']).strip() == '':
                return False, "消息内容不能为空"
                
            # 验证优先级（如果提供）
            if 'priority' in message_data:
                if isinstance(message_data['priority'], str):
                    priority_map = {'low': 2, 'normal': 5, 'high': 8, 'urgent': 10}
                    if message_data['priority'] not in priority_map:
                        return False, f"无效的优先级: {message_data['priority']}"
                elif isinstance(message_data['priority'], int):
                    if not (0 <= message_data['priority'] <= 10):
                        return False, "优先级必须在0-10之间"
                else:
                    return False, "优先级必须是字符串或整数"
                    
            return True, ""
            
        except Exception as e:
            logger.error(f"消息验证时发生错误: {e}")
            return False, f"消息验证失败: {str(e)}"
    
    @classmethod
    def create_message(cls, message_data: Dict[str, Any]) -> tuple[bool, str, Optional[str]]:
        """
        创建新的消息队列记录
        
        Args:
            message_data: 消息数据字典
            
        Returns:
            tuple: (是否成功, 消息, 消息ID)
        """
        try:
            # 验证消息数据
            is_valid, error_msg = cls.validate_message(message_data)
            if not is_valid:
                return False, error_msg, None
                
            with db_session_factory() as session:
                # 生成唯一消息ID
                message_id = f"msg_{int(time.time() * 1000)}_{hash(str(message_data['content'])) % 10000}"
                
                # 处理优先级
                priority = message_data.get('priority', 'normal')
                if isinstance(priority, str):
                    priority_map = {'low': 2, 'normal': 5, 'high': 8, 'urgent': 10}
                    priority_value = priority_map.get(priority, 5)
                else:
                    priority_value = priority
                
                # 准备元数据
                metadata = {
                    'source': message_data.get('source', 'client'),
                    'original_priority': message_data.get('priority', 'normal'),
                    **message_data.get('metadata', {})
                }
                
                # 创建消息队列记录
                message_record = MessageQueue(
                    message_id=message_id,
                    content=str(message_data['content']),
                    message_type=message_data['message_type'],
                    priority=priority_value,
                    status='pending',
                    retry_count=0,
                    max_retries=3,
                    message_metadata=json.dumps(metadata, ensure_ascii=False),
                    consumed_at=None,
                    completed_at=None,
                    error_message=None,
                    expires_at=None
                )
                
                # 保存到数据库
                session.add(message_record)
                session.commit()
                
                logger.info(f"成功创建消息队列记录: {message_id}")
                return True, "消息已成功添加到队列", message_id
                
        except Exception as e:
            logger.error(f"创建消息时发生错误: {e}")
            return False, f"创建消息失败: {str(e)}", None
    
    @classmethod
    def get_message_status(cls, message_id: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        获取消息状态
        
        Args:
            message_id: 消息ID
            
        Returns:
            tuple: (是否成功, 消息, 消息状态数据)
        """
        try:
            with db_session_factory() as session:
                message_record = session.query(MessageQueue).filter(
                    MessageQueue.message_id == message_id
                ).first()
                
                if message_record:
                    # 解析元数据
                    metadata = {}
                    if message_record.message_metadata:
                        try:
                            metadata = json.loads(message_record.message_metadata)
                        except json.JSONDecodeError:
                            pass
                    
                    message_info = {
                        'message_id': message_record.message_id,
                        'content': message_record.content,
                        'message_type': message_record.message_type,
                        'priority': message_record.priority,
                        'status': message_record.status,
                        'retry_count': message_record.retry_count,
                        'max_retries': message_record.max_retries,
                        'created_at': message_record.created_at.isoformat() if message_record.created_at else None,
                        'updated_at': message_record.updated_at.isoformat() if message_record.updated_at else None,
                        'consumed_at': message_record.consumed_at.isoformat() if message_record.consumed_at else None,
                        'completed_at': message_record.completed_at.isoformat() if message_record.completed_at else None,
                        'error_message': message_record.error_message,
                        'expires_at': message_record.expires_at.isoformat() if message_record.expires_at else None,
                        'metadata': metadata
                    }
                    return True, "获取消息状态成功", message_info
                else:
                    return False, "消息不存在", None
                    
        except Exception as e:
            logger.error(f"获取消息状态时发生错误: {e}")
            return False, f"获取消息状态失败: {str(e)}", None
    
    @classmethod
    def get_pending_messages(cls, limit: int = 10) -> tuple[bool, str, List[Dict[str, Any]]]:
        """
        获取待处理的消息列表
        
        Args:
            limit: 返回消息数量限制
            
        Returns:
            tuple: (是否成功, 消息, 消息列表)
        """
        try:
            with db_session_factory() as session:
                messages = session.query(MessageQueue).filter(
                    MessageQueue.status == 'pending'
                ).order_by(
                    desc(MessageQueue.priority), 
                    MessageQueue.created_at.asc()
                ).limit(limit).all()
                
                message_list = []
                for msg in messages:
                    # 解析元数据
                    metadata = {}
                    if msg.message_metadata:
                        try:
                            metadata = json.loads(msg.message_metadata)
                        except json.JSONDecodeError:
                            pass
                    
                    message_info = {
                        'message_id': msg.message_id,
                        'content': msg.content,
                        'message_type': msg.message_type,
                        'priority': msg.priority,
                        'status': msg.status,
                        'created_at': msg.created_at.isoformat() if msg.created_at else None,
                        'metadata': metadata
                    }
                    message_list.append(message_info)
                
                return True, f"获取到 {len(message_list)} 条待处理消息", message_list
                
        except Exception as e:
            logger.error(f"获取待处理消息时发生错误: {e}")
            return False, f"获取待处理消息失败: {str(e)}", []
    
    @classmethod
    def update_message_status(cls, message_id: str, status: str, error_message: str = None) -> tuple[bool, str]:
        """
        更新消息状态
        
        Args:
            message_id: 消息ID
            status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            valid_statuses = ['pending', 'processing', 'completed', 'failed', 'expired']
            if status not in valid_statuses:
                return False, f"无效的状态: {status}"
                
            with db_session_factory() as session:
                message_record = session.query(MessageQueue).filter(
                    MessageQueue.message_id == message_id
                ).first()
                
                if not message_record:
                    return False, "消息不存在"
                
                # 更新状态
                message_record.status = status
                
                # 更新时间戳
                current_time = datetime.now(timezone.utc)
                if status == 'processing':
                    message_record.consumed_at = current_time
                elif status in ['completed', 'failed']:
                    message_record.completed_at = current_time
                    
                # 设置错误信息
                if error_message:
                    message_record.error_message = error_message
                    
                # 如果是失败状态，增加重试次数
                if status == 'failed':
                    message_record.retry_count += 1
                
                session.commit()
                
                logger.info(f"成功更新消息状态: {message_id} -> {status}")
                return True, "消息状态更新成功"
                    
        except Exception as e:
            logger.error(f"更新消息状态时发生错误: {e}")
            return False, f"更新消息状态失败: {str(e)}"
    
    @classmethod
    def get_queue_statistics(cls) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        获取消息队列统计信息
        
        Returns:
            tuple: (是否成功, 消息, 统计数据)
        """
        try:
            with db_session_factory() as session:
                # 统计各状态的消息数量
                total_count = session.query(MessageQueue).count()
                pending_count = session.query(MessageQueue).filter(
                    MessageQueue.status == 'pending'
                ).count()
                processing_count = session.query(MessageQueue).filter(
                    MessageQueue.status == 'processing'
                ).count()
                completed_count = session.query(MessageQueue).filter(
                    MessageQueue.status == 'completed'
                ).count()
                failed_count = session.query(MessageQueue).filter(
                    MessageQueue.status == 'failed'
                ).count()
                expired_count = session.query(MessageQueue).filter(
                    MessageQueue.status == 'expired'
                ).count()
                
                # 统计各类型的消息数量
                type_stats = {}
                type_results = session.query(
                    MessageQueue.message_type, 
                    func.count(MessageQueue.id)
                ).group_by(MessageQueue.message_type).all()
                
                for msg_type, count in type_results:
                    type_stats[msg_type] = count
                
                stats = {
                    'total_messages': total_count,
                    'status_breakdown': {
                        'pending': pending_count,
                        'processing': processing_count,
                        'completed': completed_count,
                        'failed': failed_count,
                        'expired': expired_count
                    },
                    'type_breakdown': type_stats,
                    'queue_health': {
                        'active_messages': pending_count + processing_count,
                        'completion_rate': round((completed_count / total_count * 100) if total_count > 0 else 0, 2),
                        'failure_rate': round((failed_count / total_count * 100) if total_count > 0 else 0, 2)
                    },
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                return True, "获取队列统计成功", stats
                
        except Exception as e:
            logger.error(f"获取队列统计时发生错误: {e}")
            return False, f"获取队列统计失败: {str(e)}", None
    
    @classmethod
    def cleanup_expired_messages(cls) -> int:
        """
        清理过期的消息
        
        Returns:
            清理的消息数量
        """
        try:
            with db_session_factory() as session:
                # 标记过期消息
                expired_count = session.query(MessageQueue).filter(
                    and_(
                        MessageQueue.expires_at.isnot(None),
                        MessageQueue.expires_at <= datetime.now(timezone.utc),
                        MessageQueue.status.in_(['pending', 'processing'])
                    )
                ).update({"status": "expired"})
                
                session.commit()
                return expired_count
                
        except Exception as e:
            logger.error(f"清理过期消息时发生错误: {e}")
            return 0


# 创建全局服务实例（保持向后兼容）
message_queue_service = MessageQueueService()