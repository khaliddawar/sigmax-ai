"""Structured Logging and Observability System

This module provides structured logging with correlation IDs, metrics collection,
and observability features for production environments.

Key features:
- Correlation ID tracking across requests
- Structured JSON logging
- Performance metrics collection
- Circuit breaker monitoring
- Prometheus metrics export
- Request tracing
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, List
from functools import wraps
import asyncio

# Prometheus metrics (optional dependency)
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Context variables for correlation tracking
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    correlation_id: Optional[str] = None
    service: str = "simply"
    component: Optional[str] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    user_id: Optional[str] = None
    transcript_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON logging."""
        result = asdict(self)
        # Remove None values for cleaner logs
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class MetricEvent:
    """Metric event for collection."""
    name: str
    value: float
    labels: Dict[str, str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.labels is None:
            self.labels = {}


# ---------------------------------------------------------------------------
# Structured Logger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Structured logger with correlation ID support."""
    
    def __init__(self, name: str, component: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.component = component
        
        # Configure JSON formatter if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = JsonFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(
        self,
        level: str,
        message: str,
        operation: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        **kwargs
    ) -> LogEntry:
        """Create a structured log entry."""
        
        # Get correlation ID from context
        correlation_id = correlation_id_context.get()
        
        # Get request context
        req_context = request_context.get({})
        
        return LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            message=message,
            correlation_id=correlation_id,
            component=self.component,
            operation=operation,
            duration_ms=duration_ms,
            user_id=req_context.get("user_id"),
            transcript_id=req_context.get("transcript_id"),
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            metadata=kwargs if kwargs else None
        )
    
    def info(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log info message."""
        entry = self._create_log_entry("INFO", message, operation, **kwargs)
        self.logger.info(json.dumps(entry.to_dict()))
    
    def warning(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log warning message."""
        entry = self._create_log_entry("WARNING", message, operation, **kwargs)
        self.logger.warning(json.dumps(entry.to_dict()))
    
    def error(self, message: str, error: Optional[Exception] = None, operation: Optional[str] = None, **kwargs):
        """Log error message."""
        entry = self._create_log_entry("ERROR", message, operation, error=error, **kwargs)
        self.logger.error(json.dumps(entry.to_dict()))
    
    def debug(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log debug message."""
        entry = self._create_log_entry("DEBUG", message, operation, **kwargs)
        self.logger.debug(json.dumps(entry.to_dict()))


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        # If the message is already JSON, return as-is
        if hasattr(record, 'getMessage') and record.getMessage().startswith('{'):
            return record.getMessage()
        
        # Otherwise, create basic JSON structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": correlation_id_context.get()
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# ---------------------------------------------------------------------------
# Metrics Collection
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Metrics collector with Prometheus support."""
    
    def __init__(self):
        self.metrics_buffer: List[MetricEvent] = []
        self.prometheus_registry = None
        self.prometheus_metrics = {}
        
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus()
    
    def _setup_prometheus(self):
        """Setup Prometheus metrics."""
        self.prometheus_registry = CollectorRegistry()
        
        # Request metrics
        self.prometheus_metrics['request_duration'] = Histogram(
            'simply_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint', 'status'],
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['request_count'] = Counter(
            'simply_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.prometheus_registry
        )
        
        # Service metrics
        self.prometheus_metrics['qa_questions'] = Counter(
            'simply_qa_questions_total',
            'Total QA questions processed',
            ['transcript_id', 'status'],
            registry=self.prometheus_registry
        )
        
        self.prometheus_metrics['embedding_operations'] = Counter(
            'simply_embedding_operations_total',
            'Total embedding operations',
            ['provider', 'status'],
            registry=self.prometheus_registry
        )
        
        # Error metrics
        self.prometheus_metrics['errors'] = Counter(
            'simply_errors_total',
            'Total errors by component',
            ['component', 'error_type'],
            registry=self.prometheus_registry
        )
        
        # Active connections
        self.prometheus_metrics['active_connections'] = Gauge(
            'simply_active_connections',
            'Number of active connections',
            ['service'],
            registry=self.prometheus_registry
        )
    
    def record_metric(self, event: MetricEvent):
        """Record a metric event."""
        self.metrics_buffer.append(event)
        
        # Also update Prometheus if available
        if PROMETHEUS_AVAILABLE and self.prometheus_registry:
            self._update_prometheus_metric(event)
    
    def _update_prometheus_metric(self, event: MetricEvent):
        """Update Prometheus metric."""
        metric_name = event.name
        
        if metric_name in self.prometheus_metrics:
            metric = self.prometheus_metrics[metric_name]
            
            if hasattr(metric, 'labels'):
                # Counter or Histogram with labels
                if event.labels:
                    labeled_metric = metric.labels(**event.labels)
                    if hasattr(labeled_metric, 'observe'):
                        labeled_metric.observe(event.value)
                    else:
                        labeled_metric.inc(event.value)
            elif hasattr(metric, 'set'):
                # Gauge
                metric.set(event.value)
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        if not PROMETHEUS_AVAILABLE or not self.prometheus_registry:
            return "# Prometheus not available\n"
        
        return generate_latest(self.prometheus_registry).decode('utf-8')
    
    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics as JSON."""
        recent = self.metrics_buffer[-limit:] if len(self.metrics_buffer) > limit else self.metrics_buffer
        return [asdict(metric) for metric in recent]


# ---------------------------------------------------------------------------
# Context Management
# ---------------------------------------------------------------------------

def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_context.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_request_context(**kwargs):
    """Set request context variables."""
    current_context = request_context.get({})
    current_context.update(kwargs)
    request_context.set(current_context)


def clear_request_context():
    """Clear request context."""
    request_context.set({})


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def trace_operation(operation_name: str, component: Optional[str] = None):
    """Decorator to trace operations with timing and correlation."""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = StructuredLogger(f"{component or 'unknown'}.{operation_name}")
            start_time = time.time()
            
            # Generate correlation ID if not present
            if not get_correlation_id():
                set_correlation_id(generate_correlation_id())
            
            try:
                logger.info(f"Starting {operation_name}", operation=operation_name)
                result = await func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {operation_name}",
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=True
                )
                
                # Record metric
                metrics_collector.record_metric(MetricEvent(
                    name="operation_duration",
                    value=duration_ms / 1000,  # Convert to seconds
                    labels={"operation": operation_name, "component": component or "unknown", "status": "success"}
                ))
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {operation_name}",
                    error=e,
                    operation=operation_name,
                    duration_ms=duration_ms
                )
                
                # Record error metric
                metrics_collector.record_metric(MetricEvent(
                    name="operation_duration",
                    value=duration_ms / 1000,
                    labels={"operation": operation_name, "component": component or "unknown", "status": "error"}
                ))
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = StructuredLogger(f"{component or 'unknown'}.{operation_name}")
            start_time = time.time()
            
            # Generate correlation ID if not present
            if not get_correlation_id():
                set_correlation_id(generate_correlation_id())
            
            try:
                logger.info(f"Starting {operation_name}", operation=operation_name)
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {operation_name}",
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {operation_name}",
                    error=e,
                    operation=operation_name,
                    duration_ms=duration_ms
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# ---------------------------------------------------------------------------
# Global Instances
# ---------------------------------------------------------------------------

metrics_collector = MetricsCollector()


# ---------------------------------------------------------------------------
# FastAPI Integration
# ---------------------------------------------------------------------------

async def add_correlation_id_middleware(request, call_next):
    """FastAPI middleware to add correlation IDs to requests."""
    
    # Get or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
    set_correlation_id(correlation_id)
    
    # Set request context
    set_request_context(
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        user_id=request.headers.get("X-User-ID")  # If available
    )
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        # Record request metric
        duration = time.time() - start_time
        metrics_collector.record_metric(MetricEvent(
            name="request_duration",
            value=duration,
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status": str(response.status_code)
            }
        ))
        
        return response
        
    finally:
        clear_request_context()


def get_logger(name: str, component: Optional[str] = None) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name, component)


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return metrics_collector 