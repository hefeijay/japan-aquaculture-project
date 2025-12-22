#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO 目标检测服务
整合 /root/yolo 项目的检测功能，用于对虾类图像进行检测和统计
"""

import os
import cv2
import numpy as np
import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("ultralytics 未安装，YOLO 检测功能不可用")

logger = logging.getLogger(__name__)


class YOLODetectionService:
    """YOLO 目标检测服务类"""
    
    # 检测参数（与 /root/yolo/main.py 保持一致）
    PROPOR_COEFFICIENT = 16.8728  # 像素与尺寸比例系数(p/cm)
    WEIGHT_EXP_COEFFICIENT = 3.0364  # 体重指数系数
    WEIGHT_PROPOR_COEFFICIENT = 0.00639  # 体重比例系数
    THRESHOLD_SIZE1 = 8.14146  # 体长下限，单位cm，对应体重2.5g
    THRESHOLD_SIZE2 = 17.244896  # 体长上限，单位cm，对应体重25g
    DEFAULT_CONF = 0.3  # 默认置信度阈值
    DEFAULT_IOU = 0.5  # 默认IOU阈值
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化 YOLO 检测服务
        
        Args:
            model_path: 模型权重文件路径，如果为 None 则使用默认路径
        """
        if not YOLO_AVAILABLE:
            raise RuntimeError("ultralytics 未安装，无法使用 YOLO 检测功能")
        
        # 默认模型路径
        if model_path is None:
            # 尝试从 /root/yolo 项目加载模型
            default_paths = [
                '/root/yolo/runs/detect/train9/weights/best.pt',
                '/root/yolo/yolo11n.pt',
                '/root/yolo/yolov8s.pt',
            ]
            model_path = None
            for path in default_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if model_path is None:
                raise FileNotFoundError("未找到 YOLO 模型文件，请指定 model_path 或确保模型文件存在")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self.model_path = model_path
        self.model = YOLO(model_path)
        logger.info(f"YOLO 模型加载成功: {model_path}")
    
    @staticmethod
    def calculate_diagonal(box) -> float:
        """
        计算检测框的对角线长度（cm）
        
        Args:
            box: YOLO 检测框对象
            
        Returns:
            对角线长度（cm）
        """
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        pixel_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return pixel_length / YOLODetectionService.PROPOR_COEFFICIENT
    
    @staticmethod
    def filter_valid_detections(results, min_cm: float = None, max_cm: float = None) -> Any:
        """
        从预测结果中过滤不符合尺寸要求的活虾检测框
        
        Args:
            results: YOLO 预测结果
            min_cm: 最小尺寸（cm），默认使用 THRESHOLD_SIZE1
            max_cm: 最大尺寸（cm），默认使用 THRESHOLD_SIZE2
            
        Returns:
            过滤后的检测结果
        """
        if min_cm is None:
            min_cm = YOLODetectionService.THRESHOLD_SIZE1
        if max_cm is None:
            max_cm = YOLODetectionService.THRESHOLD_SIZE2
        
        filtered_boxes = []
        
        for box in results[0].boxes:
            # 只处理活虾（类别0）
            if box.cls == 0:
                # 计算体长（厘米）
                length_cm = YOLODetectionService.calculate_diagonal(box)
                # 只保留符合尺寸要求的检测框
                if min_cm <= length_cm <= max_cm:
                    filtered_boxes.append(box)
            else:
                # 保留所有死虾检测框（不进行尺寸过滤）
                filtered_boxes.append(box)
        
        # 用过滤后的检测框替换原始结果
        results[0].boxes = filtered_boxes
        return results
    
    @staticmethod
    def calculate_weight(size_cm: float) -> float:
        """
        根据尺寸计算重量
        
        Args:
            size_cm: 尺寸（cm）
            
        Returns:
            重量（g）
        """
        weight = size_cm ** YOLODetectionService.WEIGHT_EXP_COEFFICIENT
        return YOLODetectionService.WEIGHT_PROPOR_COEFFICIENT * weight
    
    def detect_batch(
        self,
        image_paths: List[str],
        conf: float = None,
        iou: float = None,
        output_dir: Optional[str] = None,
        save_results: bool = False
    ) -> Dict[str, Any]:
        """
        批量检测图片
        
        Args:
            image_paths: 图片路径列表
            conf: 置信度阈值，默认使用 DEFAULT_CONF
            iou: IOU阈值，默认使用 DEFAULT_IOU
            output_dir: 输出目录，用于保存检测结果图
            save_results: 是否保存检测结果图
            
        Returns:
            检测统计结果字典
        """
        if conf is None:
            conf = self.DEFAULT_CONF
        if iou is None:
            iou = self.DEFAULT_IOU
        
        total_live = 0
        total_dead = 0
        live_shrimp_sizes = []
        
        # 处理每张图片
        for img_path in image_paths:
            if not os.path.exists(img_path):
                logger.warning(f"图片不存在，跳过: {img_path}")
                continue
            
            try:
                # 运行检测
                results = self.model.predict(img_path, conf=conf, iou=iou, verbose=False)
                results = self.filter_valid_detections(results)
                
                live_count = 0
                dead_count = 0
                current_live_sizes = []
                
                # 统计检测结果
                for box in results[0].boxes:
                    if box.cls == 0:  # 活虾
                        live_count += 1
                        current_live_sizes.append(self.calculate_diagonal(box))
                    elif box.cls == 1:  # 死虾
                        dead_count += 1
                
                total_live += live_count
                total_dead += dead_count
                live_shrimp_sizes.extend(current_live_sizes)
                
                # 保存检测结果图（如果需要）
                if save_results and output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    plotted_img = results[0].plot(boxes=True, labels=False, conf=False)
                    
                    # 在图像上添加统计信息
                    y_offset = 30
                    line_height = 30
                    
                    cv2.putText(plotted_img, f"Live: {live_count}", (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    y_offset += line_height
                    
                    cv2.putText(plotted_img, f"Dead: {dead_count}", (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    y_offset += line_height
                    
                    if live_count > 0:
                        avg_size = np.mean(current_live_sizes)
                        cv2.putText(plotted_img, f"Avg Size: {avg_size:.1f}cm", (10, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 200), 2)
                        y_offset += line_height
                        
                        current_live_weights = [self.calculate_weight(s) for s in current_live_sizes]
                        avg_weight = np.mean(current_live_weights)
                        cv2.putText(plotted_img, f"Avg Weight: {avg_weight:.2f}g", (10, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (250, 250, 250), 2)
                    
                    # 保存结果图
                    output_filename = os.path.basename(img_path)
                    output_path = os.path.join(output_dir, f"result_{output_filename}")
                    cv2.imwrite(output_path, plotted_img)
                    logger.debug(f"检测结果图已保存: {output_path}")
                
            except Exception as e:
                logger.error(f"检测图片失败 {img_path}: {e}")
                continue
        
        # 生成统计结果
        stats = {
            "uuid": str(uuid.uuid4()),
            "conf": conf,
            "iou": iou,
            "total_live": int(total_live),
            "total_dead": int(total_dead),
            "created_at": datetime.datetime.now().astimezone().isoformat(),
        }
        
        # 如果有活虾，计算尺寸和重量统计
        if live_shrimp_sizes:
            live_shrimp_sizes_np = np.array(live_shrimp_sizes)
            live_shrimp_weights = [self.calculate_weight(s) for s in live_shrimp_sizes]
            live_shrimp_weights_np = np.array(live_shrimp_weights)
            
            stats["size_cm"] = {
                "min": float(np.min(live_shrimp_sizes_np)),
                "max": float(np.max(live_shrimp_sizes_np)),
                "mean": float(np.mean(live_shrimp_sizes_np)),
                "median": float(np.median(live_shrimp_sizes_np))
            }
            
            stats["weight_g"] = {
                "min": float(np.min(live_shrimp_weights_np)),
                "max": float(np.max(live_shrimp_weights_np)),
                "mean": float(np.mean(live_shrimp_weights_np)),
                "median": float(np.median(live_shrimp_weights_np))
            }
        else:
            stats["size_cm"] = None
            stats["weight_g"] = None
            stats["message"] = "no live shrimp detected"
        
        return stats
    
    def detect_directory(
        self,
        input_dir: str,
        conf: float = None,
        iou: float = None,
        output_dir: Optional[str] = None,
        save_results: bool = False
    ) -> Dict[str, Any]:
        """
        检测目录中的所有图片
        
        Args:
            input_dir: 输入目录路径
            conf: 置信度阈值
            iou: IOU阈值
            output_dir: 输出目录
            save_results: 是否保存检测结果图
            
        Returns:
            检测统计结果字典
        """
        if not os.path.isdir(input_dir):
            raise ValueError(f"输入目录不存在: {input_dir}")
        
        # 收集所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        image_paths = []
        
        for file in os.listdir(input_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_paths.append(os.path.join(input_dir, file))
        
        if not image_paths:
            logger.warning(f"目录中没有找到图片文件: {input_dir}")
            return {
                "uuid": str(uuid.uuid4()),
                "conf": conf or self.DEFAULT_CONF,
                "iou": iou or self.DEFAULT_IOU,
                "total_live": 0,
                "total_dead": 0,
                "message": "no images found",
                "created_at": datetime.datetime.now().astimezone().isoformat(),
            }
        
        logger.info(f"找到 {len(image_paths)} 张图片，开始检测...")
        
        # 使用批量检测
        stats = self.detect_batch(image_paths, conf, iou, output_dir, save_results)
        stats["input_subdir"] = os.path.basename(input_dir)
        if output_dir:
            stats["output_dir"] = output_dir
        else:
            stats["output_dir"] = ""
        
        return stats

