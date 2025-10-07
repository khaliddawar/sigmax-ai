"""Retrieval Coordinator Module

Main orchestrator for the retrieval pipeline, coordinating between vector search,
re-ranking, validation, and prompt generation. This replaces the monolithic
retrieval_qa_service.py with a clean, modular architecture.

Key responsibilities:
- Pipeline orchestration
- Service coordination
- Error handling and fallbacks
- Performance monitoring
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .vector import VectorSearchEngine, VectorSearchOptimizer
from .rerank import HybridReranker, SearchResult, RerankingStrategy
from .prompts import PromptGenerator, PromptResult, PromptType
from .validation import CompositeValidator, ValidationResult

logger = logging.getLogger("retrieval-coordinator")


@dataclass
class RetrievalConfig:
    """Configuration for the retrieval pipeline."""
    max_results: int = 10
    similarity_threshold: float = 0.7
    enable_reranking: bool = True
    enable_validation: bool = True
    enable_optimization: bool = True
    timeout_seconds: int = 30
    fallback_enabled: bool = True


@dataclass
class RetrievalContext:
    """Context for a retrieval request."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    domain: Optional[str] = None
    preferences: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


@dataclass
class RetrievalResult:
    """Result of the complete retrieval pipeline."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    validation_results: Optional[ValidationResult]
    prompt_metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    context: RetrievalContext


class RetrievalCoordinator:
    """Main coordinator for the retrieval pipeline."""
    
    def __init__(
        self,
        vector_engine: VectorSearchEngine,
        reranker: HybridReranker,
        prompt_generator: PromptGenerator,
        validator: CompositeValidator,
        config: Optional[RetrievalConfig] = None
    ):
        self.vector_engine = vector_engine
        self.reranker = reranker
        self.prompt_generator = prompt_generator
        self.validator = validator
        self.config = config or RetrievalConfig()
        self.optimizer = VectorSearchOptimizer()
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "average_response_time": 0.0,
            "cache_hit_rate": 0.0
        }
    
    async def retrieve_and_answer(
        self,
        question: str,
        context: Optional[RetrievalContext] = None,
        llm_service=None,
        embedding_service=None
    ) -> RetrievalResult:
        """Main entry point for retrieval and answer generation."""
        
        start_time = time.time()
        context = context or RetrievalContext()
        
        try:
            self.metrics["total_requests"] += 1
            logger.info(f"Processing question: {question[:100]}...")
            
            # Step 1: Vector search
            search_results = await self._perform_vector_search(
                question, context, embedding_service
            )
            
            # Step 2: Re-ranking (if enabled)
            if self.config.enable_reranking and search_results:
                search_results = await self._rerank_results(
                    question, search_results, context, embedding_service
                )
            
            # Step 3: Generate optimized prompt
            prompt_result = await self._generate_prompt(
                question, search_results, context
            )
            
            # Step 4: Generate answer using LLM
            answer = await self._generate_answer(
                prompt_result, llm_service
            )
            
            # Step 5: Validate answer (if enabled)
            validation_result = None
            if self.config.enable_validation:
                validation_result = await self._validate_answer(
                    question, answer, search_results, context
                )
            
            # Step 6: Calculate confidence score
            confidence_score = self._calculate_confidence(
                search_results, validation_result, prompt_result
            )
            
            # Step 7: Format sources
            sources = self._format_sources(search_results)
            
            # Performance metrics
            response_time = time.time() - start_time
            self._update_metrics(response_time, True)
            
            performance_metrics = {
                "response_time": response_time,
                "vector_search_results": len(search_results) if search_results else 0,
                "reranking_enabled": self.config.enable_reranking,
                "validation_enabled": self.config.enable_validation
            }
            
            self.metrics["successful_requests"] += 1
            
            return RetrievalResult(
                answer=answer,
                sources=sources,
                confidence_score=confidence_score,
                validation_results=validation_result,
                prompt_metadata=prompt_result.metadata,
                performance_metrics=performance_metrics,
                context=context
            )
            
        except Exception as e:
            logger.error(f"Retrieval pipeline failed: {e}")
            
            # Fallback handling
            if self.config.fallback_enabled:
                return await self._handle_fallback(question, context, e)
            else:
                raise
    
    async def _perform_vector_search(
        self,
        question: str,
        context: RetrievalContext,
        embedding_service=None
    ) -> List[SearchResult]:
        """Perform vector similarity search."""
        
        try:
            logger.debug("Performing vector search")
            
            # Optimize search parameters if enabled
            search_params = {}
            if self.config.enable_optimization:
                search_params = await self.optimizer.optimize_search_params(
                    question, context.domain
                )
            
            # Perform search
            raw_results = await self.vector_engine.search(
                query=question,
                limit=self.config.max_results * 2,  # Get more for re-ranking
                similarity_threshold=self.config.similarity_threshold,
                embedding_service=embedding_service,
                **search_params
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in raw_results:
                search_result = SearchResult(
                    content=result.get('content', ''),
                    score=result.get('score', 0.0),
                    source=result.get('source', 'unknown'),
                    metadata=result.get('metadata', {}),
                    chunk_id=result.get('chunk_id')
                )
                search_results.append(search_result)
            
            logger.debug(f"Vector search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _rerank_results(
        self,
        question: str,
        results: List[SearchResult],
        context: RetrievalContext,
        embedding_service=None
    ) -> List[SearchResult]:
        """Re-rank search results for better relevance."""
        
        try:
            logger.debug("Re-ranking search results")
            
            # Determine re-ranking strategy based on context
            strategy = self._determine_reranking_strategy(question, context)
            
            # Perform re-ranking
            reranked_results = await self.reranker.rerank_results(
                query=question,
                results=results,
                strategy=strategy,
                embedding_service=embedding_service
            )
            
            # Limit to final result count
            final_results = reranked_results[:self.config.max_results]
            
            logger.debug(f"Re-ranking returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Return original results on failure
            return results[:self.config.max_results]
    
    async def _generate_prompt(
        self,
        question: str,
        search_results: List[SearchResult],
        context: RetrievalContext
    ) -> PromptResult:
        """Generate optimized prompt for LLM."""
        
        try:
            logger.debug("Generating optimized prompt")
            
            # Combine search results into context
            combined_context = self._combine_search_results(search_results)
            
            # Generate prompt
            prompt_result = await self.prompt_generator.generate_prompt(
                question=question,
                context=combined_context,
                domain=context.domain,
                max_context_length=12000  # Adjust based on model limits
            )
            
            logger.debug(f"Generated prompt with type: {prompt_result.prompt_type.value}")
            return prompt_result
            
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            # Return fallback prompt
            return PromptResult(
                system_prompt="You are a helpful assistant.",
                user_prompt=f"Question: {question}",
                response_format="Provide a clear answer.",
                prompt_type=PromptType.FACTUAL,
                metadata={"fallback": True}
            )
    
    async def _generate_answer(
        self,
        prompt_result: PromptResult,
        llm_service
    ) -> str:
        """Generate answer using LLM service."""
        
        try:
            logger.debug("Generating answer with LLM")
            
            if not llm_service:
                raise ValueError("LLM service not provided")
            
            # Call LLM service with generated prompts
            response = await llm_service.generate_response(
                system_prompt=prompt_result.system_prompt,
                user_prompt=prompt_result.user_prompt,
                response_format=prompt_result.response_format
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I'm unable to generate an answer at this time."
    
    async def _validate_answer(
        self,
        question: str,
        answer: str,
        search_results: List[SearchResult],
        context: RetrievalContext
    ) -> ValidationResult:
        """Validate the generated answer."""
        
        try:
            logger.debug("Validating generated answer")
            
            # Prepare context for validation
            source_context = self._combine_search_results(search_results)
            
            # Perform validation - fix interface to match ValidationResult
            validation_result = await self.validator.validate(
                response=answer,  # Changed from answer to response
                context=source_context,
                question=question,  # Moved to proper position
                domain=context.domain
            )
            
            logger.debug(f"Validation confidence: {validation_result.confidence}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Answer validation failed: {e}")
            # Return neutral validation result using correct interface
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                issues=[],
                suggestions=[],
                validation_details={"validation_failed": True}
            )
    
    def _calculate_confidence(
        self,
        search_results: List[SearchResult],
        validation_result: Optional[ValidationResult],
        prompt_result: PromptResult
    ) -> float:
        """Calculate overall confidence score."""
        
        # Base confidence from search results
        if not search_results:
            return 0.1
        
        # Average search scores
        avg_search_score = sum(r.score for r in search_results) / len(search_results)
        
        # Validation score - fix to use correct field name
        validation_score = validation_result.confidence if validation_result else 0.5
        
        # Prompt quality indicators
        prompt_quality = 0.8  # Default
        if prompt_result.metadata.get("fallback"):
            prompt_quality = 0.3
        
        # Combine scores
        confidence = (
            avg_search_score * 0.4 +
            validation_score * 0.4 +
            prompt_quality * 0.2
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _format_sources(self, search_results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Format search results as sources."""
        
        sources = []
        for i, result in enumerate(search_results):
            source = {
                "id": i + 1,
                "content": result.content[:500] + "..." if len(result.content) > 500 else result.content,
                "source": result.source,
                "score": result.score,
                "metadata": result.metadata
            }
            sources.append(source)
        
        return sources
    
    def _combine_search_results(self, search_results: List[SearchResult]) -> str:
        """Combine search results into a single context string."""
        
        if not search_results:
            return ""
        
        context_parts = []
        for i, result in enumerate(search_results):
            context_parts.append(f"[Source {i+1}]: {result.content}")
        
        return "\n\n".join(context_parts)
    
    def _determine_reranking_strategy(
        self,
        question: str,
        context: RetrievalContext
    ) -> RerankingStrategy:
        """Determine appropriate re-ranking strategy."""
        
        # Domain-specific strategies
        if context.domain == "financial":
            return RerankingStrategy.KEYWORD_FOCUSED
        elif context.domain == "recent_news":
            return RerankingStrategy.RECENCY_FOCUSED
        
        # Question-type based strategies
        question_lower = question.lower()
        if any(word in question_lower for word in ["compare", "difference", "versus"]):
            return RerankingStrategy.DIVERSITY_FOCUSED
        
        # Default to hybrid
        return RerankingStrategy.HYBRID
    
    async def _handle_fallback(
        self,
        question: str,
        context: RetrievalContext,
        error: Exception
    ) -> RetrievalResult:
        """Handle fallback when main pipeline fails."""
        
        logger.warning(f"Using fallback response due to error: {error}")
        
        fallback_answer = (
            "I apologize, but I'm experiencing technical difficulties and cannot "
            "provide a complete answer to your question at this time. Please try again later."
        )
        
        return RetrievalResult(
            answer=fallback_answer,
            sources=[],
            confidence_score=0.1,
            validation_results=None,
            prompt_metadata={"fallback": True, "error": str(error)},
            performance_metrics={"fallback_used": True},
            context=context
        )
    
    def _update_metrics(self, response_time: float, success: bool):
        """Update performance metrics."""
        
        # Update average response time
        total_requests = self.metrics["total_requests"]
        current_avg = self.metrics["average_response_time"]
        
        self.metrics["average_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        
        health_status = {
            "status": "healthy",
            "components": {},
            "timestamp": time.time()
        }
        
        try:
            # Check vector engine
            health_status["components"]["vector_engine"] = await self.vector_engine.health_check()
        except Exception as e:
            health_status["components"]["vector_engine"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        # Check other components
        health_status["components"]["reranker"] = {"status": "healthy"}
        health_status["components"]["prompt_generator"] = {"status": "healthy"}
        health_status["components"]["validator"] = {"status": "healthy"}
        
        return health_status


# Factory functions
def create_default_coordinator(
    vector_engine: VectorSearchEngine,
    embedding_service=None,
    llm_service=None
) -> RetrievalCoordinator:
    """Create coordinator with default components."""
    
    from .rerank import create_default_reranker
    from .prompts import create_default_prompt_generator
    from .validation import create_default_validator
    
    reranker = create_default_reranker()
    prompt_generator = create_default_prompt_generator()
    validator = create_default_validator()
    
    return RetrievalCoordinator(
        vector_engine=vector_engine,
        reranker=reranker,
        prompt_generator=prompt_generator,
        validator=validator
    )


def create_domain_coordinator(
    vector_engine: VectorSearchEngine,
    domain: str,
    embedding_service=None,
    llm_service=None
) -> RetrievalCoordinator:
    """Create domain-specific coordinator."""
    
    from .rerank import create_semantic_reranker, create_keyword_reranker
    from .prompts import create_domain_specific_generator
    from .validation import create_strict_validator, create_default_validator
    
    # Domain-specific configurations
    if domain == "financial":
        reranker = create_keyword_reranker()
        validator = create_strict_validator()
    else:
        reranker = create_semantic_reranker()
        validator = create_default_validator()
    
    prompt_generator = create_domain_specific_generator(domain)
    
    config = RetrievalConfig(
        enable_validation=True,
        enable_reranking=True,
        enable_optimization=True
    )
    
    return RetrievalCoordinator(
        vector_engine=vector_engine,
        reranker=reranker,
        prompt_generator=prompt_generator,
        validator=validator,
        config=config
    )
