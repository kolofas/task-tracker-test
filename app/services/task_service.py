from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskStatusHistory
from app.repositories import TaskFilters, TaskHistoryRepository, TaskRepository
from app.schemas.common import Priority, Status
from app.schemas.task import TaskCreateRequest


ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.created: {Status.in_progress, Status.cancelled},
    Status.in_progress: {Status.review, Status.created},
    Status.review: {Status.done, Status.in_progress},
    Status.done: set(),
    Status.cancelled: set(),
}


class DomainError(Exception):
    """Base domain error."""


class NotFoundError(DomainError):
    pass


class InvalidStatusTransitionError(DomainError):
    def __init__(self, from_status: Status, to_status: Status) -> None:
        super().__init__(f"Invalid status transition: {from_status.value} -> {to_status.value}")
        self.from_status = from_status
        self.to_status = to_status


@dataclass(frozen=True)
class ListTasksResult:
    items: list[Task]
    total: int


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._history = TaskHistoryRepository(session)

    async def create_task(self, payload: TaskCreateRequest) -> Task:
        # Минимальная бизнес-логика: статус при создании всегда created.
        task = Task(
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority.value,
            status=Status.created.value,
            author_id=payload.author_id,
            assignee_id=payload.assignee_id,
        )

        async with self._session.begin():
            created = await self._tasks.create(task)
            row = TaskStatusHistory(
                task_id=created.id,
                from_status=Status.created.value,
                to_status=Status.created.value,
                changed_by=payload.author_id,
            )
            
            await self._history.add(row)

        return created

    async def get_task(self, task_id: int) -> Task:
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def list_tasks(
        self,
        *,
        filters: TaskFilters,
        limit: int,
        offset: int,
    ) -> ListTasksResult:
        items, total = await self._tasks.list(filters=filters, limit=limit, offset=offset)
        return ListTasksResult(items=list(items), total=total)

    async def change_status(
        self,
        *,
        task_id: int,
        new_status: Status,
        changed_by: int,
    ) -> Task:
        async with self._session.begin():
            task = await self._tasks.get_by_id_for_update(task_id)
            if task is None:
                raise NotFoundError(f"Task {task_id} not found")

            current = Status(task.status) 
            self._validate_transition(current, new_status)

            await self._tasks.set_status(task, new_status)

            row = TaskStatusHistory(
                task_id=task.id,
                from_status=current.value,
                to_status=new_status.value,
                changed_by=changed_by,
            )
            await self._history.add(row)

            return task

    async def get_history(self, task_id: int) -> list[TaskStatusHistory]:
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")

        rows = await self._history.list_by_task_id(task_id)
        return list(rows)

    def _validate_transition(self, from_status: Status, to_status: Status) -> None:
        allowed = ALLOWED_TRANSITIONS[from_status]
        if to_status not in allowed:
            raise InvalidStatusTransitionError(from_status, to_status)