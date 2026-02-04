#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警调度服务
负责管理所有预警规则的定时检查任务
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging
import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from config.settings import Config

logger = logging.getLogger(__name__)


class AlertSchedulerService:
    """预警调度服务 - 管理所有预警规则的定时任务"""
    
    _scheduler: Optional[BackgroundScheduler] = None
    _initialized: bool = False
    
    @classmethod
    def init_scheduler(cls, database_url: str):
        """
        初始化调度器（在 Flask 应用启动时调用）
        
        Args:
            database_url: 数据库连接URL，用于任务持久化
        """
        if cls._initialized:
            logger.warning("调度器已初始化，跳过重复初始化")
            return
        
        try:
            # 配置 JobStore（持久化到数据库）
            jobstores = {
                'default': SQLAlchemyJobStore(url=database_url)
            }
            
            # 配置执行器
            executors = {
                'default': ThreadPoolExecutor(Config.ALERT_SCHEDULER_THREAD_POOL_SIZE)
            }
            
            # 任务默认配置
            job_defaults = {
                'coalesce': Config.ALERT_SCHEDULER_COALESCE,
                'max_instances': Config.ALERT_SCHEDULER_MAX_INSTANCES,
                'misfire_grace_time': Config.ALERT_SCHEDULER_MISFIRE_GRACE_TIME
            }
            
            cls._scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )
            
            # 启动调度器
            cls._scheduler.start()
            cls._initialized = True
            
            # 注册退出时关闭调度器
            atexit.register(cls.shutdown)
            
            # 加载所有启用的规则
            cls._load_all_rules()
            
            logger.info("预警调度服务已启动")
            
        except Exception as e:
            logger.error(f"初始化调度器失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def _load_all_rules(cls):
        """加载所有启用的预警规则到调度器，并清理孤儿任务"""
        from db_models.db_session import db_session_factory
        from db_models.alert_rule import AlertRule
        
        try:
            with db_session_factory() as session:
                rules = session.query(AlertRule).filter(
                    AlertRule.is_enabled == True
                ).all()
                
                # 构建有效任务ID集合
                valid_job_ids = set()
                
                for rule in rules:
                    job_id = f"alert_rule_{rule.id}"
                    valid_job_ids.add(job_id)
                    
                    rule_dict = {
                        'id': rule.id,
                        'rule_id': rule.rule_id,
                        'check_interval': rule.check_interval,
                        'check_interval_unit': rule.check_interval_unit
                    }
                    cls.add_or_update_job(rule_dict)
                
                logger.info(f"已加载 {len(rules)} 条预警规则到调度器")
                
                # 清理孤儿任务：删除 jobs 表中存在但 alert_rules 中不存在/已禁用的任务
                cls._cleanup_orphan_jobs(valid_job_ids)
                
        except Exception as e:
            logger.error(f"加载预警规则失败: {str(e)}", exc_info=True)
    
    @classmethod
    def _cleanup_orphan_jobs(cls, valid_job_ids: set):
        """
        清理孤儿任务
        
        Args:
            valid_job_ids: 当前有效的任务ID集合
        """
        if not cls._scheduler:
            return
        
        try:
            all_jobs = cls._scheduler.get_jobs()
            orphan_count = 0
            
            for job in all_jobs:
                # 只处理预警规则相关的任务（以 alert_rule_ 开头）
                if job.id.startswith("alert_rule_") and job.id not in valid_job_ids:
                    cls._scheduler.remove_job(job.id)
                    orphan_count += 1
                    logger.info(f"清理孤儿任务: {job.id}")
            
            if orphan_count > 0:
                logger.info(f"共清理 {orphan_count} 个孤儿任务")
                
        except Exception as e:
            logger.warning(f"清理孤儿任务失败: {str(e)}")
    
    @classmethod
    def add_or_update_job(cls, rule: Dict[str, Any]):
        """
        添加或更新预警检查任务
        
        Args:
            rule: 规则信息字典，需包含 id, rule_id, check_interval, check_interval_unit
        """
        if not cls._scheduler:
            logger.warning("调度器未初始化")
            return
        
        from services.alert_check_service import AlertCheckService
        
        job_id = f"alert_rule_{rule['id']}"
        
        # 计算检查间隔（秒）
        interval_seconds = cls._calculate_interval_seconds(
            rule['check_interval'],
            rule['check_interval_unit']
        )
        
        # 添加任务（replace_existing=True 会原子性替换已存在的任务）
        cls._scheduler.add_job(
            func=AlertCheckService.check_rule,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            args=[rule['id']],
            name=f"Alert Check: {rule['rule_id']}",
            replace_existing=True
        )
        
        logger.info(f"已添加/更新预警任务: {job_id}, 间隔: {interval_seconds}秒")
    
    @classmethod
    def remove_job(cls, rule_id: int):
        """
        移除预警检查任务
        
        Args:
            rule_id: 规则主键ID
        """
        if not cls._scheduler:
            return
        
        job_id = f"alert_rule_{rule_id}"
        
        try:
            if cls._scheduler.get_job(job_id):
                cls._scheduler.remove_job(job_id)
                logger.info(f"已移除预警任务: {job_id}")
        except Exception as e:
            logger.warning(f"移除任务失败 {job_id}: {str(e)}")
    
    @classmethod
    def pause_job(cls, rule_id: int):
        """
        暂停预警检查任务（规则禁用时）
        
        Args:
            rule_id: 规则主键ID
        """
        if not cls._scheduler:
            return
        
        job_id = f"alert_rule_{rule_id}"
        
        try:
            if cls._scheduler.get_job(job_id):
                cls._scheduler.pause_job(job_id)
                logger.info(f"已暂停预警任务: {job_id}")
        except Exception as e:
            logger.warning(f"暂停任务失败 {job_id}: {str(e)}")
    
    @classmethod
    def resume_job(cls, rule_id: int):
        """
        恢复预警检查任务（规则启用时）
        
        Args:
            rule_id: 规则主键ID
        """
        if not cls._scheduler:
            return
        
        job_id = f"alert_rule_{rule_id}"
        
        try:
            if cls._scheduler.get_job(job_id):
                cls._scheduler.resume_job(job_id)
                logger.info(f"已恢复预警任务: {job_id}")
        except Exception as e:
            logger.warning(f"恢复任务失败 {job_id}: {str(e)}")
    
    @classmethod
    def _calculate_interval_seconds(cls, interval: int, unit: str) -> int:
        """
        计算检查间隔（秒）
        
        Args:
            interval: 间隔数值
            unit: 间隔单位（minute/hour/day）
            
        Returns:
            间隔秒数
        """
        multipliers = {
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        return interval * multipliers.get(unit, 60)
    
    @classmethod
    def shutdown(cls):
        """关闭调度器"""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
            cls._initialized = False
            logger.info("预警调度服务已关闭")
    
    @classmethod
    def is_initialized(cls) -> bool:
        """检查调度器是否已初始化"""
        return cls._initialized
