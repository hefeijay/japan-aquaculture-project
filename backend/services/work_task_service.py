#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理中心服务模块
负责业务任务的创建、编辑、撤销和查询
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from db_models.base import Base
from db_models.db_session import db_session_factory
from db_models.db_session import get_engine
from db_models.work_task import WorkTask
from db_models.user import User
from db_models.pond import Pond

logger = logging.getLogger(__name__)


class WorkTaskService:
    """任务管理中心服务类"""

    @classmethod
    def ensure_tables(cls) -> None:
        """确保任务表存在。"""
        try:
            Base.metadata.create_all(get_engine(), tables=[WorkTask.__table__])
        except Exception as e:
            logger.error(f"创建任务表失败: {str(e)}", exc_info=True)

    @classmethod
    def generate_task_id(cls, session: Session) -> str:
        """
        生成任务业务ID，格式为 TASK-{年份}-{序号}（如 TASK-2026-0001）
        """
        current_year = datetime.now(timezone.utc).year
        prefix = f"TASK-{current_year}-"

        last_task = (
            session.query(WorkTask)
            .filter(WorkTask.task_id.like(f"{prefix}%"))
            .order_by(desc(WorkTask.id))
            .first()
        )

        if last_task and last_task.task_id:
            try:
                seq = int(last_task.task_id.split("-")[-1])
                next_seq = seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"

    # ==================== 查询 ====================

    @classmethod
    def get_task_list(
        cls,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        查询任务列表，支持筛选、搜索和分页
        """
        try:
            with db_session_factory() as session:
                query = session.query(WorkTask)

                if status:
                    query = query.filter(WorkTask.status == status)

                if priority:
                    query = query.filter(WorkTask.priority == priority)

                if search:
                    search_pattern = f"%{search}%"
                    assignee_ids = (
                        session.query(User.id)
                        .filter(User.username.ilike(search_pattern))
                        .all()
                    )
                    assignee_id_list = [uid for (uid,) in assignee_ids]

                    conditions = [
                        WorkTask.topic.ilike(search_pattern),
                        WorkTask.task_id.ilike(search_pattern),
                    ]
                    if assignee_id_list:
                        conditions.append(
                            WorkTask.assignee_id.in_(assignee_id_list)
                        )

                    query = query.filter(or_(*conditions))

                total = query.count()

                offset = (page - 1) * page_size
                tasks = (
                    query.order_by(desc(WorkTask.updated_at))
                    .offset(offset)
                    .limit(page_size)
                    .all()
                )

                user_ids = set()
                pond_ids = set()
                for t in tasks:
                    if t.creator_id:
                        user_ids.add(t.creator_id)
                    if t.assignee_id:
                        user_ids.add(t.assignee_id)
                    if t.pond_id:
                        pond_ids.add(t.pond_id)

                users_map = {}
                if user_ids:
                    users = session.query(User).filter(User.id.in_(user_ids)).all()
                    users_map = {u.id: u for u in users}

                ponds_map = {}
                if pond_ids:
                    ponds = session.query(Pond).filter(Pond.id.in_(pond_ids)).all()
                    ponds_map = {p.id: p for p in ponds}

                items = []
                for task in tasks:
                    creator = users_map.get(task.creator_id)
                    assignee = users_map.get(task.assignee_id) if task.assignee_id else None
                    pond = ponds_map.get(task.pond_id) if task.pond_id else None
                    items.append(cls._format_task(task, creator, assignee, pond))

                total_pages = (total + page_size - 1) // page_size if total > 0 else 0
                pagination = {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                }

                return items, pagination

        except Exception as e:
            logger.error(f"查询任务列表失败: {str(e)}", exc_info=True)
            raise

    # ==================== 创建 ====================

    @classmethod
    def create_task(
        cls,
        topic: str,
        priority: str,
        creator_name: str,
        assignee_id: int,
        pond_id: Optional[int] = None,
        deadline: Optional[str] = None,
        status: str = "pending",
        description: Optional[str] = None,
        execute_immediately: bool = False,
    ) -> Dict[str, Any]:
        """
        创建新任务
        """
        try:
            with db_session_factory() as session:
                creator = session.query(User).filter(User.username == creator_name).first()
                if not creator:
                    raise ValueError(f"创建人不存在: {creator_name}")

                assignee = session.query(User).filter(User.id == assignee_id).first()
                if not assignee:
                    raise ValueError(f"负责人不存在: {assignee_id}")

                pond = None
                if pond_id:
                    pond = session.query(Pond).filter(Pond.id == pond_id).first()
                    if not pond:
                        raise ValueError(f"池位不存在: {pond_id}")

                task_id = cls.generate_task_id(session)

                task = WorkTask(
                    topic=topic,
                    priority=priority,
                    creator_id=creator.id,
                )

                task.task_id = task_id
                task.description = description

                task.assignee_id = assignee_id
                if pond_id:
                    task.pond_id = pond_id

                if deadline:
                    try:
                        task.deadline = datetime.fromisoformat(
                            deadline.replace("Z", "+00:00")
                        )
                    except ValueError:
                        raise ValueError(f"截止时间格式不正确: {deadline}")

                if execute_immediately:
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)
                else:
                    task.status = status

                session.add(task)
                session.commit()
                session.refresh(task)

                result = cls._format_task(task, creator, assignee, pond)
                logger.info(f"创建任务成功: {task_id}")
                return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}", exc_info=True)
            raise

    # ==================== 更新 ====================

    @classmethod
    def update_task(cls, task_pk_id: int, **kwargs) -> Dict[str, Any]:
        """
        更新任务，支持部分更新
        """
        try:
            with db_session_factory() as session:
                task = session.query(WorkTask).filter(WorkTask.id == task_pk_id).first()

                if not task:
                    raise ValueError(f"任务不存在: {task_pk_id}")

                new_status = kwargs.get("status")
                execute_immediately = kwargs.pop("execute_immediately", False)

                if task.status == "completed":
                    if new_status and new_status in ("pending", "in_progress"):
                        raise ValueError("已完成的任务不允许修改状态为待处理或进行中")
                    if execute_immediately:
                        raise ValueError("任务已经是完成状态")

                allowed_fields = [
                    "topic",
                    "priority",
                    "assignee_id",
                    "pond_id",
                    "deadline",
                    "status",
                    "description",
                ]

                if "assignee_id" in kwargs and kwargs["assignee_id"] is not None:
                    assignee = (
                        session.query(User)
                        .filter(User.id == kwargs["assignee_id"])
                        .first()
                    )
                    if not assignee:
                        raise ValueError(f"负责人不存在: {kwargs['assignee_id']}")

                if "pond_id" in kwargs and kwargs["pond_id"] is not None:
                    pond = (
                        session.query(Pond)
                        .filter(Pond.id == kwargs["pond_id"])
                        .first()
                    )
                    if not pond:
                        raise ValueError(f"池位不存在: {kwargs['pond_id']}")

                if "deadline" in kwargs and kwargs["deadline"] is not None:
                    try:
                        kwargs["deadline"] = datetime.fromisoformat(
                            kwargs["deadline"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        raise ValueError(f"截止时间格式不正确: {kwargs['deadline']}")

                for key, value in kwargs.items():
                    if key in allowed_fields and value is not None:
                        setattr(task, key, value)

                if execute_immediately:
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)

                session.commit()
                session.refresh(task)

                creator = (
                    session.query(User).filter(User.id == task.creator_id).first()
                )
                assignee_obj = (
                    session.query(User).filter(User.id == task.assignee_id).first()
                    if task.assignee_id
                    else None
                )
                pond_obj = (
                    session.query(Pond).filter(Pond.id == task.pond_id).first()
                    if task.pond_id
                    else None
                )

                result = cls._format_task(task, creator, assignee_obj, pond_obj)
                logger.info(f"更新任务成功: {task.task_id}")
                return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新任务失败: {str(e)}", exc_info=True)
            raise

    # ==================== 删除（撤销） ====================

    @classmethod
    def delete_task(cls, task_pk_id: int) -> Dict[str, Any]:
        """
        撤销（物理删除）任务，仅 pending/in_progress 状态可撤销
        """
        try:
            with db_session_factory() as session:
                task = session.query(WorkTask).filter(WorkTask.id == task_pk_id).first()

                if not task:
                    raise ValueError(f"任务不存在: {task_pk_id}")

                if task.status == "completed":
                    raise ValueError("已完成的任务不可撤销")

                result = {
                    "id": task.id,
                    "task_id": task.task_id,
                }

                session.delete(task)
                session.commit()

                logger.info(f"撤销任务成功: {result['task_id']}")
                return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"撤销任务失败: {str(e)}", exc_info=True)
            raise

    # ==================== 辅助方法 ====================

    @classmethod
    def _format_task(
        cls,
        task: WorkTask,
        creator: Optional[User],
        assignee: Optional[User],
        pond: Optional[Pond],
    ) -> Dict[str, Any]:
        """格式化任务信息"""
        return {
            "id": task.id,
            "task_id": task.task_id,
            "topic": task.topic,
            "priority": task.priority,
            "status": task.status,
            "creator_id": task.creator_id,
            "creator_name": creator.username if creator else None,
            "assignee_id": task.assignee_id,
            "assignee_name": assignee.username if assignee else None,
            "pond_id": task.pond_id,
            "pond_name": pond.name if pond else None,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "description": task.description,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
