from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of items to return (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int = Field(description="Total number of items in database")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Number of items returned")
    pages: int = Field(description="Total number of pages")
    
    class Config:
        arbitrary_types_allowed = True


def calculate_pagination(total: int, skip: int, limit: int) -> dict:
    """
    Calculate pagination metadata.
    
    Args:
        total: Total number of items
        skip: Number of items skipped
        limit: Number of items per page
        
    Returns:
        Dict with pagination metadata
    """
    pages = (total + limit - 1) // limit  # Ceiling division
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "pages": pages
    }
