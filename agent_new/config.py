#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        project_root = backend_dir.parent
        root_env_path = project_root / ".env"
        if root_env_path.exists():
            load_dotenv(root_env_path, override=False)
        else:
            load_dotenv(override=False)
except ImportError:
    pass


class Settings(BaseSettings):
    """应用配置"""
    
    # ========== 数据库配置 ==========
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "aquaculture"
    
    # ========== OpenAI 配置 ==========
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "anthropic/claude-sonnet-4.5"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # ========== 服务配置 ==========
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # ========== 工作流配置 ==========
    MAX_RETRY_COUNT: int = 3
    ENABLE_AI_ANALYSIS: bool = True
    
    # ========== 外部专家服务配置 ==========
    EXPERT_API_BASE_URL: Optional[str] = "http://localhost:5003"
    EXPERT_API_KEY: Optional[str] = None
    EXPERT_API_TIMEOUT: int = 60
    ENABLE_EXPERT_CONSULTATION: bool = True
    
    # ========== 外部设备控制专家服务配置 ==========
    DEVICE_EXPERT_API_BASE_URL: Optional[str] = "http://localhost:5004"
    DEVICE_EXPERT_API_TIMEOUT: int = 60
    ENABLE_DEVICE_EXPERT: bool = True
    
    # ========== 联网搜索配置 (Serper) ==========
    SERPER_API_KEY: Optional[str] = None
    ENABLE_WEB_SEARCH: bool = True
    WEB_SEARCH_TIMEOUT: int = 10  # 秒
    
    # ========== 天气服务配置 (OpenWeatherMap) ==========
    OPENWEATHER_API_KEY: Optional[str] = None
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5/weather"
    WEATHER_DEFAULT_LOCATION: str = "Tsukuba"  # 默认城市
    WEATHER_LANG: str = "zh_cn"  # 返回语言（中文）
    ENABLE_WEATHER_SERVICE: bool = True  # 是否启用天气服务
    
    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# 全局配置实例
settings = Settings()
