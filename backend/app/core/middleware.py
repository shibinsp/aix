"""HTTPS redirect middleware."""
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production."""
    
    async def dispatch(self, request: Request, call_next):
        # Check X-Forwarded-Proto header (set by reverse proxy)
        forwarded_proto = request.headers.get("x-forwarded-proto")
        
        if forwarded_proto == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)
        
        return await call_next(request)
