#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目常量模块
"""

# 为新创建的会话提供的默认配置数据
# 注意：与原项目保持一致，rag 和 tool 应该是字符串数组（ID 列表）
DEFAULT_CONFIG_DATA = {
    # 默认模型配置
    "model": {
        "model_name": "gpt-4o-mini",
        "temperature": 0.7
    },
    # 默认工具配置（工具 ID 列表，字符串数组）
    "tool": [],
    # 默认RAG配置（RAG 集合 ID 列表，字符串数组）
    "rag": [],
    "token_count": 1024,
    "summary_amount": 5
}


class MsgType:
    """
    WebSocket 消息类型常量
    """
    # 客户端发送到服务器的消息类型
    PING = "ping"
    INIT = "init"
    USER_SEND_MESSAGE = "userSendMessage"
    UPDATE_CONFIG = "updateConfig"
    GET_SESSION_TOPIC = "getSessionTopic"
    
    # 服务器发送到客户端的消息类型
    PONG = "pong"
    INIT_RESPONSE = "init"  # 注意：与客户端请求类型相同
    NEW_CHAT_MESSAGE = "newChatMessage"
    UPDATE_CONFIG_ACK = "updateConfig_ack"
    GET_SESSION_TOPIC_RESPONSE = "getSessionTopicResponse"

