#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转换现有 .env 文件为项目所需的格式
从现有配置中提取有用信息，创建新的 .env 文件
"""
import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def parse_database_url(database_url: str) -> dict:
    """从 DATABASE_URL 解析数据库配置"""
    try:
        # 处理 mysql+mysqlconnector:// 或 mysql+pymysql:// 格式
        url = database_url.replace("mysql+mysqlconnector://", "mysql://").replace("mysql+pymysql://", "mysql://")
        parsed = urlparse(url)
        
        return {
            "MYSQL_HOST": parsed.hostname or "localhost",
            "MYSQL_PORT": str(parsed.port or 3306),
            "MYSQL_USER": parsed.username or "root",
            "MYSQL_PASSWORD": parsed.password or "",
            "MYSQL_DATABASE": parsed.path.lstrip("/") if parsed.path else "aquaculture",
        }
    except Exception as e:
        print(f"⚠️  解析 DATABASE_URL 失败: {e}")
        return {}


def read_existing_env(env_path: Path) -> dict:
    """读取现有 .env 文件"""
    config = {}
    
    if not env_path.exists():
        return config
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            
            # 处理 KEY=VALUE 格式（支持等号前后有空格）
            if "=" in line:
                # 分割键值对
                parts = line.split("=", 1)
                key = parts[0].strip()
                value = parts[1].strip()
                
                # 去除引号
                value = value.strip('"').strip("'")
                
                config[key] = value
    
    return config


def create_new_env(old_config: dict, output_path: Path, overwrite: bool = False):
    """创建新的 .env 文件"""
    if output_path.exists() and not overwrite:
        print(f"⚠️  {output_path} 已存在")
        response = input("是否覆盖？(y/N): ")
        if response.lower() != 'y':
            print("已取消")
            return
    
    # 从 DATABASE_URL 解析数据库配置
    db_config = {}
    if "DATABASE_URL" in old_config:
        db_config = parse_database_url(old_config["DATABASE_URL"])
    
    # 构建新配置
    new_config = {
        # 数据库配置（优先使用解析的，否则使用环境变量或默认值）
        "MYSQL_HOST": db_config.get("MYSQL_HOST") or old_config.get("MYSQL_HOST") or "localhost",
        "MYSQL_PORT": db_config.get("MYSQL_PORT") or old_config.get("MYSQL_PORT") or "3306",
        "MYSQL_USER": db_config.get("MYSQL_USER") or old_config.get("MYSQL_USER") or "root",
        "MYSQL_PASSWORD": db_config.get("MYSQL_PASSWORD") or old_config.get("MYSQL_PASSWORD") or "",
        "MYSQL_DATABASE": db_config.get("MYSQL_DATABASE") or old_config.get("MYSQL_DATABASE") or "aquaculture",
        
        # OpenAI 配置（从旧配置中提取）
        "OPENAI_API_KEY": old_config.get("OPENAI_API_KEY", "").strip('"').strip("'"),
        "OPENAI_MODEL": old_config.get("OPENAI_MODEL") or "gpt-4o-mini",
        "OPENAI_TEMPERATURE": old_config.get("OPENAI_TEMPERATURE") or "0.7",
        
        # 服务配置
        "HOST": old_config.get("HOST") or "0.0.0.0",
        "PORT": old_config.get("PORT") or "8000",
        "WS_PORT": old_config.get("WS_PORT") or "8001",
        "DEBUG": old_config.get("DEBUG", "false").lower(),
        
        # 日志配置
        "LOG_LEVEL": old_config.get("LOG_LEVEL") or "INFO",
        "LOG_FILE": old_config.get("LOG_FILE") or "",
        
        # 工作流配置
        "MAX_RETRY_COUNT": old_config.get("MAX_RETRY_COUNT") or "3",
        "ENABLE_AI_ANALYSIS": old_config.get("ENABLE_AI_ANALYSIS", "true").lower(),
    }
    
    # 生成 .env 文件内容
    env_content = """# ============================================
# 日本陆上养殖数据处理系统 - 环境配置
# ============================================
# 此文件由 convert_env.py 自动生成
# 请根据实际情况修改配置值

# 数据库配置
MYSQL_HOST={MYSQL_HOST}
MYSQL_PORT={MYSQL_PORT}
MYSQL_USER={MYSQL_USER}
MYSQL_PASSWORD={MYSQL_PASSWORD}
MYSQL_DATABASE={MYSQL_DATABASE}

# OpenAI API 配置
OPENAI_API_KEY={OPENAI_API_KEY}
OPENAI_MODEL={OPENAI_MODEL}
OPENAI_TEMPERATURE={OPENAI_TEMPERATURE}

# 服务配置
HOST={HOST}
PORT={PORT}
WS_PORT={WS_PORT}
DEBUG={DEBUG}

# 日志配置
LOG_LEVEL={LOG_LEVEL}
LOG_FILE={LOG_FILE}

# 工作流配置
MAX_RETRY_COUNT={MAX_RETRY_COUNT}
ENABLE_AI_ANALYSIS={ENABLE_AI_ANALYSIS}
"""
    
    # 格式化内容
    content = env_content.format(**new_config)
    
    # 写入文件
    output_path.write_text(content, encoding="utf-8")
    print(f"✓ 已创建 {output_path}")
    print(f"\n配置摘要:")
    print(f"  数据库: {new_config['MYSQL_USER']}@{new_config['MYSQL_HOST']}:{new_config['MYSQL_PORT']}/{new_config['MYSQL_DATABASE']}")
    print(f"  服务端口: {new_config['PORT']}")
    print(f"  OpenAI 模型: {new_config['OPENAI_MODEL']}")
    if new_config['OPENAI_API_KEY']:
        print(f"  OpenAI API Key: {'*' * 20}...{new_config['OPENAI_API_KEY'][-4:]}")
    else:
        print(f"  ⚠️  OpenAI API Key 未设置，请手动填入")


if __name__ == "__main__":
    import sys
    
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    
    # 查找现有的 .env 文件（可能在多个位置）
    possible_locations = [
        backend_dir / ".env",
        project_root / ".env",
        Path.cwd() / ".env",
    ]
    
    old_env_path = None
    for path in possible_locations:
        if path.exists():
            old_env_path = path
            print(f"找到现有 .env 文件: {path}")
            break
    
    if not old_env_path:
        print("未找到现有 .env 文件，将使用默认配置创建新文件")
        old_config = {}
    else:
        old_config = read_existing_env(old_env_path)
        print(f"从现有文件读取了 {len(old_config)} 个配置项")
    
    # 创建新的 .env 文件
    new_env_path = backend_dir / ".env"
    overwrite = "--overwrite" in sys.argv or "-f" in sys.argv
    
    create_new_env(old_config, new_env_path, overwrite=overwrite)
    
    # 验证新文件
    print("\n验证新文件格式...")
    from create_env import validate_env_file
    validate_env_file(new_env_path)

