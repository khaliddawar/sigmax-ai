"""
Semantic Chunks Service

This module provides database interaction services for semantic chunks with rich metadata.
It handles storing and retrieving semantic chunks from the new domain-agnostic schema.

Key features:
- Store semantic chunks with entities, sentiment, language metadata
- Retrieve chunks with vector similarity search
- Filter by entity types and sentiment
- Support for batch operations
- Domain-agnostic design
"""

import json
import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .semantic_chunker import ChunkMetadata
from .embedding_service import EmbeddingService

# Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class SemanticChunksService:
    """
    Service for managing semantic chunks in the database.
    
    This class provides methods for storing and retrieving semantic chunks
    with rich metadata including entities, sentiment, and language information.
    """
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """
        Initialize the semantic chunks service.
        
        Args:
            supabase_url: Supabase URL (optional, uses environment if not provided)
            supabase_key: Supabase service role key (optional, uses environment if not provided)
        """
        self.client: Optional[Client] = None
        self.initialized = False
        
        # Get credentials from environment if not provided
        import os
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        # Check for both service role key and regular key as fallback
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase client not available")
            return
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client"""
        try:
            if not self.supabase_url or not self.supabase_key:
                logger.warning("Supabase credentials not found in environment")
                return
            
            self.client = create_client(self.supabase_url, self.supabase_key)
            self.initialized = True
            logger.info("Semantic chunks service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.initialized = False
    
    async def store_transcript_metadata(self, transcript_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store transcript metadata in the transcripts table.
        
        Args:
            transcript_id: Unique transcript identifier
            metadata: Transcript metadata dictionary
            
        Returns:
            Result dictionary with success status
        """
        try:
            if not self.initialized:
                return {"success": False, "error": "Service not initialized"}
            
            # Format transcript data
            transcript_data = {
                "transcript_id": transcript_id,
                "title": metadata.get("title", f"Transcript {transcript_id}"),
                "meeting_id": metadata.get("meeting_id", ""),
                "date": metadata.get("date", datetime.now().isoformat()),
                "word_count": metadata.get("word_count", 0),
                "duration_seconds": metadata.get("duration_seconds", 0),
                "source": metadata.get("source", "unknown")
            }
            
            # Store transcript metadata (upsert to handle duplicates)
            result = self.client.table("transcripts").upsert(
                transcript_data, 
                on_conflict="transcript_id"
            ).execute()
            
            if hasattr(result, 'error') and result.error is not None:
                logger.error(f"Error storing transcript metadata: {result.error}")
                return {"success": False, "error": str(result.error)}
            
            logger.info(f"Stored transcript metadata for {transcript_id}")
            return {"success": True, "transcript_id": transcript_id}
            
        except Exception as e:
            logger.error(f"Error storing transcript metadata: {e}")
            return {"success": False, "error": str(e)}
    
    async def store_semantic_chunks(self, chunks: List[ChunkMetadata], 
                                   embeddings: List[List[float]],
                                   transcript_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Store semantic chunks with their embeddings in the database.
        
        Args:
            chunks: List of semantic chunk metadata
            embeddings: List of embedding vectors
            transcript_id: Optional transcript ID (if not provided, attempts to extract from chunk source)
            
        Returns:
            Result dictionary with success status and statistics
        """
        try:
            start_time = time.time()
            
            if not self.initialized:
                return {"success": False, "error": "Service not initialized"}
            
            if len(chunks) != len(embeddings):
                return {
                    "success": False, 
                    "error": f"Chunk count ({len(chunks)}) doesn't match embedding count ({len(embeddings)})"
                }
            
            # Determine transcript_id
            if not transcript_id and chunks:
                # Try to extract from first chunk's source information
                # The semantic chunker stores the source_id in a way we can extract
                first_chunk_id = chunks[0].id
                if '_' in first_chunk_id:
                    # Extract source from chunk ID pattern (chunk IDs often include source)
                    parts = first_chunk_id.split('_')
                    if len(parts) > 1:
                        transcript_id = '_'.join(parts[:-1])  # Everything except last part (chunk number)
                
                # If still no transcript_id, this is an error condition
                if not transcript_id:
                    return {
                        "success": False,
                        "error": "transcript_id is required and could not be determined from chunk data"
                    }
            
            if not transcript_id:
                return {
                    "success": False,
                    "error": "transcript_id is required but not provided"
                }
            
            # Prepare chunks data for database
            chunks_data = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_data = {
                    "id": chunk.id,
                    "transcript_id": transcript_id,  # Use the provided/determined transcript_id
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "entities": chunk.entities,
                    "language": chunk.language,
                    "metadata": {
                        "sentence_count": chunk.sentence_count,
                        "start_position": chunk.start_position,
                        "end_position": chunk.end_position
                    },
                    "sentence_count": chunk.sentence_count,
                    "entity_types": chunk.entity_types,
                    "start_position": chunk.start_position,
                    "end_position": chunk.end_position,
                    "embedding": embedding
                }
                chunks_data.append(chunk_data)
            
            # Insert chunks in batches to avoid payload limits
            batch_size = 20  # Conservative batch size for embeddings
            inserted_count = 0
            failed_chunks = []
            
            for i in range(0, len(chunks_data), batch_size):
                batch = chunks_data[i:i+batch_size]
                
                try:
                    result = self.client.table("semantic_chunks").insert(batch).execute()
                    
                    if hasattr(result, 'error') and result.error is not None:
                        logger.warning(f"Error inserting batch {i//batch_size + 1}: {result.error}")
                        failed_chunks.extend([chunk["id"] for chunk in batch])
                    else:
                        inserted_count += len(batch)
                        logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} chunks)")
                        
                except Exception as e:
                    logger.error(f"Exception inserting batch {i//batch_size + 1}: {e}")
                    failed_chunks.extend([chunk["id"] for chunk in batch])
            
            end_time = time.time()
            
            result = {
                "success": inserted_count > 0,
                "chunks_stored": inserted_count,
                "total_chunks": len(chunks),
                "failed_chunks": failed_chunks,
                "processing_time": end_time - start_time
            }
            
            if failed_chunks:
                result["error"] = f"Failed to insert {len(failed_chunks)} chunks"
            
            logger.info(f"Stored {inserted_count}/{len(chunks)} semantic chunks in {end_time - start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error storing semantic chunks: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def search_semantic_chunks(self, query_embedding: List[float], 
                                   transcript_id: Optional[str] = None,
                                   entity_filter: Optional[List[str]] = None,
                                   match_threshold: float = 0.1,
                                   match_count: int = 10) -> List[Dict[str, Any]]:
        """
        Search semantic chunks using vector similarity with optional filters.
        
        Args:
            query_embedding: Query embedding vector
            transcript_id: Optional transcript to search within
            entity_filter: Optional list of entity types to filter by
            match_threshold: Minimum similarity threshold
            match_count: Maximum number of results
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            if not self.initialized:
                logger.error("Service not initialized")
                return []
            
            # Choose appropriate search function based on filters
            if transcript_id:
                function_name = "match_transcript_semantic_chunks"
                params = {
                    "query_embedding": query_embedding,
                    "transcript_id_param": transcript_id,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            elif entity_filter:
                function_name = "match_chunks_by_entities"
                params = {
                    "query_embedding": query_embedding,
                    "entity_types_filter": entity_filter,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            else:
                function_name = "match_semantic_chunks"
                params = {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            
            # Execute search
            result = self.client.rpc(function_name, params).execute()
            
            if hasattr(result, 'error') and result.error is not None:
                logger.error(f"Error in semantic search: {result.error}")
                return []
            
            chunks = result.data if result.data else []
            logger.info(f"Semantic search returned {len(chunks)} chunks")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def get_chunks_by_transcript(self, transcript_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific transcript.
        
        Args:
            transcript_id: Transcript identifier
            
        Returns:
            List of chunks for the transcript
        """
        try:
            if not self.initialized:
                return []
            
            result = self.client.table("semantic_chunks").select("*").eq(
                "transcript_id", transcript_id
            ).order("chunk_index").execute()
            
            if hasattr(result, 'error') and result.error is not None:
                logger.error(f"Error getting chunks for transcript {transcript_id}: {result.error}")
                return []
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting chunks for transcript: {e}")
            return []
    
    async def get_chunk_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored semantic chunks.
        
        Returns:
            Dictionary with chunk statistics
        """
        try:
            if not self.initialized:
                return {"error": "Service not initialized"}
            
            # Get total count
            count_result = self.client.table("semantic_chunks").select("id", count="exact").execute()
            total_chunks = count_result.count if hasattr(count_result, 'count') else 0
            
            # Get unique entity types
            entities_result = self.client.table("semantic_chunks").select("entity_types").execute()
            all_entity_types = set()
            
            if entities_result.data:
                for row in entities_result.data:
                    if row.get("entity_types"):
                        all_entity_types.update(row["entity_types"])
            
            # Get transcript count
            transcript_result = self.client.table("transcripts").select("transcript_id", count="exact").execute()
            total_transcripts = transcript_result.count if hasattr(transcript_result, 'count') else 0
            
            return {
                "total_chunks": total_chunks,
                "total_transcripts": total_transcripts,
                "unique_entity_types": list(all_entity_types),
                "entity_type_count": len(all_entity_types)
            }
            
        except Exception as e:
            logger.error(f"Error getting chunk statistics: {e}")
            return {"error": str(e)}
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """
        Clear all semantic chunks and transcripts (use with caution).
        
        Returns:
            Result dictionary with operation status
        """
        try:
            if not self.initialized:
                return {"success": False, "error": "Service not initialized"}
            
            # Delete all semantic chunks first (due to foreign key constraint)
            chunks_result = self.client.table("semantic_chunks").delete().neq("id", "").execute()
            
            # Delete all transcripts
            transcripts_result = self.client.table("transcripts").delete().neq("id", "").execute()
            
            logger.warning("Cleared all semantic chunks and transcripts from database")
            
            return {
                "success": True,
                "message": "All data cleared successfully",
                "chunks_deleted": len(chunks_result.data) if chunks_result.data else 0,
                "transcripts_deleted": len(transcripts_result.data) if transcripts_result.data else 0
            }
            
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return {"success": False, "error": str(e)}
    
    def is_initialized(self) -> bool:
        """Check if the service is properly initialized"""
        return self.initialized

    async def extract_key_points(self, transcript_id: str) -> Dict[str, Any]:
        """
        Extract key points from a transcript using enhanced semantic analysis.
        
        Args:
            transcript_id: The transcript to analyze
            
        Returns:
            Dictionary with key points and analysis
        """
        try:
            if not self.initialized:
                return {
                    "success": False,
                    "error": "Semantic chunks service not initialized"
                }
            
            # Get all chunks for the transcript
            chunks = await self.get_chunks_by_transcript(transcript_id)
            
            if not chunks:
                return {
                    "success": False,
                    "error": f"No chunks found for transcript {transcript_id}"
                }
            
            # Analyze chunks by entities only (no sentiment to prevent LLM bias)
            key_points = {
                "key_entities": {},
                "discussion_topics": [],
                "entity_distribution": {},
                "chunk_summary": {}
            }
            
            entity_counts = {}
            topic_entities = set()
            
            for chunk in chunks:
                entities = chunk.get('entities', [])
                text = chunk.get('text', '')
                
                # Count entities for key entities analysis
                for entity in entities:
                    entity_text = entity.get('text', '')
                    entity_label = entity.get('label', '')
                    if entity_text and entity_label:
                        key = f"{entity_text} ({entity_label})"
                        entity_counts[key] = entity_counts.get(key, 0) + 1
                        
                        # Track topic entities (PERSON, ORG, MONEY, etc.)
                        if entity_label in ['PERSON', 'ORG', 'MONEY', 'PERCENT', 'CARDINAL']:
                            topic_entities.add(entity_text)
            
            # Get top entities
            top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            key_points['key_entities'] = dict(top_entities)
            
            # Generate discussion topics from entities
            key_points['discussion_topics'] = list(topic_entities)[:15]  # Top 15 topics
            
            # Entity type distribution
            entity_type_counts = {}
            for chunk in chunks:
                for entity_type in chunk.get('entity_types', []):
                    entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
            key_points['entity_distribution'] = entity_type_counts
            
            # Basic chunk summary
            key_points['chunk_summary'] = {
                "total_chunks": len(chunks),
                "avg_chunk_length": sum(len(chunk.get('text', '')) for chunk in chunks) / len(chunks) if chunks else 0,
                "total_entities": sum(len(chunk.get('entities', [])) for chunk in chunks)
            }
            
            return {
                "success": True,
                "key_points": key_points,
                "total_chunks": len(chunks),
                "transcript_id": transcript_id,
                "metadata": {
                    "extraction_method": "enhanced_semantic",
                    "entity_types_found": len(set(e.get('label', '') for chunk in chunks for e in chunk.get('entities', []))),
                    "entity_distribution": entity_type_counts
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return {
                "success": False,
                "error": str(e)
            } 