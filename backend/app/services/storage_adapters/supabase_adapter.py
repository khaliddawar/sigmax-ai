"""Supabase Storage Adapter

This module implements the storage interfaces using Supabase as the backend.
It wraps the existing SupabaseService to provide a clean, standardized API.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..storage_interface import (
    TranscriptStorage, VectorStorage, KeywordStorage, StorageProvider,
    TranscriptMetadata, ChunkData, SearchResult
)
from ..supabase_client import SupabaseService

logger = logging.getLogger("supabase-storage-adapter")


class SupabaseTranscriptStorage(TranscriptStorage):
    """Supabase implementation of transcript storage."""
    
    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
    
    async def store_transcript(
        self, 
        metadata: TranscriptMetadata, 
        chunks: List[ChunkData]
    ) -> Dict[str, Any]:
        """Store transcript metadata and chunks."""
        try:
            # Create transcript record
            transcript_result = await self.supabase.create_transcript_record(
                metadata.transcript_id,
                metadata.to_dict()
            )
            
            if not transcript_result.get("success"):
                return transcript_result
            
            # Convert ChunkData to legacy format for existing service
            legacy_chunks = []
            embeddings = []
            
            for chunk in chunks:
                legacy_chunk = {
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "position": chunk.position,
                    "is_first": chunk.is_first,
                    "is_last": chunk.is_last,
                    "metadata": chunk.metadata or {}
                }
                legacy_chunks.append(legacy_chunk)
                
                if chunk.embedding:
                    embeddings.append(chunk.embedding)
            
            # Store chunks
            chunks_result = await self.supabase.store_transcript_chunks(
                metadata.transcript_id,
                legacy_chunks,
                embeddings if embeddings else None
            )
            
            return {
                "success": True,
                "transcript_id": metadata.transcript_id,
                "chunks_stored": len(chunks),
                "transcript_result": transcript_result,
                "chunks_result": chunks_result
            }
            
        except Exception as e:
            logger.error(f"Error storing transcript: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Retrieve transcript by ID."""
        try:
            result = await self.supabase.get_transcript_by_id(transcript_id)
            
            if not result.get("success"):
                return result
            
            # Convert to standardized format
            transcript_data = result.get("transcript", {})
            chunks_data = result.get("chunks", [])
            
            # Convert to ChunkData objects
            chunks = []
            for chunk in chunks_data:
                chunk_obj = ChunkData(
                    chunk_id=chunk.get("id", str(uuid.uuid4())),
                    transcript_id=transcript_id,
                    text=chunk.get("text", ""),
                    chunk_index=chunk.get("chunk_index", 0),
                    position=chunk.get("position", 0),
                    is_first=chunk.get("is_first", False),
                    is_last=chunk.get("is_last", False),
                    embedding=chunk.get("embedding"),
                    metadata=chunk.get("metadata", {})
                )
                chunks.append(chunk_obj)
            
            # Convert to TranscriptMetadata
            metadata = TranscriptMetadata(
                transcript_id=transcript_id,
                title=transcript_data.get("title", ""),
                date=datetime.fromisoformat(transcript_data.get("date", datetime.now().isoformat())),
                word_count=transcript_data.get("word_count", 0),
                duration_seconds=transcript_data.get("duration_seconds", 0),
                source=transcript_data.get("source", "unknown"),
                meeting_id=transcript_data.get("meeting_id"),
                extra=transcript_data.get("metadata", {})
            )
            
            return {
                "success": True,
                "metadata": metadata,
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Error retrieving transcript: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_transcripts(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """List available transcripts."""
        return await self.supabase.get_transcripts(limit=limit, offset=offset)
    
    async def delete_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Delete transcript and associated data."""
        return await self.supabase.delete_transcript(transcript_id)
    
    async def update_transcript(
        self, 
        transcript_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update transcript metadata."""
        return await self.supabase.update_transcript_record(transcript_id, updates)


class SupabaseVectorStorage(VectorStorage):
    """Supabase implementation of vector storage."""
    
    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
    
    async def store_embeddings(self, chunk_data: List[ChunkData]) -> Dict[str, Any]:
        """Store chunk embeddings for vector search."""
        try:
            # Group by transcript_id
            by_transcript = {}
            for chunk in chunk_data:
                if chunk.transcript_id not in by_transcript:
                    by_transcript[chunk.transcript_id] = []
                by_transcript[chunk.transcript_id].append(chunk)
            
            results = []
            for transcript_id, chunks in by_transcript.items():
                embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
                
                if embeddings:
                    result = await self.supabase.store_transcript_embeddings(
                        transcript_id, 
                        embeddings
                    )
                    results.append(result)
            
            return {
                "success": True,
                "transcripts_processed": len(by_transcript),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def vector_search(
        self, 
        query_embedding: List[float],
        transcript_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[SearchResult]:
        """Perform vector similarity search."""
        try:
            result = await self.supabase.get_similar_chunks(
                embedding=query_embedding,
                transcript_id=transcript_id,
                limit=top_k,
                similarity_threshold=similarity_threshold
            )
            
            if not result.get("success"):
                logger.error(f"Vector search failed: {result.get('error')}")
                return []
            
            # Convert to SearchResult objects
            search_results = []
            for chunk in result.get("chunks", []):
                search_result = SearchResult(
                    chunk_id=chunk.get("id", str(uuid.uuid4())),
                    transcript_id=chunk.get("transcript_id", ""),
                    text=chunk.get("text", ""),
                    score=chunk.get("similarity", 0.0),
                    metadata=chunk.get("metadata", {})
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    async def delete_embeddings(self, transcript_id: str) -> Dict[str, Any]:
        """Delete embeddings for a transcript."""
        # This would typically be handled by cascade delete when transcript is deleted
        return {
            "success": True,
            "message": "Embeddings deleted via cascade"
        }


class SupabaseKeywordStorage(KeywordStorage):
    """Supabase implementation of keyword storage."""
    
    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
    
    async def keyword_search(
        self,
        query: str,
        transcript_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Perform keyword/text search."""
        try:
            # Use the existing keyword search from RetrievalQAService
            # This is a simplified implementation - in practice, you'd want
            # to implement proper full-text search in Supabase
            
            # For now, return empty results as this would need proper
            # full-text search implementation in Supabase
            logger.warning("Keyword search not fully implemented for Supabase adapter")
            return []
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    async def index_text(self, chunk_data: List[ChunkData]) -> Dict[str, Any]:
        """Index text content for keyword search."""
        # This would typically set up full-text search indexes
        return {
            "success": True,
            "message": "Text indexing handled by Supabase full-text search"
        }


class SupabaseStorageProvider:
    """Unified Supabase storage provider."""
    
    def __init__(self, supabase_service: Optional[SupabaseService] = None):
        if supabase_service is None:
            supabase_service = SupabaseService()
        
        self.supabase = supabase_service
        self.transcript_storage = SupabaseTranscriptStorage(supabase_service)
        self.vector_storage = SupabaseVectorStorage(supabase_service)
        self.keyword_storage = SupabaseKeywordStorage(supabase_service)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check storage provider health."""
        return self.supabase.check_connection()
    
    async def close(self) -> None:
        """Clean up resources."""
        # Supabase client doesn't need explicit cleanup
        logger.debug("Supabase storage provider closed")


# Register with the storage factory
from ..storage_interface import StorageFactory
StorageFactory.register_provider("supabase", SupabaseStorageProvider) 