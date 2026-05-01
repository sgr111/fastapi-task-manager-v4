"""User service for authentication and user management."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.schemas.user import UserCreate, UserUpdate


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = hash_password(user_create.password)
    db_user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.tasks))
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    """Authenticate user by username and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(
    db: AsyncSession, user_id: int, user_update: UserUpdate
) -> User | None:
    """Update user information."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user by ID."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.flush()
    return True


async def user_exists(db: AsyncSession, username: str, email: str) -> bool:
    """Check if user with username or email already exists."""
    result = await db.execute(
        select(User).where((User.username == username) | (User.email == email))
    )
    return result.scalar_one_or_none() is not None