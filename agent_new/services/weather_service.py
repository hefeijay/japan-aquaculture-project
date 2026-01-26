#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气查询服务 - 使用 OpenWeatherMap API
"""
import logging
import aiohttp
from typing import Dict, Any, Optional

from config import settings
from core.llm import llm_manager, format_messages

logger = logging.getLogger(__name__)


class WeatherService:
    """OpenWeatherMap 天气查询服务"""
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = settings.OPENWEATHER_BASE_URL
        self.default_location = settings.WEATHER_DEFAULT_LOCATION
        self.lang = settings.WEATHER_LANG
        self.enabled = settings.ENABLE_WEATHER_SERVICE
    
    async def needs_weather_query(self, user_input: str) -> bool:
        """
        判断用户输入是否需要查询天气（使用 LLM 判断）
        
        Args:
            user_input: 用户输入
            
        Returns:
            bool: 是否需要查询天气
        """
        if not self.enabled:
            return False
        
        if not self.api_key:
            logger.debug("未配置 OPENWEATHER_API_KEY，跳过天气判断")
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

        messages = format_messages(
            system_prompt=system_prompt,
            user_message=user_input,
        )
        
        try:
            response = await llm_manager.invoke(
                messages=messages,
                temperature=0,
            )
            result = response.strip()
            needs_weather = result == "是"
            logger.info(f"🌤️ 天气意图判断: {result} (需要查询: {needs_weather})")
            return needs_weather
        except Exception as e:
            logger.warning(f"天气意图判断失败: {e}")
            return False
    
    async def extract_city(self, text: str) -> str:
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

        messages = format_messages(
            system_prompt=system_prompt,
            user_message=text,
        )
        
        try:
            response = await llm_manager.invoke(
                messages=messages,
                temperature=0,
            )
            city = response.strip()
            logger.info(f"🌍 LLM提取城市: {city}")
            return city if city else self.default_location
        except Exception as e:
            logger.warning(f"城市提取失败: {e}, 使用默认城市 {self.default_location}")
            return self.default_location
    
    async def get_weather(self, city: str = None) -> Optional[Dict[str, Any]]:
        """
        调用 OpenWeatherMap API 获取天气
        
        Args:
            city: 城市英文名
            
        Returns:
            天气信息字典，失败返回 None
        """
        if not self.api_key:
            logger.warning("⚠️ 未配置 OPENWEATHER_API_KEY")
            return None
        
        city = city or self.default_location
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": self.lang,
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        weather_info = {
                            "city": data.get("name", city),
                            "temp": round(data["main"]["temp"], 1),
                            "feels_like": round(data["main"]["feels_like"], 1),
                            "humidity": data["main"]["humidity"],
                            "weather": data["weather"][0]["description"],
                            "wind_speed": data["wind"]["speed"],
                            "description": f"{data.get('name', city)}当前{data['weather'][0]['description']}，气温{round(data['main']['temp'], 1)}°C，湿度{data['main']['humidity']}%"
                        }
                        logger.info(f"🌤️ 天气查询成功: {weather_info['description']}")
                        return weather_info
                    else:
                        error_text = await response.text()
                        logger.error(f"天气 API 错误: {response.status} - {error_text}")
                        return None
                        
        except aiohttp.ClientTimeout:
            logger.warning(f"天气查询超时: {city}")
            return None
        except Exception as e:
            logger.error(f"天气查询失败: {e}", exc_info=True)
            return None
    
    async def check_and_query_weather(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        主入口：先判断是否需要查天气，如果需要则查询
        
        Args:
            user_input: 用户输入
            
        Returns:
            天气信息字典，不需要或失败返回 None
        """
        # 1. 先判断是否需要查询天气
        if not await self.needs_weather_query(user_input):
            return None
        
        # 2. 需要查询，用 LLM 提取城市并调用 API
        city = await self.extract_city(user_input)
        return await self.get_weather(city)
    
    def format_for_context(self, weather_info: Dict[str, Any]) -> str:
        """
        将天气信息格式化为上下文文本
        
        Args:
            weather_info: 天气信息字典
            
        Returns:
            str: 格式化后的文本
        """
        if not weather_info:
            return ""
        
        return f"""【当前天气信息】
城市: {weather_info.get('city', '未知')}
天气: {weather_info.get('weather', '未知')}
气温: {weather_info.get('temp', '未知')}°C
体感温度: {weather_info.get('feels_like', '未知')}°C
湿度: {weather_info.get('humidity', '未知')}%
风速: {weather_info.get('wind_speed', '未知')} m/s"""


# 全局实例
weather_service = WeatherService()

