#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接和会话管理 - 参考 db_models/db_session.py
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from contextlib import contextmanager
from typing import Generator
import structlog

from config import settings

logger = structlog.get_logger()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_size=15,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=600,
    pool_pre_ping=True,
    pool_use_lifo=True,
    echo=settings.DEBUG,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器
    参考 db_models/db_session.py 的 db_session_factory
    """
    db = SessionLocal()
    logger.debug("数据库会话已创建")
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("数据库操作失败", error=str(e))
        raise
    finally:
        db.close()
        logger.debug("数据库会话已关闭")


def get_db_session() -> Generator[Session, None, None]:
    """
    获取数据库会话（用于依赖注入）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
