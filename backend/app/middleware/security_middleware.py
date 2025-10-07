"""
Security middleware for BPT Pipeline API
Handles CORS, CSP, JWT validation, and security headers
"""
import os
import logging
from typing import List, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.services.supabase_client import get_supabase_client
from app.settings import get_settings

logger = logging.getLogger(__name__)

def get_cors_middleware():
    """Configure CORS middleware for Chrome extension support"""
    settings = get_settings()
    
    # Base allowed origins
    allowed_origins = [
        "http://localhost:3000",  # Development frontend
        "http://localhost:8000",  # FastAPI dev server
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://127.0.0.1:8000",  # Alternative localhost
    ]
    
    # Add Chrome extension origin if configured
    chrome_extension_id = getattr(settings, 'chrome_extension_id', None)
    if chrome_extension_id:
        allowed_origins.append(f"chrome-extension://{chrome_extension_id}")
        logger.info(f"Added Chrome extension origin: chrome-extension://{chrome_extension_id}")
    
    # For development/testing: Allow all origins (less secure but works for testing)
    # TODO: Configure proper Chrome extension ID in production
    if os.getenv("ENVIRONMENT", "development") != "production":
        allowed_origins = ["*"]  # Allow all origins for development
        logger.info("Development mode: Allowing all origins")
    
    # Add production frontend URL if configured
    frontend_url = getattr(settings, 'frontend_url', None)
    if frontend_url:
        allowed_origins.append(frontend_url)
        logger.info(f"Added frontend URL: {frontend_url}")
    
    return CORSMiddleware, {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "X-Idempotency-Key",
            "X-Extension-Request",  # Allow Chrome extension custom header
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Mx-ReqToken",
            "Keep-Alive",
        ],
        "expose_headers": [
            "X-Job-Id", 
            "X-Job-Status", 
            "X-Quota-Remaining",
            "X-Rate-Limit-Remaining"
        ],
    }

def get_trusted_host_middleware():
    """Configure trusted host middleware for production"""
    settings = get_settings()
    
    # Default to allow all in development
    allowed_hosts = ["*"]
    
    # Use configured hosts in production
    if os.getenv("ENVIRONMENT", "development") == "production":
        configured_hosts = getattr(settings, 'allowed_hosts', None)
        if configured_hosts:
            allowed_hosts = configured_hosts
        else:
            # Default production hosts
            allowed_hosts = [
                "localhost",
                "127.0.0.1",
                "*.railway.app",  # Railway deployment
            ]
    
    return TrustedHostMiddleware, {
        "allowed_hosts": allowed_hosts
    }

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https: wss: chrome-extension:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "media-src 'self' https: blob:; "
        "frame-src 'none'; "
        "base-uri 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    
    # Additional security headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    
    return response

async def jwt_validation_middleware(request: Request, call_next):
    """Validate JWT tokens for protected routes"""
    
    # Public routes that don't require authentication
    public_routes = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ]
    
    # Check if this is a public route
    path = request.url.path
    if any(path.startswith(route) for route in public_routes):
        return await call_next(request)
    
    # Extract authorization header
    authorization = request.headers.get("Authorization")
    
    if not authorization:
        logger.warning(f"Missing authorization header for {path}")
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authorization required",
                "message": "Please provide a valid JWT token in the Authorization header"
            }
        )
    
    try:
        # Extract token from "Bearer <token>" format
        if not authorization.startswith("Bearer "):
            raise ValueError("Invalid authorization format")
        
        token = authorization.split(" ", 1)[1]
        
        # Validate JWT with Supabase
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise ValueError("Invalid user response")
        
        # Add user info to request state
        request.state.user = user_response.user
        request.state.user_id = user_response.user.id
        
        logger.debug(f"Authenticated user {user_response.user.id} for {path}")
        
    except Exception as e:
        logger.warning(f"JWT validation failed for {path}: {e}")
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid or expired token",
                "message": "Please check your authentication token and try again"
            }
        )
    
    return await call_next(request)

async def rate_limiting_middleware(request: Request, call_next):
    """Basic rate limiting and request logging"""
    
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # Get client info
    client_ip = getattr(request.client, 'host', 'unknown')
    user_agent = request.headers.get('user-agent', 'unknown')
    
    # Log request for monitoring
    logger.info(
        f"API Request: {request.method} {request.url.path} "
        f"from {client_ip} ({user_agent[:50]}...)"
    )
    
    # TODO: Implement proper rate limiting with Redis
    # For now, just add rate limit headers
    response = await call_next(request)
    
    # Add rate limit headers (placeholder values)
    response.headers["X-Rate-Limit-Limit"] = "1000"
    response.headers["X-Rate-Limit-Remaining"] = "999"
    response.headers["X-Rate-Limit-Reset"] = "3600"
    
    return response

def setup_security_middleware(app):
    """Setup all security middleware for the FastAPI app"""
    
    # 1. CORS middleware (must be first)
    cors_class, cors_config = get_cors_middleware()
    app.add_middleware(cors_class, **cors_config)
    
    # 2. Trusted host middleware
    if os.getenv("ENVIRONMENT", "development") == "production":
        trusted_host_class, trusted_host_config = get_trusted_host_middleware()
        app.add_middleware(trusted_host_class, **trusted_host_config)
    
    # 3. Security headers middleware
    app.middleware("http")(security_headers_middleware)
    
    # 4. Rate limiting middleware
    app.middleware("http")(rate_limiting_middleware)
    
    # 5. JWT validation middleware (last, so it can use request state)
    app.middleware("http")(jwt_validation_middleware)
    
    logger.info("✅ Security middleware configured successfully")

# Exception handlers
async def security_exception_handler(request: Request, exc: Exception):
    """Handle security-related exceptions"""
    
    logger.error(f"Security exception on {request.method} {request.url}: {exc}")
    
    # Don't expose internal errors in production
    if os.getenv("ENVIRONMENT", "development") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__
            }
        ) 