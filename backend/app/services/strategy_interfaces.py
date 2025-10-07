"""Strategy Interfaces for Pluggable Components

This module defines interfaces for validation, prompt engineering, and retrieval
strategies that can be easily swapped without modifying the core QA service.

Key benefits:
- Pluggable validation strategies
- Swappable prompt engineering approaches  
- Different retrieval algorithms
- Easy A/B testing of strategies
- Clean separation of concerns
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Standardized validation result."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any] = None


@dataclass
class PromptResult:
    """Result from prompt engineering."""
    system_prompt: str
    user_prompt: str
    response_format: str
    metadata: Dict[str, Any] = None


@dataclass
class RetrievalResult:
    """Result from retrieval strategy."""
    chunks: List[Dict[str, Any]]
    scores: List[float]
    total_found: int
    strategy_used: str
    metadata: Dict[str, Any] = None


# ---------------------------------------------------------------------------
# Strategy Interfaces
# ---------------------------------------------------------------------------

class ValidationStrategy(ABC):
    """Abstract interface for validation strategies."""
    
    @abstractmethod
    async def validate_response(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate a generated response."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this validation strategy."""
        pass


class PromptStrategy(ABC):
    """Abstract interface for prompt engineering strategies."""
    
    @abstractmethod
    async def build_prompt(
        self,
        question: str,
        context: str,
        domain: Optional[str] = None,
        **kwargs
    ) -> PromptResult:
        """Build prompts for LLM generation."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this prompt strategy."""
        pass


class RetrievalStrategy(ABC):
    """Abstract interface for retrieval strategies."""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        transcript_id: Optional[str] = None,
        top_k: int = 5,
        **kwargs
    ) -> RetrievalResult:
        """Retrieve relevant chunks for a query."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this retrieval strategy."""
        pass


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

class StrategyRegistry:
    """Registry for managing different strategy implementations."""
    
    def __init__(self):
        self._validation_strategies: Dict[str, type] = {}
        self._prompt_strategies: Dict[str, type] = {}
        self._retrieval_strategies: Dict[str, type] = {}
    
    def register_validation_strategy(self, name: str, strategy_class: type) -> None:
        """Register a validation strategy."""
        self._validation_strategies[name] = strategy_class
    
    def register_prompt_strategy(self, name: str, strategy_class: type) -> None:
        """Register a prompt strategy."""
        self._prompt_strategies[name] = strategy_class
    
    def register_retrieval_strategy(self, name: str, strategy_class: type) -> None:
        """Register a retrieval strategy."""
        self._retrieval_strategies[name] = strategy_class
    
    def create_validation_strategy(self, name: str, **kwargs) -> ValidationStrategy:
        """Create a validation strategy instance."""
        if name not in self._validation_strategies:
            raise ValueError(f"Unknown validation strategy: {name}")
        return self._validation_strategies[name](**kwargs)
    
    def create_prompt_strategy(self, name: str, **kwargs) -> PromptStrategy:
        """Create a prompt strategy instance."""
        if name not in self._prompt_strategies:
            raise ValueError(f"Unknown prompt strategy: {name}")
        return self._prompt_strategies[name](**kwargs)
    
    def create_retrieval_strategy(self, name: str, **kwargs) -> RetrievalStrategy:
        """Create a retrieval strategy instance."""
        if name not in self._retrieval_strategies:
            raise ValueError(f"Unknown retrieval strategy: {name}")
        return self._retrieval_strategies[name](**kwargs)
    
    def list_strategies(self) -> Dict[str, List[str]]:
        """List all registered strategies."""
        return {
            "validation": list(self._validation_strategies.keys()),
            "prompt": list(self._prompt_strategies.keys()),
            "retrieval": list(self._retrieval_strategies.keys())
        }


# ---------------------------------------------------------------------------
# Global Registry Instance
# ---------------------------------------------------------------------------

_strategy_registry = StrategyRegistry()


def get_strategy_registry() -> StrategyRegistry:
    """Get the global strategy registry."""
    return _strategy_registry


# ---------------------------------------------------------------------------
# Strategy-Based QA Service Interface
# ---------------------------------------------------------------------------

class StrategyBasedQAService:
    """QA service that uses pluggable strategies."""
    
    def __init__(
        self,
        validation_strategy: ValidationStrategy,
        prompt_strategy: PromptStrategy,
        retrieval_strategy: RetrievalStrategy
    ):
        self.validation_strategy = validation_strategy
        self.prompt_strategy = prompt_strategy
        self.retrieval_strategy = retrieval_strategy
    
    async def answer_question(
        self,
        question: str,
        transcript_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Answer a question using the configured strategies."""
        
        # Step 1: Retrieve relevant context
        retrieval_result = await self.retrieval_strategy.retrieve(
            query=question,
            transcript_id=transcript_id,
            **kwargs
        )
        
        # Step 2: Build context string
        context = "\n\n".join([
            chunk.get("text", "") for chunk in retrieval_result.chunks
        ])
        
        # Step 3: Generate prompts
        prompt_result = await self.prompt_strategy.build_prompt(
            question=question,
            context=context,
            **kwargs
        )
        
        # Step 4: Generate response (would call LLM here)
        # For now, return a placeholder
        generated_response = "This would be the LLM-generated response"
        
        # Step 5: Validate response
        validation_result = await self.validation_strategy.validate_response(
            response=generated_response,
            context=context,
            question=question,
            **kwargs
        )
        
        return {
            "answer": generated_response,
            "validation": validation_result,
            "retrieval_info": {
                "strategy": retrieval_result.strategy_used,
                "chunks_found": len(retrieval_result.chunks),
                "total_available": retrieval_result.total_found
            },
            "prompt_info": {
                "strategy": self.prompt_strategy.get_strategy_name(),
                "metadata": prompt_result.metadata
            }
        }


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------

def create_qa_service_with_strategies(
    validation_strategy_name: str = "default",
    prompt_strategy_name: str = "default", 
    retrieval_strategy_name: str = "hybrid",
    **strategy_kwargs
) -> StrategyBasedQAService:
    """Factory function to create QA service with specific strategies."""
    
    registry = get_strategy_registry()
    
    validation_strategy = registry.create_validation_strategy(
        validation_strategy_name, 
        **strategy_kwargs.get("validation", {})
    )
    
    prompt_strategy = registry.create_prompt_strategy(
        prompt_strategy_name,
        **strategy_kwargs.get("prompt", {})
    )
    
    retrieval_strategy = registry.create_retrieval_strategy(
        retrieval_strategy_name,
        **strategy_kwargs.get("retrieval", {})
    )
    
    return StrategyBasedQAService(
        validation_strategy=validation_strategy,
        prompt_strategy=prompt_strategy,
        retrieval_strategy=retrieval_strategy
    ) 