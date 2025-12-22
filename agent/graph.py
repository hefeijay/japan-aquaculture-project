#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 状态图定义 - 参考 cognitive_model/orchestrator.py
"""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from state import AquacultureState
from agents.intent_agent import IntentAgent
from agents.routing_agent import RoutingAgent
from agents.thinking_agent import ThinkingAgent
from handlers.sensor_handler import SensorHandler
from handlers.image_handler import ImageHandler
from handlers.feeder_handler import FeederHandler
from config import settings

logger = logging.getLogger(__name__)


class AquacultureOrchestrator:
    """
    养殖数据处理协调器 - 参考 CognitiveOrchestrator
    
    使用 LangGraph 构建状态图工作流，协调各个组件完成数据处理任务
    """
    
    def __init__(self):
        """初始化协调器"""
        # 初始化 Agents
        self.intent_agent = IntentAgent()
        self.routing_agent = RoutingAgent()
        self.thinking_agent = ThinkingAgent()
        
        # 初始化 Handlers
        self.sensor_handler = SensorHandler()
        self.image_handler = ImageHandler()
        self.feeder_handler = FeederHandler()
        
        # Handler 映射
        self.handler_map = {
            "sensor": self.sensor_handler,
            "image": self.image_handler,
            "feeder": self.feeder_handler,
        }
        
        # 配置
        self.config = {
            "ENABLE_AI_ANALYSIS": settings.ENABLE_AI_ANALYSIS,
            "MAX_RETRY_COUNT": settings.MAX_RETRY_COUNT,
        }
        
        # 构建状态图
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(AquacultureState)
        
        # 添加节点
        workflow.add_node("intent_recognition", self.intent_recognition)
        workflow.add_node("routing_decision", self.routing_decision)
        workflow.add_node("data_validation", self.data_validation)
        workflow.add_node("data_cleaning", self.data_cleaning)
        workflow.add_node("handler_process", self.handler_process)
        workflow.add_node("ai_analysis", self.ai_analysis)
        workflow.add_node("response_generation", self.response_generation)
        workflow.add_node("error_handling", self.error_handling)
        
        # 设置入口点
        workflow.set_entry_point("intent_recognition")
        
        # 添加边
        workflow.add_edge("intent_recognition", "routing_decision")
        workflow.add_edge("routing_decision", "data_validation")
        
        workflow.add_conditional_edges(
            "data_validation",
            self.should_continue_after_validation,
            {
                "continue": "data_cleaning",
                "error": "error_handling",
            }
        )
        
        workflow.add_edge("data_cleaning", "handler_process")
        
        workflow.add_conditional_edges(
            "handler_process",
            self.should_analyze,
            {
                "analyze": "ai_analysis",
                "skip": "response_generation",
            }
        )
        
        workflow.add_edge("ai_analysis", "response_generation")
        workflow.add_edge("response_generation", END)
        workflow.add_edge("error_handling", END)
        
        return workflow.compile()
    
    async def intent_recognition(self, state: AquacultureState) -> AquacultureState:
        """意图识别节点"""
        logger.info("开始意图识别", session_id=state.get("session_id"))
        
        try:
            user_input = state.get("user_input", "")
            history = []  # 可以从 state 中获取历史记录
            
            intent, stats = await self.intent_agent.get_intent(
                user_input=user_input,
                history=history,
            )
            
            state["intent"] = intent
            state["nodes_completed"] = state.get("nodes_completed", [])
            state["nodes_completed"].append("intent_recognition")
            state["current_node"] = "intent_recognition"
            
            logger.info(f"意图识别完成: {intent}")
            
        except Exception as e:
            logger.error(f"意图识别失败: {e}", exc_info=True)
            state["error"] = f"意图识别失败: {str(e)}"
            state["should_continue"] = False
        
        return state
    
    async def routing_decision(self, state: AquacultureState) -> AquacultureState:
        """路由决策节点"""
        logger.info("开始路由决策", session_id=state.get("session_id"))
        
        try:
            user_input = state.get("user_input", "")
            intent = state.get("intent", "")
            data_type = state.get("data_type", "")
            
            # 根据数据类型决定处理路径
            if data_type in self.handler_map:
                state["current_node"] = "routing_decision"
                state["nodes_completed"] = state.get("nodes_completed", [])
                state["nodes_completed"].append("routing_decision")
                state["should_continue"] = True
            else:
                # 如果没有明确的数据类型，使用路由智能体
                decision = await self.routing_agent.route_decision(
                    user_input=user_input,
                    intent=intent,
                )
                state["routing_decision"] = decision
            
            logger.info("路由决策完成")
            
        except Exception as e:
            logger.error(f"路由决策失败: {e}", exc_info=True)
            state["error"] = f"路由决策失败: {str(e)}"
            state["should_continue"] = False
        
        return state
    
    async def data_validation(self, state: AquacultureState) -> AquacultureState:
        """数据验证节点"""
        logger.info("开始数据验证", session_id=state.get("session_id"))
        
        try:
            input_data = state.get("input_data", {})
            data_type = state.get("data_type", "")
            
            # 根据数据类型选择验证逻辑
            if data_type == "sensor":
                # 传感器数据验证逻辑已在 handler 中实现
                state["validation_result"] = {"valid": True}
            else:
                state["validation_result"] = {"valid": True}
            
            state["current_node"] = "data_validation"
            state["nodes_completed"] = state.get("nodes_completed", [])
            state["nodes_completed"].append("data_validation")
            state["should_continue"] = True
            
            logger.info("数据验证完成")
            
        except Exception as e:
            logger.error(f"数据验证失败: {e}", exc_info=True)
            state["error"] = f"数据验证失败: {str(e)}"
            state["should_continue"] = False
        
        return state
    
    async def data_cleaning(self, state: AquacultureState) -> AquacultureState:
        """数据清洗节点"""
        logger.info("开始数据清洗", session_id=state.get("session_id"))
        
        try:
            input_data = state.get("input_data", {})
            # 数据清洗逻辑已在 handler 中实现，这里只是标记
            state["cleaned_data"] = input_data
            state["current_node"] = "data_cleaning"
            state["nodes_completed"] = state.get("nodes_completed", [])
            state["nodes_completed"].append("data_cleaning")
            state["should_continue"] = True
            
            logger.info("数据清洗完成")
            
        except Exception as e:
            logger.error(f"数据清洗失败: {e}", exc_info=True)
            state["error"] = f"数据清洗失败: {str(e)}"
            state["should_continue"] = False
        
        return state
    
    async def handler_process(self, state: AquacultureState) -> AquacultureState:
        """处理器执行节点"""
        logger.info("开始处理器执行", session_id=state.get("session_id"))
        
        try:
            data_type = state.get("data_type", "")
            handler = self.handler_map.get(data_type)
            
            if handler:
                state = await handler.handle(self, state)
            else:
                logger.warning(f"未找到数据类型 {data_type} 对应的处理器")
                state["error"] = f"不支持的数据类型: {data_type}"
                state["should_continue"] = False
            
            state["current_node"] = "handler_process"
            
        except Exception as e:
            logger.error(f"处理器执行失败: {e}", exc_info=True)
            state["error"] = f"处理器执行失败: {str(e)}"
            state["should_continue"] = False
        
        return state
    
    async def ai_analysis(self, state: AquacultureState) -> AquacultureState:
        """AI 分析节点"""
        logger.info("开始AI分析", session_id=state.get("session_id"))
        
        try:
            if not self.config.get("ENABLE_AI_ANALYSIS", True):
                state["ai_analysis"] = {"skipped": True}
                return state
            
            user_input = state.get("user_input", "")
            context = {
                "data_type": state.get("data_type"),
                "db_result": state.get("db_result"),
            }
            
            analysis, stats = await self.thinking_agent.think(
                user_input=user_input,
                context=context,
            )
            
            state["ai_analysis"] = {
                "analysis": analysis,
                "stats": stats,
            }
            state["current_node"] = "ai_analysis"
            state["nodes_completed"] = state.get("nodes_completed", [])
            state["nodes_completed"].append("ai_analysis")
            
            logger.info("AI分析完成")
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}", exc_info=True)
            state["ai_analysis"] = {"error": str(e)}
        
        return state
    
    async def response_generation(self, state: AquacultureState) -> AquacultureState:
        """响应生成节点"""
        logger.info("生成最终响应", session_id=state.get("session_id"))
        
        response = {
            "status": "success" if not state.get("error") else "error",
            "nodes_completed": state.get("nodes_completed", []),
            "db_result": state.get("db_result"),
            "ai_analysis": state.get("ai_analysis"),
        }
        
        if state.get("error"):
            response["error"] = state["error"]
        
        # 生成完整响应文本
        full_response = f"数据处理完成。状态: {response['status']}"
        if state.get("ai_analysis") and "analysis" in state["ai_analysis"]:
            full_response += f"\n\nAI分析:\n{state['ai_analysis']['analysis']}"
        
        state["response"] = response
        state["full_response"] = full_response
        state["current_node"] = "response_generation"
        
        logger.info("响应生成完成", status=response["status"])
        
        return state
    
    async def error_handling(self, state: AquacultureState) -> AquacultureState:
        """错误处理节点"""
        logger.error("处理错误", error=state.get("error"), session_id=state.get("session_id"))
        
        state["response"] = {
            "status": "error",
            "error": state.get("error"),
            "nodes_completed": state.get("nodes_completed", []),
        }
        state["full_response"] = f"处理失败: {state.get('error')}"
        state["current_node"] = "error_handling"
        
        return state
    
    def should_continue_after_validation(self, state: AquacultureState) -> Literal["continue", "error"]:
        """验证后的条件判断"""
        if state.get("error") or not state.get("should_continue", True):
            return "error"
        return "continue"
    
    def should_analyze(self, state: AquacultureState) -> Literal["analyze", "skip"]:
        """判断是否需要AI分析"""
        if state.get("error"):
            return "skip"
        
        if self.config.get("ENABLE_AI_ANALYSIS", True) and state.get("data_type") in ["sensor", "image"]:
            return "analyze"
        
        return "skip"
    
    async def process(self, input_data: dict, data_type: str, session_id: str = "default") -> dict:
        """
        处理数据的主入口
        
        Args:
            input_data: 输入数据
            data_type: 数据类型
            session_id: 会话ID
            
        Returns:
            dict: 处理结果
        """
        initial_state: AquacultureState = {
            "user_input": str(input_data),
            "session_id": session_id,
            "data_type": data_type,
            "input_data": input_data,
            "current_node": "start",
            "nodes_completed": [],
            "error": None,
            "intent": None,
            "intent_confidence": None,
            "validation_result": None,
            "cleaned_data": None,
            "db_result": None,
            "ai_analysis": None,
            "response": None,
            "full_response": None,
            "batch_id": input_data.get("batch_id"),
            "pool_id": input_data.get("pool_id"),
            "device_id": input_data.get("device_id"),
            "timestamp": None,
            "should_continue": True,
            "retry_count": 0,
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result.get("response", {})

