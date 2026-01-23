#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话历史记录服务
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from database import get_db
from models.chat_history import ChatHistory

logger = logging.getLogger(__name__)


def save_message(
    session_id: str,
    role: str,
    message: str,
    intent: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    保存对话消息到历史记录
    
    Args:
        session_id: 会话ID
        role: 角色 (user 或 assistant)
        message: 消息内容
        intent: 意图（可选，存储在 type 字段）
        metadata: 额外信息（可选，存储在 meta_data 字段）
        
    Returns:
        Dict: 包含完整消息信息的字典，包括 id, message_id, timestamp 等
    """
    try:
        import uuid
        from datetime import datetime
        with get_db() as db:
            # 生成 message_id (UUID)
            message_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            chat_record = ChatHistory(
                session_id=session_id,
                role=role,
                content=message,  # 使用 content 字段
                message_type=intent,  # 将 intent 存储在 type 字段（通过 message_type 属性）
                timestamp=timestamp,  # 使用 timestamp 字段
                message_id=message_id,  # 保存 message_id
                meta_data=json.dumps(metadata, ensure_ascii=False) if metadata else None,  # 使用 meta_data 字段
                updated_at=timestamp,
            )
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            
            # 获取 ID 后立即返回，避免会话分离问题
            record_id = chat_record.id
            
            # 返回完整的消息信息（与原项目格式一致）
            result = {
                "id": record_id,
                "message_id": message_id,
                "session_id": session_id,
                "role": role,
                "content": message,
                "type": intent or "text",  # 使用 intent 或默认 "text"
                "timestamp": int(timestamp.timestamp()),  # Unix 时间戳
            }
            
            logger.debug(f"保存对话记录: session_id={session_id}, role={role}, id={record_id}, message_id={message_id}")
            return result
    except Exception as e:
        logger.error(f"保存对话记录失败: {e}", exc_info=True)
        raise


def get_history(
    session_id: str,
    limit: int = 20,
    before_id: Optional[int] = None,
) -> List[Dict]:
    """
    获取对话历史记录
    
    Args:
        session_id: 会话ID
        limit: 返回的最大记录数
        before_id: 获取此ID之前的记录（用于分页）
        
    Returns:
        List[Dict]: 历史记录字典列表，按时间正序排列
    """
    try:
        with get_db() as db:
            query = db.query(ChatHistory).filter(
                ChatHistory.session_id == session_id
            )
            
            if before_id:
                query = query.filter(ChatHistory.id < before_id)
            
            # 使用 timestamp 字段排序（兼容 created_at）
            records = query.order_by(ChatHistory.timestamp.asc()).limit(limit).all()
            
            # 在会话关闭之前转换为字典，避免会话分离问题
            result = [record.to_dict() for record in records]
            
            logger.debug(f"获取对话历史: session_id={session_id}, count={len(result)}")
            return result
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        return []


def format_history_for_llm(history: List[Dict]) -> List[Dict[str, str]]:
    """
    将历史记录格式化为 LLM 需要的格式
    
    Args:
        history: 历史记录字典列表
        
    Returns:
        List[Dict[str, str]]: 格式化的历史记录，格式为 [{"role": "user", "content": "..."}, ...]
    """
    formatted = []
    for record in history:
        # record 现在是字典，直接访问键
        message_content = record.get("message") or record.get("content") or ""
        role = record.get("role")
        if message_content and role:  # 只添加有效的记录
            formatted.append({
                "role": role,
                "content": message_content,
            })
    return formatted


def clear_history(session_id: str) -> int:
    """
    清除指定会话的历史记录
    
    Args:
        session_id: 会话ID
        
    Returns:
        int: 删除的记录数
    """
    try:
        with get_db() as db:
            count = db.query(ChatHistory).filter(
                ChatHistory.session_id == session_id
            ).delete()
            db.commit()
            
            logger.info(f"清除对话历史: session_id={session_id}, deleted={count}")
            return count
    except Exception as e:
        logger.error(f"清除对话历史失败: {e}", exc_info=True)
        return 0

