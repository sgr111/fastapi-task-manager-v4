"""
Shared rate limiter instance.
Import this in both main.py and endpoint files to use the SAME limiter.
Uses username-based rate limiting when authenticated, falls back to IP.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_or_ip(request: Request) -> str:
    """Rate limit by username if authenticated, else by IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        try:
            from app.core.security import get_username_from_token
            username = get_username_from_token(token)
            if username:
                return username
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip)