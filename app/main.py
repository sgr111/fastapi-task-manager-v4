from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.exceptions import AppException

# Import models so Alembic can detect them
from app.models import task, user  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"📚 Docs: /docs")
    print(f"🔗 API: /api/v1")
    yield
    # Shutdown
    print(f"🛑 {settings.APP_NAME} shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-grade task management REST API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,  # replaces deprecated @app.on_event
    )

    # ===== MIDDLEWARE =====
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== RATE LIMITING =====
    app.state.limiter = limiter

    # ===== ERROR HANDLERS =====

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": exc.code,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "code": "RATE_LIMIT_EXCEEDED",
                "detail": str(exc.detail),
            },
        )

    # ===== ROUTES =====
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health/db", tags=["Health"])
    async def db_health_check(db: AsyncSession = Depends(get_db)):
        """Check database connectivity."""
        try:
            await db.execute(text("SELECT 1"))
            return {"database": "ok", "status": "connected"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection failed: {str(e)}",
            )

    return app


app = create_app()