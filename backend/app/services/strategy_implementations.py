"""Concrete Strategy Implementations

This module provides concrete implementations of the strategy interfaces,
demonstrating how existing services can be decoupled and made pluggable.

These implementations wrap existing services to provide the strategy interface.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .strategy_interfaces import (
    ValidationStrategy, PromptStrategy, RetrievalStrategy,
    ValidationResult, PromptResult, RetrievalResult,
    get_strategy_registry
)

logger = logging.getLogger("bpt-strategy-implementations")


# ---------------------------------------------------------------------------
# Validation Strategy Implementations
# ---------------------------------------------------------------------------

class LegacyQAValidationStrategy(ValidationStrategy):
    """Validation strategy that wraps the existing QA response validator."""
    
    def __init__(self, **kwargs):
        from .retrieval_qa_service import QAResponseValidator
        self.validator = QAResponseValidator()
    
    async def validate_response(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate using the existing QA response validator."""
        
        try:
            validation_results = self.validator.validate_qa_response(
                answer=response,
                context=context,
                question=question
            )
            
            is_valid = validation_results.get("overall_valid", False)
            issues = validation_results.get("issues", [])
            
            # Extract suggestions from validation details
            suggestions = []
            validations = validation_results.get("validations", {})
            
            if not validations.get("numeric", {}).get("is_valid", True):
                suggestions.append("Ensure all numeric values are grounded in the source context")
            
            if not validations.get("quotes", {}).get("is_valid", True):
                suggestions.append("Verify all quoted text matches the source material exactly")
            
            if not validations.get("grounding", {}).get("is_valid", True):
                suggestions.append("Improve grounding of answer concepts in the provided context")
            
            # Calculate confidence based on validation results
            confidence = 1.0 if is_valid else 0.5
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                metadata=validation_results
            )
            
        except Exception as e:
            logger.error(f"Error in legacy QA validation: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Validation error: {str(e)}"],
                suggestions=["Check validation service configuration"],
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "legacy_qa_validation"


