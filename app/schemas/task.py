from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import model_validator


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[dict] = Field(None, description="Flexible JSONB metadata")


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    priority: Optional[str] = None
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
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    is_completed: Optional[bool] = None
    status: Optional[str] = None
    priority: Optional[str] = None
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
    id: int
    title: str
    description: Optional[str]
    is_completed: bool
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    # FIX: alias metadata_ model field to metadata in response
    metadata: Optional[dict] = Field(None, serialization_alias="metadata", alias="metadata_")
    owner_id: int = Field(..., alias="user_id")
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

    @model_validator(mode="before")
    @classmethod
    def extract_status_priority(cls, data):
        if hasattr(data, "metadata_"):
            meta = data.metadata_
            if isinstance(meta, dict):
                if "__status" in meta:
                    data.__dict__["status"] = meta["__status"]
                if "__priority" in meta:
                    data.__dict__["priority"] = meta["__priority"]
        return data


class PaginatedTaskResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    skip: int
    limit: int
    has_more: bool  # FIX: required field included

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 10,
                "skip": 0,
                "limit": 10,
                "has_more": False,
            }
        }
    }


class AuditLogResponse(BaseModel):
    id: int
    task_id: int
    action: str
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    changed_by: Optional[int] = None
    changed_at: datetime

    model_config = {
        "from_attributes": True,
    }
