"""Re-ranking Module

Handles result scoring, re-ranking, and relevance optimization for QA responses.
Extracted from the monolithic retrieval_qa_service.py for better maintainability.

Key responsibilities:
- Result relevance scoring
- Multi-factor re-ranking
- Diversity optimization
- Quality filtering
"""
from __future__ import annotations

import logging
import math
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger("retrieval-rerank")


@dataclass
class SearchResult:
    """Represents a search result with metadata."""
    content: str
    score: float
    source: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None
    position: Optional[int] = None


@dataclass
class RerankingConfig:
    """Configuration for re-ranking algorithms."""
    semantic_weight: float = 0.4
    keyword_weight: float = 0.3
    recency_weight: float = 0.2
    diversity_weight: float = 0.1
    max_results: int = 10
    min_score_threshold: float = 0.1
    diversity_threshold: float = 0.8


class RerankingStrategy(Enum):
    """Different re-ranking strategies."""
    SEMANTIC_ONLY = "semantic"
    HYBRID = "hybrid"
    KEYWORD_FOCUSED = "keyword"
    DIVERSITY_FOCUSED = "diversity"
    RECENCY_FOCUSED = "recency"


class SemanticScorer:
    """Handles semantic similarity scoring."""
    
    def __init__(self):
        self.cache = {}
    
    def score_semantic_relevance(
        self,
        query: str,
        content: str,
        embedding_service=None
    ) -> float:
        """Score semantic relevance between query and content."""
        
        # Simple keyword overlap scoring as fallback
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        return overlap / len(query_words)
    
    async def score_with_embeddings(
        self,
        query: str,
        content: str,
        embedding_service
    ) -> float:
        """Score using embedding similarity."""
        try:
            # This would use actual embedding service
            # For now, fallback to keyword scoring
            return self.score_semantic_relevance(query, content)
        except Exception as e:
            logger.warning(f"Embedding scoring failed: {e}")
            return self.score_semantic_relevance(query, content)


class KeywordScorer:
    """Handles keyword-based scoring."""
    
    def __init__(self):
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
    
    def score_keyword_relevance(self, query: str, content: str) -> float:
        """Score keyword relevance with TF-IDF-like scoring."""
        
        query_terms = self._extract_terms(query)
        content_terms = self._extract_terms(content)
        
        if not query_terms:
            return 0.0
        
        # Calculate term frequency scores
        total_score = 0.0
        for term in query_terms:
            tf = content_terms.count(term) / max(len(content_terms), 1)
            # Simple IDF approximation
            idf = math.log(1 + (1 / max(query_terms.count(term), 1)))
            total_score += tf * idf
        
        return min(total_score, 1.0)
    
    def _extract_terms(self, text: str) -> List[str]:
        """Extract meaningful terms from text."""
        # Simple tokenization and stopword removal
        terms = re.findall(r'\b\w+\b', text.lower())
        return [term for term in terms if term not in self.stopwords and len(term) > 2]


class RecencyScorer:
    """Handles recency-based scoring."""
    
    def score_recency(self, result: SearchResult) -> float:
        """Score based on content recency."""
        
        # Extract timestamp from metadata if available
        timestamp = result.metadata.get('timestamp')
        if not timestamp:
            return 0.5  # Neutral score for unknown recency
        
        try:
            # This would implement actual recency scoring
            # For now, return neutral score
            return 0.5
        except Exception:
            return 0.5


