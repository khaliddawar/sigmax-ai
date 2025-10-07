"""Dependency Injection Container

This module provides a proper dependency injection system to replace
global singletons and manage service lifecycles correctly.

Key benefits:
- Explicit dependency management
- Proper async lifecycle handling
- Easy testing with mock services
- No import-time initialization
- Thread-safe service creation
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Callable, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import weakref

logger = logging.getLogger("dependency-container")

T = TypeVar("T")


@dataclass
class ServiceDefinition:
    """Definition of how to create a service."""
    factory: Callable[..., Any]
    singleton: bool = True
    async_factory: bool = False
    dependencies: list[str] = field(default_factory=list)
    cleanup_method: Optional[str] = None  # Method name to call on cleanup


class DependencyContainer:
    """Async-aware dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._creating: set[str] = set()  # Track services being created to detect cycles
        self._cleanup_callbacks: list[Callable[[], Awaitable[None]]] = []
        self._lock = asyncio.Lock()
    
    def register(
        self,
        name: str,
        factory: Callable[..., Any],
        *,
        singleton: bool = True,
        async_factory: bool = False,
        dependencies: Optional[list[str]] = None,
        cleanup_method: Optional[str] = None
    ) -> None:
        """Register a service with the container."""
        self._services[name] = ServiceDefinition(
            factory=factory,
            singleton=singleton,
            async_factory=async_factory,
            dependencies=dependencies or [],
            cleanup_method=cleanup_method
        )
        logger.debug(f"Registered service: {name}")
    
    async def get(self, name: str) -> Any:
        """Get a service instance."""
        async with self._lock:
            return await self._get_instance(name)
    
    async def _get_instance(self, name: str) -> Any:
        """Internal method to get or create service instance."""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        
        service_def = self._services[name]
        
        # Return existing singleton if available
        if service_def.singleton and name in self._instances:
            return self._instances[name]
        
        # Check for circular dependencies
        if name in self._creating:
            raise ValueError(f"Circular dependency detected for service '{name}'")
        
        try:
            self._creating.add(name)
            
            # Resolve dependencies
            dep_instances = {}
            for dep_name in service_def.dependencies:
                dep_instances[dep_name] = await self._get_instance(dep_name)
            
            # Create instance
            if service_def.async_factory:
                instance = await service_def.factory(**dep_instances)
            else:
                instance = service_def.factory(**dep_instances)
            
            # Store singleton instance
            if service_def.singleton:
                self._instances[name] = instance
                
                # Register cleanup if needed
                if service_def.cleanup_method:
                    cleanup_func = getattr(instance, service_def.cleanup_method, None)
                    if cleanup_func:
                        self._cleanup_callbacks.append(cleanup_func)
            
            logger.debug(f"Created service instance: {name}")
            return instance
            
        finally:
            self._creating.discard(name)
    
    async def close(self) -> None:
        """Clean up all services."""
        logger.info("Cleaning up dependency container...")
        
        # Call cleanup callbacks in reverse order
        for cleanup_func in reversed(self._cleanup_callbacks):
            try:
                await cleanup_func()
            except Exception as e:
                logger.error(f"Error during service cleanup: {e}")
        
        self._cleanup_callbacks.clear()
        self._instances.clear()
        logger.info("Dependency container cleanup complete")
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for container lifecycle."""
        try:
            yield self
        finally:
            await self.close()


# ---------------------------------------------------------------------------
# Pre-configured Container Factory
# ---------------------------------------------------------------------------

def create_application_container() -> DependencyContainer:
    """Create a pre-configured container with all application services."""
    from .embedding_service import EmbeddingService
    from .supabase_client import SupabaseService
    from .file_storage import FileStorageService
    from .semantic_chunker import SemanticChunker
    from .retrieval_qa_service import RetrievalQAService
    from .summary_service_v2 import SummaryServiceRouter
    from .email_service import EmailService
    
    container = DependencyContainer()
    
    # Core services
    container.register(
        "embedding_service",
        EmbeddingService,
        async_factory=False,
        cleanup_method="close"
    )
    
    container.register(
        "supabase_service", 
        SupabaseService,
        async_factory=False
    )
    
    container.register(
        "file_storage_service",
        FileStorageService,
        async_factory=False
    )
    
    container.register(
        "semantic_chunker",
        lambda: SemanticChunker(domain_type="generic"),
        async_factory=False
    )
    
    # Composite services with dependencies
    container.register(
        "qa_service",
        lambda embedding_service, supabase_service, file_storage_service: RetrievalQAService(
            embedding_service=embedding_service,
            storage_service=supabase_service,
            file_storage_service=file_storage_service
        ),
        dependencies=["embedding_service", "supabase_service", "file_storage_service"],
        cleanup_method="close"
    )
    
    container.register(
        "summary_service",
        SummaryServiceRouter,
        async_factory=False
    )
    
    container.register(
        "email_service",
        EmailService,
        async_factory=False
    )
    
    return container


# ---------------------------------------------------------------------------
# Global Container Instance (Managed Properly)
# ---------------------------------------------------------------------------

_application_container: Optional[DependencyContainer] = None


async def get_application_container() -> DependencyContainer:
    """Get the global application container (lazy initialization)."""
    global _application_container
    
    if _application_container is None:
        _application_container = create_application_container()
        logger.info("Initialized application dependency container")
    
    return _application_container


async def cleanup_application_container() -> None:
    """Clean up the global application container."""
    global _application_container
    
    if _application_container is not None:
        await _application_container.close()
        _application_container = None
        logger.info("Cleaned up application dependency container")


# ---------------------------------------------------------------------------
# FastAPI Integration Helpers
# ---------------------------------------------------------------------------

async def get_service(service_name: str) -> Any:
    """FastAPI dependency helper to get services."""
    container = await get_application_container()
    return await container.get(service_name)


# Specific service getters for FastAPI dependencies
async def get_embedding_service():
    """Get embedding service for FastAPI dependency injection."""
    return await get_service("embedding_service")


async def get_supabase_service():
    """Get Supabase service for FastAPI dependency injection."""
    return await get_service("supabase_service")


async def get_qa_service():
    """Get QA service for FastAPI dependency injection."""
    return await get_service("qa_service")


async def get_summary_service():
    """Get summary service for FastAPI dependency injection."""
    return await get_service("summary_service")


async def get_email_service():
    """Get email service for FastAPI dependency injection."""
    return await get_service("email_service") 