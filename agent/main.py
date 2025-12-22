#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 主应用 - 参考 singa_one_server 的设计
"""
import json
import logging
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

from config import settings
from database import get_db_session, Session
from graph import AquacultureOrchestrator
from models.sensor_reading import SensorReading
from agents.thinking_agent import ThinkingAgent
from agents.intent_agent import IntentAgent
from agents.routing_agent import RoutingAgent
from agents.query_rewriter import QueryRewriter
from agents.chat_agent import ChatAgent
from services.chat_history_service import (
    save_message,
    get_history,
    format_history_for_llm,
    clear_history,
)
from services.expert_consultation_service import expert_service
from services.session_service import initialize_session
from core.constants import MsgType

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.LOG_LEVEL),
)

logger = structlog.get_logger()

# 创建 FastAPI 应用
app = FastAPI(
    title="日本陆上养殖数据处理系统 - LangGraph 后端",
    description="基于 LangGraph 的养殖数据处理工作流系统",
    version="1.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化协调器和 Agents
orchestrator = AquacultureOrchestrator()
thinking_agent = ThinkingAgent()
intent_agent = IntentAgent()
routing_agent = RoutingAgent()
query_rewriter = QueryRewriter()
chat_agent = ChatAgent()  # 基础对话智能体，用于快速聊天


# Pydantic 模型
class SensorDataInput(BaseModel):
    """传感器数据输入"""
    device_id: int
    batch_id: Optional[int] = None
    pool_id: Optional[str] = None
    metric: str
    value: float
    unit: Optional[str] = None
    ts_utc: Optional[datetime] = None
    ts_local: Optional[datetime] = None


class FeederDataInput(BaseModel):
    """喂食机数据输入"""
    feeder_id: int
    batch_id: Optional[int] = None
    pool_id: Optional[str] = None
    feed_amount_g: Optional[float] = None
    run_time_s: Optional[int] = None
    status: str = "ok"
    leftover_estimate_g: Optional[float] = None
    ts_utc: Optional[datetime] = None
    ts_local: Optional[datetime] = None


class ImageDataInput(BaseModel):
    """图像数据输入"""
    camera_id: int
    batch_id: Optional[int] = None
    pool_id: Optional[str] = None
    storage_uri: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    format: Optional[str] = None
    detection: Optional[Dict[str, Any]] = None
    ts_utc: Optional[datetime] = None
    ts_local: Optional[datetime] = None


class ChatInput(BaseModel):
    """对话输入"""
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


# API 路由
@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "日本陆上养殖数据处理系统 - LangGraph 后端",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "sensor_data": "/api/v1/data/sensor",
            "sensor_readings": "/api/v1/sensor/readings",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/api/v1/chat")
async def chat(
    input: ChatInput,
    db: Session = Depends(get_db_session),
):
    """
    对话接口 - 支持自然语言查询养殖数据
    
    示例问题：
    - "查询1号池最近的水温数据"
    - "分析最近一周的溶解氧趋势"
    - "1号池的pH值是多少？"
    """
    try:
        user_message = input.message
        session_id = input.session_id or "default"
        context = input.context or {}
        
        # 0. 获取历史对话记录
        history_records = get_history(session_id, limit=20)
        history = format_history_for_llm(history_records)
        
        # 1. 保存用户消息到历史记录（保存原始消息）
        save_message(
            session_id=session_id,
            role="user",
            message=user_message,
        )
        
        # 2. 意图识别（使用原始问题，先判断是否需要专家）
        intent, intent_stats = await intent_agent.get_intent(
            user_input=user_message,  # 使用原始问题进行意图识别
            history=history,
        )
        
        # 3. 根据意图判断是否需要专家，如果需要则进行查询重写
        processed_query = user_message  # 默认使用原始问题
        needs_expert_by_intent = False
        
        # 判断意图是否需要专家（数据查询、统计分析等需要专家）
        expert_intents = ["数据查询", "统计分析", "历史记录", "数据查询", "数据分析"]
        if intent in expert_intents or "数据" in intent or "查询" in intent or "分析" in intent:
            needs_expert_by_intent = True
        
        # 如果需要专家，进行查询重写
        if needs_expert_by_intent:
            rewritten_query, rewrite_stats = await query_rewriter.rewrite(
                user_input=user_message,
                history=history,
                context=context,
            )
            
            # 打印重写结果
            print("=" * 80)
            print("📝 查询重写结果:")
            print(f"   原始问题: {user_message}")
            print(f"   重写后:   {rewritten_query}")
            print("=" * 80)
            logger.info("查询重写完成", original=user_message, rewritten=rewritten_query)
            
            processed_query = rewritten_query
        
        # 4. 路由决策（如果需要专家，使用重写后的问题；否则使用原始问题）
        route_decision = await routing_agent.route_decision(
            user_input=processed_query,  # 使用重写后的问题（如果需要专家）或原始问题
            intent=intent,
            context=context,
        )
        
        # 4. 根据路由决策执行操作
        response_content = ""
        expert_response = None
        
        # 如果需要调用专家，由专家负责数据查询和聚合
        if route_decision.get("needs_expert", False) or route_decision.get("needs_data", False):
            if settings.ENABLE_EXPERT_CONSULTATION:
                # 构建专家API配置（参考 cognitive_model/handlers/query_handler.py）
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
                
                # 咨询外部日本养殖专家（专家负责数据查询和聚合）
                expert_response = await expert_service.consult(
                    query=processed_query,  # 使用重写后的问题
                    context={
                        "original_query": user_message,
                        "intent": intent,
                        "route_decision": route_decision,
                        **context,
                    },
                    session_id=session_id,
                    config=expert_config,
                )
                
                if expert_response.get("success"):
                    print("=" * 80)
                    print("👨‍🔬 专家咨询结果:")
                    print(f"   专家回答: {expert_response.get('answer', '')[:100]}...")
                    print(f"   置信度: {expert_response.get('confidence', 0.0)}")
                    print("=" * 80)
                    logger.info("专家咨询成功", answer_preview=expert_response.get('answer', '')[:50])
                else:
                    print("=" * 80)
                    print("⚠️  专家咨询失败:")
                    print(f"   错误: {expert_response.get('error', '未知错误')}")
                    print("=" * 80)
                    logger.warning("专家咨询失败", error=expert_response.get('error'))
        
        # 如果不需要专家，使用基础对话智能体进行快速聊天（不进行数据查询）
        use_chat_agent = not expert_response and not (route_decision.get("needs_expert", False) or route_decision.get("needs_data", False))
        
        # 5. 使用 ThinkingAgent 生成最终回答（基于专家回答或数据查询结果）
        thinking_context = {
            "intent": intent,
            "route_decision": route_decision,
            "original_query": user_message,  # 保留原始问题供参考
            **context,
        }
        
        # 根据路由决策选择不同的处理方式
        if expert_response and expert_response.get("success"):
            # 情况1: 专家咨询成功，使用专家的回答作为主要输入
            thinking_context["expert_answer"] = expert_response.get("answer", "")
            thinking_context["expert_confidence"] = expert_response.get("confidence", 0.0)
            thinking_context["expert_sources"] = expert_response.get("sources", [])
            
            # 基于专家的回答生成最终回答
            analysis, stats = await thinking_agent.think(
                user_input=f"用户问题：{user_message}\n\n专家回答：{expert_response.get('answer', '')}",  # 将专家回答作为输入
                context=thinking_context,
                memory=history,  # 传入历史记录
                tool_results=None,  # 专家已经处理了数据查询，不需要tool_results
            )
        elif use_chat_agent:
            # 情况2: 不需要专家，使用基础对话智能体进行快速聊天
            print("=" * 80)
            print("💬 使用基础对话智能体 (REST API):")
            print(f"   用户问题: {user_message}")
            print("=" * 80)
            logger.info("使用基础对话智能体进行快速聊天")
            
            # 使用基础对话智能体（不进行数据查询）
            analysis, stats = await chat_agent.chat(
                user_input=user_message,  # 使用原始问题，保持对话自然
                context=thinking_context,
                memory=history,  # 传入历史记录
            )
        else:
            # 情况3: 需要专家但专家咨询失败，使用 ThinkingAgent 作为兜底
            logger.warning("专家咨询失败，使用 ThinkingAgent 作为兜底")
            analysis, stats = await thinking_agent.think(
                user_input=processed_query,  # 使用重写后的问题
                context=thinking_context,
                memory=history,  # 传入历史记录
                tool_results=None,  # 不进行数据查询
            )
        
        # 确保 response_content 不为 None，避免前端 marked.js 报错
        response_content = str(analysis) if analysis is not None else ""
        
        # 5. 保存 AI 回答到历史记录
        save_message(
            session_id=session_id,
            role="assistant",
            message=response_content,
            intent=intent,
            metadata={
                "route_decision": route_decision,
                "data_used": False,  # 不再使用 tool_results
                "expert_consulted": bool(expert_response and expert_response.get("success")),
                "chat_agent_used": use_chat_agent,  # 标记是否使用了基础对话智能体
            },
        )
        
        return {
            "status": "success",
            "response": response_content,  # 确保是字符串，不为 None
            "intent": intent if intent else "",
            "route_decision": route_decision if route_decision else {},
            "data_used": False,  # 不再使用 tool_results
            "chat_agent_used": use_chat_agent,  # 标记是否使用了基础对话智能体
            "session_id": session_id,
            "history_count": len(history) + 2,  # 包含刚保存的两条消息
        }
        
    except Exception as e:
        logger.error("对话处理失败", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理对话时发生错误: {str(e)}")


@app.post("/api/v1/data/sensor")
async def process_sensor_data(
    data: SensorDataInput,
    db: Session = Depends(get_db_session),
):
    """处理传感器数据"""
    try:
        input_dict = data.model_dump()
        if not input_dict.get("ts_utc"):
            input_dict["ts_utc"] = datetime.utcnow()
        
        result = await orchestrator.process(
            input_data=input_dict,
            data_type="sensor",
            session_id=f"sensor_{input_dict.get('device_id')}",
        )
        return result
    except Exception as e:
        logger.error("处理传感器数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/data/feeder")
async def process_feeder_data(
    data: FeederDataInput,
    db: Session = Depends(get_db_session),
):
    """处理喂食机数据"""
    try:
        input_dict = data.model_dump()
        if not input_dict.get("ts_utc"):
            input_dict["ts_utc"] = datetime.utcnow()
        
        result = await orchestrator.process(
            input_data=input_dict,
            data_type="feeder",
            session_id=f"feeder_{input_dict.get('feeder_id')}",
        )
        return result
    except Exception as e:
        logger.error("处理喂食机数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/data/image")
async def process_image_data(
    data: ImageDataInput,
    db: Session = Depends(get_db_session),
):
    """处理图像数据"""
    try:
        input_dict = data.model_dump()
        if not input_dict.get("ts_utc"):
            input_dict["ts_utc"] = datetime.utcnow()
        
        result = await orchestrator.process(
            input_data=input_dict,
            data_type="image",
            session_id=f"image_{input_dict.get('camera_id')}",
        )
        return result
    except Exception as e:
        logger.error("处理图像数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sensor/readings")
async def get_sensor_readings(
    batch_id: Optional[int] = None,
    pool_id: Optional[str] = None,
    metric: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db_session),
):
    """获取传感器读数"""
    try:
        query = db.query(SensorReading)
        
        if batch_id:
            query = query.filter(SensorReading.batch_id == batch_id)
        if pool_id:
            query = query.filter(SensorReading.pool_id == pool_id)
        if metric:
            query = query.filter(SensorReading.metric == metric)
        
        readings = query.order_by(SensorReading.ts_utc.desc()).limit(limit).all()
        
        result = [
            {
                "id": r.id,
                "device_id": r.device_id,
                "batch_id": r.batch_id,
                "pool_id": r.pool_id,
                "ts_utc": r.ts_utc.isoformat() if r.ts_utc else None,
                "metric": r.metric,
                "value": float(r.value) if r.value else None,
                "unit": r.unit,
                "quality_flag": r.quality_flag.value if r.quality_flag else None,
            }
            for r in readings
        ]
        
        return {"readings": result, "count": len(result)}
    except Exception as e:
        logger.error("获取传感器读数失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/chat/history")
async def get_chat_history(
    session_id: str,
    limit: int = 20,
    db: Session = Depends(get_db_session),
):
    """获取对话历史记录"""
    try:
        history_records = get_history(session_id, limit=limit)
        # get_history 现在返回字典列表，直接使用
        return {"history": history_records, "count": len(history_records), "session_id": session_id}
    except Exception as e:
        logger.error("获取对话历史失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/chat/history")
async def delete_chat_history(
    session_id: str,
    db: Session = Depends(get_db_session),
):
    """清除对话历史记录"""
    try:
        count = clear_history(session_id)
        return {"status": "success", "deleted": count, "session_id": session_id}
    except Exception as e:
        logger.error("清除对话历史失败", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket 路由
# 支持两个路径：/ 和 /ws
@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点 - 支持实时对话和数据流
    
    连接示例：
    ```javascript
    const ws = new WebSocket('ws://your-server:8000/');
    ws.onopen = () => {
        ws.send(JSON.stringify({message: '查询最近的水温数据'}));
    };
    ws.onmessage = (event) => {
        console.log(JSON.parse(event.data));
    };
    ```
    """
    await websocket.accept()
    logger.info("WebSocket 连接已建立", client=str(websocket.client))
    
    session_id = None  # 会话ID，在收到 init 消息后设置
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info("收到 WebSocket 消息", data=data)
            
            try:
                message_data = json.loads(data)
                msg_type = message_data.get("type")
                msg_data = message_data.get("data", {})
                
                # 处理心跳消息
                if msg_type == MsgType.PING:
                    await websocket.send_text(json.dumps({"type": MsgType.PONG}))
                    continue
                
                # 处理初始化消息
                if msg_type == MsgType.INIT:
                    init_session_id = msg_data.get("session_id")
                    user_id = msg_data.get("user_id", "default_user")
                    
                    # 初始化会话
                    init_data = initialize_session(init_session_id, user_id)
                    session_id = init_data["session_id"]
                    
                    # 返回初始化响应
                    response = {
                        "type": MsgType.INIT_RESPONSE,
                        "data": init_data
                    }
                    await websocket.send_text(json.dumps(response, ensure_ascii=False))
                    logger.info(f"会话初始化完成: {session_id}, 用户: {user_id}")
                    continue
                
                # 对于其他消息，需要先初始化会话
                if not session_id:
                    # 尝试从消息中获取 session_id
                    session_id = msg_data.get("session_id")
                    if not session_id:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "会话未初始化，请先发送 init 消息"
                        }, ensure_ascii=False))
                        continue
                
                # 处理用户消息
                if msg_type == MsgType.USER_SEND_MESSAGE or msg_type is None:
                    # 兼容旧的消息格式（没有 type 字段，直接是 message）
                    user_message = msg_data.get("content") or msg_data.get("message") or message_data.get("message", "")
                    context = msg_data.get("context", {}) or message_data.get("context", {})
                    
                    if not user_message:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "消息格式错误：缺少 'message' 或 'content' 字段"
                        }, ensure_ascii=False))
                        continue
                    
                    # 0. 获取历史对话记录
                    history_records = get_history(session_id, limit=20)
                    history = format_history_for_llm(history_records)
                    
                    # 1. 保存用户消息到历史记录（保存原始消息）
                    user_msg_data = save_message(
                        session_id=session_id,
                        role="user",
                        message=user_message,
                    )
                    
                    # 1.5. 立即返回用户消息确认（与原项目流程一致）
                    user_msg_type = msg_data.get("type", "text")  # 从请求中获取 type，默认为 "text"
                    user_response = {
                        "type": MsgType.NEW_CHAT_MESSAGE,
                        "data": {
                            "session_id": session_id,
                            "content": user_message,
                            "message_id": user_msg_data.get("message_id", ""),
                            "role": "user",
                            "timestamp": user_msg_data.get("timestamp", int(datetime.now().timestamp())),
                            "type": user_msg_type,
                        }
                    }
                    await websocket.send_text(json.dumps(user_response, ensure_ascii=False))
                    logger.info(f"已返回用户消息确认: message_id={user_msg_data.get('message_id')}")
                
                    # 2. 意图识别（使用原始问题，先判断是否需要专家）
                    intent, intent_stats = await intent_agent.get_intent(
                        user_input=user_message,  # 使用原始问题进行意图识别
                        history=history,
                    )
                    
                    # 3. 根据意图判断是否需要专家，如果需要则进行查询重写
                    processed_query = user_message  # 默认使用原始问题
                    needs_expert_by_intent = False
                    
                    # 判断意图是否需要专家（数据查询、统计分析等需要专家）
                    expert_intents = ["数据查询", "统计分析", "历史记录", "数据查询", "数据分析"]
                    if intent in expert_intents or "数据" in intent or "查询" in intent or "分析" in intent:
                        needs_expert_by_intent = True
                    
                    # 如果需要专家，进行查询重写
                    if needs_expert_by_intent:
                        rewritten_query, rewrite_stats = await query_rewriter.rewrite(
                            user_input=user_message,
                            history=history,
                            context=context,
                        )
                        
                        # 打印重写结果
                        print("=" * 80)
                        print("📝 查询重写结果 (WebSocket):")
                        print(f"   原始问题: {user_message}")
                        print(f"   重写后:   {rewritten_query}")
                        print("=" * 80)
                        logger.info("查询重写完成", original=user_message, rewritten=rewritten_query)
                        
                        processed_query = rewritten_query
                    
                    # 4. 路由决策（如果需要专家，使用重写后的问题；否则使用原始问题）
                    route_decision = await routing_agent.route_decision(
                        user_input=processed_query,  # 使用重写后的问题（如果需要专家）或原始问题
                        intent=intent,
                        context=context,
                    )
                    
                    # 4. 根据路由决策执行操作
                    expert_response = None
                    
                    # 如果需要调用专家，由专家负责数据查询和聚合
                    if route_decision.get("needs_expert", False) or route_decision.get("needs_data", False):
                        if settings.ENABLE_EXPERT_CONSULTATION:
                            # 构建专家API配置（参考 cognitive_model/handlers/query_handler.py）
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
                            
                            # 咨询外部日本养殖专家（专家负责数据查询和聚合）
                            expert_response = await expert_service.consult(
                                query=processed_query,  # 使用重写后的问题
                                context={
                                    "original_query": user_message,
                                    "intent": intent,
                                    "route_decision": route_decision,
                                    **context,
                                },
                                session_id=session_id,
                                config=expert_config,
                            )
                            
                            if expert_response.get("success"):
                                print("=" * 80)
                                print("👨‍🔬 专家咨询结果 (WebSocket):")
                                print(f"   专家回答: {expert_response.get('answer', '')[:100]}...")
                                print(f"   置信度: {expert_response.get('confidence', 0.0)}")
                                print("=" * 80)
                                logger.info("专家咨询成功", answer_preview=expert_response.get('answer', '')[:50])
                            else:
                                print("=" * 80)
                                print("⚠️  专家咨询失败 (WebSocket):")
                                print(f"   错误: {expert_response.get('error', '未知错误')}")
                                print("=" * 80)
                                logger.warning("专家咨询失败", error=expert_response.get('error'))
                    
                    # 如果不需要专家，使用基础对话智能体进行快速聊天（不进行数据查询）
                    use_chat_agent = not expert_response and not (route_decision.get("needs_expert", False) or route_decision.get("needs_data", False))
                
                    # 5. 生成 AI 回答（真正的流式返回，逐块发送）
                    import uuid
                    assistant_message_id = str(uuid.uuid4())
                    assistant_timestamp = int(datetime.now().timestamp())
                    
                    thinking_context = {
                        "intent": intent,
                        "route_decision": route_decision,
                        "original_query": user_message,  # 保留原始问题供参考
                        **context,
                    }
                    
                    # 累积 AI 回答内容（用于最后保存到数据库）
                    assistant_content = ""
                    
                    # 发送流式输出开始事件
                    stream_start_response = {
                        "type": MsgType.STREAM_CHUNK,
                        "data": {
                            "session_id": session_id,
                            "content": "",
                            "event": "start",
                            "message_id": assistant_message_id,
                            "role": "assistant",
                            "timestamp": assistant_timestamp,
                            "type": "stream_chunk",
                        }
                    }
                    await websocket.send_text(json.dumps(stream_start_response, ensure_ascii=False))
                    logger.debug(f"发送流式输出开始事件: message_id={assistant_message_id}")
                    
                    # 定义流式回调函数，用于逐块发送消息
                    async def stream_chunk_callback(chunk: str):
                        """流式回调函数，每收到一个块就立即发送给前端"""
                        nonlocal assistant_content
                        assistant_content += chunk  # 累积内容
                        
                        # 立即发送流式消息块（与原项目格式一致）
                        stream_response = {
                            "type": MsgType.STREAM_CHUNK,
                            "data": {
                                "session_id": session_id,
                                "content": chunk,  # 只发送当前块
                                "event": "content",
                                "message_id": assistant_message_id,
                                "role": "assistant",
                                "timestamp": assistant_timestamp,
                                "type": "stream_chunk",
                            }
                        }
                        await websocket.send_text(json.dumps(stream_response, ensure_ascii=False))
                    
                    # 根据路由决策选择不同的处理方式
                    if expert_response and expert_response.get("success"):
                        # 情况1: 专家咨询成功，使用专家的回答作为主要输入
                        thinking_context["expert_answer"] = expert_response.get("answer", "")
                        thinking_context["expert_confidence"] = expert_response.get("confidence", 0.0)
                        thinking_context["expert_sources"] = expert_response.get("sources", [])
                        
                        # 基于专家的回答生成最终回答（真正的流式输出）
                        analysis, stats = await thinking_agent.think(
                            user_input=f"用户问题：{user_message}\n\n专家回答：{expert_response.get('answer', '')}",  # 将专家回答作为输入
                            context=thinking_context,
                            memory=history,  # 传入历史记录
                            tool_results=None,  # 专家已经处理了数据查询，不需要tool_results
                            stream=True,  # 启用流式输出
                            stream_callback=stream_chunk_callback,  # 传入流式回调函数
                        )
                    elif use_chat_agent:
                        # 情况2: 不需要专家，使用基础对话智能体进行快速聊天
                        print("=" * 80)
                        print("💬 使用基础对话智能体 (WebSocket):")
                        print(f"   用户问题: {user_message}")
                        print("=" * 80)
                        logger.info("使用基础对话智能体进行快速聊天")
                        
                        # 使用基础对话智能体（不进行数据查询）
                        analysis, stats = await chat_agent.chat(
                            user_input=user_message,  # 使用原始问题，保持对话自然
                            context=thinking_context,
                            memory=history,  # 传入历史记录
                            stream=True,  # 启用流式输出
                            stream_callback=stream_chunk_callback,  # 传入流式回调函数
                        )
                    else:
                        # 情况3: 需要专家但专家咨询失败，使用 ThinkingAgent 作为兜底
                        logger.warning("专家咨询失败，使用 ThinkingAgent 作为兜底")
                        analysis, stats = await thinking_agent.think(
                            user_input=processed_query,  # 使用重写后的问题
                            context=thinking_context,
                            memory=history,  # 传入历史记录
                            tool_results=None,  # 不进行数据查询
                            stream=True,  # 启用流式输出
                            stream_callback=stream_chunk_callback,  # 传入流式回调函数
                        )
                    
                    # 确保 assistant_content 包含完整内容（如果回调没有正确累积，使用 analysis 作为后备）
                    if not assistant_content and analysis:
                        assistant_content = str(analysis)
                    
                    # 发送流式输出结束事件
                    stream_end_response = {
                        "type": MsgType.STREAM_CHUNK,
                        "data": {
                            "session_id": session_id,
                            "content": "",
                            "event": "end",
                            "message_id": assistant_message_id,
                            "role": "assistant",
                            "timestamp": int(datetime.now().timestamp()),
                            "type": "stream_chunk",
                        }
                    }
                    await websocket.send_text(json.dumps(stream_end_response, ensure_ascii=False))
                    logger.debug(f"发送流式输出结束事件: message_id={assistant_message_id}")
                    
                    # 6. 保存 AI 回答到历史记录
                    save_message(
                        session_id=session_id,
                        role="assistant",
                        message=assistant_content,
                        intent=intent,
                        metadata={
                            "route_decision": route_decision,
                            "data_used": False,  # 不再使用 tool_results
                            "expert_consulted": bool(expert_response and expert_response.get("success")),
                            "chat_agent_used": use_chat_agent,  # 标记是否使用了基础对话智能体
                        },
                    )
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "error": "消息格式错误：必须是有效的 JSON"
                }, ensure_ascii=False))
            except Exception as e:
                logger.error("处理 WebSocket 消息失败", error=str(e), exc_info=True)
                await websocket.send_text(json.dumps({
                    "error": f"处理消息时发生错误: {str(e)}"
                }, ensure_ascii=False))
                
    except WebSocketDisconnect:
        logger.info("WebSocket 连接已断开", client=str(websocket.client))
    except Exception as e:
        logger.error("WebSocket 连接错误", error=str(e), exc_info=True)
        try:
            await websocket.close()
        except:
            pass


# 添加 /ws 路径支持（与 / 路径使用相同的处理逻辑）
@app.websocket("/ws")
async def websocket_endpoint_ws(websocket: WebSocket):
    """WebSocket 端点 - /ws 路径（与 / 路径相同）"""
    await websocket_endpoint(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
