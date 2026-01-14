"""Rate limiting middleware using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


# Rate limit decorators
def default_limit():
    """Default rate limit for general endpoints."""
    return f"{settings.RATE_LIMIT_PER_MINUTE}/minute"


def auth_limit():
    """Stricter rate limit for auth endpoints."""
    return f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute"
