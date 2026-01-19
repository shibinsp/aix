from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import limiter
from app.core.middleware import HTTPSRedirectMiddleware, SecurityHeadersMiddleware
from app.api.routes import auth, chat, courses, labs, skills, users, news
from app.api.routes import organizations, batches, environments, limits, invitations, analytics
from app.api.routes.admin import router as admin_router
from app.api.websockets import chat_ws, terminal_ws
from app.services.rag import knowledge_base
from app.services.labs.lab_manager import lab_manager

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting AI CyberX Platform...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize knowledge base with default content
    try:
        docs_added = knowledge_base.knowledge_base.initialize_with_defaults()
        logger.info(f"Knowledge base initialized with {docs_added} documents")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base: {e}")

    # Check Docker availability for lab orchestration
    docker_available = await lab_manager.check_docker_available()
    if docker_available:
        logger.info("Lab orchestration ready with Docker support")
    else:
        logger.warning("Docker not available - labs will run in simulation mode")

    yield

    # Shutdown - cleanup all active lab sessions
    logger.info("Shutting down AI CyberX Platform...")

    active_count = len(lab_manager.active_sessions)
    if active_count > 0:
        logger.info(f"Cleaning up {active_count} active lab sessions...")
        session_ids = list(lab_manager.active_sessions.keys())

        # Cleanup with timeout to prevent hanging
        cleanup_timeout = 30  # seconds

        async def cleanup_with_timeout():
            for session_id in session_ids:
                try:
                    await lab_manager.stop_lab_session(session_id)
                except Exception as e:
                    logger.error(f"Failed to cleanup session {session_id}: {e}")

        try:
            await asyncio.wait_for(cleanup_with_timeout(), timeout=cleanup_timeout)
            logger.info("Lab sessions cleaned up")
        except asyncio.TimeoutError:
            logger.warning(f"Lab cleanup timed out after {cleanup_timeout} seconds")

    try:
        await asyncio.wait_for(
            lab_manager.cleanup_expired_sessions(),
            timeout=10
        )
    except asyncio.TimeoutError:
        logger.warning("Expired sessions cleanup timed out")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CyberAIx - AI-Powered Cybersecurity Learning Platform",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware (apply to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# HTTPS redirect (enable in production behind reverse proxy)
if settings.FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS middleware - restricted to specific methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["AI Chat"])
app.include_router(courses.router, prefix=f"{settings.API_V1_PREFIX}/courses", tags=["Courses"])
app.include_router(labs.router, prefix=f"{settings.API_V1_PREFIX}/labs", tags=["Labs"])
app.include_router(skills.router, prefix=f"{settings.API_V1_PREFIX}/skills", tags=["Skills"])
app.include_router(news.router, prefix=f"{settings.API_V1_PREFIX}/news", tags=["Cyber News"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_PREFIX}/organizations", tags=["Organizations"])
app.include_router(batches.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Batches"])
app.include_router(environments.router, prefix=f"{settings.API_V1_PREFIX}/environments", tags=["Environments"])
app.include_router(limits.router, prefix=f"{settings.API_V1_PREFIX}/limits", tags=["Resource Limits"])
app.include_router(invitations.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Invitations"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(admin_router, prefix=settings.API_V1_PREFIX, tags=["Admin"])

# WebSocket endpoints
app.include_router(chat_ws.router, prefix="/ws", tags=["WebSocket"])
app.include_router(terminal_ws.router, prefix="/ws", tags=["WebSocket Terminal"])


@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - minimal info for load balancers."""
    return {
        "status": "healthy",
    }
