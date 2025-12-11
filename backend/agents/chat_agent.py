#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础对话智能体 - 用于快速聊天，不进行数据查询
"""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    基础对话智能体
    
    用于快速聊天场景，不进行数据查询，只基于历史记录和上下文进行对话
    适用于：闲聊、一般性问题、不需要专业数据分析的对话
    """
    
    def __init__(self):
        """初始化基础对话智能体"""
        pass
    
    async def chat(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        memory: Optional[List[Dict[str, str]]] = None,
        model_config: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        进行基础对话
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可选）
            memory: 记忆/历史记录
            model_config: 模型配置
            stream: 是否流式返回
            stream_callback: 流式回调函数，接收 (chunk: str) -> None
            
        Returns:
            tuple: (回答内容, 统计信息)
        """
        system_prompt = """你是一个友好的AI助手，专门为日本陆上养殖系统提供对话服务。

你的特点：
1. 友好、专业、简洁
2. 能够进行自然对话
3. 对于需要数据查询的问题，建议用户使用更具体的查询方式
4. 用中文回答，语气自然亲切

注意：你不需要进行数据查询，只需要基于对话历史进行回答。如果用户询问具体数据，可以友好地引导用户使用更具体的查询方式。"""
        
        # 构建上下文信息（简化版，不包含数据查询结果）
        context_parts = []
        
        if context:
            # 只包含基本的上下文信息，不包含数据查询结果
            basic_context = {
                k: v for k, v in context.items() 
                if k not in ["tool_results", "data_used", "expert_response"]
            }
            if basic_context:
                context_parts.append(f"上下文信息：{basic_context}")
        
        context_str = "\n".join(context_parts) if context_parts else ""
        
        user_prompt = f"""{context_str}

用户问题：{user_input}

请基于对话历史，给出友好、自然的回答。"""
        
        config = format_config_for_llm(model_config)
        messages = format_messages_for_llm(system_prompt, memory or [])
        messages.append(HumanMessage(content=user_prompt))
        
        try:
            response_content, stats = await execute_llm_call(
                messages, 
                config, 
                stream=stream,
                stream_callback=stream_callback
            )
            
            logger.info("基础对话智能体生成回答成功")
            return response_content, stats
            
        except Exception as e:
            logger.error(f"基础对话智能体失败: {e}", exc_info=True)
            return f"抱歉，处理您的问题时发生错误：{str(e)}", {"error": str(e)}

