# Initialize routes package
from fastapi import APIRouter
from .auth_routes import router as auth_router
from .transcript_routes import router as transcript_router
from .health_routes import router as health_router
from .qa_routes import router as qa_router
from .admin import router as admin_router
from .youtube_routes import router as youtube_router
from .payment_routes import router as payment_router
from .webhook_routes import router as webhook_router
# Temporarily commented out to prevent deployment issues
# from .debug_routes import router as debug_router

# Create main router
api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(transcript_router)
api_router.include_router(health_router)
api_router.include_router(qa_router)
api_router.include_router(admin_router)
api_router.include_router(youtube_router)
api_router.include_router(payment_router)
api_router.include_router(webhook_router, prefix="/webhooks/signalscope", tags=["webhooks"])
# Temporarily commented out to prevent deployment issues
# api_router.include_router(debug_router)

# Add more routers here as needed
# api_router.include_router(user_router)
# api_router.include_router(admin_router) 