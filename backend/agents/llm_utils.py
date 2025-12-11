#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 工具函数 - 参考 cognitive_model/agents/llm_utils.py
"""
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import settings

logger = logging.getLogger(__name__)


class LLMConfig:
    """LLM 配置类"""
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.model = model or settings.OPENAI_MODEL
        self.temperature = temperature or settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens


def format_messages_for_llm(
    system_prompt: str,
    history: Optional[List[Dict[str, str]]] = None
) -> List:
    """格式化消息为 LLM 格式"""
    messages = [SystemMessage(content=system_prompt)]
    
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    return messages


def format_config_for_llm(model_config: Optional[Dict[str, Any]] = None) -> LLMConfig:
    """格式化 LLM 配置"""
    if model_config:
        return LLMConfig(
            model=model_config.get("model_name"),
            temperature=model_config.get("temperature"),
            max_tokens=model_config.get("max_tokens"),
        )
    return LLMConfig()


async def execute_llm_call(
    messages: List,
    config: Optional[LLMConfig] = None,
    stream: bool = False
) -> tuple[str, Dict[str, Any]]:
    """
    执行 LLM 调用
    
    Returns:
        tuple: (response_content, stats_dict)
    """
    config = config or LLMConfig()
    
    llm = ChatOpenAI(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        api_key=settings.OPENAI_API_KEY,
    )
    
    try:
        if stream:
            # 流式调用 - 收集所有块后返回完整内容
            # 注意：如果需要真正的流式输出，需要修改为生成器或回调函数
            chunks = []
            async for chunk in llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    chunks.append(chunk.content)
            response_content = "".join(chunks)
        else:
            # 非流式调用
            response = await llm.ainvoke(messages)
            response_content = response.content
        
        # 统计信息（简化版）
        stats = {
            "total_tokens": len(response_content.split()),  # 简化的 token 计数
            "model": config.model,
        }
        
        return response_content, stats
        
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}", exc_info=True)
        raise

