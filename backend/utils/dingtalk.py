#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉自定义机器人群消息通知工具
"""

import os
import time
import hmac
import hashlib
import base64
import logging
import urllib.parse
import requests

logger = logging.getLogger(__name__)


def send_dingtalk_message(msg, at_user_ids=None, at_mobiles=None, is_at_all=False,
                          access_token=None, secret=None):
    """
    发送钉钉自定义机器人群消息。

    如果未传入 access_token / secret，则从环境变量
    DINGTALK_ACCESS_TOKEN / DINGTALK_SECRET 读取。
    """
    access_token = access_token or os.getenv("DINGTALK_ACCESS_TOKEN")
    secret = secret or os.getenv("DINGTALK_SECRET")

    if not access_token or not secret:
        logger.error("钉钉 access_token 或 secret 未配置，无法发送消息")
        return None

    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    url = (
        f"https://oapi.dingtalk.com/robot/send"
        f"?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    )

    body = {
        "msgtype": "text",
        "text": {"content": msg},
        "at": {
            "isAtAll": bool(is_at_all),
            "atUserIds": at_user_ids or [],
            "atMobiles": at_mobiles or [],
        },
    }

    try:
        resp = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=10)
        result = resp.json()
        logger.info("钉钉消息发送结果: %s", result)
        return result
    except Exception as e:
        logger.error("钉钉消息发送失败: %s", e)
        return None
