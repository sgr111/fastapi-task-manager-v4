from fastapi import status


class AppException(Exception):
    """Base exception for the application."""
    def __init__(
        self, 
        detail: str, 
        status_code: int = 400, 
        code: str = "INTERNAL_ERROR"
    ):
        self.detail = detail
        self.status_code = status_code
        self.code = code
        super().__init__(self.detail)


# ===== AUTHENTICATION ERRORS =====

class UnauthorizedError(AppException):
    """User is not authenticated or token is invalid."""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED"
        )


class ForbiddenError(AppException):
    """User is authenticated but doesn't have permission."""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN"
        )


class InvalidTokenError(AppException):
    """Token is malformed or invalid."""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN"
        )


class TokenExpiredError(AppException):
    """Token has expired."""
    def __init__(self, detail: str = "Token expired"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED"
        )


# ===== RESOURCE ERRORS =====

class NotFoundError(AppException):
    """Resource not found."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            detail=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND"
        )


class TaskNotFoundError(NotFoundError):
    """Task not found."""
    def __init__(self):
        super().__init__(resource="Task")


class UserNotFoundError(NotFoundError):
    """User not found."""
    def __init__(self):
        super().__init__(resource="User")


# ===== VALIDATION ERRORS =====

class ValidationError(AppException):
    """Input validation failed."""
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR"
        )


class DuplicateError(AppException):
    """Resource already exists."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            detail=f"{resource} already exists",
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE"
        )


class DuplicateEmailError(DuplicateError):
    """Email already registered."""
    def __init__(self):
        super().__init__(resource="Email")


class DuplicateUsernameError(DuplicateError):
    """Username already taken."""
    def __init__(self):
        super().__init__(resource="Username")


class WeakPasswordError(ValidationError):
    """Password doesn't meet strength requirements."""
    def __init__(self):
        super().__init__(
            detail="Password must be at least 8 characters with uppercase and number"
        )


# ===== RATE LIMIT ERRORS =====

class RateLimitError(AppException):
    """Rate limit exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED"
        )


# ===== AUTHENTICATION LOGIC ERRORS =====

class InvalidCredentialsError(AppException):
    """Username or password is incorrect."""
    def __init__(self):
        super().__init__(
            detail="Invalid username or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS"
        )
