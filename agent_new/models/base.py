#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础模型类 - 参考 db_models/base.py
"""
from typing import Any, Dict

# 直接使用 database 模块中的 Base
from database import Base


# 为 Base 添加辅助方法
def as_dict(self) -> Dict[str, Any]:
    """
    将模型实例转换为字典格式
    """
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 将方法添加到 Base 类
Base.as_dict = as_dict

