"""
API v1 routers.

All API endpoints are versioned under /v1/.
"""
from fastapi import APIRouter
from app.api.v1 import auth, onboarding, sessions, diagnostic, practice, dashboard, reviews

# Create main v1 router
api_router = APIRouter(prefix="/v1")

# Include all sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Practice Sessions"])
api_router.include_router(diagnostic.router, prefix="/diagnostic", tags=["Diagnostic Assessment"])
api_router.include_router(practice.router, prefix="/practice", tags=["Practice Sessions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Spaced Repetition"])

__all__ = ["api_router"]
