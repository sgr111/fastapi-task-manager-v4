"""Task endpoints for CRUD operations with rate limiting."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
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

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/",
    response_model=PaginatedTaskResponse,
    summary="List user's tasks with pagination",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def list_tasks(
    request: Request,  # Required for limiter - MUST BE FIRST
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Number of items to return",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all active tasks for the logged-in user with pagination.
    
    **Parameters:**
    - skip: How many tasks to skip (default 0)
    - limit: How many tasks to return (default 10, max 100)
    
    **Soft deletes:** Deleted tasks are excluded automatically
    """
    tasks, total = await get_tasks_by_user(db, current_user.id, skip, limit)
    pagination = calculate_pagination(total, skip, limit)
    
    return {
        "items": tasks,
        **pagination,
    }


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def create_new_task(
    request: Request,  # Required for limiter - MUST BE FIRST
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new task.
    
    **Fields:**
    - title: 3-255 characters (required)
    - description: Optional, max 2000 characters
    - status: todo, in_progress, done, cancelled (optional)
    - priority: low, medium, high, urgent (optional)
    - metadata: Optional JSONB object (e.g., tags, priority)
    
    **Example metadata:**
    ```json
    {
        "tags": ["urgent", "work"],
        "priority": "high",
        "category": "backend"
    }
    ```
    """
    return await create_task(db, task_data, current_user.id)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a single task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def get_task(
    request: Request,  # Required for limiter - MUST BE FIRST
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single task by ID (must be your own task)."""
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task or task.is_deleted():
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def update_existing_task(
    request: Request,  # Required for limiter - MUST BE FIRST
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a task (partial updates supported).
    
    **Supported fields:**
    - title: Update task title
    - description: Update task description
    - status: Update task status
    - priority: Update task priority
    - metadata: Update custom metadata
    
    Unchanged fields can be omitted.
    """
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task or task.is_deleted():
        raise HTTPException(status_code=404, detail="Task not found")
    return await update_task(db, task, task_data)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task (soft delete)",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def delete_existing_task(
    request: Request,  # Required for limiter - MUST BE FIRST
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a task using soft delete (marked as deleted, not removed from DB).
    
    **Note:** Task is hidden from list but audit logs are retained.
    """
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
    request: Request,  # Required for limiter - MUST BE FIRST
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the complete audit log (CDC) for a task.
    
    Shows:
    - All changes (CREATE, UPDATE, DELETE)
    - Old and new values
    - Who made the change
    - When it was changed
    
    **Use case:** Track task history and changes for compliance/debugging.
    """
    task = await get_task_by_id(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return await get_audit_logs_for_task(db, task_id)