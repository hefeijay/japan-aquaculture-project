#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心处理逻辑 - 统一处理 REST 和 WebSocket 请求
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from config import settings
from prompts import load_prompt
from core.llm import llm_manager, format_messages
from core.intent import recognize_intent, needs_expert, is_device_control, is_casual_chat
from core.query_rewriter import rewrite_query
from services.expert_consultation_service import expert_service
from services.device_expert_service import device_expert_service
from services.chat_history_service import save_message, get_history, format_history_for_llm
from services.web_search_service import web_search_service
from services.weather_service import weather_service

logger = logging.getLogger(__name__)


class ChatHandler:
    """
    聊天处理器 - 核心业务逻辑
    
    处理流程:
    1. 意图识别
    2. 根据意图路由到不同处理分支
    3. 所有结果最终通过 thinking agent 整合输出
    """
    
    def __init__(self):
        pass
    
    async def process(
        self,
        query: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        处理用户请求
        
        Args:
            query: 用户输入
            session_id: 会话 ID
            context: 上下文信息
            stream_callback: 流式回调函数（用于 WebSocket）
            
        Returns:
            Dict: 处理结果
        """
        logger.info(f"🚀 收到请求 | session={session_id} | query={query[:30]}...")
        context = context or {}
        
        # 1. 获取历史对话记录
        history_records = get_history(session_id, limit=20)
        history = format_history_for_llm(history_records)
        
        # 2. 保存用户消息
        save_message(session_id=session_id, role="user", message=query)
        
        # 3. 🔥 启动联网搜索任务（并行，不阻塞主流程）
        search_task = asyncio.create_task(web_search_service.search(query))
        logger.info(f"🔍 联网搜索任务已启动")
        
        # 4. 意图识别
        intent, intent_stats = await recognize_intent(query, history)
        logger.info(f"🎯 意图: {intent}")
        
        # 5. 🌤️ 天气查询（判断是否需要查天气，需要则查询）
        weather_info = await weather_service.check_and_query_weather(query)
        if weather_info:
            context["weather_info"] = weather_info
            context["weather_queried"] = True
            logger.info(f"🌤️ 已将天气信息添加到上下文: {weather_info.get('description', '')}")
        else:
            logger.info(f"🌤️ 无需查询天气或查询失败")
        
        # 6. 根据意图处理（传入 search_task，在 thinking 阶段合并）
        response_content = ""
        metadata = {"intent": intent}
        
        try:
            if is_device_control(intent):
                # 设备控制分支
                logger.info(f"→ 设备控制")
                response_content, metadata = await self._handle_device_control(
                    query=query,
                    session_id=session_id,
                    context=context,
                    history=history,
                    stream_callback=stream_callback,
                    search_task=search_task,
                )
            elif needs_expert(intent):
                # 数据查询/分析分支 - 需要专家
                logger.info(f"→ 数据专家")
                response_content, metadata = await self._handle_expert_query(
                    query=query,
                    session_id=session_id,
                    context=context,
                    history=history,
                    intent=intent,
                    stream_callback=stream_callback,
                    search_task=search_task,
                )
            else:
                # 闲聊分支
                logger.info(f"→ 闲聊")
                response_content, metadata = await self._handle_casual_chat(
                    query=query,
                    context=context,
                    history=history,
                    stream_callback=stream_callback,
                    search_task=search_task,
                )
            
            metadata["intent"] = intent
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}", exc_info=True)
            response_content = f"抱歉，处理您的问题时发生错误：{str(e)}"
            metadata["error"] = str(e)
        
        # 5. 保存 AI 回答
        save_message(
            session_id=session_id,
            role="assistant",
            message=response_content,
            intent=intent,
            metadata=metadata,
        )
        
        logger.info(f"✅ 完成 | intent={intent}")
        
        return {
            "status": "success" if "error" not in metadata else "error",
            "response": response_content,
            "intent": intent,
            "session_id": session_id,
            "metadata": metadata,
        }
    
    async def _handle_device_control(
        self,
        query: str,
        session_id: str,
        context: Dict[str, Any],
        history: List[Dict[str, str]],
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        search_task: Optional[asyncio.Task] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """处理设备控制请求"""
        
        if not settings.ENABLE_DEVICE_EXPERT:
            return "设备控制功能未启用，请联系管理员", {"device_expert_enabled": False}
        
        try:
            # 调用设备专家服务
            device_response = await device_expert_service.consult(
                query=query,
                session_id=session_id,
                context=context,
                stream_callback=stream_callback,
            )
            
            if device_response.get("success"):
                # 提取设备专家的回答
                result = device_response.get("result", {})
                messages = result.get("messages", [])
                if messages:
                    device_answer = messages[0].get("content", "设备操作完成")
                else:
                    device_answer = "设备操作完成"
                
                # 🔥 等待联网搜索结果
                search_result = {}
                if search_task:
                    try:
                        search_result = await search_task
                        logger.info(f"🔍 联网搜索完成，结果数: {len(search_result.get('results', []))}")
                    except Exception as e:
                        logger.warning(f"联网搜索失败: {e}")
                
                logger.info(f"→ thinking整合")
                # 通过 thinking agent 整合输出
                final_response = await self._thinking_integrate(
                    user_query=query,
                    raw_answer=device_answer,
                    source="设备专家",
                    context=context,
                    history=history,
                    stream_callback=stream_callback,
                    search_result=search_result,
                )
                
                return final_response, {
                    "device_expert_used": True,
                    "device_type": device_response.get("device_type"),
                    "success": True,
                    "web_search_used": search_result.get("success", False),
                }
            else:
                error = device_response.get("error", "未知错误")
                logger.error(f"❌ 设备专家失败: {error}")
                return f"抱歉，设备操作失败：{error}", {
                    "device_expert_used": True,
                    "success": False,
                    "error": error,
                }
                
        except Exception as e:
            logger.error(f"设备控制失败: {e}", exc_info=True)
            return f"抱歉，设备控制时发生错误：{str(e)}", {"error": str(e)}
    
    async def _handle_expert_query(
        self,
        query: str,
        session_id: str,
        context: Dict[str, Any],
        history: List[Dict[str, str]],
        intent: str,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        search_task: Optional[asyncio.Task] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """处理需要专家的数据查询/分析请求"""
        
        # 查询重写
        rewritten_query, rewrite_stats = await rewrite_query(
            query=query,
            history=history,
            context=context,
        )
        
        if not settings.ENABLE_EXPERT_CONSULTATION:
            # 专家未启用，使用兜底
            logger.warning(f"⚠️ 数据专家未启用")
            return await self._handle_casual_chat(
                query=rewritten_query,
                context=context,
                history=history,
                stream_callback=stream_callback,
                search_task=search_task,
            )
        
        try:
            # 调用专家服务
            expert_config = {
                "rag": {
                    "collection_name": "japan_shrimp",
                    "topk_single": 5,
                    "topk_multi": 5
                },
                "mode": "single",
                "single": {
                    "temperature": 0.4,
                    "system_prompt": "你是一个日本陆上养殖领域的专家，你的任务是根据用户的问题，结合增强检索后的相关知识，进行数据查询、聚合分析，并给出专业的结论和建议。",
                    "max_tokens": 4096
                }
            }
            
            expert_response = await expert_service.consult(
                query=rewritten_query,
                context={
                    "original_query": query,
                    "intent": intent,
                    **context,
                },
                session_id=session_id,
                config=expert_config,
            )
            
            if expert_response.get("success"):
                expert_answer = expert_response.get("answer", "")
                
                # 🔥 等待联网搜索结果
                search_result = {}
                if search_task:
                    try:
                        search_result = await search_task
                        logger.info(f"🔍 联网搜索完成，结果数: {len(search_result.get('results', []))}")
                    except Exception as e:
                        logger.warning(f"联网搜索失败: {e}")
                
                logger.info(f"→ thinking整合")
                # 通过 thinking agent 整合输出
                final_response = await self._thinking_integrate(
                    user_query=query,
                    raw_answer=expert_answer,
                    source="养殖专家",
                    context=context,
                    history=history,
                    stream_callback=stream_callback,
                    search_result=search_result,
                )
                
                return final_response, {
                    "expert_consulted": True,
                    "confidence": expert_response.get("confidence", 0.0),
                    "web_search_used": search_result.get("success", False),
                }
            else:
                # 专家咨询失败，使用兜底
                logger.warning(f"⚠️ 数据专家失败: {expert_response.get('error')}")
                return await self._handle_casual_chat(
                    query=rewritten_query,
                    context=context,
                    history=history,
                    stream_callback=stream_callback,
                    search_task=search_task,
                )
                
        except Exception as e:
            logger.error(f"专家咨询失败: {e}", exc_info=True)
            return await self._handle_casual_chat(
                query=rewritten_query,
                context=context,
                history=history,
                stream_callback=stream_callback,
                search_task=search_task,
            )
    
    async def _handle_casual_chat(
        self,
        query: str,
        context: Dict[str, Any],
        history: List[Dict[str, str]],
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        search_task: Optional[asyncio.Task] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """处理闲聊请求"""
        
        # 加载闲聊提示词
        system_prompt = load_prompt("chat")
        
        # 构建消息
        messages = format_messages(
            system_prompt=system_prompt,
            user_message=query,
            history=history,
        )
        
        # 调用 LLM 获取初步回答
        raw_answer = await llm_manager.invoke(
            messages=messages,
            stream=False,  # 先不流式，等 thinking 整合时再流式
        )
        
        # 🔥 等待联网搜索结果
        search_result = {}
        if search_task:
            try:
                search_result = await search_task
                logger.info(f"🔍 联网搜索完成，结果数: {len(search_result.get('results', []))}")
            except Exception as e:
                logger.warning(f"联网搜索失败: {e}")
        
        # 🔥 通过 thinking agent 整合输出（统一在这里使用搜索结果）
        logger.info(f"→ thinking整合")
        final_response = await self._thinking_integrate(
            user_query=query,
            raw_answer=raw_answer,
            source="聊天助手",
            context=context,
            history=history,
            stream_callback=stream_callback,
            search_result=search_result,
        )
        
        return final_response, {
            "chat_agent_used": True,
            "web_search_used": search_result.get("success", False),
        }
    
    async def _thinking_integrate(
        self,
        user_query: str,
        raw_answer: str,
        source: str,
        context: Dict[str, Any],
        history: List[Dict[str, str]],
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        search_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        通过 thinking agent 整合输出
        
        所有外部服务（专家、设备）的回答都通过这里整合，
        确保输出格式一致、专业。
        
        Args:
            user_query: 用户原始问题
            raw_answer: 原始回答（来自专家或设备服务）
            source: 回答来源（如"养殖专家"、"设备专家"）
            context: 上下文信息
            history: 对话历史
            stream_callback: 流式回调
            search_result: 联网搜索结果（可选）
            
        Returns:
            str: 整合后的回答
        """
        # 加载 thinking 提示词
        system_prompt = load_prompt("thinking")
        
        # 构建整合提示
        user_prompt = f"""用户问题：{user_query}

{source}回答：
{raw_answer}"""
        
        # 🌤️ 如果有天气信息，追加到提示中
        if context.get("weather_info"):
            weather_text = weather_service.format_for_context(context["weather_info"])
            if weather_text:
                user_prompt += f"""

{weather_text}"""
        
        # 🔥 如果有联网搜索结果，追加到提示中
        if search_result:
            search_text = web_search_service.format_for_llm(search_result)
            if search_text:
                user_prompt += f"""

{search_text}"""
        
        user_prompt += """

请基于以上信息，整合并优化回答，确保：
1. 回答专业、准确
2. 格式清晰、易读
3. 如有天气信息，结合天气给出建议
4. 如有联网搜索结果，可参考补充最新信息
5. 如有必要，补充引导问题"""
        
        # 构建消息
        messages = format_messages(
            system_prompt=system_prompt,
            user_message=user_prompt,
            history=history,
        )
        
        # 调用 LLM
        response = await llm_manager.invoke(
            messages=messages,
            stream=stream_callback is not None,
            stream_callback=stream_callback,
        )
        
        return response


# 全局处理器实例
chat_handler = ChatHandler()

