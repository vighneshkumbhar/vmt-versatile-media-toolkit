from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, Base
from app.routers import auth, extensions, developer, admin, submissions
from app.security.rate_limiter import slowapi_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="VMT Extension Ecosystem API",
    description="Backend service for VMT developer identity and secure extension submission pipeline.",
    version="1.0.1",
    lifespan=lifespan
)

# SlowAPI Rate Limiter integration
app.state.limiter = slowapi_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration with explicit origins (No wildcard '*' when credentialed authentication is used)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Router Registration
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
app.include_router(extensions.router, prefix="/extensions", tags=["extensions"])
app.include_router(developer.router, prefix="/developer", tags=["developer"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