class DiversityScorer:
    """Handles diversity scoring to avoid redundant results."""
    
    def __init__(self):
        self.similarity_cache = {}
    
    def calculate_diversity_score(
        self,
        candidate: SearchResult,
        selected_results: List[SearchResult],
        threshold: float = 0.8
    ) -> float:
        """Calculate diversity score for a candidate result."""
        
        if not selected_results:
            return 1.0  # First result is always diverse
        
        max_similarity = 0.0
        for selected in selected_results:
            similarity = self._calculate_content_similarity(
                candidate.content, selected.content
            )
            max_similarity = max(max_similarity, similarity)
        
        # Return diversity score (inverse of similarity)
        return 1.0 - max_similarity
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content pieces."""
        
        # Simple Jaccard similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


class HybridReranker:
    """Main re-ranking engine combining multiple scoring strategies."""
    
    def __init__(self, config: Optional[RerankingConfig] = None):
        self.config = config or RerankingConfig()
        self.semantic_scorer = SemanticScorer()
        self.keyword_scorer = KeywordScorer()
        self.recency_scorer = RecencyScorer()
        self.diversity_scorer = DiversityScorer()
    
    async def rerank_results(
        self,
        query: str,
        results: List[SearchResult],
        strategy: RerankingStrategy = RerankingStrategy.HYBRID,
        embedding_service=None
    ) -> List[SearchResult]:
        """Re-rank search results using specified strategy."""
        
        if not results:
            return []
        
        logger.debug(f"Re-ranking {len(results)} results using {strategy.value} strategy")
        
        try:
            # Score all results
            scored_results = []
            for i, result in enumerate(results):
                result.position = i  # Track original position
                
                # Calculate component scores
                scores = await self._calculate_component_scores(
                    query, result, embedding_service
                )
                
                # Calculate final score based on strategy
                final_score = self._calculate_final_score(scores, strategy)
                
                # Create new result with updated score
                reranked_result = SearchResult(
                    content=result.content,
                    score=final_score,
                    source=result.source,
                    metadata={
                        **result.metadata,
                        "original_score": result.score,
                        "original_position": i,
                        "component_scores": scores
                    },
                    chunk_id=result.chunk_id,
                    position=result.position
                )
                
                scored_results.append(reranked_result)
            
            # Apply diversity filtering if enabled
            if self.config.diversity_weight > 0:
                scored_results = self._apply_diversity_filtering(scored_results)
            
            # Sort by final score and apply limits
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            # Filter by minimum score threshold
            filtered_results = [
                r for r in scored_results 
                if r.score >= self.config.min_score_threshold
            ]
            
            # Apply max results limit
            final_results = filtered_results[:self.config.max_results]
            
            logger.debug(f"Re-ranking complete: {len(final_results)} results returned")
            return final_results
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Return original results on failure
            return results[:self.config.max_results]
    
    async def _calculate_component_scores(
        self,
        query: str,
        result: SearchResult,
        embedding_service=None
    ) -> Dict[str, float]:
        """Calculate individual component scores."""
        
        scores = {}
        
        # Semantic score
        if embedding_service:
            scores['semantic'] = await self.semantic_scorer.score_with_embeddings(
                query, result.content, embedding_service
            )
        else:
            scores['semantic'] = self.semantic_scorer.score_semantic_relevance(
                query, result.content
            )
        
        # Keyword score
        scores['keyword'] = self.keyword_scorer.score_keyword_relevance(
            query, result.content
        )
        
        # Recency score
        scores['recency'] = self.recency_scorer.score_recency(result)
        
        # Original score (from initial retrieval)
        scores['original'] = result.score
        
        return scores
    
    def _calculate_final_score(
        self,
        scores: Dict[str, float],
        strategy: RerankingStrategy
    ) -> float:
        """Calculate final score based on strategy."""
        
        if strategy == RerankingStrategy.SEMANTIC_ONLY:
            return scores['semantic']
        
        elif strategy == RerankingStrategy.KEYWORD_FOCUSED:
            return (
                scores['keyword'] * 0.6 +
                scores['semantic'] * 0.3 +
                scores['original'] * 0.1
            )
        
        elif strategy == RerankingStrategy.RECENCY_FOCUSED:
            return (
                scores['recency'] * 0.5 +
                scores['semantic'] * 0.3 +
                scores['keyword'] * 0.2
            )
        
        elif strategy == RerankingStrategy.DIVERSITY_FOCUSED:
            # Diversity will be handled in filtering step
            return (
                scores['semantic'] * 0.4 +
                scores['keyword'] * 0.4 +
                scores['original'] * 0.2
            )
        
        else:  # HYBRID strategy
            return (
                scores['semantic'] * self.config.semantic_weight +
                scores['keyword'] * self.config.keyword_weight +
                scores['recency'] * self.config.recency_weight +
                scores['original'] * (1 - self.config.semantic_weight - 
                                    self.config.keyword_weight - 
                                    self.config.recency_weight)
            )
    
    def _apply_diversity_filtering(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Apply diversity filtering to reduce redundant results."""
        
        if len(results) <= 1:
            return results
        
        # Sort by score first
        results.sort(key=lambda x: x.score, reverse=True)
        
        diverse_results = [results[0]]  # Always include top result
        
        for candidate in results[1:]:
            diversity_score = self.diversity_scorer.calculate_diversity_score(
                candidate, diverse_results, self.config.diversity_threshold
            )
            
            # Adjust final score based on diversity
            adjusted_score = (
                candidate.score * (1 - self.config.diversity_weight) +
                diversity_score * self.config.diversity_weight
            )
            
            candidate.score = adjusted_score
            candidate.metadata['diversity_score'] = diversity_score
            
            diverse_results.append(candidate)
        
        return diverse_results


# Factory functions
def create_default_reranker() -> HybridReranker:
    """Create default re-ranker with standard configuration."""
    return HybridReranker()


def create_semantic_reranker() -> HybridReranker:
    """Create semantic-focused re-ranker."""
    config = RerankingConfig(
        semantic_weight=0.7,
        keyword_weight=0.2,
        recency_weight=0.05,
        diversity_weight=0.05
    )
    return HybridReranker(config)


def create_keyword_reranker() -> HybridReranker:
    """Create keyword-focused re-ranker."""
    config = RerankingConfig(
        semantic_weight=0.2,
        keyword_weight=0.6,
        recency_weight=0.1,
        diversity_weight=0.1
    )
    return HybridReranker(config)


def create_diversity_reranker() -> HybridReranker:
    """Create diversity-focused re-ranker."""
    config = RerankingConfig(
        semantic_weight=0.3,
        keyword_weight=0.3,
        recency_weight=0.1,
        diversity_weight=0.3,
        diversity_threshold=0.7
    )
    return HybridReranker(config) 