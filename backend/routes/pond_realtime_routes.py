#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
养殖池实时监控路由蓝图
包含传感器实时数据、摄像头实时数据、设备列表、AI决策实时数据、设备开关控制等接口
支持通过 stream=true 查询参数开启 SSE（Server-Sent Events）实时推送
"""

import json
import logging
import os
import time

from flask import Blueprint, Response, jsonify, request, send_file

from config.settings import Config
from services.pond_realtime_service import PondRealtimeService

pond_realtime_bp = Blueprint("pond_realtime", __name__, url_prefix="/api/v1")

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# SSE helper
# ------------------------------------------------------------------


def _sse_generator(fetch_fn, interval: int = None):
    """
    通用 SSE 生成器：轮询 fetch_fn，当数据发生变化时推送事件。

    fetch_fn 应返回 (data_dict, error_msg) 元组。
    """
    if interval is None:
        interval = Config.SSE_POLL_INTERVAL
    last_snapshot: str | None = None
    while True:
        try:
            data, err = fetch_fn()
            if err:
                payload = json.dumps({"error": err}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            else:
                payload = json.dumps(data, ensure_ascii=False, default=str)
                if payload != last_snapshot:
                    yield f"data: {payload}\n\n"
                    last_snapshot = payload
            time.sleep(interval)
        except GeneratorExit:
            break
        except Exception as e:
            logger.error(f"SSE generator error: {e}", exc_info=True)
            err_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err_payload}\n\n"
            time.sleep(interval)


def _is_stream(req) -> bool:
    return req.args.get("stream", "false").lower() == "true"


# ------------------------------------------------------------------
# API 1: 获取养殖池传感器实时数据
# ------------------------------------------------------------------
@pond_realtime_bp.route("/ponds/<int:pond_id>/sensors/realtime", methods=["GET"])
def pond_sensors_realtime(pond_id: int):
    """
    获取指定养殖池下所有传感器设备的最新读数。
    支持 stream=true 开启 SSE 实时推送。
    """
    if _is_stream(request):
        return Response(
            _sse_generator(lambda: PondRealtimeService.get_pond_sensors_realtime(pond_id)),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    data, err = PondRealtimeService.get_pond_sensors_realtime(pond_id)
    if err:
        status_code = 404 if "不存在" in err else 500
        return jsonify({"code": status_code, "message": err, "data": None}), status_code
    return jsonify({"code": 200, "message": "success", "data": data})


# ------------------------------------------------------------------
# API 2: 获取养殖池摄像头实时数据
# ------------------------------------------------------------------
@pond_realtime_bp.route("/ponds/<int:pond_id>/cameras/realtime", methods=["GET"])
def pond_cameras_realtime(pond_id: int):
    """
    获取指定养殖池下所有摄像头设备的最新状态和拍摄时间元数据。
    支持 stream=true 开启 SSE 实时推送。
    """
    if _is_stream(request):
        return Response(
            _sse_generator(lambda: PondRealtimeService.get_pond_cameras_realtime(pond_id)),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    data, err = PondRealtimeService.get_pond_cameras_realtime(pond_id)
    if err:
        status_code = 404 if "不存在" in err else 500
        return jsonify({"code": status_code, "message": err, "data": None}), status_code
    return jsonify({"code": 200, "message": "success", "data": data})


# ------------------------------------------------------------------
# API 3: 获取摄像头最新图片（二进制）
# ------------------------------------------------------------------
@pond_realtime_bp.route(
    "/ponds/<int:pond_id>/cameras/<int:device_id>/image", methods=["GET"]
)
def pond_camera_image(pond_id: int, device_id: int):
    """
    获取指定养殖池下指定摄像头的最新拍摄图片，直接返回二进制图片数据。
    前端可直接用 <img src="..."> 渲染。
    """
    meta, err, status_code = PondRealtimeService.get_camera_image_meta(pond_id, device_id)
    if err:
        return jsonify({"code": status_code, "message": err, "data": None}), status_code

    storage_url = meta.get("storage_url")
    image_url = meta.get("image_url", "")
    file_path = None

    if storage_url and os.path.isfile(storage_url):
        file_path = storage_url
    else:
        if image_url:
            relative_path = image_url.lstrip("/")
            search_bases = [
                os.getcwd(),
                os.path.dirname(os.getcwd()),
                os.path.dirname(os.path.dirname(os.getcwd())),
            ]
            for base in search_bases:
                candidate = os.path.join(base, relative_path)
                if os.path.isfile(candidate):
                    file_path = candidate
                    break

    if file_path is None:
        logger.error(f"摄像头设备{device_id}图片文件不存在: storage_url={storage_url}, image_url={image_url}")
        return jsonify({"code": 404, "message": "图片文件不存在", "data": None}), 404

    fmt = meta.get("format", "jpeg").lower()
    mime_map = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    mimetype = mime_map.get(fmt, "image/jpeg")
    return send_file(file_path, mimetype=mimetype)


# ------------------------------------------------------------------
# API 4: 获取养殖池设备列表
# ------------------------------------------------------------------
@pond_realtime_bp.route("/ponds/<int:pond_id>/devices", methods=["GET"])
def pond_devices(pond_id: int):
    """
    获取指定养殖池下所有设备，支持按设备类别筛选。
    支持 stream=true 开启 SSE 实时推送。
    """
    category = request.args.get("category")
    valid_categories = (
        "sensor", "feeder", "camera", "water_pump",
        "air_blower", "water_switch", "solar_heater_pump",
        "air_pump", "physical_filter",
    )
    if category and category not in valid_categories:
        return jsonify({
            "code": 400,
            "message": f"无效的设备类别，可选值: {', '.join(valid_categories)}",
            "data": None,
        }), 400

    if _is_stream(request):
        return Response(
            _sse_generator(
                lambda: PondRealtimeService.get_pond_devices(pond_id, category=category)
            ),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    data, err = PondRealtimeService.get_pond_devices(pond_id, category=category)
    if err:
        status_code = 404 if "不存在" in err else 500
        return jsonify({"code": status_code, "message": err, "data": None}), status_code
    return jsonify({"code": 200, "message": "success", "data": data})


# ------------------------------------------------------------------
# API 5: 获取养殖池AI决策实时数据
# ------------------------------------------------------------------
@pond_realtime_bp.route("/ponds/<int:pond_id>/ai-decisions/realtime", methods=["GET"])
def pond_ai_decisions_realtime(pond_id: int):
    """
    获取与指定养殖池相关的活跃AI决策列表。
    支持 stream=true 开启 SSE 实时推送。
    """
    if _is_stream(request):
        return Response(
            _sse_generator(
                lambda: PondRealtimeService.get_pond_ai_decisions_realtime(pond_id)
            ),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    data, err = PondRealtimeService.get_pond_ai_decisions_realtime(pond_id)
    if err:
        status_code = 404 if "不存在" in err else 500
        return jsonify({"code": status_code, "message": err, "data": None}), status_code
    return jsonify({"code": 200, "message": "success", "data": data})


# ------------------------------------------------------------------
# API 6: 设备开关控制
# ------------------------------------------------------------------
@pond_realtime_bp.route("/devices/<int:device_id>/control", methods=["POST"])
def device_control(device_id: int):
    """
    通过 MQTT 发送控制指令给指定设备。
    请求体: { "action": "start" | "stop" }
    """
    body = request.get_json(silent=True)
    if not body or "action" not in body:
        return jsonify({
            "code": 400,
            "message": "缺少必填参数 action",
            "data": None,
        }), 400

    data, err, status_code = PondRealtimeService.control_device(
        device_id, body["action"]
    )
    if err:
        return jsonify({"code": status_code, "message": err, "data": None}), status_code
    return jsonify({"code": 200, "message": "控制指令已发送", "data": data})
