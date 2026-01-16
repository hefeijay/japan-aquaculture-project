#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询重写智能体 - 基于上下文重写用户问题
"""
import logging
from typing import Dict, Any, List, Optional

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    查询重写智能体
    
    负责基于对话历史和上下文，将用户的简短问题重写为更完整、更明确的查询
    例如：
    - "那pH值呢？" -> "查询最近的水温数据对应的pH值"
    - "再查一下" -> "查询刚才讨论的溶解氧数据的最新值"
    """
    
    def __init__(self):
        """初始化查询重写智能体"""
        pass
    
    async def rewrite(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        重写用户查询
        
        Args:
            user_input: 用户原始输入
            history: 对话历史
            context: 上下文信息
            model_config: 模型配置
            
        Returns:
            tuple: (重写后的查询, 统计信息)
        """
        now = datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M:%S")
        system_prompt = f"""你是一个查询重写专家，专门处理日本陆上养殖数据查询的上下文理解。
【重要】当前时间信息：
- 今天是：{current_date}
- 当前时间：{current_time}

你的任务：
1. 分析用户的简短问题（如"那pH值呢？"、"再查一下"等）
2. 结合对话历史，理解用户的真实意图
3. 将问题拆分成更具体、更明确的问题，适合发送给日本养殖专家进行数据查询和分析

重写原则：
- 如果用户使用了代词（"那"、"它"、"这个"等），需要明确指代的内容
- 如果用户说"再查一下"、"还有吗"等，需要基于历史记录推断查询内容
- 将复杂问题拆分成多个具体问题（如果需要）
- 保持原问题的核心意图，补充完整信息
- 如果问题已经很完整，可以保持原样或稍作优化
- 使用专业术语，确保问题清晰明确，便于专家进行数据查询和聚合
- 【时间处理】对于相对时间表述（如"最近两天"、"昨天"、"上周"），保持原样，不需要转换为具体日期，如果一定要转换，请使用当前时间作为参考。

示例：
- 历史：用户问"查询水温"，AI回答"水温是25.5°C"
- 用户："那pH值呢？" -> 重写为："查询当前养殖池的pH值数据，包括最新值和历史趋势"
- 用户："分析一下水质" -> 重写为："查询当前养殖池的水质数据，包括pH值、溶解氧、温度等关键指标，并进行综合分析"
- 用户："再查一下" -> 重写为："查询刚才讨论的水温数据的最新值和变化趋势"

请只返回重写后的查询，不要添加其他解释。"""
        # 构建历史上下文摘要
        history_context = ""
        if history and len(history) > 0:
            # 只取最近3轮对话作为上下文
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

用户当前问题：{user_input}

请基于对话历史，将用户问题重写为完整、明确的查询语句，适合发送给日本养殖专家。"""
        
        # 查询重写不需要搜索，显式禁用
        config = LLMConfig(
            model=model_config.get("model_name") if model_config else None,
            temperature=model_config.get("temperature") if model_config else None,
            max_tokens=model_config.get("max_tokens") if model_config else None,
            enable_search=False  # 查询重写禁用搜索
        )
        
        messages = format_messages_for_llm(system_prompt)
        messages.append(HumanMessage(content=user_prompt))
        
        try:
            response_content, stats = await execute_llm_call(messages, config)
            
            # 清洗响应
            rewritten_query = response_content.strip().strip('"').strip("'")
            
            # 如果重写结果为空或异常，使用原问题
            if not rewritten_query or len(rewritten_query) < 2:
                logger.warning("查询重写结果为空，使用原问题")
                rewritten_query = user_input
            
            logger.info(f"查询重写: '{user_input}' -> '{rewritten_query}'")
            return rewritten_query, stats
            
        except Exception as e:
            logger.error(f"查询重写失败: {e}", exc_info=True)
            # 失败时返回原问题
            return user_input, {"error": str(e)}

