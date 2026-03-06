from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import TaskFilters
from app.schemas import (
    ListResponse,
    PaginationMeta,
    PaginationParams,
    Priority,
    Status,
    TaskCreateRequest,
    TaskHistoryItem,
    TaskHistoryResponse,
    TaskResponse,
    TaskStatusUpdateRequest,
    TaskStatusUpdateResponse,
)
from app.services import InvalidStatusTransitionError, NotFoundError, TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_service(session: AsyncSession = Depends(get_session)) -> TaskService:
    return TaskService(session)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
    service: TaskService = Depends(get_service),
) -> TaskResponse:
    task = await service.create_task(payload)
    return TaskResponse.model_validate(task.__dict__)


@router.get("/", response_model=ListResponse[TaskResponse])
async def list_tasks(
    status_: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    assignee_id: int | None = None,
    project_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: TaskService = Depends(get_service),
) -> ListResponse[TaskResponse]:
    filters = TaskFilters(
        status=status_,
        priority=priority,
        assignee_id=assignee_id,
        project_id=project_id,
    )

    result = await service.list_tasks(filters=filters, limit=limit, offset=offset)

    items = [TaskResponse.model_validate(t.__dict__) for t in result.items]

    return ListResponse(
        items=items,
        meta=PaginationMeta(limit=limit, offset=offset, total=result.total),
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    service: TaskService = Depends(get_service),
) -> TaskResponse:
    try:
        task = await service.get_task(task_id)
        return TaskResponse.model_validate(task.__dict__)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{task_id}/status", response_model=TaskStatusUpdateResponse)
async def update_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    service: TaskService = Depends(get_service),
) -> TaskStatusUpdateResponse:
    try:
        task = await service.change_status(
            task_id=task_id,
            new_status=payload.new_status,
            changed_by=payload.changed_by,
        )

        return TaskStatusUpdateResponse(
            id=task.id,
            status=Status(task.status),
            updated_at=task.updated_at,
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/history", response_model=TaskHistoryResponse)
async def get_history(
    task_id: int,
    service: TaskService = Depends(get_service),
) -> TaskHistoryResponse:
    try:
        rows = await service.get_history(task_id)

        items = [
            TaskHistoryItem(
                id=row.id,
                task_id=row.task_id,
                from_status=Status(row.from_status),
                to_status=Status(row.to_status),
                changed_by=row.changed_by,
                changed_at=row.changed_at,
            )
            for row in rows
        ]

        return TaskHistoryResponse(task_id=task_id, items=items)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))