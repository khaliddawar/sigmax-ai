"""Vector Search Module

Handles vector similarity search operations extracted from the monolithic
retrieval_qa_service.py for better maintainability and single responsibility.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("retrieval-vector")

@dataclass
class VectorSearchConfig:
    similarity_threshold: float = 0.1
    max_results: int = 10
    enable_reranking: bool = True

class VectorSearchEngine:
    def __init__(self, storage_service=None, config=None):
        self.storage_service = storage_service
        self.config = config or VectorSearchConfig()
        logger.info("VectorSearchEngine initialized")
    
    async def search(self, query=None, query_embedding=None, transcript_id=None, limit=None, similarity_threshold=None, embedding_service=None, **kwargs):
        try:
            limit = limit or self.config.max_results
            similarity_threshold = similarity_threshold or self.config.similarity_threshold
            
            if not self.storage_service:
                logger.error("No storage service available")
                return []
            
            # Generate embedding if not provided
            if query_embedding is None and query is not None:
                if embedding_service:
                    query_embedding = await embedding_service.get_embedding(query)
                    if not query_embedding:
                        logger.error("Failed to generate query embedding")
                        return []
                else:
                    logger.error("No embedding service available and no query_embedding provided")
                    return []
            elif query_embedding is None:
                logger.error("Neither query nor query_embedding provided")
                return []
            
            logger.debug(f"Vector search: threshold={similarity_threshold}, limit={limit}, transcript_id={transcript_id}")
            
            # Call Supabase stored procedure (extracted from original)
            if transcript_id:
                response = self.storage_service.client.rpc(
                    "match_transcript_semantic_chunks",
                    {
                        "query_embedding": query_embedding,
                        "transcript_id_param": transcript_id,
                        "match_threshold": similarity_threshold,
                        "match_count": limit
                    }
                ).execute()
            else:
                response = self.storage_service.client.rpc(
                    "match_semantic_chunks",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": similarity_threshold,
                        "match_count": limit
                    }
                ).execute()
            
            if hasattr(response, 'error') and response.error is not None:
                logger.error(f"Supabase RPC error: {response.error}")
                return []
            
            chunks = response.data if response.data else []
            logger.info(f"Vector search returned {len(chunks)} chunks")
            
            # Convert to consistent format for modular architecture
            formatted_results = []
            for chunk in chunks:
                formatted_result = {
                    'content': chunk.get('text', chunk.get('content', '')),
                    'score': chunk.get('similarity_score', chunk.get('score', 0.0)),
                    'source': f"chunk_{chunk.get('chunk_index', 'unknown')}",
                    'metadata': {
                        'chunk_index': chunk.get('chunk_index'),
                        'transcript_id': chunk.get('transcript_id'),
                        **chunk
                    },
                    'chunk_id': chunk.get('chunk_index')
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []
    
    async def health_check(self):
        return {"status": "healthy" if self.storage_service else "unhealthy"}

class VectorSearchOptimizer:
    def __init__(self):
        pass
    
    async def optimize_search_params(self, query: str, domain=None):
        params = {}
        
        # Extracted from original logic
        if any(phrase in query.lower() for phrase in ["how many topics", "topics", "covered"]):
            params["limit"] = 20
            params["similarity_threshold"] = 0.05
        
        if any(word in query.lower() for word in ["most bullish", "most bearish", "overall view"]):
            params["limit"] = max(params.get("limit", 10), 12)
        
        return params

def create_vector_search_engine(storage_service=None, config=None):
    return VectorSearchEngine(storage_service=storage_service, config=config)
