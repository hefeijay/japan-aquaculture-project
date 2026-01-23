#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询重写模块
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from prompts import load_prompt
from core.llm import llm_manager, format_messages

logger = logging.getLogger(__name__)


async def rewrite_query(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    重写用户查询
    
    Args:
        query: 用户原始输入
        history: 对话历史
        context: 上下文信息
        
    Returns:
        Tuple[str, Dict]: (重写后的查询, 统计信息)
    """
    try:
        # 加载查询重写提示词并填充时间
        now = datetime.now()
        system_prompt = load_prompt("query_rewriter").format(
            current_date=now.strftime("%Y年%m月%d日"),
            current_time=now.strftime("%H:%M:%S"),
        )
        
        # 构建历史上下文摘要
        history_context = ""
        if history and len(history) > 0:
            recent_history = history[-6:] if len(history) > 6 else history
            history_parts = []
            for msg in recent_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_parts.append(f"用户：{content}")
                elif role == "assistant":
                    history_parts.append(f"助手：{content}")
            history_context = "\n".join(history_parts)
        
        context_str = ""
        if context:
            context_str = f"\n额外上下文：{context}"
        
        user_prompt = f"""对话历史：
{history_context if history_context else "（无历史记录）"}{context_str}

用户当前问题：{query}

请基于对话历史，将用户问题重写为完整、明确的查询语句，适合发送给日本养殖专家。"""
        
        # 构建消息
        messages = format_messages(
            system_prompt=system_prompt,
            user_message=user_prompt,
        )
        
        # 调用 LLM
        response = await llm_manager.invoke(
            messages=messages,
            temperature=0.3,
        )
        
        # 清洗响应
        rewritten = response.strip().strip('"').strip("'")
        
        # 如果重写结果为空或异常，使用原问题
        if not rewritten or len(rewritten) < 2:
            logger.warning("查询重写结果为空，使用原问题")
            rewritten = query
        
        logger.info(f"📝 查询重写: '{query}' -> '{rewritten}'")
        
        return rewritten, {"model": llm_manager.default_model}
        
    except Exception as e:
        logger.error(f"查询重写失败: {e}", exc_info=True)
        return query, {"error": str(e)}

