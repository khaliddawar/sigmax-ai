"""Enhanced Dependency Injection Container

This module provides an interface-based dependency injection system that follows
the expert recommendations for proper service architecture.

Key improvements:
- Interface-based service registration
- Proper lifecycle management
- Easy testing with mock implementations
- Configuration-driven service creation
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Callable, get_type_hints
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from .interfaces import (
    VectorStore, TextStore, EmbeddingService, LLMService,
    QAService, SummaryService, ValidationService, RetrievalService,
    EmailGateway, CacheService, ConfigurationService
)

logger = logging.getLogger("enhanced-dependency-container")

T = TypeVar("T")


@dataclass
class ServiceBinding:
    """Binding between interface and implementation."""
    interface: Type
    implementation: Type
    factory: Optional[Callable[..., Any]] = None
    singleton: bool = True
    async_factory: bool = False
    dependencies: Dict[str, Type] = field(default_factory=dict)
    lifecycle_hooks: Dict[str, str] = field(default_factory=dict)  # init, cleanup method names


class InterfaceBasedContainer:
    """Enhanced dependency injection container using interfaces."""
    
    def __init__(self, config_service: Optional[ConfigurationService] = None):
        self.config_service = config_service
        self._bindings: Dict[Type, ServiceBinding] = {}
        self._instances: Dict[Type, Any] = {}
        self._creating: set[Type] = set()
        self._lock = asyncio.Lock()
    
    def bind(
        self,
        interface: Type[T],
        implementation: Type[T],
        *,
        singleton: bool = True,
        factory: Optional[Callable[..., T]] = None,
        dependencies: Optional[Dict[str, Type]] = None,
        init_method: Optional[str] = None,
        cleanup_method: Optional[str] = None
    ) -> 'InterfaceBasedContainer':
        """
        Bind an interface to an implementation.
        
        Args:
            interface: The interface type
            implementation: The concrete implementation type
            singleton: Whether to create singleton instances
            factory: Optional factory function
            dependencies: Interface dependencies by parameter name
            init_method: Method to call after creation
            cleanup_method: Method to call during cleanup
        """
        lifecycle_hooks = {}
        if init_method:
            lifecycle_hooks['init'] = init_method
        if cleanup_method:
            lifecycle_hooks['cleanup'] = cleanup_method
        
        self._bindings[interface] = ServiceBinding(
            interface=interface,
            implementation=implementation,
            factory=factory,
            singleton=singleton,
            async_factory=asyncio.iscoroutinefunction(factory) if factory else False,
            dependencies=dependencies or {},
            lifecycle_hooks=lifecycle_hooks
        )
        
        logger.debug(f"Bound {interface.__name__} to {implementation.__name__}")
        return self
    
    async def get(self, interface: Type[T]) -> T:
        """Get service instance by interface."""
        async with self._lock:
            return await self._get_instance(interface)
    
    async def _get_instance(self, interface: Type[T]) -> T:
        """Internal method to get or create service instance."""
        if interface not in self._bindings:
            raise ValueError(f"No binding found for interface {interface.__name__}")
        
        binding = self._bindings[interface]
        
        # Return existing singleton if available
        if binding.singleton and interface in self._instances:
            return self._instances[interface]
        
        # Check for circular dependencies
        if interface in self._creating:
            raise ValueError(f"Circular dependency detected for {interface.__name__}")
        
        try:
            self._creating.add(interface)
            
            # Resolve dependencies
            dependency_instances = {}
            for param_name, dep_interface in binding.dependencies.items():
                dependency_instances[param_name] = await self._get_instance(dep_interface)
            
            # Create instance
            if binding.factory:
                if binding.async_factory:
                    instance = await binding.factory(**dependency_instances)
                else:
                    instance = binding.factory(**dependency_instances)
            else:
                # Use constructor injection
                instance = binding.implementation(**dependency_instances)
            
            # Call initialization hook if specified
            if 'init' in binding.lifecycle_hooks:
                init_method = getattr(instance, binding.lifecycle_hooks['init'], None)
                if init_method:
                    if asyncio.iscoroutinefunction(init_method):
                        await init_method()
                    else:
                        init_method()
            
            # Store singleton instance
            if binding.singleton:
                self._instances[interface] = instance
            
            logger.debug(f"Created instance of {interface.__name__}")
            return instance
            
        finally:
            self._creating.discard(interface)
    
    async def close(self) -> None:
        """Clean up all services."""
        logger.info("Cleaning up enhanced dependency container...")
        
        # Call cleanup methods in reverse order of creation
        for interface, instance in reversed(list(self._instances.items())):
            try:
                binding = self._bindings.get(interface)
                if binding and 'cleanup' in binding.lifecycle_hooks:
                    cleanup_method = getattr(instance, binding.lifecycle_hooks['cleanup'], None)
                    if cleanup_method:
                        if asyncio.iscoroutinefunction(cleanup_method):
                            await cleanup_method()
                        else:
                            cleanup_method()
            except Exception as e:
                logger.error(f"Error cleaning up {interface.__name__}: {e}")
        
        self._instances.clear()
        logger.info("Enhanced dependency container cleanup complete")
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for container lifecycle."""
        try:
            yield self
        finally:
            await self.close()
    
    def get_bindings(self) -> Dict[str, str]:
        """Get current bindings for debugging."""
        return {
            interface.__name__: binding.implementation.__name__
            for interface, binding in self._bindings.items()
        }


