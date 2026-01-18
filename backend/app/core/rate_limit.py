"""Rate limiting middleware using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


def get_real_ip(request: Request) -> str:
    """
    Get the real client IP address, accounting for reverse proxies.

    Checks headers in order:
    1. X-Forwarded-For (most common proxy header)
    2. X-Real-IP (nginx)
    3. CF-Connecting-IP (Cloudflare)
    4. Falls back to direct remote address

    Returns the first non-private IP or the direct address.
    """
    # Check X-Forwarded-For (can contain multiple IPs, first is the client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (leftmost is the original client)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # Check X-Real-IP (set by nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Check Cloudflare header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # Fall back to direct remote address
    return get_remote_address(request)


limiter = Limiter(key_func=get_real_ip)


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
