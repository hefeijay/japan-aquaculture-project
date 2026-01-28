#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 处理器
"""
import json
import uuid
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from core.constants import MsgType
from core.handler import chat_handler
from services.chat_history_service import get_history, format_history_for_llm
from services.session_service import initialize_session

logger = logging.getLogger(__name__)


async def handle_websocket(websocket: WebSocket):
    """
    WebSocket 处理入口
    
    支持：
    - init: 初始化会话
    - userSendMessage: 用户发送消息
    - ping/pong: 心跳
    """
    await websocket.accept()
    logger.info(f"WebSocket 连接已建立: {websocket.client}")
    
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"收到 WebSocket 消息: {data[:200]}...")
            
            try:
                message_data = json.loads(data)
                msg_type = message_data.get("type")
                msg_data = message_data.get("data", {})
                
                # 心跳处理
                if msg_type == MsgType.PING:
                    await websocket.send_text(json.dumps({"type": MsgType.PONG}))
                    continue
                
                # 初始化会话
                if msg_type == MsgType.INIT:
                    session_id = await _handle_init(websocket, msg_data)
                    continue
                
                # 检查会话是否已初始化
                if not session_id:
                    session_id = msg_data.get("session_id")
                    if not session_id:
                        await _send_error(websocket, "会话未初始化，请先发送 init 消息")
                        continue
                
                # 用户消息处理
                if msg_type == MsgType.USER_SEND_MESSAGE or msg_type is None:
                    await _handle_user_message(
                        websocket=websocket,
                        session_id=session_id,
                        msg_data=msg_data,
                        message_data=message_data,
                    )
                    
            except json.JSONDecodeError:
                await _send_error(websocket, "消息格式错误：必须是有效的 JSON")
            except Exception as e:
                logger.error(f"处理 WebSocket 消息失败: {e}", exc_info=True)
                await _send_error(websocket, f"处理消息时发生错误: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接已断开: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket 连接错误: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass


async def _handle_init(websocket: WebSocket, msg_data: dict) -> str:
    """处理会话初始化"""
    init_session_id = msg_data.get("session_id")
    user_id = msg_data.get("user_id", "default_user")
    
    # 初始化会话
    init_data = initialize_session(init_session_id, user_id)
    session_id = init_data["session_id"]
    
    # 返回初始化响应
    response = {
        "type": MsgType.INIT_RESPONSE,
        "data": init_data
    }
    await websocket.send_text(json.dumps(response, ensure_ascii=False))
    logger.info(f"会话初始化完成: {session_id}, 用户: {user_id}")
    
    return session_id


async def _handle_user_message(
    websocket: WebSocket,
    session_id: str,
    msg_data: dict,
    message_data: dict,
):
    """处理用户消息"""
    # 提取消息内容
    user_message = msg_data.get("content") or msg_data.get("message") or message_data.get("message", "")
    context = msg_data.get("context", {}) or message_data.get("context", {})
    
    if not user_message:
        await _send_error(websocket, "消息格式错误：缺少 'message' 或 'content' 字段")
        return
    
    # 生成用户消息的 message_id 和 timestamp（用于返回给前端）
    # 注意：用户消息的保存由 chat_handler.process() 统一处理，这里不再重复保存
    user_message_id = str(uuid.uuid4())
    user_timestamp = int(datetime.now().timestamp())
    
    # 返回用户消息确认
    user_msg_type = msg_data.get("type", "text")
    user_response = {
        "type": MsgType.NEW_CHAT_MESSAGE,
        "data": {
            "session_id": session_id,
            "content": user_message,
            "message_id": user_message_id,
            "role": "user",
            "timestamp": user_timestamp,
            "type": user_msg_type,
        }
    }
    await websocket.send_text(json.dumps(user_response, ensure_ascii=False))
    
    # 生成 AI 回答的 message_id
    assistant_message_id = str(uuid.uuid4())
    assistant_timestamp = int(datetime.now().timestamp())
    
    # 发送流式开始事件
    await _send_stream_event(websocket, session_id, assistant_message_id, assistant_timestamp, "start", "")
    
    # 累积回答内容
    assistant_content = ""
    
    # 定义流式回调
    async def stream_callback(chunk: str):
        nonlocal assistant_content
        assistant_content += chunk
        await _send_stream_event(websocket, session_id, assistant_message_id, assistant_timestamp, "content", chunk)
    
    try:
        # 调用核心处理器
        result = await chat_handler.process(
            query=user_message,
            session_id=session_id,
            context=context,
            stream_callback=stream_callback,
        )
        
        # 如果流式回调没有输出（某些分支可能直接返回），发送完整内容
        if not assistant_content and result.get("response"):
            assistant_content = result["response"]
            await _send_stream_event(websocket, session_id, assistant_message_id, assistant_timestamp, "content", assistant_content)
        
    except Exception as e:
        logger.error(f"处理用户消息失败: {e}", exc_info=True)
        error_msg = f"抱歉，处理您的问题时发生错误：{str(e)}"
        await _send_stream_event(websocket, session_id, assistant_message_id, assistant_timestamp, "content", error_msg)
        assistant_content = error_msg
    
    # 发送流式结束事件
    await _send_stream_event(websocket, session_id, assistant_message_id, int(datetime.now().timestamp()), "end", "")


async def _send_stream_event(
    websocket: WebSocket,
    session_id: str,
    message_id: str,
    timestamp: int,
    event: str,
    content: str,
):
    """发送流式事件"""
    response = {
        "type": MsgType.STREAM_CHUNK,
        "data": {
            "session_id": session_id,
            "content": content,
            "event": event,
            "message_id": message_id,
            "role": "assistant",
            "timestamp": timestamp,
            "type": "stream_chunk",
        }
    }
    await websocket.send_text(json.dumps(response, ensure_ascii=False))


async def _send_error(websocket: WebSocket, error: str):
    """发送错误消息"""
    response = {
        "type": "error",
        "error": error,
    }
    await websocket.send_text(json.dumps(response, ensure_ascii=False))