class ServiceFactory:
    """Factory for creating service instances with proper configuration."""
    
    def __init__(self, container: InterfaceBasedContainer):
        self.container = container
    
    async def create_embedding_service(self, **config) -> EmbeddingService:
        """Create embedding service with configuration."""
        from ..embedding_service import EmbeddingService as ConcreteEmbeddingService
        
        # Apply configuration
        service = ConcreteEmbeddingService()
        
        # Configure based on settings
        if hasattr(service, 'configure'):
            service.configure(**config)
        
        return service
    
    async def create_vector_store(self, **config) -> VectorStore:
        """Create vector store with configuration."""
        from ..storage_adapters.supabase_adapter import SupabaseVectorAdapter
        
        # Get Supabase service from container
        supabase_service = await self.container.get(TextStore)  # Assuming TextStore is bound to Supabase
        
        return SupabaseVectorAdapter(supabase_service)
    
    async def create_qa_service(self, **config) -> QAService:
        """Create QA service with all dependencies."""
        from ..retrieval_qa_service import RetrievalQAService
        
        # Get dependencies from container
        embedding_service = await self.container.get(EmbeddingService)
        vector_store = await self.container.get(VectorStore)
        
        return RetrievalQAService(
            embedding_service=embedding_service,
            storage_service=vector_store
        )


def create_production_container(config_service: ConfigurationService) -> InterfaceBasedContainer:
    """Create a production-ready container with all bindings."""
    container = InterfaceBasedContainer(config_service)
    
    # Configuration service (already provided)
    container.bind(ConfigurationService, type(config_service), factory=lambda: config_service)
    
    # Core services
    container.bind(
        EmbeddingService,
        _get_embedding_implementation(),
        singleton=True,
        cleanup_method="close"
    )
    
    container.bind(
        VectorStore,
        _get_vector_store_implementation(),
        dependencies={"supabase_service": TextStore},
        singleton=True
    )
    
    container.bind(
        TextStore,
        _get_text_store_implementation(),
        singleton=True
    )
    
    # Business logic services
    container.bind(
        QAService,
        _get_qa_service_implementation(),
        dependencies={
            "embedding_service": EmbeddingService,
            "vector_store": VectorStore
        },
        singleton=True,
        cleanup_method="close"
    )
    
    container.bind(
        SummaryService,
        _get_summary_service_implementation(),
        singleton=True
    )
    
    container.bind(
        ValidationService,
        _get_validation_service_implementation(),
        singleton=True
    )
    
    # Communication services
    container.bind(
        EmailGateway,
        _get_email_gateway_implementation(),
        singleton=True
    )
    
    return container


def create_test_container() -> InterfaceBasedContainer:
    """Create a container for testing with mock implementations."""
    from .test_implementations import (
        MockEmbeddingService, MockVectorStore, MockQAService,
        MockEmailGateway, MockConfigurationService
    )
    
    container = InterfaceBasedContainer()
    
    # Mock implementations for testing
    container.bind(ConfigurationService, MockConfigurationService)
    container.bind(EmbeddingService, MockEmbeddingService)
    container.bind(VectorStore, MockVectorStore)
    container.bind(QAService, MockQAService)
    container.bind(EmailGateway, MockEmailGateway)
    
    return container


# =============================================================================
# Implementation Selection Functions
# =============================================================================

def _get_embedding_implementation():
    """Get embedding service implementation based on configuration."""
    from ..embedding_service import EmbeddingService
    return EmbeddingService


def _get_vector_store_implementation():
    """Get vector store implementation based on configuration."""
    from ..storage_adapters.supabase_adapter import SupabaseVectorAdapter
    return SupabaseVectorAdapter


def _get_text_store_implementation():
    """Get text store implementation based on configuration."""
    from ..supabase_client import SupabaseService
    return SupabaseService


def _get_qa_service_implementation():
    """Get QA service implementation based on configuration."""
    from ..retrieval_qa_service import RetrievalQAService
    return RetrievalQAService


def _get_summary_service_implementation():
    """Get summary service implementation based on configuration."""
    from ..summary_service_v2 import SummaryServiceRouter
    return SummaryServiceRouter


def _get_validation_service_implementation():
    """Get validation service implementation based on configuration."""
    from ..retrieval.validation import CompositeValidator
    return CompositeValidator


def _get_email_gateway_implementation():
    """Get email gateway implementation based on configuration."""
    from ..email_service import EmailService
    return EmailService


# =============================================================================
# Global Container Management
# =============================================================================

_global_container: Optional[InterfaceBasedContainer] = None


async def get_global_container() -> InterfaceBasedContainer:
    """Get the global container instance."""
    global _global_container
    
    if _global_container is None:
        # Create configuration service
        from config.config import get_settings
        config_service = get_settings()
        
        # Create production container
        _global_container = create_production_container(config_service)
        logger.info("Initialized global enhanced dependency container")
    
    return _global_container


async def cleanup_global_container() -> None:
    """Clean up the global container."""
    global _global_container
    
    if _global_container is not None:
        await _global_container.close()
        _global_container = None
        logger.info("Cleaned up global enhanced dependency container")


# =============================================================================
# FastAPI Integration
# =============================================================================

async def get_service_by_interface(interface: Type[T]) -> T:
    """FastAPI dependency helper to get services by interface."""
    container = await get_global_container()
    return await container.get(interface)


# Specific dependency functions for FastAPI
async def get_embedding_service() -> EmbeddingService:
    """Get embedding service for FastAPI dependency injection."""
    return await get_service_by_interface(EmbeddingService)


async def get_qa_service() -> QAService:
    """Get QA service for FastAPI dependency injection."""
    return await get_service_by_interface(QAService)


async def get_summary_service() -> SummaryService:
    """Get summary service for FastAPI dependency injection."""
    return await get_service_by_interface(SummaryService)


async def get_email_gateway() -> EmailGateway:
    """Get email gateway for FastAPI dependency injection."""
    return await get_service_by_interface(EmailGateway) 