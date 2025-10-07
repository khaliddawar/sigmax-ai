"""Observability Middleware

This module provides comprehensive observability features including:
- Structured logging with correlation IDs
- Request/response metrics collection
- Circuit breaker monitoring
- Performance tracking
- Error rate monitoring
"""
from __future__ import annotations

import time
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

# Import our structured logging system
from ..utils.structured_logging import (
    StructuredLogger, MetricsCollector, MetricEvent,
    set_correlation_id, generate_correlation_id, set_request_context,
    clear_request_context, get_correlation_id
)

logger = StructuredLogger("observability-middleware", "middleware")


# ---------------------------------------------------------------------------
# Circuit Breaker Implementation
# ---------------------------------------------------------------------------

class CircuitBreakerState:
    """Circuit breaker state tracking."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        # HALF_OPEN state
        return True


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers by service."""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreakerState] = {}
    
    def get_breaker(self, service_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker for service."""
        if service_name not in self.breakers:
            self.breakers[service_name] = CircuitBreakerState()
        return self.breakers[service_name]
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time
            }
            for name, breaker in self.breakers.items()
        }


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()


# ---------------------------------------------------------------------------
# Request Tracking
# ---------------------------------------------------------------------------

class RequestTracker:
    """Track request metrics and performance."""
    
    def __init__(self):
        self.active_requests = 0
        self.total_requests = 0
        self.error_count = 0
        self.response_times = []
        self.metrics_collector = MetricsCollector()
    
    def start_request(self, request: Request) -> Dict[str, Any]:
        """Start tracking a request."""
        self.active_requests += 1
        self.total_requests += 1
        
        request_info = {
            "start_time": time.time(),
            "method": request.method,
            "path": request.url.path,
            "correlation_id": get_correlation_id()
        }
        
        # Record active requests metric
        self.metrics_collector.record_metric(MetricEvent(
            name="active_requests",
            value=self.active_requests,
            labels={"service": "simply"}
        ))
        
        return request_info
    
    def end_request(self, request_info: Dict[str, Any], status_code: int, error: Optional[Exception] = None):
        """End tracking a request."""
        self.active_requests -= 1
        duration = time.time() - request_info["start_time"]
        
        if error or status_code >= 400:
            self.error_count += 1
        
        # Record metrics
        self.metrics_collector.record_metric(MetricEvent(
            name="request_duration",
            value=duration,
            labels={
                "method": request_info["method"],
                "endpoint": request_info["path"],
                "status": str(status_code)
            }
        ))
        
        self.metrics_collector.record_metric(MetricEvent(
            name="request_count",
            value=1,
            labels={
                "method": request_info["method"],
                "endpoint": request_info["path"],
                "status": str(status_code)
            }
        ))
        
        # Track response times
        self.response_times.append(duration)
        if len(self.response_times) > 1000:  # Keep only last 1000
            self.response_times = self.response_times[-1000:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current request statistics."""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.total_requests if self.total_requests > 0 else 0,
            "avg_response_time": avg_response_time,
            "recent_response_times": self.response_times[-10:]  # Last 10 for debugging
        }


# Global request tracker
request_tracker = RequestTracker()


# ---------------------------------------------------------------------------
# Middleware Functions
# ---------------------------------------------------------------------------

async def observability_middleware(request: Request, call_next):
    """Main observability middleware."""
    
    # Generate correlation ID if not present
    correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
    set_correlation_id(correlation_id)
    
    # Set request context
    set_request_context(
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        user_id=request.headers.get("X-User-ID"),
        ip_address=request.client.host if request.client else None
    )
    
    # Start request tracking
    request_info = request_tracker.start_request(request)
    
    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        operation="request_start",
        method=request.method,
        path=request.url.path,
        user_agent=request.headers.get("user-agent")
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Add observability headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = correlation_id  # Alternative header name
        
        # End request tracking
        request_tracker.end_request(request_info, response.status_code)
        
        # Log successful request
        duration_ms = (time.time() - request_info["start_time"]) * 1000
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            operation="request_complete",
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response
        
    except Exception as e:
        # End request tracking with error
        request_tracker.end_request(request_info, 500, error=e)
        
        # Log error
        duration_ms = (time.time() - request_info["start_time"]) * 1000
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            error=e,
            operation="request_error",
            duration_ms=duration_ms
        )
        
        # Return structured error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "correlation_id": correlation_id,
                "timestamp": time.time()
            },
            headers={"X-Correlation-ID": correlation_id}
        )
    
    finally:
        # Always clear request context
        clear_request_context()


async def circuit_breaker_middleware(request: Request, call_next):
    """Circuit breaker middleware for service protection."""
    
    # Determine service based on path
    service_name = _get_service_name_from_path(request.url.path)
    breaker = circuit_breaker_registry.get_breaker(service_name)
    
    # Check if service is available
    if not breaker.can_attempt():
        logger.warning(
            f"Circuit breaker OPEN for service: {service_name}",
            operation="circuit_breaker_open",
            service=service_name,
            failure_count=breaker.failure_count
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service temporarily unavailable",
                "service": service_name,
                "retry_after": breaker.timeout
            }
        )
    
    try:
        response = await call_next(request)
        
        # Record success if response is ok
        if response.status_code < 500:
            breaker.record_success()
        else:
            breaker.record_failure()
        
        return response
        
    except Exception as e:
        # Record failure
        breaker.record_failure()
        
        logger.error(
            f"Service failure recorded for: {service_name}",
            error=e,
            operation="circuit_breaker_failure",
            service=service_name
        )
        
        raise


def _get_service_name_from_path(path: str) -> str:
    """Extract service name from request path."""
    if path.startswith("/api/qa"):
        return "qa_service"
    elif path.startswith("/api/youtube"):
        return "youtube_service"
    elif path.startswith("/api/transcripts"):
        return "transcript_service"
    elif path.startswith("/api/auth"):
        return "auth_service"
    else:
        return "general"


# ---------------------------------------------------------------------------
# Health Check Endpoints
# ---------------------------------------------------------------------------

def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "request_stats": request_tracker.get_stats(),
        "circuit_breakers": circuit_breaker_registry.get_status(),
        "correlation_id": get_correlation_id()
    }


def get_metrics() -> Dict[str, Any]:
    """Get metrics in JSON format."""
    return {
        "request_stats": request_tracker.get_stats(),
        "circuit_breakers": circuit_breaker_registry.get_status(),
        "recent_metrics": request_tracker.metrics_collector.get_recent_metrics()
    }


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics."""
    return request_tracker.metrics_collector.get_prometheus_metrics() 