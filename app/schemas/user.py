"""Pydantic schemas for user validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from pydantic import field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "SecurePass123!",
            }
        }
    }


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "newusername",
                "email": "newemail@example.com",
                "password": "NewSecurePass123!",
            }
        }
    }


class UserResponse(UserBase):
    """Schema for user response (no password)."""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john@example.com",
                "created_at": "2024-04-01T10:00:00",
                "updated_at": "2024-04-01T10:00:00",
                "is_active": True,
            }
        }
    }


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "johndoe",
                "password": "SecurePass123!",
            }
        }
    }


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }


class AccessTokenOnly(BaseModel):
    """Schema for access token only response."""
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: str
    exp: int
    iat: int
    type: str = "access"


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }