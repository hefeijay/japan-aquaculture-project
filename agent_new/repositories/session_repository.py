#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话仓库 (Session Repository)
"""
import json
import logging
from typing import Optional
from datetime import datetime, timezone

from database import get_db
from models.session import Session
from core.constants import DEFAULT_CONFIG_DATA

logger = logging.getLogger(__name__)


def find_session_by_id(session_id: str) -> Optional[dict]:
    """
    根据会话ID查找会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话字典或 None（包含所有字段，避免会话关闭后访问属性的问题）
    """
    try:
        with get_db() as db:
            session = db.query(Session).filter_by(session_id=session_id).first()
            if session:
                # 在会话关闭前提取所有需要的数据
                return {
                    "id": session.id,
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "config": session.config,
                    "status": session.status,
                    "session_name": session.session_name,
                    "summary": session.summary,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
            return None
    except Exception as e:
        logger.error(f"查找会话失败: {e}", exc_info=True)
        return None


def create_new_session(session_id: str, user_id: str = "default_user") -> dict:
    """
    创建新会话
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        
    Returns:
        新创建的会话字典（包含所有字段，避免会话关闭后访问属性的问题）
    """
    try:
        with get_db() as db:
            new_session = Session(
                session_id=session_id,
                user_id=user_id,
                config=json.dumps(DEFAULT_CONFIG_DATA, ensure_ascii=False, indent=2),
                status="active",
                session_name="new chat",
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            logger.info(f"创建新会话: {session_id}, 用户: {user_id}")
            # 在会话关闭前提取所有需要的数据
            return {
                "id": new_session.id,
                "session_id": new_session.session_id,
                "user_id": new_session.user_id,
                "config": new_session.config,
                "status": new_session.status,
                "session_name": new_session.session_name,
                "summary": new_session.summary,
                "created_at": new_session.created_at,
                "updated_at": new_session.updated_at,
            }
    except Exception as e:
        logger.error(f"创建会话失败: {e}", exc_info=True)
        raise


def update_session_config(session: Session, new_config: dict):
    """
    更新会话配置
    
    Args:
        session: Session 对象
        new_config: 新配置字典
    """
    try:
        with get_db() as db:
            db.add(session)
            session.config = json.dumps(new_config, ensure_ascii=False, indent=2)
            db.commit()
            logger.info(f"更新会话配置: {session.session_id}")
    except Exception as e:
        logger.error(f"更新会话配置失败: {e}", exc_info=True)
        raise


def delete_session(session_id: str) -> bool:
    """
    删除会话（用于清理空会话）
    
    Args:
        session_id: 会话ID
        
    Returns:
        是否删除成功
    """
    try:
        with get_db() as db:
            result = db.query(Session).filter_by(session_id=session_id).delete()
            db.commit()
            logger.info(f"删除空会话: {session_id}")
            return result > 0
    except Exception as e:
        logger.error(f"删除会话失败: {e}", exc_info=True)
        return False


def update_session_name(session_id: str, session_name: str) -> bool:
    """
    更新会话名称
    
    Args:
        session_id: 会话ID
        session_name: 新的会话名称
        
    Returns:
        是否更新成功
    """
    try:
        with get_db() as db:
            result = db.query(Session).filter_by(session_id=session_id).update({
                "session_name": session_name
            })
            db.commit()
            logger.info(f"更新会话名称: {session_id} -> {session_name}")
            return result > 0
    except Exception as e:
        logger.error(f"更新会话名称失败: {e}", exc_info=True)
        return False


def touch_session(session_id: str) -> bool:
    """
    更新会话的 updated_at 时间（每次对话时调用）
    
    Args:
        session_id: 会话ID
        
    Returns:
        是否更新成功
    """
    try:
        with get_db() as db:
            result = db.query(Session).filter_by(session_id=session_id).update({
                "updated_at": datetime.now(timezone.utc)
            })
            db.commit()
            return result > 0
    except Exception as e:
        logger.error(f"更新会话时间失败: {e}", exc_info=True)
        return False
