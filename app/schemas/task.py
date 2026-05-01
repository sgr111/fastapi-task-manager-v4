from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseModel):
    """Base task schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[dict] = Field(None, description="Flexible JSONB metadata")


class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None  # Not used in model but accepted
    priority: Optional[str] = None  # Not used in model but accepted
    metadata: Optional[dict] = Field(None, description="Flexible JSONB metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Complete project report",
                "description": "Finish Q1 quarterly report",
                "metadata": {"tags": ["urgent", "report"], "department": "finance"}
            }
        }
    }


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    is_completed: Optional[bool] = None
    status: Optional[str] = None  # Not used but accepted for compatibility
    priority: Optional[str] = None  # Not used but accepted for compatibility
    metadata: Optional[dict] = Field(None, description="Flexible JSONB metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Updated task title",
                "is_completed": True,
                "metadata": {"completion_percentage": 100}
            }
        }
    }


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: int
    title: str
    description: Optional[str]
    is_completed: bool
    status: Optional[str] = "todo"  # For API compatibility
    priority: Optional[str] = "medium"  # For API compatibility
    owner_id: int = Field(..., alias="user_id")
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class PaginatedTaskResponse(BaseModel):
    """Schema for paginated task response."""
    items: List[TaskResponse]
    total: int
    skip: int
    limit: int
    has_more: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 10,
                "skip": 0,
                "limit": 10,
                "has_more": False
            }
        }
    }


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: int
    task_id: int
    action: str
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    changed_by: int
    changed_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "task_id": 1,
                "action": "CREATE",
                "old_values": None,
                "new_values": {"title": "New Task"},
                "changed_by": 1,
                "changed_at": "2024-04-01T10:00:00"
            }
        }
    }