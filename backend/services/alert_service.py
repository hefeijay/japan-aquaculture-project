#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警服务模块
负责预警规则和预警通知的业务逻辑处理
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
import logging

from config.settings import Config


def get_local_timezone():
    """获取本地时区（从配置中读取）"""
    return timezone(timedelta(hours=Config.LOCAL_TIMEZONE_OFFSET))

from sqlalchemy import or_, desc, and_
from sqlalchemy.orm import Session

from db_models.db_session import db_session_factory
from db_models.alert_rule import AlertRule
from db_models.alert_notification import AlertNotification
from db_models.device import Device, DeviceType

logger = logging.getLogger(__name__)


class AlertService:
    """预警服务类"""
    
    # ==================== 规则相关 ====================
    
    @classmethod
    def generate_rule_id(cls, session: Session) -> str:
        """
        生成规则业务ID，格式为 AT-XXX（如 AT-001）
        
        Args:
            session: 数据库会话
            
        Returns:
            唯一的规则业务ID
        """
        # 查询当前最大的规则编号
        last_rule = session.query(AlertRule).order_by(desc(AlertRule.id)).first()
        
        if last_rule and last_rule.rule_id:
            # 尝试从现有rule_id提取编号
            try:
                # 假设格式为 AT-XXX
                parts = last_rule.rule_id.split('-')
                if len(parts) == 2 and parts[0] == 'AT':
                    next_num = int(parts[1]) + 1
                else:
                    next_num = last_rule.id + 1
            except (ValueError, IndexError):
                next_num = last_rule.id + 1
        else:
            next_num = 1
        
        return f"AT-{next_num:03d}"
    
    @classmethod
    def generate_notification_id(cls, session: Session) -> str:
        """
        生成预警记录业务ID，格式为 REC-XXX（如 REC-001）
        
        Args:
            session: 数据库会话
            
        Returns:
            唯一的预警记录业务ID
        """
        # 查询当前最大的记录编号
        last_notification = session.query(AlertNotification).order_by(desc(AlertNotification.id)).first()
        
        if last_notification and last_notification.notification_id:
            try:
                parts = last_notification.notification_id.split('-')
                if len(parts) == 2 and parts[0] == 'REC':
                    next_num = int(parts[1]) + 1
                else:
                    next_num = last_notification.id + 1
            except (ValueError, IndexError):
                next_num = last_notification.id + 1
        else:
            next_num = 1
        
        return f"REC-{next_num:03d}"
    
    @classmethod
    def search_rules(
        cls,
        search: Optional[str] = None,
        device_id: Optional[int] = None,
        severity_level: Optional[str] = None,
        is_enabled: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        搜索预警规则
        
        Args:
            search: 搜索关键词（设备名称或规则ID）
            device_id: 设备ID筛选
            severity_level: 严重级别筛选
            is_enabled: 是否启用筛选
            page: 页码
            page_size: 每页数量
            
        Returns:
            (规则列表, 分页信息)
        """
        try:
            with db_session_factory() as session:
                # 基础查询
                query = session.query(AlertRule, Device).join(
                    Device, AlertRule.device_id == Device.id
                )
                
                # 筛选条件
                if is_enabled is not None:
                    query = query.filter(AlertRule.is_enabled == is_enabled)
                
                if device_id:
                    query = query.filter(AlertRule.device_id == device_id)
                
                if severity_level:
                    query = query.filter(AlertRule.severity_level == severity_level)
                
                if search:
                    search_pattern = f"%{search}%"
                    query = query.filter(
                        or_(
                            Device.name.ilike(search_pattern),
                            AlertRule.rule_id.ilike(search_pattern)
                        )
                    )
                
                # 计算总数
                total = query.count()
                
                # 分页
                offset = (page - 1) * page_size
                rules = query.order_by(desc(AlertRule.created_at)).offset(offset).limit(page_size).all()
                
                # 构建返回数据
                items = []
                for rule, device in rules:
                    items.append(cls._format_rule(rule, device))
                
                # 分页信息
                total_pages = (total + page_size - 1) // page_size
                pagination = {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
                
                return items, pagination
                
        except Exception as e:
            logger.error(f"搜索预警规则失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def create_rule(
        cls,
        device_id: int,
        metric: str,
        severity_level: str,
        trigger_condition: str,
        threshold: str,
        check_interval: int = 5,
        check_interval_unit: str = "minute"
    ) -> Dict[str, Any]:
        """
        创建预警规则
        
        Args:
            device_id: 设备ID
            metric: 检测指标
            severity_level: 严重级别
            trigger_condition: 触发条件
            threshold: 阈值
            check_interval: 检测间隔数值（默认5）
            check_interval_unit: 检测间隔单位（默认minute）
            
        Returns:
            创建的规则信息
        """
        try:
            with db_session_factory() as session:
                # 验证设备存在且为传感器
                device = session.query(Device).join(
                    DeviceType, Device.device_type_id == DeviceType.id
                ).filter(
                    Device.id == device_id,
                    Device.is_deleted == False
                ).first()
                
                if not device:
                    raise ValueError(f"设备不存在: {device_id}")
                
                # 获取设备类型
                device_type = session.query(DeviceType).filter(
                    DeviceType.id == device.device_type_id
                ).first()
                
                if device_type.category != 'sensor':
                    raise ValueError(f"当前仅支持传感器设备创建预警规则，该设备类型为: {device_type.category}")
                
                # 检查规则唯一性（同一设备、同一指标、同一触发条件、同一严重级别）
                existing_rule = session.query(AlertRule).filter(
                    AlertRule.device_id == device_id,
                    AlertRule.metric == metric,
                    AlertRule.trigger_condition == trigger_condition,
                    AlertRule.severity_level == severity_level
                ).first()
                
                if existing_rule:
                    raise ValueError(
                        f"该设备的该指标在该触发条件和严重级别下已存在预警规则（规则ID: {existing_rule.rule_id}）。"
                        f"同一设备的同一检测指标、同一触发条件（above/below）、同一严重级别不能重复创建规则。"
                    )
                
                # 生成规则ID
                rule_id = cls.generate_rule_id(session)
                
                # 创建规则
                rule = AlertRule(
                    device_id=device_id,
                    rule_id=rule_id,
                    metric=metric,
                    severity_level=severity_level,
                    trigger_condition=trigger_condition,
                    threshold=threshold
                )
                
                # 设置检测间隔（使用属性赋值而非构造函数参数，因为有默认值）
                rule.check_interval = check_interval
                rule.check_interval_unit = check_interval_unit
                
                session.add(rule)
                session.commit()
                session.refresh(rule)
                
                result = cls._format_rule(rule, device)
                
                # 同步调度器：添加定时检查任务
                from services.alert_scheduler_service import AlertSchedulerService
                if AlertSchedulerService.is_initialized():
                    AlertSchedulerService.add_or_update_job(result)
                
                logger.info(f"创建预警规则成功: {rule_id}")
                return result
                
        except ValueError as e:
            # 业务验证错误（设备不存在、规则冲突等），不打印堆栈
            logger.warning(f"创建预警规则失败: {str(e)}")
            raise
        except Exception as e:
            # 系统错误，打印完整堆栈
            logger.error(f"创建预警规则失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def update_rule(cls, rule_pk_id: int, **kwargs) -> Dict[str, Any]:
        """
        更新预警规则
        
        Args:
            rule_pk_id: 规则主键ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的规则信息
        """
        try:
            with db_session_factory() as session:
                rule = session.query(AlertRule).filter(AlertRule.id == rule_pk_id).first()
                
                if not rule:
                    raise ValueError(f"预警规则不存在: {rule_pk_id}")
                
                # 记录修改前的状态（用于判断是否需要同步调度器）
                old_is_enabled = rule.is_enabled
                old_check_interval = rule.check_interval
                old_check_interval_unit = rule.check_interval_unit
                
                # 允许更新的字段
                allowed_fields = ['device_id', 'metric', 'severity_level', 'trigger_condition', 'threshold', 'check_interval', 'check_interval_unit', 'is_enabled']
                
                for key, value in kwargs.items():
                    if key in allowed_fields and value is not None:
                        setattr(rule, key, value)
                
                session.commit()
                session.refresh(rule)
                
                # 获取设备信息
                device = session.query(Device).filter(Device.id == rule.device_id).first()
                
                result = cls._format_rule(rule, device)
                
                # 同步调度器
                from services.alert_scheduler_service import AlertSchedulerService
                if AlertSchedulerService.is_initialized():
                    # 检查是否修改了启用状态
                    new_is_enabled = kwargs.get('is_enabled')
                    if new_is_enabled is not None and new_is_enabled != old_is_enabled:
                        if new_is_enabled:
                            # 规则被启用，添加或恢复任务
                            AlertSchedulerService.add_or_update_job(result)
                        else:
                            # 规则被禁用，暂停任务
                            AlertSchedulerService.pause_job(rule_pk_id)
                    
                    # 检查是否修改了检查间隔（且规则是启用状态）
                    new_check_interval = kwargs.get('check_interval')
                    new_check_interval_unit = kwargs.get('check_interval_unit')
                    interval_changed = (
                        (new_check_interval is not None and new_check_interval != old_check_interval) or
                        (new_check_interval_unit is not None and new_check_interval_unit != old_check_interval_unit)
                    )
                    
                    if interval_changed and rule.is_enabled:
                        # 检查间隔变更且规则启用，更新任务
                        AlertSchedulerService.add_or_update_job(result)
                
                logger.info(f"更新预警规则成功: {rule.rule_id}")
                return result
                
        except ValueError as e:
            logger.warning(f"更新预警规则失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"更新预警规则失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def delete_rule(cls, rule_pk_id: int) -> Dict[str, Any]:
        """
        删除预警规则
        
        Args:
            rule_pk_id: 规则主键ID
            
        Returns:
            删除的规则信息
        """
        try:
            # 先从调度器移除任务（即使任务正在执行也不影响）
            from services.alert_scheduler_service import AlertSchedulerService
            if AlertSchedulerService.is_initialized():
                AlertSchedulerService.remove_job(rule_pk_id)
            
            with db_session_factory() as session:
                rule = session.query(AlertRule).filter(AlertRule.id == rule_pk_id).first()
                
                if not rule:
                    raise ValueError(f"预警规则不存在: {rule_pk_id}")
                
                result = {
                    "id": rule.id,
                    "rule_id": rule.rule_id
                }
                
                session.delete(rule)
                session.commit()
                
                logger.info(f"删除预警规则成功: {result['rule_id']}")
                return result
                
        except ValueError as e:
            logger.warning(f"删除预警规则失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"删除预警规则失败: {str(e)}", exc_info=True)
            raise
    
    # ==================== 通知相关 ====================
    
    @classmethod
    def get_rule_notifications(
        cls,
        rule_pk_id: int,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
        """
        获取指定规则的预警通知历史
        
        Args:
            rule_pk_id: 规则主键ID
            status: 状态筛选
            page: 页码
            page_size: 每页数量
            
        Returns:
            (规则信息, 通知列表, 分页信息)
        """
        try:
            with db_session_factory() as session:
                # 获取规则信息
                rule = session.query(AlertRule).filter(AlertRule.id == rule_pk_id).first()
                
                if not rule:
                    raise ValueError(f"预警规则不存在: {rule_pk_id}")
                
                device = session.query(Device).filter(Device.id == rule.device_id).first()
                rule_info = cls._format_rule(rule, device)
                
                # 查询通知
                query = session.query(AlertNotification).filter(
                    AlertNotification.alert_rule_id == rule_pk_id
                )
                
                if status:
                    query = query.filter(AlertNotification.status == status)
                
                # 计算总数
                total = query.count()
                
                # 分页
                offset = (page - 1) * page_size
                notifications = query.order_by(desc(AlertNotification.triggered_at)).offset(offset).limit(page_size).all()
                
                # 构建返回数据
                items = []
                for notification in notifications:
                    items.append(cls._format_notification(notification, device, rule))
                
                # 分页信息
                total_pages = (total + page_size - 1) // page_size
                pagination = {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
                
                return rule_info, items, pagination
                
        except ValueError as e:
            logger.warning(f"获取预警通知历史失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"获取预警通知历史失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def get_all_notifications(
        cls,
        status: Optional[str] = None,
        device_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        获取所有预警通知列表
        
        Args:
            status: 状态筛选（pending/resolved）
            device_id: 设备ID筛选
            rule_id: 规则主键ID筛选
            page: 页码
            page_size: 每页数量
            
        Returns:
            (通知列表, 分页信息)
        """
        try:
            with db_session_factory() as session:
                # 基础查询，关联设备和规则
                query = session.query(AlertNotification, Device, AlertRule).outerjoin(
                    Device, AlertNotification.device_id == Device.id
                ).outerjoin(
                    AlertRule, AlertNotification.alert_rule_id == AlertRule.id
                )
                
                # 筛选条件
                if status:
                    query = query.filter(AlertNotification.status == status)
                
                if device_id:
                    query = query.filter(AlertNotification.device_id == device_id)
                
                if rule_id:
                    query = query.filter(AlertNotification.alert_rule_id == rule_id)
                
                # 计算总数
                total = query.count()
                
                # 分页，按更新时间倒序（最新的在最上面）
                offset = (page - 1) * page_size
                results = query.order_by(desc(AlertNotification.updated_at)).offset(offset).limit(page_size).all()
                
                # 构建返回数据
                items = []
                for notification, device, rule in results:
                    items.append(cls._format_notification(notification, device, rule))
                
                # 分页信息
                total_pages = (total + page_size - 1) // page_size
                pagination = {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
                
                return items, pagination
                
        except Exception as e:
            logger.error(f"获取所有预警通知失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def resolve_notification(cls, notification_pk_id: int) -> Dict[str, Any]:
        """
        标记预警通知为已处理
        
        Args:
            notification_pk_id: 通知主键ID
            
        Returns:
            更新后的通知信息
        """
        try:
            with db_session_factory() as session:
                notification = session.query(AlertNotification).filter(
                    AlertNotification.id == notification_pk_id
                ).first()
                
                if not notification:
                    raise ValueError(f"预警通知不存在: {notification_pk_id}")
                
                if notification.status == 'resolved':
                    raise ValueError("该预警已被处理")
                
                # 更新状态
                now_utc = datetime.now(timezone.utc)
                now_local = now_utc.astimezone(get_local_timezone())
                notification.status = 'resolved'
                notification.resolved_at = now_utc
                notification.resolved_at_local = now_local
                
                session.commit()
                session.refresh(notification)
                
                # 获取关联信息
                rule = session.query(AlertRule).filter(AlertRule.id == notification.alert_rule_id).first()
                device = session.query(Device).filter(Device.id == notification.device_id).first()
                
                logger.info(f"标记预警为已处理: {notification.notification_id}")
                return cls._format_notification(notification, device, rule)
                
        except ValueError as e:
            logger.warning(f"标记预警处理失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"标记预警处理失败: {str(e)}", exc_info=True)
            raise
    
    # ==================== 辅助方法 ====================
    
    @classmethod
    def _format_rule(cls, rule: AlertRule, device: Device) -> Dict[str, Any]:
        """格式化规则信息"""
        return {
            "id": rule.id,
            "device_id": rule.device_id,
            "device_name": device.name if device else None,
            "rule_id": rule.rule_id,
            "metric": rule.metric,
            "severity_level": rule.severity_level,
            "trigger_condition": rule.trigger_condition,
            "threshold": rule.threshold,
            "check_interval": rule.check_interval,
            "check_interval_unit": rule.check_interval_unit,
            "is_enabled": rule.is_enabled,
            "last_checked_at": rule.last_checked_at.isoformat() if rule.last_checked_at else None,
            "last_checked_at_local": rule.last_checked_at_local.isoformat() if rule.last_checked_at_local else None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
        }
    
    @classmethod
    def _format_notification(
        cls, 
        notification: AlertNotification, 
        device: Optional[Device], 
        rule: Optional[AlertRule]
    ) -> Dict[str, Any]:
        """格式化通知信息"""
        return {
            "id": notification.id,
            "notification_id": notification.notification_id,
            "alert_rule_id": notification.alert_rule_id,
            "device_id": notification.device_id,
            "device_name": device.name if device else None,
            "rule_id": rule.rule_id if rule else None,
            "status": notification.status,
            "content": notification.content,
            "current_value": notification.current_value,
            "triggered_at": notification.triggered_at.isoformat() if notification.triggered_at else None,
            "triggered_at_local": notification.triggered_at_local.isoformat() if notification.triggered_at_local else None,
            "resolved_at": notification.resolved_at.isoformat() if notification.resolved_at else None,
            "resolved_at_local": notification.resolved_at_local.isoformat() if notification.resolved_at_local else None,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "updated_at": notification.updated_at.isoformat() if notification.updated_at else None
        }

