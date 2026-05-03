from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.limiter import limiter
from app.core.config import settings

from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.db.session import get_db
from app.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.schemas.user import (
    Token,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
    AccessTokenOnly,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    
    **Required fields:**
    - email: Valid email address
    - username: 3-50 characters, unique
    - password: 8+ characters with uppercase and number
    """
    # Check if email already exists
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Check if username already exists
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    
    user = await create_user(db, user_data)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get tokens",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username and password.
    
    Returns both **access_token** (30 min) and **refresh_token** (7 days).
    
    **Use access_token:**
    - Add to header: `Authorization: Bearer <access_token>`
    - For all protected endpoints
    
    **Use refresh_token:**
    - When access token expires
    - POST to /auth/refresh endpoint
    """
    user = await authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/refresh",
    response_model=AccessTokenOnly,
    summary="Refresh access token",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def refresh_access_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a new access token using a refresh token.
    
    **Flow:**
    1. Your access token expires (30 min)
    2. Use refresh token (7 day expiry) to get new access token
    3. Add new access token to Authorization header
    
    **When refresh token expires:**
    - User must login again
    """
    payload = decode_refresh_token(token_data.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Verify user still exists
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Generate new access token
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
