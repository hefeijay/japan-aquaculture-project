#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务启动入口
"""
import uvicorn
from config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 启动日本陆上养殖数据处理系统 v2.0.0")
    print("=" * 60)
    print(f"   Host: {settings.HOST}")
    print(f"   Port: {settings.PORT}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   Model: {settings.OPENAI_MODEL}")
    print("=" * 60)
    
    uvicorn.run(
        "api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

