"""Task endpoints for CRUD operations with rate limiting."""

from typing import List, Optional  # removed duplicate
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.task_service import get_task_by_id_any_user
from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    PaginatedTaskResponse,
    AuditLogResponse,
)
from app.services.task_service import (
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_user,
    update_task,
    get_audit_logs_for_task,
)
from app.utils.pagination import calculate_pagination

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get(
    "/",
    response_model=PaginatedTaskResponse,
    summary="List user's tasks with pagination and filtering",  # kept the better summary
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def list_tasks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1),
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in task title"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(limit, settings.MAX_PAGE_SIZE)
    tasks, total = await get_tasks_by_user(
        db, current_user.id, skip, limit,
        is_completed=is_completed,
        search=search,
    )
    pagination = calculate_pagination(total, skip, limit)
    return {"items": tasks, **pagination}


@router.post(                               # ← was missing entirely
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def create_new_task(
    request: Request,
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_task(db, task_data, current_user.id)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a single task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def get_task(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await get_task_by_id_any_user(db, task_id)
    if not task or task.is_deleted():
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return task


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def update_existing_task(
    request: Request,
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task or task.is_deleted():
        raise HTTPException(status_code=404, detail="Task not found")
    return await update_task(db, task, task_data, current_user.id)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task (soft delete)",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def delete_existing_task(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task or task.is_deleted():
        raise HTTPException(status_code=404, detail="Task not found")
    await delete_task(db, task)


@router.get(
    "/{task_id}/audit",
    response_model=List[AuditLogResponse],
    summary="Get audit log for a task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def get_task_audit_log(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return await get_audit_logs_for_task(db, task_id)