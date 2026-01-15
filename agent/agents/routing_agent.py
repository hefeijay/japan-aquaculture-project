#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由决策智能体 - 参考 cognitive_model/agents/routing_agent.py
"""
import logging
from typing import Dict, Any, List, Optional

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage
from json_repair import repair_json

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
            
            # 调试：打印原始响应
            print(f"🔍 RoutingAgent 原始响应: {response_content}")
            
            # 尝试解析 JSON
            import json
            import re
            try:
                # 1. 移除 markdown 代码块标记
                cleaned = response_content.strip()
                if "```json" in cleaned or "```" in cleaned:
                    cleaned = re.sub(r'```json\s*|\s*```', '', cleaned)
                    cleaned = cleaned.strip()
                
                # print(f"🔍 清洗后的内容: {cleaned[:200]}")
                
                # 2. 尝试直接用 json.loads 解析
                try:
                    decision = json.loads(cleaned)
                    print(f"✅ JSON 解析成功（json.loads）")
                except json.JSONDecodeError as e:
                    print(f"⚠️ json.loads 失败: {e}, 尝试 repair_json")
                    # 如果 json.loads 失败，尝试使用 repair_json
                    try:
                        decision = repair_json(cleaned, return_objects=True)  # 注意是 return_objects 不是 return_object
                        print(f"✅ JSON 解析成功（repair_json）")
                    except Exception as repair_error:
                        print(f"❌ repair_json 也失败: {repair_error}")
                        raise repair_error
                
                # 确保包含needs_expert字段
                if "needs_expert" not in decision:
                    decision["needs_expert"] = decision.get("needs_data", False)
                
                print(f"✅ 最终决策: {decision}")
                
            except Exception as parse_error:
                # 如果解析失败，使用默认决策
                print(f"❌ JSON 解析失败: {parse_error}")
                print(f"❌ 原始内容: {response_content[:300]}")
                decision = {
                    "decision": "直接回答",
                    "reason": f"无法解析路由决策: {str(parse_error)}",
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

