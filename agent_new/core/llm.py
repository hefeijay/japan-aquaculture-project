#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 管理器 - 统一管理 LLM 调用
"""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from openai import AsyncOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import settings

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM 管理器 - 单例模式"""
    
    _instance: Optional["LLMManager"] = None
    
    def __init__(self):
        """初始化 LLM 管理器"""
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.default_model = settings.OPENAI_MODEL
        self.default_temperature = settings.OPENAI_TEMPERATURE
        logger.info(f"LLM 管理器初始化完成: model={self.default_model}")
    
    @classmethod
    def get_instance(cls) -> "LLMManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """
        调用 LLM
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            model: 模型名称（可选，默认使用配置中的模型）
            temperature: 温度参数（可选）
            max_tokens: 最大 token 数（可选）
            stream: 是否流式返回
            stream_callback: 流式回调函数
            
        Returns:
            str: LLM 响应内容
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        
        # 准备 API 参数
        api_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        
        try:
            if stream and stream_callback:
                # 流式调用
                chunks = []
                response = await self.client.chat.completions.create(
                    **api_params,
                    stream=True
                )
                
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        chunks.append(content)
                        await stream_callback(content)
                
                return "".join(chunks)
            else:
                # 非流式调用
                response = await self.client.chat.completions.create(**api_params)
                return response.choices[0].message.content or ""
                
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}", exc_info=True)
            raise


def format_messages(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    格式化消息为 LLM API 格式
    
    Args:
        system_prompt: 系统提示词
        user_message: 用户消息
        history: 历史对话记录
        
    Returns:
        List[Dict]: 格式化的消息列表
    """
    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": user_message})
    
    return messages


def convert_langchain_messages(messages: List) -> List[Dict[str, str]]:
    """
    将 LangChain 消息转换为 OpenAI API 格式
    
    Args:
        messages: LangChain 消息列表
        
    Returns:
        List[Dict]: OpenAI API 格式的消息列表
    """
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            result.append(msg)
        elif isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
        elif hasattr(msg, 'content'):
            role = getattr(msg, 'type', 'user')
            if role == 'human':
                role = 'user'
            elif role == 'ai':
                role = 'assistant'
            result.append({"role": role, "content": msg.content})
    
    return result


# 全局实例
llm_manager = LLMManager.get_instance()

