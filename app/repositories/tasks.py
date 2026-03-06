from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.schemas.common import Priority, Status


@dataclass(frozen=True)
class TaskFilters:
    status: Status | None = None
    priority: Priority | None = None
    assignee_id: int | None = None
    project_id: int | None = None


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task: Task) -> Task:
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id_for_update(self, task_id: int) -> Task | None:
        stmt = select(Task).where(Task.id == task_id).with_for_update()
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        *,
        filters: TaskFilters,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Task], int]:
        base = select(Task)

        base = self._apply_filters(base, filters)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        items = (await self._session.execute(items_stmt)).scalars().all()

        return items, total

    async def set_status(self, task: Task, new_status: Status) -> Task:
        task.status = new_status.value  
        await self._session.flush()
        await self._session.refresh(task)
        return task

    def _apply_filters(self, stmt: Select[tuple[Task]], filters: TaskFilters) -> Select[tuple[Task]]:
        if filters.status is not None:
            stmt = stmt.where(Task.status == filters.status.value)
        if filters.priority is not None:
            stmt = stmt.where(Task.priority == filters.priority.value)
        if filters.assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == filters.assignee_id)
        if filters.project_id is not None:
            stmt = stmt.where(Task.project_id == filters.project_id)
        return stmt