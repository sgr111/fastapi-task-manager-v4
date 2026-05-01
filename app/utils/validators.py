import re
from email_validator import validate_email, EmailNotValidError

from app.core.config import settings
from app.exceptions import WeakPasswordError, ValidationError


def validate_password_strength(password: str) -> bool:
    """
    Validate password meets security requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one number
    - At least one special character (optional but recommended)
    
    Args:
        password: Password to validate
        
    Returns:
        True if password is strong
        
    Raises:
        WeakPasswordError: If password doesn't meet requirements
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise WeakPasswordError()
    
    if not re.search(r"[A-Z]", password):
        raise WeakPasswordError()
    
    if not re.search(r"\d", password):
        raise WeakPasswordError()
    
    return True


def validate_email_format(email: str) -> str:
    """
    Validate email format and normalize it.
    
    Args:
        email: Email to validate
        
    Returns:
        Normalized email address
        
    Raises:
        ValidationError: If email is invalid
    """
    try:
        valid_email = validate_email(email, check_deliverability=False)
        return valid_email.normalized
    except EmailNotValidError as e:
        raise ValidationError(detail=f"Invalid email: {str(e)}")


def validate_title(title: str, min_length: int = 3, max_length: int = 255) -> bool:
    """
    Validate task title length.
    
    Args:
        title: Title to validate
        min_length: Minimum length (default 3)
        max_length: Maximum length (default 255)
        
    Returns:
        True if title is valid
        
    Raises:
        ValidationError: If title length is invalid
    """
    if len(title.strip()) < min_length:
        raise ValidationError(detail=f"Title must be at least {min_length} characters")
    
    if len(title) > max_length:
        raise ValidationError(detail=f"Title must not exceed {max_length} characters")
    
    return True


def validate_description(description: str, max_length: int = 2000) -> bool:
    """
    Validate task description length.
    
    Args:
        description: Description to validate
        max_length: Maximum length (default 2000)
        
    Returns:
        True if description is valid
        
    Raises:
        ValidationError: If description is too long
    """
    if description and len(description) > max_length:
        raise ValidationError(detail=f"Description must not exceed {max_length} characters")
    
    return True
