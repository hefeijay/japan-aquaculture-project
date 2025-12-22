#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建 .env 文件的辅助脚本
从现有环境变量或用户输入创建正确格式的 .env 文件
"""
import os
from pathlib import Path

def create_env_file(env_path: Path, overwrite: bool = False):
    """创建 .env 文件"""
    if env_path.exists() and not overwrite:
        print(f"⚠️  {env_path} 已存在，跳过创建")
        print(f"   如需覆盖，请使用: python create_env.py --overwrite")
        return
    
    # 从环境变量或默认值获取配置
    env_content = """# ============================================
# 日本陆上养殖数据处理系统 - 环境配置
# ============================================
# 此文件由 create_env.py 自动生成
# 请根据实际情况修改配置值

# 数据库配置
MYSQL_HOST={mysql_host}
MYSQL_PORT={mysql_port}
MYSQL_USER={mysql_user}
MYSQL_PASSWORD={mysql_password}
MYSQL_DATABASE={mysql_database}

# OpenAI API 配置
OPENAI_API_KEY={openai_api_key}
OPENAI_MODEL={openai_model}
OPENAI_TEMPERATURE={openai_temperature}

# 服务配置
HOST={host}
PORT={port}
WS_PORT={ws_port}
DEBUG={debug}

# 日志配置
LOG_LEVEL={log_level}
LOG_FILE={log_file}

# 工作流配置
MAX_RETRY_COUNT={max_retry_count}
ENABLE_AI_ANALYSIS={enable_ai_analysis}
"""
    
    # 获取配置值（优先使用环境变量，否则使用默认值）
    config = {
        "mysql_host": os.getenv("MYSQL_HOST", "localhost"),
        "mysql_port": os.getenv("MYSQL_PORT", "3306"),
        "mysql_user": os.getenv("MYSQL_USER", "root"),
        "mysql_password": os.getenv("MYSQL_PASSWORD", ""),
        "mysql_database": os.getenv("MYSQL_DATABASE", "aquaculture"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "openai_temperature": os.getenv("OPENAI_TEMPERATURE", "0.7"),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": os.getenv("PORT", "8000"),
        "ws_port": os.getenv("WS_PORT", "8001"),
        "debug": os.getenv("DEBUG", "false"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_file": os.getenv("LOG_FILE", ""),
        "max_retry_count": os.getenv("MAX_RETRY_COUNT", "3"),
        "enable_ai_analysis": os.getenv("ENABLE_AI_ANALYSIS", "true"),
    }
    
    # 格式化内容
    content = env_content.format(**config)
    
    # 写入文件
    env_path.write_text(content, encoding="utf-8")
    print(f"✓ 已创建 {env_path}")
    print(f"  请编辑文件并填入实际的配置值（特别是密码和 API 密钥）")


def validate_env_file(env_path: Path):
    """验证 .env 文件格式"""
    if not env_path.exists():
        print(f"❌ {env_path} 不存在")
        return False
    
    errors = []
    warnings = []
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            
            # 检查格式
            if "=" not in line:
                errors.append(f"第 {line_num} 行: 缺少等号")
                continue
            
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # 检查键名
            if not key:
                errors.append(f"第 {line_num} 行: 键名为空")
            
            # 检查敏感信息是否为空
            sensitive_keys = ["MYSQL_PASSWORD", "OPENAI_API_KEY"]
            if key in sensitive_keys and not value:
                warnings.append(f"第 {line_num} 行: {key} 为空，请填入实际值")
    
    if errors:
        print("❌ 发现格式错误:")
        for error in errors:
            print(f"   {error}")
        return False
    
    if warnings:
        print("⚠️  警告:")
        for warning in warnings:
            print(f"   {warning}")
    
    print("✓ .env 文件格式正确")
    return True


if __name__ == "__main__":
    import sys
    
    backend_dir = Path(__file__).parent
    env_path = backend_dir / ".env"
    
    overwrite = "--overwrite" in sys.argv or "-f" in sys.argv
    
    if "--validate" in sys.argv or "-v" in sys.argv:
        validate_env_file(env_path)
    else:
        create_env_file(env_path, overwrite=overwrite)
        print("\n提示: 使用 --validate 或 -v 参数验证 .env 文件格式")

