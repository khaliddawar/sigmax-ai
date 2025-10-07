"""
Hybrid Retrieval System

This module implements a domain-agnostic hybrid retrieval system that combines:
- BM25 keyword search for broad recall
- Embedding-based semantic search for precision  
- Maximal Marginal Relevance (MMR) for diversity
- Dynamic k values based on query patterns
- Entity-based filtering and organization

Key features:
- Works across any domain (financial, medical, legal, etc.)
- Uses semantic chunks with rich metadata
- Combines statistical and semantic relevance
- Ensures topic/entity diversity in results
- Configurable scoring weights and parameters
"""

import logging
import math
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum

# BM25 implementation
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    
# Scientific computing
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Import our semantic chunking system
from .semantic_chunker import ChunkMetadata, SemanticChunker
from .embedding_service import EmbeddingService
from config.domain_loader import get_domain_loader
from config.settings import get_retrieval_config

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Query type classification for adaptive retrieval"""
    INVENTORY = "inventory"  # "How many...", "List all...", "What topics..."
    FOCUSED = "focused"      # Specific questions about entities/concepts
    EXPLORATORY = "exploratory"  # Broad questions requiring diverse context

@dataclass 
class RetrievalResult:
    """Result from hybrid retrieval with scoring breakdown"""
    chunk: ChunkMetadata
    bm25_score: float
    embedding_score: float
    final_score: float
    relevance_factors: Dict[str, float]  # breakdown of scoring factors

@dataclass
class RetrievalConfig:
    """Configuration for hybrid retrieval"""
    # BM25 parameters
    bm25_k1: float = 1.2  # Term frequency saturation parameter
    bm25_b: float = 0.75  # Length normalization parameter
    bm25_weight: float = 0.4  # Weight for BM25 score in final ranking
    
    # Embedding parameters  
    embedding_weight: float = 0.6  # Weight for embedding score in final ranking
    
    # MMR parameters
    mmr_lambda: float = 0.7  # Balance between relevance and diversity
    
    # Dynamic k values
    k_inventory: int = 25  # Results for inventory questions
    k_focused: int = 8     # Results for focused questions  
    k_exploratory: int = 15 # Results for exploratory questions
    
    # BM25 candidate pool size
    bm25_candidates: int = 50  # Initial BM25 candidates before re-ranking

class HybridRetriever:
    """
    Domain-agnostic hybrid retrieval system combining BM25 and embeddings.
    
    This class implements a sophisticated retrieval pipeline that:
    1. Uses BM25 for broad keyword-based recall
    2. Re-ranks with embedding similarity for semantic precision
    3. Applies MMR for entity/topic diversity
    4. Adapts parameters based on query type
    """
    
    def __init__(self, embedding_service: EmbeddingService, 
                 domain_type: Optional[str] = None):
        """
        Initialize the hybrid retriever.
        
        Args:
            embedding_service: Service for generating embeddings
            domain_type: Domain type for configuration (optional)
        """
        self.embedding_service = embedding_service
        self.domain_loader = get_domain_loader()
        
        # Load configuration
        retrieval_config = get_retrieval_config()
        self.config = RetrievalConfig(
            bm25_weight=retrieval_config.get('bm25_weight', 0.4),
            embedding_weight=retrieval_config.get('embedding_weight', 0.6),
            mmr_lambda=retrieval_config.get('mmr_lambda', 0.7),
            k_inventory=retrieval_config.get('k_inventory', 25),
            k_focused=retrieval_config.get('k_focused', 8),
            k_exploratory=retrieval_config.get('k_exploratory', 15),
            bm25_candidates=retrieval_config.get('bm25_candidates', 50)
        )
        
        # BM25 components
        self.bm25_index = None
        self.chunk_corpus = []  # Tokenized chunks for BM25
        self.chunk_metadata = []  # Corresponding metadata
        self.index_built = False
        
        # Query pattern detection
        self.inventory_patterns = [
            r'how many',
            r'list all', 
            r'what topics',
            r'which.*discussed',
            r'topics.*covered',
            r'count.*'
        ]
        
        logger.info(f"Initialized HybridRetriever with BM25 available: {BM25_AVAILABLE}")
    
    def build_index(self, chunks: List[ChunkMetadata]) -> None:
        """
        Build BM25 index from semantic chunks.
        
        Args:
            chunks: List of semantic chunks with metadata
        """
        if not chunks:
            logger.warning("No chunks provided for index building")
            return
        
        if not BM25_AVAILABLE:
            logger.warning("BM25 not available, using fallback scoring")
            self.chunk_metadata = chunks
            self.index_built = True
            return
        
        logger.info(f"Building BM25 index for {len(chunks)} chunks")
        
        # Tokenize chunk texts for BM25
        self.chunk_corpus = []
        self.chunk_metadata = []
        
        for chunk in chunks:
            # Tokenize text for BM25 (simple word splitting)
            tokens = self._tokenize_text(chunk.text)
            self.chunk_corpus.append(tokens)
            self.chunk_metadata.append(chunk)
        
        # Build BM25 index
        try:
            self.bm25_index = BM25Okapi(
                self.chunk_corpus,
                k1=self.config.bm25_k1,
                b=self.config.bm25_b
            )
            self.index_built = True
            logger.info("BM25 index built successfully")
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.index_built = False
    
    async def retrieve(self, query: str, k: Optional[int] = None, 
                entity_filter: Optional[List[str]] = None,
                sentiment_filter: Optional[str] = None) -> List[RetrievalResult]:
        """
        Perform hybrid retrieval combining BM25 and embeddings.
        
        Args:
            query: Search query
            k: Number of results to return (auto-detected if None)
            entity_filter: Filter by entity types
            sentiment_filter: Filter by sentiment
            
        Returns:
            List of retrieval results with scoring breakdown
        """
        if not self.index_built:
            logger.warning("Index not built, returning empty results")
            return []
        
        # Classify query type and determine k
        query_type = self._classify_query(query)
        if k is None:
            k = self._get_k_for_query_type(query_type)
        
        logger.info(f"Retrieving for query type: {query_type.value}, k={k}")
        
        # Phase 1: BM25 broad recall
        bm25_results = self._bm25_search(query, self.config.bm25_candidates)
        
        if not bm25_results:
            logger.warning("No BM25 results found")
            return []
        
        # Phase 2: Embedding re-ranking
        reranked_results = await self._embedding_rerank(query, bm25_results)
        
        # Phase 3: Apply filters
        if entity_filter or sentiment_filter:
            reranked_results = self._apply_filters(
                reranked_results, entity_filter, sentiment_filter
            )
        
        # Phase 4: MMR diversity selection
        final_results = self._apply_mmr_diversity(reranked_results, k)
        
        logger.info(f"Retrieved {len(final_results)} results after MMR diversity")
        return final_results
    
    def _classify_query(self, query: str) -> QueryType:
        """
        Classify query type for adaptive retrieval.
        
        Args:
            query: Search query
            
        Returns:
            Classified query type
        """
        query_lower = query.lower()
        
        # Check for inventory patterns
        for pattern in self.inventory_patterns:
            if re.search(pattern, query_lower):
                return QueryType.INVENTORY
        
        # Check for specific entity mentions (focused queries)
        try:
            domain_terms = self.domain_loader.get_domain_specific_terms()
            entity_mentions = 0
            
            for category, terms_data in domain_terms.items():
                if isinstance(terms_data, dict):
                    for subcategory, terms in terms_data.items():
                        if isinstance(terms, list):
                            for term in terms:
                                if term.lower() in query_lower:
                                    entity_mentions += 1
                                    
            if entity_mentions >= 2:  # Multiple specific entity mentions
                return QueryType.FOCUSED
                
        except Exception as e:
            logger.warning(f"Error in entity detection for query classification: {e}")
        
        # Default to exploratory
        return QueryType.EXPLORATORY
    
    def _get_k_for_query_type(self, query_type: QueryType) -> int:
        """Get appropriate k value for query type"""
        if query_type == QueryType.INVENTORY:
            return self.config.k_inventory
        elif query_type == QueryType.FOCUSED:
            return self.config.k_focused
        else:
            return self.config.k_exploratory
    
    def _tokenize_text(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 processing.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Simple but effective tokenization
        # Remove punctuation and split on whitespace
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        
        # Remove very short tokens and numbers
        tokens = [t for t in tokens if len(t) > 2 and not t.isdigit()]
        
        return tokens
    
    def _bm25_search(self, query: str, k: int) -> List[Tuple[int, float]]:
        """
        Perform BM25 search and return top candidates.
        
        Args:
            query: Search query
            k: Number of candidates to return
            
        Returns:
            List of (chunk_index, bm25_score) tuples
        """
        if not BM25_AVAILABLE or self.bm25_index is None:
            # Fallback: return all chunks with uniform scores
            results = [(i, 1.0) for i in range(len(self.chunk_metadata))]
            return results[:k]
        
        # Tokenize query
        query_tokens = self._tokenize_text(query)
        
        if not query_tokens:
            logger.warning("No valid tokens in query for BM25")
            return []
        
        try:
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Create (index, score) pairs and sort by score
            results = [(i, score) for i, score in enumerate(scores)]
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Filter out zero scores and return top k
            results = [(i, score) for i, score in results if score > 0]
            return results[:k]
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    async def _embedding_rerank(self, query: str, 
                               bm25_results: List[Tuple[int, float]]) -> List[RetrievalResult]:
        """
        Re-rank BM25 results using embedding similarity.
        
        Args:
            query: Search query
            bm25_results: List of (chunk_index, bm25_score) from BM25
            
        Returns:
            List of retrieval results with combined scores
        """
        if not bm25_results:
            return []
        
        try:
            # Get query embedding
            query_embedding = await self.embedding_service.get_embedding(query)
            
            if not query_embedding:
                logger.warning("Could not get query embedding, using BM25 scores only")
                # Return results with only BM25 scores
                return [
                    RetrievalResult(
                        chunk=self.chunk_metadata[idx],
                        bm25_score=bm25_score,
                        embedding_score=0.0,
                        final_score=bm25_score,
                        relevance_factors={'bm25_only': bm25_score}
                    )
                    for idx, bm25_score in bm25_results
                ]
            
            # Get embeddings for candidate chunks
            candidate_texts = [self.chunk_metadata[idx].text for idx, _ in bm25_results]
            chunk_embeddings = await self.embedding_service.get_embeddings(candidate_texts)
            
            if not chunk_embeddings:
                logger.warning("Could not get chunk embeddings, using BM25 scores only")
                return [
                    RetrievalResult(
                        chunk=self.chunk_metadata[idx],
                        bm25_score=bm25_score,
                        embedding_score=0.0,
                        final_score=bm25_score,
                        relevance_factors={'bm25_only': bm25_score}
                    )
                    for idx, bm25_score in bm25_results
                ]
            
            # Calculate combined scores
            results = []
            for i, (chunk_idx, bm25_score) in enumerate(bm25_results):
                if i < len(chunk_embeddings):
                    # Calculate cosine similarity
                    embedding_score = self._cosine_similarity(query_embedding, chunk_embeddings[i])
                    
                    # Normalize scores (BM25 scores can vary widely)
                    normalized_bm25 = self._normalize_bm25_score(bm25_score)
                    
                    # Combine scores
                    final_score = (
                        self.config.bm25_weight * normalized_bm25 +
                        self.config.embedding_weight * embedding_score
                    )
                    
                    results.append(RetrievalResult(
                        chunk=self.chunk_metadata[chunk_idx],
                        bm25_score=bm25_score,
                        embedding_score=embedding_score,
                        final_score=final_score,
                        relevance_factors={
                            'bm25_normalized': normalized_bm25,
                            'embedding': embedding_score,
                            'combined': final_score
                        }
                    ))
            
            # Sort by final score
            results.sort(key=lambda x: x.final_score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Embedding re-ranking failed: {e}")
            # Fallback to BM25 only
            return [
                RetrievalResult(
                    chunk=self.chunk_metadata[idx],
                    bm25_score=bm25_score,
                    embedding_score=0.0,
                    final_score=bm25_score,
                    relevance_factors={'bm25_fallback': bm25_score}
                )
                for idx, bm25_score in bm25_results
            ]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not NUMPY_AVAILABLE:
            # Fallback implementation
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(a * a for a in vec2))
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        else:
            # Numpy implementation
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            
            cosine_sim = np.dot(vec1_np, vec2_np) / (np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np))
            return float(cosine_sim)
    
    def _normalize_bm25_score(self, bm25_score: float) -> float:
        """
        Normalize BM25 score to 0-1 range.
        
        Args:
            bm25_score: Raw BM25 score
            
        Returns:
            Normalized score between 0 and 1
        """
        # BM25 scores are typically in range 0-20, but can go higher
        # Use sigmoid-like normalization
        return 1 / (1 + math.exp(-bm25_score / 5))
    
    def _apply_filters(self, results: List[RetrievalResult],
                      entity_filter: Optional[List[str]] = None,
                      sentiment_filter: Optional[str] = None) -> List[RetrievalResult]:
        """
        Apply entity and sentiment filters to results.
        
        Args:
            results: Retrieval results to filter
            entity_filter: List of entity types to include
            sentiment_filter: Sentiment to filter by
            
        Returns:
            Filtered results
        """
        filtered_results = results
        
        if entity_filter:
            filtered_results = [
                result for result in filtered_results
                if any(entity_type in result.chunk.entity_types for entity_type in entity_filter)
            ]
            logger.info(f"Entity filter reduced results from {len(results)} to {len(filtered_results)}")
        
        if sentiment_filter:
            filtered_results = [
                result for result in filtered_results
                if result.chunk.sentiment == sentiment_filter
            ]
            logger.info(f"Sentiment filter reduced results to {len(filtered_results)}")
        
        return filtered_results
    
    def _apply_mmr_diversity(self, results: List[RetrievalResult], 
                           k: int) -> List[RetrievalResult]:
        """
        Apply Maximal Marginal Relevance for diverse result selection.
        
        Args:
            results: Retrieval results to diversify
            k: Number of diverse results to select
            
        Returns:
            Diversified results
        """
        if len(results) <= k:
            return results
        
        # Initialize with highest scoring result
        selected = [results[0]]
        remaining = results[1:]
        
        # Greedy MMR selection
        while len(selected) < k and remaining:
            best_idx = 0
            best_mmr_score = -1
            
            for i, candidate in enumerate(remaining):
                # Calculate MMR score
                relevance_score = candidate.final_score
                
                # Calculate diversity (based on entity overlap)
                max_similarity = 0
                for selected_result in selected:
                    similarity = self._entity_similarity(candidate.chunk, selected_result.chunk)
                    max_similarity = max(max_similarity, similarity)
                
                # MMR formula: λ * relevance - (1 - λ) * max_similarity
                mmr_score = (
                    self.config.mmr_lambda * relevance_score - 
                    (1 - self.config.mmr_lambda) * max_similarity
                )
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = i
            
            # Add best candidate and remove from remaining
            selected.append(remaining.pop(best_idx))
        
        logger.info(f"MMR selected {len(selected)} diverse results from {len(results)} candidates")
        return selected
    
    def _entity_similarity(self, chunk1: ChunkMetadata, chunk2: ChunkMetadata) -> float:
        """
        Calculate entity-based similarity between two chunks.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            Similarity score between 0 and 1
        """
        entities1 = set(chunk1.entity_types)
        entities2 = set(chunk2.entity_types)
        
        if not entities1 and not entities2:
            return 0.0
        
        if not entities1 or not entities2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(entities1.intersection(entities2))
        union = len(entities1.union(entities2))
        
        return intersection / union if union > 0 else 0.0
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index"""
        if not self.index_built:
            return {"status": "not_built"}
        
        return {
            "status": "built",
            "total_chunks": len(self.chunk_metadata),
            "bm25_available": BM25_AVAILABLE,
            "config": {
                "bm25_weight": self.config.bm25_weight,
                "embedding_weight": self.config.embedding_weight,
                "mmr_lambda": self.config.mmr_lambda
            }
        } 