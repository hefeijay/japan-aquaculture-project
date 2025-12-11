#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 主应用 - 参考 singa_one_server 的设计
"""
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
from services.chat_history_service import (
    save_message,
    get_history,
    format_history_for_llm,
    clear_history,
)

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
        
        # 1. 保存用户消息到历史记录
        save_message(
            session_id=session_id,
            role="user",
            message=user_message,
        )
        
        # 2. 意图识别（使用历史记录）
        intent, intent_stats = await intent_agent.get_intent(
            user_input=user_message,
            history=history,
        )
        
        # 2. 路由决策
        route_decision = await routing_agent.route_decision(
            user_input=user_message,
            intent=intent,
            context=context,
        )
        
        # 3. 根据决策执行操作
        response_content = ""
        tool_results = []
        
        if route_decision.get("needs_data", False):
            # 需要查询数据库
            # 简单的关键词匹配查询逻辑
            if "水温" in user_message or "温度" in user_message or "temp" in user_message.lower():
                # 查询温度数据
                # 注意：使用 ts_utc 或 recorded_at 进行排序
                query = db.query(SensorReading).filter(
                    SensorReading.metric == "temp"
                )
                # 优先使用 ts_utc，如果为空则使用 recorded_at
                # MySQL 不支持 NULLS LAST，使用 COALESCE 处理
                from sqlalchemy import func as sql_func
                readings = query.order_by(
                    sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                ).limit(10).all()
                
                if readings:
                    tool_results.append({
                        "type": "sensor_data",
                        "metric": "temp",
                        "readings": [
                            {
                                "value": float(r.value),
                                "unit": r.unit or r.type_name,
                                "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                "pool_id": r.pool_id,
                                "sensor_id": r.sensor_id,
                            }
                            for r in readings
                        ]
                    })
            
            elif "溶解氧" in user_message or "do" in user_message.lower() or "氧" in user_message:
                # 查询溶解氧数据
                query = db.query(SensorReading).filter(
                    SensorReading.metric == "do"
                )
                from sqlalchemy import func as sql_func
                readings = query.order_by(
                    sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                ).limit(10).all()
                
                if readings:
                    tool_results.append({
                        "type": "sensor_data",
                        "metric": "do",
                        "readings": [
                            {
                                "value": float(r.value),
                                "unit": r.unit or r.type_name,
                                "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                "pool_id": r.pool_id,
                                "sensor_id": r.sensor_id,
                            }
                            for r in readings
                        ]
                    })
            
            elif "ph" in user_message.lower() or "ph值" in user_message:
                # 查询pH数据
                query = db.query(SensorReading).filter(
                    SensorReading.metric == "ph"
                )
                from sqlalchemy import func as sql_func
                readings = query.order_by(
                    sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                ).limit(10).all()
                
                if readings:
                    tool_results.append({
                        "type": "sensor_data",
                        "metric": "ph",
                        "readings": [
                            {
                                "value": float(r.value),
                                "unit": r.unit or r.type_name,
                                "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                "pool_id": r.pool_id,
                                "sensor_id": r.sensor_id,
                            }
                            for r in readings
                        ]
                    })
        
        # 4. 使用 ThinkingAgent 生成回答（使用历史记录）
        analysis, stats = await thinking_agent.think(
            user_input=user_message,
            context={
                "intent": intent,
                "route_decision": route_decision,
                **context,
            },
            memory=history,  # 传入历史记录
            tool_results=tool_results if tool_results else None,
        )
        
        response_content = analysis
        
        # 5. 保存 AI 回答到历史记录
        save_message(
            session_id=session_id,
            role="assistant",
            message=response_content,
            intent=intent,
            metadata={
                "route_decision": route_decision,
                "data_used": bool(tool_results),
            },
        )
        
        return {
            "status": "success",
            "response": response_content,
            "intent": intent,
            "route_decision": route_decision,
            "data_used": tool_results if tool_results else None,
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
@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点 - 支持实时对话和数据流
    
    连接示例：
    ```javascript
    const ws = new WebSocket('ws://your-server:8001/');
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
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info("收到 WebSocket 消息", data=data)
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                session_id = message_data.get("session_id", f"ws_{websocket.client}")
                context = message_data.get("context", {})
                
                if not user_message:
                    await websocket.send_text(json.dumps({
                        "error": "消息格式错误：缺少 'message' 字段"
                    }, ensure_ascii=False))
                    continue
                
                # 1. 意图识别
                intent, intent_stats = await intent_agent.get_intent(
                    user_input=user_message,
                    history=[],
                )
                
                # 2. 路由决策
                route_decision = await routing_agent.route_decision(
                    user_input=user_message,
                    intent=intent,
                    context=context,
                )
                
                # 3. 根据决策执行操作
                tool_results = []
                
                if route_decision.get("needs_data", False):
                    # 需要查询数据库
                    from database import get_db
                    with get_db() as db:
                        # 简单的关键词匹配查询逻辑
                        if "水温" in user_message or "温度" in user_message or "temp" in user_message.lower():
                            query = db.query(SensorReading).filter(
                                SensorReading.metric == "temp"
                            )
                            from sqlalchemy import func as sql_func
                            readings = query.order_by(
                                sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                            ).limit(10).all()
                            
                            if readings:
                                tool_results.append({
                                    "type": "sensor_data",
                                    "metric": "temp",
                                    "readings": [
                                        {
                                            "value": float(r.value),
                                            "unit": r.unit or r.type_name,
                                            "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                            "pool_id": r.pool_id,
                                            "sensor_id": r.sensor_id,
                                        }
                                        for r in readings
                                    ]
                                })
                        
                        elif "溶解氧" in user_message or "do" in user_message.lower() or "氧" in user_message:
                            query = db.query(SensorReading).filter(
                                SensorReading.metric == "do"
                            )
                            from sqlalchemy import func as sql_func
                            readings = query.order_by(
                                sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                            ).limit(10).all()
                            
                            if readings:
                                tool_results.append({
                                    "type": "sensor_data",
                                    "metric": "do",
                                    "readings": [
                                        {
                                            "value": float(r.value),
                                            "unit": r.unit or r.type_name,
                                            "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                            "pool_id": r.pool_id,
                                            "sensor_id": r.sensor_id,
                                        }
                                        for r in readings
                                    ]
                                })
                        
                        elif "ph" in user_message.lower() or "ph值" in user_message:
                            query = db.query(SensorReading).filter(
                                SensorReading.metric == "ph"
                            )
                            from sqlalchemy import func as sql_func
                            readings = query.order_by(
                                sql_func.coalesce(SensorReading.ts_utc, SensorReading.recorded_at).desc()
                            ).limit(10).all()
                            
                            if readings:
                                tool_results.append({
                                    "type": "sensor_data",
                                    "metric": "ph",
                                    "readings": [
                                        {
                                            "value": float(r.value),
                                            "unit": r.unit or r.type_name,
                                            "timestamp": (r.ts_utc or r.recorded_at).isoformat() if (r.ts_utc or r.recorded_at) else None,
                                            "pool_id": r.pool_id,
                                            "sensor_id": r.sensor_id,
                                        }
                                        for r in readings
                                    ]
                                })
                
                # 4. 使用 ThinkingAgent 生成回答（使用历史记录）
                analysis, stats = await thinking_agent.think(
                    user_input=user_message,
                    context={
                        "intent": intent,
                        "route_decision": route_decision,
                        **context,
                    },
                    memory=history,  # 传入历史记录
                    tool_results=tool_results if tool_results else None,
                )
                
                # 5. 保存 AI 回答到历史记录
                save_message(
                    session_id=session_id,
                    role="assistant",
                    message=analysis,
                    intent=intent,
                    metadata={
                        "route_decision": route_decision,
                        "data_used": bool(tool_results),
                    },
                )
                
                # 6. 发送响应
                response = {
                    "status": "success",
                    "response": analysis,
                    "intent": intent,
                    "route_decision": route_decision,
                    "data_used": tool_results if tool_results else None,
                    "session_id": session_id,
                    "history_count": len(history) + 2,  # 包含刚保存的两条消息
                }
                
                await websocket.send_text(json.dumps(response, ensure_ascii=False))
                
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
