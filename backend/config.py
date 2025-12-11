#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 参考 singa_one_server/core/config.py
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# 在导入 Settings 之前，尝试加载 .env 文件
# 这样可以确保 pydantic-settings 能够正确读取环境变量
try:
    from dotenv import load_dotenv
    # 优先从 backend 目录加载 .env
    backend_dir = Path(__file__).parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        # 如果 backend/.env 不存在，尝试从项目根目录加载
        project_root = backend_dir.parent
        root_env_path = project_root / ".env"
        if root_env_path.exists():
            load_dotenv(root_env_path, override=False)
        else:
            # 最后尝试从当前工作目录加载
            load_dotenv(override=False)
except ImportError:
    # 如果没有 python-dotenv，手动解析 .env 文件
    backend_dir = Path(__file__).parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith("#"):
                        continue
                    # 解析 KEY=VALUE 格式
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # 仅在未设置时设置，避免覆盖已有环境变量
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass  # 静默失败，不影响后续配置加载


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "aquaculture"
    
    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.7
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WS_PORT: int = 8001  # WebSocket 端口
    DEBUG: bool = False
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # 工作流配置
    MAX_RETRY_COUNT: int = 3
    ENABLE_AI_ANALYSIS: bool = True
    
    # 外部专家服务配置（参考 cognitive_model/tools/tools.json）
    EXPERT_API_BASE_URL: Optional[str] = "http://localhost:5003"  # 专家API基础地址，默认: "http://localhost:5003"
    EXPERT_API_KEY: Optional[str] = None  # 专家API密钥（可选）
    EXPERT_API_TIMEOUT: int = 60  # 专家API超时时间（秒），SSE流式响应需要更长时间
    ENABLE_EXPERT_CONSULTATION: bool = True  # 是否启用专家咨询
    
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
        extra = "ignore"  # 忽略额外的环境变量，避免与其他项目的配置冲突
        


# 全局配置实例
settings = Settings()
