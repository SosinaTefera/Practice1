import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import (
    admin,
    auth,
    billing,
    catalogs,
    clients,
    exercises,
    fatigue,
    progress,
    session_programming,
    standalone_sessions,
    trainers,
    training_plans,
    training_sessions,
)
from .core.config import settings
from .core.logging import get_logger, setup_logging
from .db.session import get_db

# Setup logging
setup_logging()
logger = get_logger("main")


# Professional client IP detection for rate limiting
def get_real_client_ip(request: Request) -> str:
    """
    Extract real client IP from proxy headers.
    Handles X-Forwarded-For, X-Real-IP, and direct connections.
    """
    # Check X-Forwarded-For header (most common proxy header)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


# Rate limiter setup with real client IP detection
limiter = Limiter(key_func=get_real_client_ip)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    yield
    # Shutdown logic
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Professional fitness training management system",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.is_development else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Security middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS or ["*"],
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # CSP: relax in development to allow Swagger UI to load; strict in production
    if settings.is_development:
        # Allow inline/eval scripts and data: for Swagger UI in dev only
        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self' data: https://cdn.jsdelivr.net "
                "https://fastapi.tiangolo.com; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' data:; connect-src 'self'; "
                "frame-ancestors 'self'; base-uri 'self'"
            ),
        )
    else:
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
    return response


# Exception handlers
def _sanitize_for_json(obj):
    """Recursively convert non-serializable objects (e.g., Exceptions) to strings."""
    try:
        # Quick path for simple types
        import json

        json.dumps(obj)
        return obj
    except Exception:
        pass

    if isinstance(obj, Exception):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_for_json(v) for v in obj)
    return str(obj)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors (like unique constraints)"""
    logger.error(f"Database Integrity Error: {str(exc)}")

    if "unique constraint" in str(exc).lower():
        # Extract the constraint name and details
        detail = str(exc)
        if "idx_progress_tracking_unique" in detail:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Validation error",
                    "errors": [
                        {
                            "type": "unique_violation",
                            "loc": ["body"],
                            "msg": (
                                "A progress record for this client, exercise, "
                                "and date already exists"
                            ),
                            "input": None,
                        }
                    ],
                },
            )
        elif "idx_client_progress_unique" in detail:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Validation error",
                    "errors": [
                        {
                            "type": "unique_violation",
                            "loc": ["body"],
                            "msg": (
                                "A progress record for this client and date "
                                "already exists"
                            ),
                            "input": None,
                        }
                    ],
                },
            )
        else:
            # Generic unique constraint violation
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Validation error",
                    "errors": [
                        {
                            "type": "unique_violation",
                            "loc": ["body"],
                            "msg": "A record with these values already exists",
                            "input": None,
                        }
                    ],
                },
            )

    # Generic integrity error
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": [
                {
                    "type": "integrity_error",
                    "loc": ["body"],
                    "msg": "Data integrity constraint violated",
                    "input": None,
                }
            ],
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    safe_errors = _sanitize_for_json(exc.errors())
    return JSONResponse(
        status_code=422, content={"detail": "Validation error", "errors": safe_errors}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check endpoint with database connectivity
@app.get("/health")
async def health_check():
    try:
        # Test database connectivity
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "timestamp": time.time(),
    }


# API routes
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(clients.router, prefix=settings.API_V1_STR)
app.include_router(trainers.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(billing.router, prefix=f"{settings.API_V1_STR}")
app.include_router(catalogs.router, prefix=settings.API_V1_STR)
app.include_router(exercises.router, prefix=settings.API_V1_STR)
app.include_router(
    training_plans.router,
    prefix=f"{settings.API_V1_STR}/training-plans",
    tags=["Training Planning"],
)
app.include_router(
    training_sessions.router,
    prefix=f"{settings.API_V1_STR}/training-sessions",
    tags=["Training Sessions"],
)
app.include_router(
    standalone_sessions.router,
    prefix=f"{settings.API_V1_STR}/standalone-sessions",
    tags=["Standalone Sessions"],
)
app.include_router(
    progress.router,
    prefix=f"{settings.API_V1_STR}/progress",
    tags=["Progress Tracking"],
)
app.include_router(
    fatigue.router,
    prefix=f"{settings.API_V1_STR}/fatigue",
    tags=["Fatigue Analysis & Monitoring"],
)
app.include_router(
    session_programming.router,
    prefix=settings.API_V1_STR,
    tags=["Session Programming"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
