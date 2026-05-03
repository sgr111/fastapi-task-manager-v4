"""Task service with business logic."""
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, AuditLog
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.pagination import calculate_pagination


def _safe_metadata(value) -> Optional[dict]:
    """Safely convert metadata to dict."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:
        return None


from typing import Optional


async def create_task(db: AsyncSession, task_create: TaskCreate, user_id: int) -> Task:
    """Create a new task with audit log."""
    metadata = _safe_metadata(task_create.metadata)

    task = Task(
        title=task_create.title,
        description=task_create.description,
        metadata_=metadata,
        owner_id=user_id,
    )
    db.add(task)
    await db.flush()

    audit_log = AuditLog(
        task_id=task.id,
        action="CREATE",
        new_values={
            "title": task.title,
            "description": task.description,
            "metadata": metadata,
        },
        changed_by=user_id,
    )
    db.add(audit_log)
    # FIX: commit so data is persisted
    await db.commit()
    await db.refresh(task)

    # FIX: ensure metadata_ is a plain dict after refresh
    if task.metadata_ is not None and not isinstance(task.metadata_, dict):
        task.metadata_ = _safe_metadata(task.metadata_)

    return task


async def get_task_by_id(db: AsyncSession, task_id: int, user_id: int) -> Task | None:
    """Get a task by ID (must belong to user)."""
    result = await db.execute(
        select(Task)
        .where(and_(Task.id == task_id, Task.owner_id == user_id))
        .options(selectinload(Task.audit_logs))
    )
    return result.scalar_one_or_none()

async def get_task_by_id_any_user(db: AsyncSession, task_id: int) -> Task | None:
    """Get task by ID regardless of owner - used to distinguish 403 vs 404."""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.audit_logs))
    )
    return result.scalar_one_or_none()

async def get_tasks_by_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 10
) -> tuple[list[Task], int]:
    """Get all active (non-deleted) tasks for a user with count."""
    # Get total count efficiently
    count_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.owner_id == user_id, Task.deleted_at.is_(None))
        )
    )
    total = count_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(Task)
        .where(and_(Task.owner_id == user_id, Task.deleted_at.is_(None)))
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(Task.audit_logs))
    )
    tasks = result.scalars().all()
    return tasks, total


async def update_task(
    db: AsyncSession, task: Task, task_update: TaskUpdate, user_id: int
) -> Task:
    """Update a task (partial updates supported) with audit log."""
    old_values = {
        "title": task.title,
        "description": task.description,
        "is_completed": task.is_completed,
        "metadata": _safe_metadata(task.metadata_),
    }

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata":
            setattr(task, "metadata_", value)

        elif field == "status":
            current_metadata = _safe_metadata(task.metadata_) or {}
            current_metadata["__status"] = value
            task.metadata_ = current_metadata
        elif field == "priority":
            current_metadata = _safe_metadata(task.metadata_) or {}
            current_metadata["__priority"] = value
            task.metadata_ = current_metadata
        else:
            setattr(task, field, value)

    await db.flush()

    new_values = {
        "title": task.title,
        "description": task.description,
        "is_completed": task.is_completed,
        "metadata": _safe_metadata(task.metadata_),
    }

    audit_log = AuditLog(
        task_id=task.id,
        action="UPDATE",
        old_values=old_values,
        new_values=new_values,
        changed_by=user_id,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(task)

    if task.metadata_ is not None and not isinstance(task.metadata_, dict):
        task.metadata_ = _safe_metadata(task.metadata_)

    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    """Soft delete a task with audit log."""
    old_values = {
        "title": task.title,
        "deleted_at": None,
    }

    task.soft_delete()
    await db.flush()

    audit_log = AuditLog(
        task_id=task.id,
        action="DELETE",
        old_values=old_values,
        new_values={"deleted_at": task.deleted_at.isoformat()},
        changed_by=task.owner_id,
    )
    db.add(audit_log)
    await db.commit()


async def get_audit_logs_for_task(db: AsyncSession, task_id: int) -> list[AuditLog]:
    """Get all audit logs for a task ordered by time."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.task_id == task_id)
        .order_by(AuditLog.changed_at.asc())
    )
    return result.scalars().all()
