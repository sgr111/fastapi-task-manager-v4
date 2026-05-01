"""Task service with business logic."""

from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.task import Task, AuditLog
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.pagination import calculate_pagination


async def create_task(db: AsyncSession, task_create: TaskCreate, user_id: int) -> Task:
    """Create a new task."""
    # Ensure metadata is a dict, not a SQLAlchemy object
    metadata = task_create.metadata if isinstance(task_create.metadata, dict) else None
    
    task = Task(
        title=task_create.title,
        description=task_create.description,
        metadata_=metadata,
        owner_id=user_id,
    )
    db.add(task)
    await db.flush()
    
    # Create audit log for creation
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
    await db.flush()
    
    # Don't refresh - keep metadata as dict
    # Manually set created_at and updated_at if needed
    if task.created_at is None:
        task.created_at = datetime.utcnow()
    if task.updated_at is None:
        task.updated_at = datetime.utcnow()
    
    # Ensure metadata_ is a dict
    if task.metadata_ is None:
        task.metadata_ = {}
    elif not isinstance(task.metadata_, dict):
        try:
            task.metadata_ = dict(task.metadata_)
        except:
            task.metadata_ = {}
    
    return task


async def get_task_by_id(db: AsyncSession, task_id: int, user_id: int) -> Task | None:
    """Get a task by ID (must belong to user)."""
    result = await db.execute(
        select(Task)
        .where(and_(Task.id == task_id, Task.owner_id == user_id))
        .options(selectinload(Task.audit_logs))
    )
    return result.scalar_one_or_none()


async def get_tasks_by_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 10
) -> tuple[list[Task], int]:
    """Get all active (non-deleted) tasks for a user."""
    # Get total count
    count_result = await db.execute(
        select(Task).where(
            and_(Task.owner_id == user_id, Task.deleted_at.is_(None))
        )
    )
    total = len(count_result.scalars().all())
    
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
    """Update a task (partial updates supported)."""
    old_values = {
        "title": task.title,
        "description": task.description,
        "is_completed": task.is_completed,
        "metadata": task.metadata_,
    }
    
    # Update only provided fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata":
            setattr(task, "metadata_", value)
        else:
            setattr(task, field, value)
    
    await db.flush()
    
    new_values = {
        "title": task.title,
        "description": task.description,
        "is_completed": task.is_completed,
        "metadata": task.metadata_,
    }
    
    # Create audit log for update
    audit_log = AuditLog(
        task_id=task.id,
        action="UPDATE",
        old_values=old_values,
        new_values=new_values,
        changed_by=user_id,
    )
    db.add(audit_log)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    """Soft delete a task."""
    old_values = {
        "title": task.title,
        "deleted_at": None,
    }
    
    task.soft_delete()  # Mark as deleted
    await db.flush()
    
    # Create audit log for deletion
    audit_log = AuditLog(
        task_id=task.id,
        action="DELETE",
        old_values=old_values,
        new_values={"deleted_at": task.deleted_at.isoformat()},
        changed_by=task.owner_id,
    )
    db.add(audit_log)
    await db.flush()


async def get_audit_logs_for_task(db: AsyncSession, task_id: int) -> list[AuditLog]:
    """Get all audit logs for a task."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.task_id == task_id)
        .order_by(AuditLog.changed_at.asc())
    )
    return result.scalars().all()