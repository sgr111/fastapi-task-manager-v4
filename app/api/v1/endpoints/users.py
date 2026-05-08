"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import update_user, get_user_by_email, get_user_by_username

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_READ)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the currently logged-in user's profile."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
@limiter.limit(settings.RATE_LIMIT_TASKS_WRITE)
async def update_me(
    request: Request,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the currently logged-in user's profile."""
    # Check if new email already taken by another user
    if user_data.email and user_data.email != current_user.email:
        existing = await get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    # Check if new username already taken by another user
    if user_data.username and user_data.username != current_user.username:
        existing = await get_user_by_username(db, user_data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    updated = await update_user(db, current_user.id, user_data)
    return updated
