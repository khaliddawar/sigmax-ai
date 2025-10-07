"""Storage Interface Abstraction Layer

This module provides abstract interfaces for storage operations, decoupling
business logic from specific storage implementations (Supabase, Pinecone, 
local files, etc.).

Key benefits:
- Easy switching between storage backends
- Simplified testing with mock implementations  
- Clear separation of concerns
- Consistent error handling
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class TranscriptMetadata:
    """Standardized transcript metadata."""
    transcript_id: str
    title: str
    date: datetime
    word_count: int = 0
    duration_seconds: int = 0
    source: str = "unknown"
    meeting_id: Optional[str] = None
    extra: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript_id": self.transcript_id,
            "title": self.title,
            "date": self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            "word_count": self.word_count,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            "meeting_id": self.meeting_id,
            **(self.extra or {})
        }


@dataclass
class ChunkData:
    """Standardized chunk data."""
    chunk_id: str
    transcript_id: str
    text: str
    chunk_index: int
    position: int = 0
    is_first: bool = False
    is_last: bool = False
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "transcript_id": self.transcript_id,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "position": self.position,
            "is_first": self.is_first,
            "is_last": self.is_last,
            "embedding": self.embedding,
            "metadata": self.metadata or {}
        }


@dataclass
class SearchResult:
    """Standardized search result."""
    chunk_id: str
    transcript_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = None


# ---------------------------------------------------------------------------
# Abstract Interfaces
# ---------------------------------------------------------------------------

class TranscriptStorage(ABC):
    """Abstract interface for transcript storage operations."""

    @abstractmethod
    async def store_transcript(
        self, 
        metadata: TranscriptMetadata, 
        chunks: List[ChunkData]
    ) -> Dict[str, Any]:
        """Store transcript metadata and chunks."""
        pass

    @abstractmethod
    async def get_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Retrieve transcript by ID."""
        pass

    @abstractmethod
    async def list_transcripts(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """List available transcripts."""
        pass

    @abstractmethod
    async def delete_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Delete transcript and associated data."""
        pass

    @abstractmethod
    async def update_transcript(
        self, 
        transcript_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update transcript metadata."""
        pass


class VectorStorage(ABC):
    """Abstract interface for vector storage and search operations."""

    @abstractmethod
    async def store_embeddings(
        self, 
        chunk_data: List[ChunkData]
    ) -> Dict[str, Any]:
        """Store chunk embeddings for vector search."""
        pass

    @abstractmethod
    async def vector_search(
        self, 
        query_embedding: List[float],
        transcript_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[SearchResult]:
        """Perform vector similarity search."""
        pass

    @abstractmethod
    async def delete_embeddings(self, transcript_id: str) -> Dict[str, Any]:
        """Delete embeddings for a transcript."""
        pass


class KeywordStorage(ABC):
    """Abstract interface for keyword/text search operations."""

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        transcript_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Perform keyword/text search."""
        pass

    @abstractmethod
    async def index_text(self, chunk_data: List[ChunkData]) -> Dict[str, Any]:
        """Index text content for keyword search."""
        pass


# ---------------------------------------------------------------------------
# Unified Storage Interface
# ---------------------------------------------------------------------------

@runtime_checkable
class StorageProvider(Protocol):
    """Protocol for unified storage providers."""
    
    transcript_storage: TranscriptStorage
    vector_storage: VectorStorage
    keyword_storage: KeywordStorage

    async def health_check(self) -> Dict[str, Any]:
        """Check storage provider health."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...


# ---------------------------------------------------------------------------
# Storage Factory
# ---------------------------------------------------------------------------

class StorageFactory:
    """Factory for creating storage provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a storage provider implementation."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> StorageProvider:
        """Create a storage provider instance."""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown storage provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available storage providers."""
        return list(cls._providers.keys())


# ---------------------------------------------------------------------------
# Async Context Manager for Storage
# ---------------------------------------------------------------------------

class StorageManager:
    """Async context manager for storage operations."""
    
    def __init__(self, provider: StorageProvider):
        self.provider = provider
    
    async def __aenter__(self) -> StorageProvider:
        # Perform any initialization if needed
        return self.provider
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.provider.close() 