class EnhancedValidationStrategy(ValidationStrategy):
    """Enhanced validation strategy using the prompt validator."""
    
    def __init__(self, **kwargs):
        try:
            from .prompt_validator import PromptValidator
            from .hybrid_retriever import HybridRetriever
            
            # Initialize with a dummy retriever for validation
            self.retriever = HybridRetriever()
            self.validator = PromptValidator(self.retriever)
        except ImportError as e:
            logger.warning(f"Enhanced validation not available: {e}")
            self.validator = None
    
    async def validate_response(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate using the enhanced prompt validator."""
        
        if not self.validator:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=["Enhanced validation not available"],
                suggestions=["Use legacy validation strategy"],
                metadata={"error": "PromptValidator not initialized"}
            )
        
        try:
            # Create mock retrieval results for validation
            mock_results = [{
                "chunk": {"text": context, "sentiment": "neutral"},
                "score": 1.0
            }]
            
            # Use the prompt validator's validation logic
            validation_result = self.validator._validate_response(
                response=response,
                retrieval_results=mock_results,
                validation_rules={"evidence_required": True, "numeric_check": True}
            )
            
            return ValidationResult(
                is_valid=validation_result.is_valid,
                confidence=0.9 if validation_result.is_valid else 0.3,
                issues=validation_result.validation_errors,
                suggestions=[f"Missing: {elem}" for elem in validation_result.missing_elements],
                metadata={
                    "evidence_count": validation_result.evidence_count,
                    "has_evidence": validation_result.has_evidence,
                    "has_numeric": validation_result.has_required_numeric
                }
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced validation: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Enhanced validation error: {str(e)}"],
                suggestions=["Check enhanced validator configuration"],
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "enhanced_validation"


# ---------------------------------------------------------------------------
# Prompt Strategy Implementations
# ---------------------------------------------------------------------------

class DomainAgnosticPromptStrategy(PromptStrategy):
    """Prompt strategy using domain-agnostic templates."""
    
    def __init__(self, **kwargs):
        self.domain = kwargs.get("domain", "generic")
        
        # Basic prompt templates
        self.templates = {
            "system": (
                "You are a helpful AI assistant that answers questions based on provided context. "
                "Always cite your sources using {{source}} notation and be factual."
            ),
            "user": (
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Please provide a comprehensive answer based only on the information in the context above. "
                "Use {{source}} notation to cite relevant parts of the context."
            ),
            "format": (
                "Structure your response as follows:\n"
                "- Direct answer to the question\n"
                "- Supporting evidence from context with {{citations}}\n"
                "- Any limitations or uncertainties"
            )
        }
    
    async def build_prompt(
        self,
        question: str,
        context: str,
        domain: Optional[str] = None,
        **kwargs
    ) -> PromptResult:
        """Build domain-agnostic prompts."""
        
        try:
            # Use provided domain or default
            active_domain = domain or self.domain
            
            # Customize based on domain if needed
            system_prompt = self.templates["system"]
            if active_domain == "financial":
                system_prompt += " Focus on financial terminology and numerical accuracy."
            elif active_domain == "medical":
                system_prompt += " Use precise medical terminology and emphasize accuracy."
            
            # Build user prompt
            user_prompt = self.templates["user"].format(
                context=context,
                question=question
            )
            
            return PromptResult(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=self.templates["format"],
                metadata={
                    "domain": active_domain,
                    "strategy": "domain_agnostic",
                    "context_length": len(context),
                    "question_length": len(question)
                }
            )
            
        except Exception as e:
            logger.error(f"Error building domain-agnostic prompt: {e}")
            # Return fallback prompt
            return PromptResult(
                system_prompt="You are a helpful assistant.",
                user_prompt=f"Context: {context}\n\nQuestion: {question}",
                response_format="Provide a clear, factual answer.",
                metadata={"error": str(e), "fallback": True}
            )
    
    def get_strategy_name(self) -> str:
        return "domain_agnostic_prompt"


class EnhancedPromptStrategy(PromptStrategy):
    """Enhanced prompt strategy using the prompt validator system."""
    
    def __init__(self, **kwargs):
        try:
            from .prompt_validator import PromptValidator
            from .hybrid_retriever import HybridRetriever
            
            self.retriever = HybridRetriever()
            self.validator = PromptValidator(self.retriever)
        except ImportError as e:
            logger.warning(f"Enhanced prompt strategy not available: {e}")
            self.validator = None
    
    async def build_prompt(
        self,
        question: str,
        context: str,
        domain: Optional[str] = None,
        **kwargs
    ) -> PromptResult:
        """Build prompts using the enhanced prompt validator."""
        
        if not self.validator:
            # Fallback to basic prompt
            return PromptResult(
                system_prompt="You are a helpful assistant.",
                user_prompt=f"Context: {context}\n\nQuestion: {question}",
                response_format="Provide a clear answer with evidence.",
                metadata={"error": "Enhanced prompt validator not available", "fallback": True}
            )
        
        try:
            # Classify the question type
            response_type = self.validator.classify_response_type(question)
            
            # Get the appropriate template
            template = self.validator.prompt_templates.get(response_type)
            if not template:
                template = self.validator.prompt_templates[list(self.validator.prompt_templates.keys())[0]]
            
            # Build the prompt
            user_prompt = template.user_prompt.format(
                context=context,
                question=question
            )
            
            return PromptResult(
                system_prompt=template.system_prompt,
                user_prompt=user_prompt,
                response_format=template.response_format,
                metadata={
                    "response_type": response_type.value,
                    "strategy": "enhanced_prompt",
                    "validation_rules": template.validation_rules
                }
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced prompt strategy: {e}")
            # Return fallback
            return PromptResult(
                system_prompt="You are a helpful assistant that answers questions accurately.",
                user_prompt=f"Context: {context}\n\nQuestion: {question}",
                response_format="Provide a factual answer with evidence citations.",
                metadata={"error": str(e), "fallback": True}
            )
    
    def get_strategy_name(self) -> str:
        return "enhanced_prompt"


# ---------------------------------------------------------------------------
# Retrieval Strategy Implementations
# ---------------------------------------------------------------------------

class HybridRetrievalStrategy(RetrievalStrategy):
    """Retrieval strategy using the hybrid retriever."""
    
    def __init__(self, **kwargs):
        try:
            from .hybrid_retriever import HybridRetriever
            self.retriever = HybridRetriever()
        except ImportError as e:
            logger.warning(f"Hybrid retriever not available: {e}")
            self.retriever = None
    
    async def retrieve(
        self,
        query: str,
        transcript_id: Optional[str] = None,
        top_k: int = 5,
        **kwargs
    ) -> RetrievalResult:
        """Retrieve using the hybrid retriever."""
        
        if not self.retriever:
            return RetrievalResult(
                chunks=[],
                scores=[],
                total_found=0,
                strategy_used="hybrid_retrieval_unavailable",
                metadata={"error": "Hybrid retriever not available"}
            )
        
        try:
            # Use the hybrid retriever
            results = await self.retriever.retrieve(
                query=query,
                k=top_k,
                transcript_id=transcript_id
            )
            
            # Extract chunks and scores
            chunks = []
            scores = []
            
            for result in results:
                chunks.append({
                    "text": result.chunk.text,
                    "metadata": {
                        "chunk_id": result.chunk.id,
                        "transcript_id": result.chunk.transcript_id,
                        "position": result.chunk.position,
                        "sentiment": result.chunk.sentiment,
                        "entities": result.chunk.entities
                    }
                })
                scores.append(result.score)
            
            return RetrievalResult(
                chunks=chunks,
                scores=scores,
                total_found=len(chunks),
                strategy_used="hybrid_retrieval",
                metadata={
                    "query_length": len(query),
                    "transcript_id": transcript_id,
                    "top_k_requested": top_k
                }
            )
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return RetrievalResult(
                chunks=[],
                scores=[],
                total_found=0,
                strategy_used="hybrid_retrieval_error",
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "hybrid_retrieval"


class LegacyRetrievalStrategy(RetrievalStrategy):
    """Retrieval strategy using the legacy QA service methods."""
    
    def __init__(self, **kwargs):
        # This would wrap the existing retrieval methods from RetrievalQAService
        self.similarity_threshold = kwargs.get("similarity_threshold", 0.7)
    
    async def retrieve(
        self,
        query: str,
        transcript_id: Optional[str] = None,
        top_k: int = 5,
        **kwargs
    ) -> RetrievalResult:
        """Retrieve using legacy QA service methods."""
        
        try:
            # This would call the existing vector search methods
            # For now, return a mock implementation
            logger.info(f"Legacy retrieval for query: {query[:50]}...")
            
            # Simulate retrieval
            chunks = [
                {
                    "text": f"Mock chunk {i} for query: {query[:30]}...",
                    "metadata": {
                        "chunk_id": f"legacy_{i}",
                        "transcript_id": transcript_id or "unknown",
                        "position": i
                    }
                }
                for i in range(min(top_k, 3))  # Mock 3 results
            ]
            
            scores = [0.9, 0.8, 0.7][:len(chunks)]
            
            return RetrievalResult(
                chunks=chunks,
                scores=scores,
                total_found=len(chunks),
                strategy_used="legacy_retrieval",
                metadata={
                    "similarity_threshold": self.similarity_threshold,
                    "mock": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error in legacy retrieval: {e}")
            return RetrievalResult(
                chunks=[],
                scores=[],
                total_found=0,
                strategy_used="legacy_retrieval_error",
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "legacy_retrieval"


# ---------------------------------------------------------------------------
# Strategy Registration
# ---------------------------------------------------------------------------

def register_all_strategies():
    """Register all available strategy implementations."""
    
    registry = get_strategy_registry()
    
    # Register validation strategies
    registry.register_validation_strategy("legacy_qa", LegacyQAValidationStrategy)
    registry.register_validation_strategy("enhanced", EnhancedValidationStrategy)
    registry.register_validation_strategy("default", LegacyQAValidationStrategy)  # Default
    
    # Register prompt strategies
    registry.register_prompt_strategy("domain_agnostic", DomainAgnosticPromptStrategy)
    registry.register_prompt_strategy("enhanced", EnhancedPromptStrategy)
    registry.register_prompt_strategy("default", DomainAgnosticPromptStrategy)  # Default
    
    # Register retrieval strategies
    registry.register_retrieval_strategy("hybrid", HybridRetrievalStrategy)
    registry.register_retrieval_strategy("legacy", LegacyRetrievalStrategy)
    registry.register_retrieval_strategy("default", HybridRetrievalStrategy)  # Default
    
    logger.info("All strategy implementations registered")
    
    return registry


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------

def create_default_qa_service():
    """Create a QA service with default strategies."""
    
    from .strategy_interfaces import create_qa_service_with_strategies
    
    # Ensure strategies are registered
    register_all_strategies()
    
    return create_qa_service_with_strategies(
        validation_strategy_name="default",
        prompt_strategy_name="default",
        retrieval_strategy_name="default"
    )


def create_enhanced_qa_service():
    """Create a QA service with enhanced strategies."""
    
    from .strategy_interfaces import create_qa_service_with_strategies
    
    # Ensure strategies are registered
    register_all_strategies()
    
    return create_qa_service_with_strategies(
        validation_strategy_name="enhanced",
        prompt_strategy_name="enhanced",
        retrieval_strategy_name="hybrid"
    )


# Auto-register strategies when module is imported
register_all_strategies() 