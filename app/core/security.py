from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# ===== PASSWORD HASHING =====

def hash_password(password: str) -> str:
    """Hash password using bcrypt with configurable rounds."""
    return bcrypt.hashpw(
        password.encode("utf-8"), 
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), 
        hashed_password.encode("utf-8")
    )


# ===== TOKEN MANAGEMENT =====

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with optional expiration override.
    
    Args:
        data: Claims to encode (usually {"sub": username})
        expires_delta: Custom expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token (longer expiration).
    
    Args:
        data: Claims to encode (usually {"sub": username})
        expires_delta: Custom expiration time (defaults to REFRESH_TOKEN_EXPIRE_DAYS)
    
    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token claims or None if invalid/expired/wrong type
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        # Validate token type (access tokens only)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT refresh token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token claims or None if invalid/expired/wrong type
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        # Validate token type (refresh tokens only)
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def get_username_from_token(token: str) -> Optional[str]:
    """Extract username from valid access token."""
    payload = decode_access_token(token)
    return payload.get("sub") if payload else None
