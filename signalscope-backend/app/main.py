"""
SignalScope Backend - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import structlog
from datetime import datetime
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time

from app.settings import settings
from app.routes import webhook_routes, report_routes
from app.services.redis_service import RedisService
from app.utils.logger import setup_logging

# Setup structured logging
setup_logging(log_level=settings.log_level)
logger = structlog.get_logger()

# Prometheus metrics
request_count = Counter("signalscope_requests_total", "Total requests", ["method", "endpoint"])
request_duration = Histogram("signalscope_request_duration_seconds", "Request duration")
active_connections = Gauge("signalscope_active_connections", "Active connections")
message_queue_depth = Gauge("signalscope_queue_depth", "Message queue depth", ["priority"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown
    """
    # Startup
    logger.info("Starting SignalScope Backend", version=settings.app_version)
    
    # Initialize Redis connection (use mock if Redis not available)
    try:
        redis_service = RedisService()
        await redis_service.initialize()
        app.state.redis = redis_service
        logger.info("Using real Redis service")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        logger.info("Falling back to mock Redis service (in-memory)")
        from app.services.mock_redis_service import MockRedisService
        redis_service = MockRedisService()
        await redis_service.initialize()
        app.state.redis = redis_service
    
    # Initialize Supabase connection if configured
    if settings.supabase_url and settings.supabase_key:
        try:
            from app.services.supabase_service import SupabaseService
            supabase_service = SupabaseService()
            await supabase_service.initialize()
            app.state.supabase = supabase_service
            logger.info("Supabase connection initialized")
        except Exception as e:
            logger.warning(f"Supabase initialization failed: {e}")
            logger.info("Running without database - data will not be persisted")
            app.state.supabase = None
    else:
        logger.warning("Supabase not configured - running without database")
        app.state.supabase = None
    
    logger.info("SignalScope Backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SignalScope Backend")
    
    # Cleanup Redis connection
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
    
    # Cleanup Supabase connection
    if hasattr(app.state, "supabase"):
        await app.state.supabase.close()
    
    logger.info("SignalScope Backend shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Trading Intelligence Processing Pipeline for SignalScope",
    lifespan=lifespan,
    debug=settings.debug
)

# Add CORS middleware
# Include "null" for local file testing and "*" for development
cors_origins = settings.cors_origins + ["null", "*"] if settings.debug else settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)


# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics and add request ID"""
    request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
    
    # Track metrics
    active_connections.inc()
    start_time = time.time()
    
    # Add request ID to logger context
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Track success metrics
        duration = time.time() - start_time
        request_count.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()
        request_duration.observe(duration)
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(duration)
        
        return response
        
    except Exception as e:
        logger.error("Request failed", error=str(e), request_id=request_id)
        raise
    finally:
        active_connections.dec()
        structlog.contextvars.unbind_contextvars("request_id")


# Health check endpoint
@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "services": {}
    }
    
    # Check Redis
    try:
        if hasattr(request.app.state, "redis"):
            await request.app.state.redis.ping()
            health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Supabase
    try:
        if hasattr(request.app.state, "supabase"):
            await request.app.state.supabase.health_check()
            health_status["services"]["supabase"] = "healthy"
    except Exception as e:
        health_status["services"]["supabase"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


# Ready check endpoint
@app.get("/ready")
async def ready_check():
    """Readiness check for Kubernetes"""
    return {"ready": True, "timestamp": datetime.utcnow().isoformat()}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Trading Intelligence Processing Pipeline",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "webhooks": "/api/webhooks/signalscope",
            "reports": "/api/reports",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# Include routers
app.include_router(
    webhook_routes.router,
    prefix="/api/webhooks",
    tags=["webhooks"]
)

app.include_router(
    report_routes.router,
    prefix="/api/reports",
    tags=["reports"]
)

# Mount Prometheus metrics endpoint
if settings.prometheus_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )