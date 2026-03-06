from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Priority, Status


class TaskCreateRequest(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: Priority
    author_id: int
    assignee_id: int | None = None


class TaskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    priority: Priority
    status: Status
    author_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime


class TaskStatusUpdateRequest(BaseModel):
    new_status: Status
    changed_by: int


class TaskStatusUpdateResponse(BaseModel):
    id: int
    status: Status
    updated_at: datetime


class TaskHistoryItem(BaseModel):
    id: int
    task_id: int
    from_status: Status
    to_status: Status
    changed_by: int
    changed_at: datetime


class TaskHistoryResponse(BaseModel):
    task_id: int
    items: list[TaskHistoryItem]