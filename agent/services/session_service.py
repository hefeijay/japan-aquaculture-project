#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话服务 (Session Service)
"""
import json
import logging
import uuid
from typing import Optional
from datetime import datetime

from repositories.session_repository import (
    find_session_by_id,
    create_new_session,
)
from services.chat_history_service import get_history
from core.constants import DEFAULT_CONFIG_DATA

logger = logging.getLogger(__name__)


def initialize_session(session_id: Optional[str] = None, user_id: str = "default_user") -> dict:
    """
    初始化或加载会话
    
    如果提供了 session_id，则加载现有会话的配置和历史消息。
    如果未提供 session_id，则创建新会话并使用默认配置。
    
    Args:
        session_id: 会话ID（可选）
        user_id: 用户ID
        
    Returns:
        包含 session_id、messages 和 config 的字典
    """
    messages = []
    config = {}
    
    session_detail = None
    
    # 检查是否为现有会话
    if session_id:
        logger.info(f"加载现有会话: {session_id}")
        session_detail = find_session_by_id(session_id)
        
        if session_detail:
            # 加载配置（session_detail 现在是字典）
            if session_detail.get("config"):
                try:
                    config = json.loads(session_detail["config"])
                    # 确保 config 格式正确：rag 和 tool 应该是数组
                    if not isinstance(config.get("rag"), list):
                        config["rag"] = []
                    if not isinstance(config.get("tool"), list):
                        config["tool"] = []
                except json.JSONDecodeError:
                    logger.warning(f"会话 {session_id} 的配置格式错误，使用默认配置")
                    config = DEFAULT_CONFIG_DATA.copy()
            else:
                config = DEFAULT_CONFIG_DATA.copy()
            
            # 加载历史消息
            history_records = get_history(session_id, limit=100)  # 加载更多历史记录
            for msg in history_records:
                # 确保所有字段都有默认值，避免前端 marked.js 报错
                content = msg.get("content") or msg.get("message") or ""
                msg_dict = {
                    "id": msg.get("id"),
                    "session_id": msg.get("session_id") or "",
                    "role": msg.get("role", "user"),
                    "content": str(content) if content is not None else "",  # 确保是字符串，不为 None
                    "type": msg.get("type") or "",
                    "timestamp": msg.get("timestamp"),
                    "meta_data": msg.get("meta_data") or {},
                }
                # 转换时间戳
                if msg_dict.get("timestamp") and isinstance(msg_dict["timestamp"], datetime):
                    msg_dict["timestamp"] = int(msg_dict["timestamp"].timestamp())
                messages.append(msg_dict)
        else:
            # 会话不存在，创建新会话
            logger.info(f"会话 {session_id} 不存在，创建新会话")
            session_detail = create_new_session(session_id, user_id)
            config = DEFAULT_CONFIG_DATA.copy()
    else:
        # 创建新会话
        session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {session_id}, 用户: {user_id}")
        session_detail = create_new_session(session_id, user_id)
        config = DEFAULT_CONFIG_DATA.copy()
    
    # 返回给客户端的数据
    # 确保与原项目响应结构一致：只返回 session_id、messages 和 config
    # 确保 messages 始终是数组，避免前端 .includes() 报错
    # 确保 config 始终是有效的字典，不能为 None 或空
    if not isinstance(config, dict) or not config:
        config = DEFAULT_CONFIG_DATA.copy()
    
    # 确保 rag 和 tool 是数组（与原项目格式一致）
    if "rag" not in config or not isinstance(config.get("rag"), list):
        config["rag"] = []
    if "tool" not in config or not isinstance(config.get("tool"), list):
        config["tool"] = []
    
    if not isinstance(messages, list):
        messages = []
    
    # 构建返回结果，确保字段顺序与原项目一致
    # 原项目可能的字段顺序：session_id, messages, config
    # 使用 OrderedDict 或直接构建字典（Python 3.7+ 字典保持插入顺序）
    result = {
        "session_id": str(session_id) if session_id else "",
        "messages": messages,  # 确保是数组
        "config": config,  # 确保是有效的字典
    }
    
    # 确保所有字段都存在且类型正确
    assert "session_id" in result, "session_id 字段缺失"
    assert "messages" in result, "messages 字段缺失"
    assert "config" in result, "config 字段缺失"
    assert isinstance(result["messages"], list), "messages 必须是数组"
    assert isinstance(result["config"], dict), "config 必须是字典"
    assert result["config"], "config 不能为空"
    
    # 注意：原项目响应中不包含 user_id、created_at、updated_at、session_name、status、summary 等字段
    # 为了保持兼容性，只返回这三个核心字段
    
    return result

