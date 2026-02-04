#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警检查服务
负责执行实际的阈值检查和预警触发/恢复逻辑
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import desc

from config.settings import Config

logger = logging.getLogger(__name__)


class AlertCheckService:
    """预警检查服务 - 执行实际的阈值检查和预警触发"""
    
    @classmethod
    def check_rule(cls, rule_id: int):
        """
        检查单条预警规则
        
        Args:
            rule_id: 规则主键ID
        """
        from db_models.db_session import db_session_factory
        from db_models.alert_rule import AlertRule
        from db_models.alert_notification import AlertNotification
        from db_models.sensor_reading import SensorReading
        from db_models.device import Device
        
        try:
            with db_session_factory() as session:
                # ========== 1. 获取规则（实时查询，确保数据最新） ==========
                rule = session.query(AlertRule).filter(
                    AlertRule.id == rule_id,
                    AlertRule.is_enabled == True
                ).first()
                
                if not rule:
                    logger.debug(f"规则不存在或已禁用: {rule_id}")
                    return
                
                # 记录查询时的版本（用于后续验证）
                rule_updated_at = rule.updated_at
                
                # ========== 2. 获取设备最新传感器数据 ==========
                latest_reading = session.query(SensorReading).filter(
                    SensorReading.device_id == rule.device_id
                ).order_by(desc(SensorReading.created_at)).first()
                
                if not latest_reading:
                    logger.debug(f"设备 {rule.device_id} 无传感器数据，跳过检查")
                    # 仍然更新检查时间
                    rule.last_checked_at = datetime.now(timezone.utc)
                    session.commit()
                    return
                
                # ========== 3. 执行阈值判断 ==========
                current_value = float(latest_reading.value)
                threshold = float(rule.threshold)
                is_triggered = cls._check_threshold(
                    current_value, threshold, rule.trigger_condition
                )
                
                if is_triggered:
                    # ========== 4. 触发预警 ==========
                    # 4.1 防抖检查
                    if cls._should_create_notification(session, rule.id):
                        # 4.2 版本验证（确保规则未在检查过程中被修改）
                        # 注意：必须在更新 last_checked_at 之前进行版本验证
                        # 因为 updated_at 字段会在任何更新时自动变化
                        current_rule = session.query(AlertRule).filter(
                            AlertRule.id == rule_id,
                            AlertRule.updated_at == rule_updated_at
                        ).first()
                        
                        if current_rule:
                            # 4.3 创建预警通知
                            cls._create_notification(session, rule, current_value)
                            logger.info(
                                f"预警触发: 规则={rule.rule_id}, "
                                f"设备={rule.device_id}, "
                                f"当前值={current_value}, 阈值={threshold}"
                            )
                        else:
                            logger.info(f"规则 {rule.rule_id} 在检查过程中被修改，放弃本次结果")
                else:
                    # ========== 5. 指标正常，自动恢复 ==========
                    cls._auto_resolve_alerts(session, rule, current_value)
                
                # ========== 6. 更新检查时间（放在最后，避免影响版本验证） ==========
                rule.last_checked_at = datetime.now(timezone.utc)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"检查规则 {rule_id} 失败: {str(e)}", exc_info=True)
    
    @classmethod
    def _check_threshold(cls, value: float, threshold: float, condition: str) -> bool:
        """
        检查是否触发阈值
        
        Args:
            value: 当前值
            threshold: 阈值
            condition: 触发条件（below/above）
            
        Returns:
            是否触发
        """
        if condition == 'below':
            return value < threshold
        elif condition == 'above':
            return value > threshold
        return False
    
    @classmethod
    def _should_create_notification(cls, session, rule_id: int) -> bool:
        """
        防抖判断：是否应该创建新的预警通知
        同一规则在 ALERT_DEBOUNCE_SECONDS 内只创建一条预警
        
        Args:
            session: 数据库会话
            rule_id: 规则主键ID
            
        Returns:
            是否应该创建预警
        """
        from db_models.alert_notification import AlertNotification
        
        debounce_seconds = Config.ALERT_DEBOUNCE_SECONDS
        debounce_threshold = datetime.now(timezone.utc) - timedelta(seconds=debounce_seconds)
        
        # 检查是否有最近的未处理预警
        existing = session.query(AlertNotification).filter(
            AlertNotification.alert_rule_id == rule_id,
            AlertNotification.status == 'pending',
            AlertNotification.triggered_at >= debounce_threshold
        ).first()
        
        if existing:
            logger.debug(
                f"规则 {rule_id} 在 {debounce_seconds} 秒内已有预警，跳过"
            )
            return False
        
        return True
    
    @classmethod
    def _create_notification(cls, session, rule, current_value: float):
        """
        创建预警通知
        
        Args:
            session: 数据库会话
            rule: 预警规则对象
            current_value: 当前传感器值
        """
        from db_models.alert_notification import AlertNotification
        from services.alert_service import AlertService
        
        # 生成通知业务ID
        notification_id = AlertService.generate_notification_id(session)
        
        # 构建预警内容
        condition_text = "低于" if rule.trigger_condition == 'below' else "高于"
        content = f"{rule.metric} {condition_text}阈值 {rule.threshold}，当前值: {current_value}"
        
        # 创建通知记录
        notification = AlertNotification(
            notification_id=notification_id,
            alert_rule_id=rule.id,
            device_id=rule.device_id,
            content=content,
            triggered_at=datetime.now(timezone.utc)
        )
        notification.current_value = str(current_value)
        
        session.add(notification)
        
        logger.info(f"创建预警通知: {notification_id}")
    
    @classmethod
    def _auto_resolve_alerts(cls, session, rule, current_value: float):
        """
        自动恢复：当指标恢复正常时，关闭该规则下所有 pending 预警
        
        Args:
            session: 数据库会话
            rule: 预警规则对象
            current_value: 当前传感器值
        """
        from db_models.alert_notification import AlertNotification
        
        # 查询该规则下所有 pending 预警
        pending_alerts = session.query(AlertNotification).filter(
            AlertNotification.alert_rule_id == rule.id,
            AlertNotification.status == 'pending'
        ).all()
        
        if not pending_alerts:
            return
        
        now = datetime.now(timezone.utc)
        resolved_count = 0
        
        for alert in pending_alerts:
            alert.status = 'resolved'
            alert.resolved_at = now
            # 追加恢复信息到内容
            alert.content = f"{alert.content} [自动恢复: 指标已恢复正常，当前值: {current_value}]"
            resolved_count += 1
        
        logger.info(
            f"规则 {rule.rule_id} 指标恢复正常，自动恢复 {resolved_count} 条预警"
        )
