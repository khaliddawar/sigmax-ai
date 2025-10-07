"""Service Interfaces for Dependency Injection

This module defines abstract interfaces for all major services to enable
proper dependency injection with interface types instead of concrete classes.

Key benefits:
- Loose coupling between services
- Easy testing with mock implementations
- Clear service contracts
- Better maintainability
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    success: bool
    embeddings: List[List[float]]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Result from search operations."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class QAResult:
    """Result from QA operations."""
    answer: str
    confidence: float
    sources: List[SearchResult]
    metadata: Dict[str, Any]


@dataclass
class SummaryResult:
    """Result from summarization operations."""
    summary: str
    key_points: List[str]
    metadata: Dict[str, Any]


@dataclass
class ValidationResult:
    """Result from validation operations."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]


# =============================================================================
# Storage Interfaces
# =============================================================================

@runtime_checkable
class VectorStore(Protocol):
    """Interface for vector storage operations."""
    
    async def store_embeddings(
        self,
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """Store embeddings with metadata."""
        ...
    
    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform similarity search."""
        ...
    
    async def delete_by_id(self, ids: List[str]) -> bool:
        """Delete embeddings by IDs."""
        ...


@runtime_checkable
class TextStore(Protocol):
    """Interface for text storage operations."""
    
    async def store_text(
        self,
        id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store text content with metadata."""
        ...
    
    async def get_text(self, id: str) -> Optional[Dict[str, Any]]:
        """Get text content by ID."""
        ...
    
    async def search_text(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search text content."""
        ...


# =============================================================================
# AI Service Interfaces
# =============================================================================

@runtime_checkable
class EmbeddingService(Protocol):
    """Interface for embedding generation services."""
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """Generate embeddings for texts."""
        ...
    
    async def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """Get embedding dimension for model."""
        ...


@runtime_checkable
class LLMService(Protocol):
    """Interface for language model services."""
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate text response."""
        ...
    
    async def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured response matching schema."""
        ...


# =============================================================================
# Business Logic Interfaces
# =============================================================================

@runtime_checkable
class QAService(Protocol):
    """Interface for question answering services."""
    
    async def answer_question(
        self,
        question: str,
        context: Optional[str] = None,
        transcript_id: Optional[str] = None
    ) -> QAResult:
        """Answer a question based on available context."""
        ...
    
    async def batch_answer(
        self,
        questions: List[str],
        context: Optional[str] = None
    ) -> List[QAResult]:
        """Answer multiple questions."""
        ...


@runtime_checkable
class SummaryService(Protocol):
    """Interface for summarization services."""
    
    async def generate_summary(
        self,
        content: str,
        summary_type: str = "general"
    ) -> SummaryResult:
        """Generate summary of content."""
        ...
    
    async def extract_key_points(
        self,
        content: str,
        max_points: int = 10
    ) -> List[str]:
        """Extract key points from content."""
        ...


@runtime_checkable
class ValidationService(Protocol):
    """Interface for validation services."""
    
    async def validate_response(
        self,
        response: str,
        context: str,
        question: str
    ) -> ValidationResult:
        """Validate response against context and question."""
        ...
    
    async def validate_content(
        self,
        content: str,
        content_type: str = "general"
    ) -> ValidationResult:
        """Validate content quality."""
        ...


@runtime_checkable
class RetrievalService(Protocol):
    """Interface for retrieval services."""
    
    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 10,
        transcript_id: Optional[str] = None
    ) -> List[SearchResult]:
        """Retrieve relevant content chunks."""
        ...
    
    async def hybrid_search(
        self,
        query: str,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """Perform hybrid vector + keyword search."""
        ...


# =============================================================================
# Communication Interfaces
# =============================================================================

@runtime_checkable
class EmailGateway(Protocol):
    """Interface for email services."""
    
    async def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        content_type: str = "text/plain"
    ) -> bool:
        """Send email."""
        ...
    
    async def send_template_email(
        self,
        to: str,
        template_id: str,
        variables: Dict[str, Any]
    ) -> bool:
        """Send templated email."""
        ...


@runtime_checkable
class NotificationService(Protocol):
    """Interface for notification services."""
    
    async def send_notification(
        self,
        user_id: str,
        message: str,
        notification_type: str = "info"
    ) -> bool:
        """Send notification to user."""
        ...
    
    async def broadcast_notification(
        self,
        message: str,
        user_ids: Optional[List[str]] = None
    ) -> bool:
        """Broadcast notification to multiple users."""
        ...


# =============================================================================
# Infrastructure Interfaces
# =============================================================================

@runtime_checkable
class CacheService(Protocol):
    """Interface for caching services."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...


@runtime_checkable
class QueueService(Protocol):
    """Interface for queue services."""
    
    async def enqueue(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delay: Optional[int] = None
    ) -> str:
        """Enqueue message."""
        ...
    
    async def dequeue(
        self,
        queue_name: str,
        timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Dequeue message."""
        ...


@runtime_checkable
class FileStorage(Protocol):
    """Interface for file storage services."""
    
    async def store_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store file and return file ID."""
        ...
    
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get file content by ID."""
        ...
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by ID."""
        ...


# =============================================================================
# Configuration Interface
# =============================================================================

@runtime_checkable
class ConfigurationService(Protocol):
    """Interface for configuration services."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section."""
        ...
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if feature is enabled."""
        ...


# =============================================================================
# Service Factory Interface
# =============================================================================

@runtime_checkable
class ServiceFactory(Protocol):
    """Interface for service factory."""
    
    async def create_embedding_service(self) -> EmbeddingService:
        """Create embedding service."""
        ...
    
    async def create_llm_service(self) -> LLMService:
        """Create LLM service."""
        ...
    
    async def create_qa_service(self) -> QAService:
        """Create QA service."""
        ...
    
    async def create_summary_service(self) -> SummaryService:
        """Create summary service."""
        ...
    
    async def create_vector_store(self) -> VectorStore:
        """Create vector store."""
        ...
    
    async def create_text_store(self) -> TextStore:
        """Create text store."""
        ...


# =============================================================================
# Service Registry Interface
# =============================================================================

class ServiceRegistry(ABC):
    """Abstract service registry for dependency injection."""
    
    @abstractmethod
    async def register(
        self,
        interface: type,
        implementation: type,
        singleton: bool = True
    ) -> None:
        """Register service implementation."""
        pass
    
    @abstractmethod
    async def get(self, interface: type) -> Any:
        """Get service instance by interface."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close registry and cleanup services."""
        pass


# =============================================================================
# Utility Functions
# =============================================================================

def is_service_interface(obj: Any) -> bool:
    """Check if object implements a service interface."""
    service_interfaces = [
        VectorStore, TextStore, EmbeddingService, LLMService,
        QAService, SummaryService, ValidationService, RetrievalService,
        EmailGateway, NotificationService, CacheService, QueueService,
        FileStorage, ConfigurationService
    ]
    
    return any(isinstance(obj, interface) for interface in service_interfaces)


def get_interface_name(interface: type) -> str:
    """Get human-readable name for interface."""
    return getattr(interface, '__name__', str(interface)) 