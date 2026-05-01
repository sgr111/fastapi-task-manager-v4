from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # ===== PHASE 1: NEW FIELDS =====
    # JSONB for flexible metadata (tags, priority, custom fields, etc.)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        JSON, 
        nullable=True, 
        default=None,
        name="metadata"  # Column name in DB
    )
    
    # Soft delete: null = active, datetime = deleted
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True, 
        index=True
    )
    
    # ===== TIMESTAMPS =====
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now()
    )

    # Foreign key → links task to its owner
    owner_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )

    # Relationship — back-reference to User
    owner: Mapped[User] = relationship("User", back_populates="tasks")
    
    # Relationship — back-reference to AuditLog (Phase 1)
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", 
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # ===== METHODS =====
    
    def is_deleted(self) -> bool:
        """Check if task is soft-deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark task as deleted without removing from DB."""
        self.deleted_at = datetime.now(datetime.timezone.utc)
    
    def restore(self) -> None:
        """Restore a soft-deleted task."""
        self.deleted_at = None


class AuditLog(Base):
    """Phase 1: CDC (Change Data Capture) - tracks task changes."""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Action: CREATE, UPDATE, DELETE
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # JSON snapshot of old/new values
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Who made the change
    changed_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # When the change was made
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    
    # Optional: reason for change (e.g., "User requested deletion")
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationship
    task: Mapped[Task] = relationship("Task", back_populates="audit_logs")


# Import at the end to avoid circular imports
from app.models.user import User  # noqa: E402, F401
