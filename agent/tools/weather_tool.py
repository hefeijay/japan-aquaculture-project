#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气查询工具 - 使用 OpenWeatherMap API
"""
import httpx
from typing import Dict, Any, Optional
from config import settings
from agents.llm_utils import execute_llm_call, format_messages_for_llm, LLMConfig
from langchain_core.messages import HumanMessage


async def extract_city(text: str) -> str:
    """
    用 LLM 从文本中智能提取日本城市名（英文）
    
    Args:
        text: 用户输入
        
    Returns:
        str: 英文城市名
    """
    system_prompt = """你是一个日本城市名提取助手。从用户输入中提取日本城市名，返回英文名称。

规则：
1. 只识别日本城市
2. 如果用户提到日本城市（中文、日文或英文），返回该城市的英文名
3. 如果没有明确提到城市，返回默认城市：Tsukuba
4. 只返回城市英文名，不要有其他任何内容

示例：
- "东京天气怎么样" → Tokyo
- "大阪明天会下雨吗" → Osaka
- "京都的气温" → Kyoto
- "筑波天气" → Tsukuba
- "今天天气如何" → Tsukuba
- "适合喂食吗" → Tsukuba"""

    messages = format_messages_for_llm(system_prompt)
    messages.append(HumanMessage(content=text))
    
    try:
        # 显式禁用搜索，只需要简单的城市名提取
        response, _ = await execute_llm_call(
            messages, 
            LLMConfig(temperature=0, enable_search=False)
        )
        city = response.strip()
        print(f"🌍 LLM提取城市: {city}")
        return city if city else "Tsukuba"
    except Exception as e:
        print(f"❌ 城市提取失败: {e}, 使用默认城市 Tsukuba")
        return "Tsukuba"


async def needs_weather_query(user_input: str) -> bool:
    """
    判断用户输入是否需要查询天气（使用 LLM 判断）
    
    Args:
        user_input: 用户输入
        
    Returns:
        bool: 是否需要查询天气
    """
    if not settings.ENABLE_WEATHER_SERVICE:
        return False
    
    system_prompt = """你是一个判断助手。请判断用户的输入是否涉及天气查询需求。

涉及天气的情况（返回 是）：
- 直接询问天气：今天天气怎么样、气温多少、会下雨吗
- 结合天气的操作：天气适合喂食吗、根据天气调整投喂

不涉及天气的情况（返回 否）：
- 纯设备操作：帮我喂食、打开摄像头
- 纯数据查询：查询水温数据、分析溶解氧
- 闲聊：你好、谢谢

请只回答"是"或"否"，不要有其他内容。"""

    messages = format_messages_for_llm(system_prompt)
    messages.append(HumanMessage(content=user_input))
    
    try:
        # 显式禁用搜索，只需要简单的是/否判断
        response, _ = await execute_llm_call(
            messages, 
            LLMConfig(temperature=0, enable_search=False)
        )
        result = response.strip()
        needs_weather = result == "是"
        print(f"🌤️ 天气意图判断: {result} (需要查询: {needs_weather})")
        return needs_weather
    except Exception as e:
        print(f"❌ 天气意图判断失败: {e}")
        return False


async def get_weather(city: str = "Tokyo") -> Optional[Dict[str, Any]]:
    """
    调用 OpenWeatherMap API 获取天气
    
    Args:
        city: 城市英文名
        
    Returns:
        天气信息字典，失败返回 None
    """
    if not settings.OPENWEATHER_API_KEY:
        print("⚠️ 未配置 OPENWEATHER_API_KEY")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                settings.OPENWEATHER_BASE_URL,
                params={
                    "q": city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": settings.WEATHER_LANG
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            weather_info = {
                "city": data.get("name", city),
                "temp": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "humidity": data["main"]["humidity"],
                "weather": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "description": f"{data.get('name', city)}当前{data['weather'][0]['description']}，气温{round(data['main']['temp'], 1)}°C，湿度{data['main']['humidity']}%"
            }
            print(f"🌤️ 天气查询成功: {weather_info['description']}")
            return weather_info
            
    except Exception as e:
        print(f"❌ 天气查询失败: {e}")
        return None


async def check_and_query_weather(user_input: str) -> Optional[Dict[str, Any]]:
    """
    主入口：先判断是否需要查天气，如果需要则查询
    
    Args:
        user_input: 用户输入
        
    Returns:
        天气信息字典，不需要或失败返回 None
    """
    # 1. 先判断是否需要查询天气
    if not await needs_weather_query(user_input):
        return None
    
    # 2. 需要查询，用 LLM 提取城市并调用API
    city = await extract_city(user_input)
    return await get_weather(city)
