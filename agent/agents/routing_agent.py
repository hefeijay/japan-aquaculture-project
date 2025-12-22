#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由决策智能体 - 参考 cognitive_model/agents/routing_agent.py
"""
import logging
from typing import Dict, Any, List, Optional

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class RoutingAgent:
    """
    路由决策智能体
    
    负责决定处理用户请求的最佳路径（是否需要工具、需要哪些工具等）
    """
    
    def __init__(self):
        """初始化路由决策智能体"""
        pass
    
    async def route_decision(
        self,
        user_input: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        做出路由决策
        
        Args:
            user_input: 用户输入
            intent: 识别的意图
            context: 上下文信息
            model_config: 模型配置
            
        Returns:
            dict: 路由决策结果
        """
        system_prompt = """你是一个路由决策专家。根据用户意图和输入，决定是否需要调用日本养殖专家进行数据查询和分析。

决策选项：
1. 需要调用专家（needs_expert: true, needs_data: true）- 当用户询问数据、统计、历史记录、需要专业分析时
2. 不需要调用专家（needs_expert: false, needs_data: false）- 当用户只是聊天、询问一般性问题时

注意：如果需要数据查询和分析，应该调用专家服务，由专家负责数据查询、聚合和结论输出。

请返回JSON格式：
{
    "decision": "调用专家|直接回答",
    "reason": "决策理由",
    "needs_expert": true/false,
    "needs_data": true/false
}
"""
        
        context_str = ""
        if context:
            context_str = f"\n上下文信息：{context}"
        
        user_prompt = f"""用户意图：{intent}
用户输入：{user_input}{context_str}

请做出路由决策。"""
        
        config = format_config_for_llm(model_config)
        messages = format_messages_for_llm(system_prompt)
        messages.append(HumanMessage(content=user_prompt))
        
        try:
            response_content, stats = await execute_llm_call(messages, config)
            
            # 尝试解析 JSON（简化版，实际应该用 json.loads）
            import json
            try:
                decision = json.loads(response_content)
                # 确保包含needs_expert字段
                if "needs_expert" not in decision:
                    decision["needs_expert"] = decision.get("needs_data", False)
            except:
                # 如果解析失败，使用默认决策
                decision = {
                    "decision": "直接回答",
                    "reason": "无法解析路由决策",
                    "needs_expert": False,
                    "needs_data": False
                }
            
            logger.info(f"路由决策: {decision.get('decision')}")
            return decision
            
        except Exception as e:
            logger.error(f"路由决策失败: {e}", exc_info=True)
            return {
                "decision": "直接回答",
                "reason": f"路由决策失败: {str(e)}",
                "needs_expert": False,
                "needs_data": False
            }

