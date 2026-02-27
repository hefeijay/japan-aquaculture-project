#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于数据库的AI决策服务模块
替代原有的随机生成逻辑，从数据库中获取和管理AI决策消息
"""

import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

# 导入数据库相关模块
from db_models.db_session import db_session_factory
from db_models.ai_decision import AIDecision, MessageType, DecisionRule


class AIDecisionService:
    """基于数据库的AI决策服务类"""
    
    @staticmethod
    def format_japanese_time() -> str:
        """
        格式化为日本时间格式
        
        Returns:
            格式化的时间字符串 (HH:MM:SS)
        """
        return datetime.now().strftime("%H:%M:%S")
    
    @classmethod
    def get_recent_decisions(cls, num_messages: int = 10, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """
        从数据库获取最近的AI决策消息
        
        Args:
            num_messages: 消息数量，默认为None时返回所有符合条件的消息
            max_age_hours: 最大消息年龄（小时），默认24小时
            
        Returns:
            AI决策消息列表
        """
        try:
            with db_session_factory() as session:
                # 计算时间范围
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
                
                # 构建查询
                query = session.query(AIDecision).filter(
                    and_(
                        AIDecision.status == 'active',
                        or_(
                            AIDecision.expires_at.is_(None),
                            AIDecision.expires_at > datetime.now(timezone.utc)
                        ),
                        AIDecision.created_at >= cutoff_time
                    )
                ).order_by(desc(AIDecision.priority), desc(AIDecision.created_at))
                
                # 限制数量
                query = query.limit(num_messages)
                
                decisions = query.all()
                
                # 转换为API格式
                result = []
                for decision in decisions:
                    # 获取消息类型配置
                    message_type = cls._get_message_type_config(session, decision.type)
                    
                    message_data = {
                        "id": decision.decision_id,
                        "timestamp": int(decision.created_at.timestamp() * 1000),
                        "type": decision.type,
                        "icon": message_type.get("icon", "🤖"),
                        "color": message_type.get("color", "#00a8cc"),
                        "message": decision.message,
                        "action": decision.action or "",
                        "time": decision.created_at.strftime("%H:%M:%S"),
                        "priority": decision.priority,
                        "confidence": float(decision.confidence) if decision.confidence else None,
                        "source": decision.source,
                        "source_id": decision.source_id
                    }
                    result.append(message_data)
                
                return result
                
        except Exception as e:
            print(f"获取AI决策消息时发生错误: {e}")
            # 如果数据库查询失败，返回空列表
            return []
    
    @classmethod
    def _get_message_type_config(cls, session: Session, message_type: str) -> Dict[str, str]:
        """
        获取消息类型配置
        
        Args:
            session: 数据库会话
            message_type: 消息类型
            
        Returns:
            消息类型配置字典
        """
        try:
            type_config = session.query(MessageType).filter(
                MessageType.type == message_type,
                MessageType.is_active == True
            ).first()
            
            if type_config:
                return {
                    "icon": type_config.icon,
                    "color": type_config.color
                }
            else:
                # 默认配置
                default_configs = {
                    "analysis": {"icon": "🔍", "color": "#00a8cc"},
                    "warning": {"icon": "⚠️", "color": "#ff6b35"},
                    "action": {"icon": "🎯", "color": "#20B2AA"},
                    "optimization": {"icon": "⚡", "color": "#41b3d3"}
                }
                return default_configs.get(message_type, {"icon": "🤖", "color": "#00a8cc"})
                
        except Exception as e:
            print(f"获取消息类型配置时发生错误: {e}")
            return {"icon": "🤖", "color": "#00a8cc"}
    
    @classmethod
    def create_decision(cls, 
                       decision_type: str,
                       message: str,
                       action: Optional[str] = None,
                       priority: int = 0,
                       source: Optional[str] = None,
                       source_id: Optional[str] = None,
                       confidence: Optional[float] = None,
                       expires_hours: Optional[int] = None) -> Optional[str]:
        """
        创建新的AI决策消息
        
        Args:
            decision_type: 决策类型 (analysis/warning/action/optimization)
            message: 消息内容
            action: 建议操作
            priority: 优先级 (0-10)
            source: 数据源类型
            source_id: 数据源ID
            confidence: 置信度 (0-100)
            expires_hours: 过期时间（小时）
            
        Returns:
            创建的决策ID，失败时返回None
        """
        try:
            with db_session_factory() as session:
                # 生成唯一ID
                decision_id = f"decision_{int(time.time() * 1000)}_{hash(message) % 10000}"
                
                # 计算过期时间
                expires_at = None
                if expires_hours:
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
                
                # 创建决策记录
                decision = AIDecision(
                    decision_id=decision_id,
                    type=decision_type,
                    message=message,
                    action=action,
                    priority=priority,
                    source=source,
                    source_id=source_id,
                    confidence=Decimal(str(confidence)) if confidence else None,
                    expires_at=expires_at
                )
                
                session.add(decision)
                session.commit()
                
                return decision_id
                
        except Exception as e:
            print(f"创建AI决策消息时发生错误: {e}")
            return None
    
    @classmethod
    def update_decision_status(cls, decision_id: str, status: str) -> bool:
        """
        更新决策状态
        
        Args:
            decision_id: 决策ID
            status: 新状态 (active/processed/expired)
            
        Returns:
            更新是否成功
        """
        try:
            with db_session_factory() as session:
                decision = session.query(AIDecision).filter(
                    AIDecision.decision_id == decision_id
                ).first()
                
                if decision:
                    decision.status = status
                    session.commit()
                    return True
                else:
                    return False
                    
        except Exception as e:
            print(f"更新决策状态时发生错误: {e}")
            return False
    
    @classmethod
    def cleanup_expired_decisions(cls) -> int:
        """
        清理过期的决策消息
        
        Returns:
            清理的消息数量
        """
        try:
            with db_session_factory() as session:
                # 标记过期消息
                expired_count = session.query(AIDecision).filter(
                    and_(
                        AIDecision.expires_at.isnot(None),
                        AIDecision.expires_at <= datetime.now(timezone.utc),
                        AIDecision.status == 'active'
                    )
                ).update({"status": "expired"})
                
                session.commit()
                return expired_count
                
        except Exception as e:
            print(f"清理过期决策消息时发生错误: {e}")
            return 0


class DecisionRuleEngine:
    """决策规则引擎"""
    
    @classmethod
    def evaluate_sensor_data(cls, sensor_data: Dict[str, Any]) -> List[str]:
        """
        基于传感器数据评估并生成决策
        
        Args:
            sensor_data: 传感器数据
            
        Returns:
            生成的决策ID列表
        """
        decision_ids = []
        
        try:
            with db_session_factory() as session:
                # 获取活跃的传感器相关规则
                rules = session.query(DecisionRule).filter(
                    and_(
                        DecisionRule.condition_type == 'sensor',
                        DecisionRule.is_active == True
                    )
                ).all()
                
                for rule in rules:
                    # 这里可以实现具体的规则评估逻辑
                    # 根据rule.condition_config解析条件并评估sensor_data
                    # 如果条件满足，则创建决策消息
                    pass
                    
        except Exception as e:
            print(f"评估传感器数据规则时发生错误: {e}")
        
        return decision_ids
    
    @classmethod
    def create_rule(cls, 
                   name: str,
                   condition_type: str,
                   condition_config: str,
                   message_template: str,
                   decision_type: str,
                   action_template: Optional[str] = None,
                   priority: int = 0) -> Optional[str]:
        """
        创建新的决策规则
        
        Args:
            name: 规则名称
            condition_type: 条件类型
            condition_config: 条件配置(JSON)
            message_template: 消息模板
            decision_type: 决策类型
            action_template: 操作模板
            priority: 优先级
            
        Returns:
            创建的规则ID，失败时返回None
        """
        try:
            with db_session_factory() as session:
                rule_id = f"rule_{int(time.time() * 1000)}_{hash(name) % 10000}"
                
                rule = DecisionRule(
                    rule_id=rule_id,
                    name=name,
                    condition_type=condition_type,
                    condition_config=condition_config,
                    message_template=message_template,
                    action_template=action_template,
                    decision_type=decision_type,
                    priority=priority
                )
                
                session.add(rule)
                session.commit()
                
                return rule_id
                
        except Exception as e:
            print(f"创建决策规则时发生错误: {e}")
            return None           