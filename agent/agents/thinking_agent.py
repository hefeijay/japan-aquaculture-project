#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思考智能体 - 参考 cognitive_model/agents/thinking_agent.py
"""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ThinkingAgent:
    """
    思考智能体
    
    负责根据上下文、记忆和工具结果，生成深思熟虑的回答
    """
    
    def __init__(self):
        """初始化思考智能体"""
        pass
    
    async def think(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        memory: Optional[List[Dict[str, str]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        model_config: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        思考并生成回答
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            memory: 记忆/历史记录
            tool_results: 工具执行结果
            model_config: 模型配置
            stream: 是否流式返回
            stream_callback: 流式回调函数，接收 (chunk: str) -> None，用于真正的流式输出
            
        Returns:
            tuple: (回答内容, 统计信息)
        """
        system_prompt = """你是一个专业的养殖数据分析助手，专门处理日本陆上养殖的南美白对虾数据。

你的职责：
1. 准确理解用户的问题
2. 基于提供的数据和上下文进行分析
3. 给出专业、清晰的回答
4. 如果数据不足，明确说明需要哪些信息
5. 对用户进行进一步的引导，挖掘用户的意图或者进一步的问题。这些问题的格式为：
我可以继续帮助您了解：
1. 问题1 
2. 问题2 
3. 问题3”

请用中文回答，简洁明了，专业准确。"""
        
        # 构建上下文信息
        context_parts = []
        
        if context:
            context_parts.append(f"上下文信息：{context}")
        
        if tool_results:
            context_parts.append(f"工具执行结果：{tool_results}")
        
        context_str = "\n".join(context_parts) if context_parts else ""
        
        user_prompt = f"""{context_str}

用户问题：{user_input}

请基于以上信息，给出专业的回答。"""
        
        # 思考智能体基于已有数据分析，不需要搜索
        config = LLMConfig(
            model=model_config.get("model_name") if model_config else None,
            temperature=model_config.get("temperature") if model_config else None,
            max_tokens=model_config.get("max_tokens") if model_config else None,
            enable_search=False  # 思考分析禁用搜索
        )
        
        messages = format_messages_for_llm(system_prompt, memory or [])
        messages.append(HumanMessage(content=user_prompt))
        
        try:
            response_content, stats = await execute_llm_call(
                messages, 
                config, 
                stream=stream,
                stream_callback=stream_callback
            )
            
            logger.info("思考智能体生成回答成功")
            return response_content, stats
            
        except Exception as e:
            logger.error(f"思考智能体失败: {e}", exc_info=True)
            return f"抱歉，处理您的问题时发生错误：{str(e)}", {"error": str(e)}

