from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskStatusHistory


class TaskHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: TaskStatusHistory) -> TaskStatusHistory:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_by_task_id(self, task_id: int) -> Sequence[TaskStatusHistory]:
        stmt = (
            select(TaskStatusHistory)
            .where(TaskStatusHistory.task_id == task_id)
            .order_by(TaskStatusHistory.changed_at.asc())
        )
        return (await self._session.execute(stmt)).scalars().all()