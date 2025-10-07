"""Retrieval Services Module

This package contains modular retrieval services extracted from the monolithic
retrieval_qa_service.py for better maintainability and single responsibility.

Modules:
- vector: Vector similarity search
- validation: Response validation and hallucination detection
- prompts: Prompt engineering and templates
- rerank: Result re-ranking and scoring
- coordinator: Main retrieval coordination logic
"""

from .vector import VectorSearchEngine, VectorSearchOptimizer
from .validation import (
    BaseValidator, NumericConsistencyValidator, QuoteAccuracyValidator,
    ContextGroundingValidator, CompositeValidator, ValidationResult,
    create_default_validator, create_strict_validator
)
from .prompts import (
    PromptGenerator, PromptResult, PromptType, PromptTemplate,
    PromptTemplateManager, PromptClassifier, ContextOptimizer,
    create_default_prompt_generator, create_domain_specific_generator
)
from .rerank import (
    HybridReranker, SearchResult, RerankingConfig, RerankingStrategy,
    SemanticScorer, KeywordScorer, RecencyScorer, DiversityScorer,
    create_default_reranker, create_semantic_reranker, 
    create_keyword_reranker, create_diversity_reranker
)
from .coordinator import (
    RetrievalCoordinator, RetrievalConfig, RetrievalContext, RetrievalResult,
    create_default_coordinator, create_domain_coordinator
)

__all__ = [
    # Vector search
    "VectorSearchEngine",
    "VectorSearchOptimizer",
    
    # Validation
    "BaseValidator",
    "NumericConsistencyValidator",
    "QuoteAccuracyValidator",
    "ContextGroundingValidator",
    "CompositeValidator",
    "ValidationResult",
    "create_default_validator",
    "create_strict_validator",
    
    # Prompts
    "PromptGenerator",
    "PromptResult",
    "PromptType",
    "PromptTemplate",
    "PromptTemplateManager",
    "PromptClassifier",
    "ContextOptimizer",
    "create_default_prompt_generator",
    "create_domain_specific_generator",
    
    # Re-ranking
    "HybridReranker",
    "SearchResult",
    "RerankingConfig",
    "RerankingStrategy",
    "SemanticScorer",
    "KeywordScorer",
    "RecencyScorer",
    "DiversityScorer",
    "create_default_reranker",
    "create_semantic_reranker",
    "create_keyword_reranker",
    "create_diversity_reranker",
    
    # Coordination
    "RetrievalCoordinator",
    "RetrievalConfig",
    "RetrievalContext",
    "RetrievalResult",
    "create_default_coordinator",
    "create_domain_coordinator"
] 