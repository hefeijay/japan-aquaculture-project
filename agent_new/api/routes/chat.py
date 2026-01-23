#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天 API 路由
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any

from database import get_db_session, Session
from core.handler import chat_handler
from services.chat_history_service import get_history, clear_history

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 请求/响应模型 ==========

class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """对话响应"""
    status: str
    response: str
    intent: Optional[str] = None
    session_id: str
    metadata: Optional[Dict[str, Any]] = None


# ========== API 路由 ==========

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db_session),
):
    """
    对话接口 - 支持自然语言查询养殖数据
    
    示例问题：
    - "查询1号池最近的水温数据"
    - "分析最近一周的溶解氧趋势"
    - "给AI2喂食2份"
    """
    try:
        result = await chat_handler.process(
            query=request.message,
            session_id=request.session_id or "default",
            context=request.context or {},
        )
        
        return ChatResponse(
            status=result.get("status", "success"),
            response=result.get("response", ""),
            intent=result.get("intent"),
            session_id=result.get("session_id", request.session_id),
            metadata=result.get("metadata"),
        )
        
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理对话时发生错误: {str(e)}")


@router.get("/chat/history")
async def get_chat_history(
    session_id: str,
    limit: int = 20,
    db: Session = Depends(get_db_session),
):
    """获取对话历史记录"""
    try:
        history_records = get_history(session_id, limit=limit)
        return {
            "history": history_records,
            "count": len(history_records),
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/history")
async def delete_chat_history(
    session_id: str,
    db: Session = Depends(get_db_session),
):
    """清除对话历史记录"""
    try:
        count = clear_history(session_id)
        return {
            "status": "success",
            "deleted": count,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"清除对话历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

