#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预测服务
基于最近五条历史数据生成或复用预测结果，避免在 SSE 请求中同步阻塞式调用大模型。
"""

from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional

from config.settings import Config
from db_models.base import Base
from db_models.db_session import db_session_factory, get_engine
from db_models.pond import Pond
from db_models.pond_prediction_run import PondPredictionRun
from db_models.weather_cache import WeatherCache
from services.llm_service import llm_service

logger = logging.getLogger(__name__)


class PredictionService:
    """养殖池预测服务"""

    def __init__(self):
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, Config.PREDICTION_ASYNC_THREADS),
            thread_name_prefix="PredictionWorker",
        )

    def ensure_tables(self) -> None:
        """确保预测结果表存在。"""
        try:
            Base.metadata.create_all(get_engine(), tables=[PondPredictionRun.__table__])
        except Exception as exc:
            logger.error(f"创建预测结果表失败: {exc}", exc_info=True)

    def build_input_signature(self, pond_id: int, sensors: List[Dict[str, Any]]) -> str:
        """根据最近五条历史数据生成输入签名。"""
        signature_payload = {
            "pond_id": pond_id,
            "sensors": [
                {
                    "device_id": sensor["device_id"],
                    "metric": sensor["metric"],
                    "history_points": sensor.get("history_points", []),
                }
                for sensor in sensors
            ],
        }
        raw = json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_prediction_bundle(
        self,
        pond: Pond,
        sensors: List[Dict[str, Any]],
        weather_cache: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取当前池塘应返回的预测结果。
        - 若当前签名已有 ready 结果，直接返回
        - 若没有，则异步调度生成，并返回上一条 ready 结果或 pending 状态
        """
        self.ensure_tables()
        signature = self.build_input_signature(pond.id, sensors)
        latest_ready_same_data = None
        latest_ready_any_data = None
        latest_pending_same = None

        with db_session_factory() as session:
            latest_ready_same = (
                session.query(PondPredictionRun)
                .filter(PondPredictionRun.pond_id == pond.id)
                .filter(PondPredictionRun.input_signature == signature)
                .filter(PondPredictionRun.status == "ready")
                .order_by(PondPredictionRun.created_at.desc())
                .first()
            )
            latest_ready_any = (
                session.query(PondPredictionRun)
                .filter(PondPredictionRun.pond_id == pond.id)
                .filter(PondPredictionRun.status == "ready")
                .order_by(PondPredictionRun.created_at.desc())
                .first()
            )
            latest_pending_same = (
                session.query(PondPredictionRun)
                .filter(PondPredictionRun.pond_id == pond.id)
                .filter(PondPredictionRun.input_signature == signature)
                .filter(PondPredictionRun.status.in_(["pending", "processing"]))
                .order_by(PondPredictionRun.created_at.desc())
                .first()
            )
            if latest_pending_same and self._is_stale_pending_run(latest_pending_same):
                latest_pending_same.status = "failed"
                latest_pending_same.error_message = "预测任务超时或服务重载中断，已标记失效"
                session.commit()
                latest_pending_same = None

            if latest_ready_same:
                latest_ready_same_data = self._serialize_run(latest_ready_same)
            if latest_ready_any:
                latest_ready_any_data = self._serialize_run(latest_ready_any)

        if latest_ready_same_data:
            return {
                "signature": signature,
                "status": "ready",
                "run": latest_ready_same_data,
            }

        if not latest_pending_same:
            self._schedule_prediction(
                pond=pond,
                sensors=sensors,
                signature=signature,
                weather_cache=weather_cache,
            )

        if latest_ready_any_data:
            return {
                "signature": signature,
                "status": "pending",
                "run": latest_ready_any_data,
            }

        return {
            "signature": signature,
            "status": "pending",
            "run": None,
        }

    def _schedule_prediction(
        self,
        pond: Pond,
        sensors: List[Dict[str, Any]],
        signature: str,
        weather_cache: Optional[Dict[str, Any]],
    ) -> None:
        """异步调度预测任务。"""
        generated_at = datetime.utcnow()
        predicted_for_at = generated_at + timedelta(minutes=Config.PREDICTION_INTERVAL_MINUTES)

        with db_session_factory() as session:
            existing = (
                session.query(PondPredictionRun)
                .filter(PondPredictionRun.pond_id == pond.id)
                .filter(PondPredictionRun.input_signature == signature)
                .filter(PondPredictionRun.status.in_(["pending", "processing"]))
                .first()
            )
            if existing:
                if self._is_stale_pending_run(existing):
                    existing.status = "failed"
                    existing.error_message = "预测任务超时或服务重载中断，已标记失效"
                    session.commit()
                else:
                    return

            run = PondPredictionRun(
                pond_id=pond.id,
                weather_cache_id=weather_cache.get("id") if weather_cache else None,
                input_signature=signature,
                generated_at=generated_at,
                predicted_for_at=predicted_for_at,
                status="pending",
                output_payload=None,
                error_message=None,
            )
            session.add(run)
            session.commit()
            run_id = run.id

        self._executor.submit(
            self._execute_prediction_job,
            run_id,
            pond.id,
            pond.name,
            sensors,
            weather_cache.get("payload") if weather_cache else None,
        )

    def _execute_prediction_job(
        self,
        run_id: int,
        pond_id: int,
        pond_name: str,
        sensors: List[Dict[str, Any]],
        weather_payload: Optional[Dict[str, Any]],
    ) -> None:
        """执行实际预测任务。"""
        try:
            with db_session_factory() as session:
                run = session.query(PondPredictionRun).filter(PondPredictionRun.id == run_id).first()
                if not run:
                    return
                run.status = "processing"
                session.commit()

            output_payload = self._predict_payload(pond_id, pond_name, sensors, weather_payload)

            with db_session_factory() as session:
                run = session.query(PondPredictionRun).filter(PondPredictionRun.id == run_id).first()
                if not run:
                    return
                run.status = "ready"
                run.output_payload = output_payload
                run.error_message = None
                session.commit()
        except Exception as exc:
            logger.error(f"预测任务执行失败: {exc}", exc_info=True)
            with db_session_factory() as session:
                run = session.query(PondPredictionRun).filter(PondPredictionRun.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = str(exc)[:255]
                    session.commit()

    def _predict_payload(
        self,
        pond_id: int,
        pond_name: str,
        sensors: List[Dict[str, Any]],
        weather_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """优先调用大模型预测，失败时回退到规则兜底。"""
        if Config.PREDICTION_ENABLE_LLM and llm_service.is_enabled():
            try:
                return self._predict_with_llm(
                    pond_id=pond_id,
                    pond_name=pond_name,
                    sensors=sensors,
                    weather_payload=weather_payload,
                )
            except Exception as exc:
                logger.warning(f"大模型预测失败，回退到规则预测: {exc}")
                if not Config.PREDICTION_FALLBACK_ENABLED:
                    raise

        return self._predict_with_rules(pond_id, pond_name, sensors, weather_payload)

    def _predict_with_rules(
        self,
        pond_id: int,
        pond_name: str,
        sensors: List[Dict[str, Any]],
        weather_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """规则兜底预测。"""
        generated_at = datetime.utcnow()
        predicted_for_at = generated_at + timedelta(minutes=Config.PREDICTION_INTERVAL_MINUTES)
        predictions: List[Dict[str, Any]] = []

        for sensor in sensors:
            history_points = sensor.get("history_points", [])
            values = [float(point["value"]) for point in history_points if point.get("value") is not None]

            if not values:
                predictions.append(
                    {
                        "device_id": sensor["device_id"],
                        "prediction_status": "failed",
                        "predicted_value": None,
                        "trend": "stable",
                        "analysis_text": "暂无足够历史数据，暂时无法生成预测。",
                        "reason_text": "最近历史数据为空。",
                        "predicted_for_at": predicted_for_at.isoformat(),
                    }
                )
                continue

            current_value = values[-1]
            if len(values) < 2:
                avg_step = 0.0
            else:
                deltas = [values[idx] - values[idx - 1] for idx in range(1, len(values))]
                avg_step = mean(deltas)

            predicted_value = round(current_value + avg_step, 2)
            trend = self._resolve_trend(avg_step)
            analysis_text = self._build_analysis_text(sensor["name"], trend)
            reason_text = self._build_reason_text(values, trend)

            predictions.append(
                {
                    "device_id": sensor["device_id"],
                    "prediction_status": "ready",
                    "predicted_value": predicted_value,
                    "trend": trend,
                    "analysis_text": analysis_text,
                    "reason_text": reason_text,
                    "predicted_for_at": predicted_for_at.isoformat(),
                }
            )

        return {
            "pond_id": pond_id,
            "pond_name": pond_name,
            "generated_at": generated_at.isoformat(),
            "predicted_for_at": predicted_for_at.isoformat(),
            "weather": weather_payload,
            "source": "rule_fallback",
            "predictions": predictions,
        }

    def _predict_with_llm(
        self,
        pond_id: int,
        pond_name: str,
        sensors: List[Dict[str, Any]],
        weather_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """使用大模型生成预测结果。"""
        generated_at = datetime.utcnow()
        predicted_for_at = generated_at + timedelta(minutes=Config.PREDICTION_INTERVAL_MINUTES)

        normalized_sensors = []
        for sensor in sensors:
            normalized_sensors.append(
                {
                    "device_id": sensor["device_id"],
                    "name": sensor["name"],
                    "metric": sensor["metric"],
                    "unit": sensor["unit"],
                    "current_value": sensor.get("value"),
                    "recorded_at": sensor.get("recorded_at"),
                    "recorded_at_local": sensor.get("recorded_at_local"),
                    "history_points": sensor.get("history_points", []),
                }
            )

        system_prompt = (
            "你是日本陆上养殖场的专业水环境分析员，负责做下一个时间点的短时传感器联合预测。"
            "你必须同时参考同一养殖池内全部传感器最近五条历史数据，以及天气 forecast 信息，"
            "不能把单个传感器孤立判断。"
            "请优先遵循这些专业判断原则："
            "1. 水温是关键驱动因素，必须重点结合水温传感器与天气温度；"
            "2. 水温升高通常会压低溶解氧，水温稳定时溶解氧往往延续原有小幅波动；"
            "3. 降雨、湿度、天气现象可能影响 pH、浊度和水位；"
            "4. pH 变化要结合温度、天气和其他指标一起判断，不要仅凭单点值下结论；"
            "5. 浊度和水位如果历史上持续平稳，短时预测应以稳定或轻微变化为主，不要夸大波动；"
            "6. 如果多个传感器都稳定，且天气变化不剧烈，应优先给出 stable；"
            "7. 对异常跳点和孤立值要谨慎，避免过拟合。"
            "预测目标仅限下一个时间点，不做长期推演。"
            "predicted_value 必须是数值；trend 只能是 up、down、stable。"
            "analysis_text 用一句话给出业务结论。"
            "reason_text 用一句话说明主要依据，必须明确提到历史趋势、温度因素、天气因素或跨传感器联动中的至少一种。"
            "必须严格返回 JSON 对象，不要返回任何额外解释。"
            '顶层必须是 {"predictions":[...]}，且 predictions 数组必须覆盖输入中的每一个 device_id。'
            "每个 prediction 必须包含 device_id、predicted_value、trend、analysis_text、reason_text。"
        )
        user_payload = {
            "pond_id": pond_id,
            "pond_name": pond_name,
            "generated_at": generated_at.isoformat(),
            "predicted_for_at": predicted_for_at.isoformat(),
            "weather": weather_payload,
            "sensors": normalized_sensors,
        }
        user_prompt = (
            "请基于下面这个养殖池的完整输入，输出下一时间点预测。"
            "重点要求：必须结合水温、天气和多传感器联动做联合判断，结论要专业、克制、可解释。"
            "返回 JSON 完整格式示例如下：\n"
            '{\n'
            '  "predictions": [\n'
            '    {\n'
            '      "device_id": 1,\n'
            '      "predicted_value": 7.6,\n'
            '      "trend": "stable",\n'
            '      "analysis_text": "溶解氧短时保持稳定。",\n'
            '      "reason_text": "最近五条溶解氧波动很小，水温稳定，天气变化有限，因此下一时刻预计基本持平。"\n'
            '    },\n'
            '    {\n'
            '      "device_id": 2,\n'
            '      "predicted_value": 0.81,\n'
            '      "trend": "stable",\n'
            '      "analysis_text": "水位短时基本保持稳定。",\n'
            '      "reason_text": "最近五条水位变化很小，天气无明显强降雨扰动，因此下一时刻预计延续稳定。"\n'
            '    },\n'
            '    {\n'
            '      "device_id": 3,\n'
            '      "predicted_value": 7.24,\n'
            '      "trend": "up",\n'
            '      "analysis_text": "pH短时小幅上升。",\n'
            '      "reason_text": "最近五条pH缓慢上行，水温稳定且天气变化有限，因此下一时刻预计继续轻微上升。"\n'
            '    }\n'
            '  ]\n'
            '}\n'
            "请严格按这个 JSON 结构返回，不要添加 markdown 代码块，不要添加任何解释文字。\n"
            f"{json.dumps(user_payload, ensure_ascii=False)}"
        )
        llm_result = llm_service.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=Config.PREDICTION_MODEL_NAME,
            temperature=min(Config.OPENAI_TEMPERATURE, 0.2),
            max_tokens=Config.PREDICTION_LLM_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        predictions: List[Dict[str, Any]] = []
        for item in llm_result.get("predictions", []):
            device_id = item.get("device_id")
            if device_id is None:
                continue
            trend = item.get("trend", "stable")
            if trend not in {"up", "down", "stable"}:
                trend = "stable"
            predictions.append(
                {
                    "device_id": int(device_id),
                    "prediction_status": "ready",
                    "predicted_value": item.get("predicted_value"),
                    "trend": trend,
                    "analysis_text": item.get("analysis_text"),
                    "reason_text": item.get("reason_text"),
                    "predicted_for_at": predicted_for_at.isoformat(),
                }
            )

        if not predictions:
            raise ValueError("大模型未返回有效 predictions")

        return {
            "pond_id": pond_id,
            "pond_name": pond_name,
            "generated_at": generated_at.isoformat(),
            "predicted_for_at": predicted_for_at.isoformat(),
            "weather": weather_payload,
            "source": "llm",
            "predictions": predictions,
        }

    def _resolve_trend(self, avg_step: float) -> str:
        if avg_step > 0.05:
            return "up"
        if avg_step < -0.05:
            return "down"
        return "stable"

    def _build_analysis_text(self, sensor_name: str, trend: str) -> str:
        trend_text = {
            "up": "呈上升趋势",
            "down": "呈下降趋势",
            "stable": "整体保持稳定",
        }
        return f"{sensor_name}{trend_text.get(trend, '整体保持稳定')}。"

    def _build_reason_text(self, values: List[float], trend: str) -> str:
        if len(values) < 2:
            return "历史数据点不足，暂按当前值做平稳预测。"

        if trend == "up":
            return "最近五条历史数据整体上行，因此短期预测继续小幅上升。"
        if trend == "down":
            return "最近五条历史数据整体下行，因此短期预测继续小幅下降。"
        return "最近五条历史数据波动较小，因此短期预测保持稳定。"

    def build_prediction_map(
        self,
        bundle: Dict[str, Any],
    ) -> Dict[int, Dict[str, Any]]:
        """把输出载荷按 device_id 映射，方便实时接口拼装。"""
        run = bundle.get("run")
        status = bundle.get("status", "pending")
        if not run or not run.get("output_payload"):
            return {}

        payload = run.get("output_payload") or {}
        prediction_map: Dict[int, Dict[str, Any]] = {}
        for item in payload.get("predictions", []):
            device_id = item.get("device_id")
            if device_id is None:
                continue
            enriched = dict(item)
            enriched["prediction_status"] = status if status != "ready" else item.get("prediction_status", "ready")
            prediction_map[int(device_id)] = enriched
        return prediction_map

    def _serialize_run(self, run: PondPredictionRun) -> Dict[str, Any]:
        return {
            "id": run.id,
            "pond_id": run.pond_id,
            "weather_cache_id": run.weather_cache_id,
            "input_signature": run.input_signature,
            "generated_at": run.generated_at.isoformat() if run.generated_at else None,
            "predicted_for_at": run.predicted_for_at.isoformat() if run.predicted_for_at else None,
            "status": run.status,
            "output_payload": run.output_payload,
            "error_message": run.error_message,
        }

    def _is_stale_pending_run(self, run: PondPredictionRun) -> bool:
        reference_time = run.updated_at or run.created_at or run.generated_at
        if not reference_time:
            return False
        timeout_seconds = max(90, Config.OPENAI_TIMEOUT + 30)
        return (datetime.utcnow() - reference_time).total_seconds() > timeout_seconds


prediction_service = PredictionService()
