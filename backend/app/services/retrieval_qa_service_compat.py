"""Compatibility Layer for Retrieval QA Service

This module provides a bridge between the new modular retrieval services
and the existing RetrievalQAService API. It allows for gradual migration
while maintaining backward compatibility.

Key responsibilities:
- API compatibility with existing RetrievalQAService
- Gradual migration path from monolithic to modular
- Fallback to original implementation when needed
- Performance comparison between old and new implementations
"""
from __future__ import annotations

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union

# Import original service
from .retrieval_qa_service import RetrievalQAService

# Import new modular components
from .retrieval.coordinator import RetrievalCoordinator, RetrievalConfig, RetrievalContext
from .retrieval.vector import VectorSearchEngine, VectorSearchConfig, create_vector_search_engine
from .retrieval.rerank import HybridReranker, create_default_reranker
from .retrieval.prompts import PromptGenerator, create_default_prompt_generator
from .retrieval.validation import CompositeValidator, create_default_validator

logger = logging.getLogger("retrieval-qa-compat")


class RetrievalQAServiceCompat:
    """
    Compatibility layer that can use either the original monolithic service
    or the new modular architecture, with gradual migration capabilities.
    """
    
    def __init__(
        self, 
        embedding_service,
        storage_service=None,
        file_storage_service=None,
        enable_new_architecture: bool = False,
        fallback_to_original: bool = True
    ):
        """
        Initialize compatibility layer.
        
        Args:
            embedding_service: Embedding service instance
            storage_service: Storage service instance
            file_storage_service: File storage service instance
            enable_new_architecture: Whether to use new modular architecture
            fallback_to_original: Whether to fallback to original on errors
        """
        self.embedding_service = embedding_service
        self.storage_service = storage_service
        self.file_storage_service = file_storage_service
        self.enable_new_architecture = enable_new_architecture
        self.fallback_to_original = fallback_to_original
        
        # Initialize original service (always available as fallback)
        self.original_service = RetrievalQAService(
            embedding_service=embedding_service,
            storage_service=storage_service,
            file_storage_service=file_storage_service
        )
        
        # Initialize new modular architecture if enabled
        self.modular_coordinator = None
        if enable_new_architecture:
            try:
                self._initialize_modular_architecture()
                logger.info("New modular architecture initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize modular architecture: {e}")
                if not fallback_to_original:
                    raise
                logger.info("Will use original service as fallback")
        
        # Performance tracking
        self.performance_metrics = {
            "original_calls": 0,
            "modular_calls": 0,
            "original_avg_time": 0.0,
            "modular_avg_time": 0.0,
            "fallback_count": 0
        }
    
    def _initialize_modular_architecture(self):
        """Initialize the new modular architecture components."""
        
        # Create vector search engine
        vector_config = VectorSearchConfig(
            similarity_threshold=0.1,
            max_results=10,
            enable_reranking=True
        )
        vector_engine = create_vector_search_engine(
            storage_service=self.storage_service,
            config=vector_config
        )
        
        # Create other components
        reranker = create_default_reranker()
        prompt_generator = create_default_prompt_generator()
        validator = create_default_validator()
        
        # Create coordinator
        retrieval_config = RetrievalConfig(
            max_results=10,
            similarity_threshold=0.1,
            enable_reranking=True,
            enable_validation=True,
            enable_optimization=True
        )
        
        self.modular_coordinator = RetrievalCoordinator(
            vector_engine=vector_engine,
            reranker=reranker,
            prompt_generator=prompt_generator,
            validator=validator,
            config=retrieval_config
        )
    
    async def answer_question(
        self,
        question: str,
        transcript_id: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Answer a question using either the new modular architecture or original service.
        
        This method maintains the same API as the original RetrievalQAService.answer_question
        while potentially using the new modular implementation.
        """
        
        start_time = time.time()
        
        # Decide which implementation to use
        use_modular = (
            self.enable_new_architecture and 
            self.modular_coordinator is not None
        )
        
        if use_modular:
            try:
                logger.debug("Using new modular architecture")
                result = await self._answer_with_modular_architecture(
                    question, transcript_id, top_k, similarity_threshold
                )
                
                # Track performance
                processing_time = time.time() - start_time
                self._update_performance_metrics("modular", processing_time)
                
                return result
                
            except Exception as e:
                logger.error(f"Modular architecture failed: {e}")
                
                if self.fallback_to_original:
                    logger.info("Falling back to original service")
                    self.performance_metrics["fallback_count"] += 1
                    # Fall through to original implementation
                else:
                    raise
        
        # Use original implementation
        logger.debug("Using original monolithic service")
        result = await self.original_service.answer_question(
            question, transcript_id, top_k, similarity_threshold
        )
        
        # Track performance
        processing_time = time.time() - start_time
        self._update_performance_metrics("original", processing_time)
        
        return result
    
    async def _answer_with_modular_architecture(
        self,
        question: str,
        transcript_id: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Answer question using the new modular architecture."""
        
        # Create retrieval context
        context = RetrievalContext(
            metadata={
                "transcript_id": transcript_id,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
        )
        
        # Create a simple LLM service adapter for the coordinator
        llm_service = LLMServiceAdapter(self.original_service)
        
        # Use the modular coordinator
        result = await self.modular_coordinator.retrieve_and_answer(
            question=question,
            context=context,
            llm_service=llm_service,
            embedding_service=self.embedding_service
        )
        
        # Convert modular result to original API format
        return {
            "success": True,
            "answer": result.answer,
            "sources": result.sources,
            "confidence": result.confidence_score,
            "validation": result.validation_results.__dict__ if result.validation_results else None,
            "processing_time": result.performance_metrics.get("response_time", 0.0),
            "metadata": {
                "architecture": "modular",
                "prompt_metadata": result.prompt_metadata,
                "performance_metrics": result.performance_metrics
            }
        }
    
    async def extract_key_points(self, transcript_id: str) -> Dict[str, Any]:
        """Extract key points - delegates to original service for now."""
        return await self.original_service.extract_key_points(transcript_id)
    
    def _update_performance_metrics(self, implementation: str, processing_time: float):
        """Update performance tracking metrics."""
        
        if implementation == "original":
            self.performance_metrics["original_calls"] += 1
            current_avg = self.performance_metrics["original_avg_time"]
            call_count = self.performance_metrics["original_calls"]
            
            # Update rolling average
            self.performance_metrics["original_avg_time"] = (
                (current_avg * (call_count - 1) + processing_time) / call_count
            )
        
        elif implementation == "modular":
            self.performance_metrics["modular_calls"] += 1
            current_avg = self.performance_metrics["modular_avg_time"]
            call_count = self.performance_metrics["modular_calls"]
            
            # Update rolling average
            self.performance_metrics["modular_avg_time"] = (
                (current_avg * (call_count - 1) + processing_time) / call_count
            )
    
    def get_performance_comparison(self) -> Dict[str, Any]:
        """Get performance comparison between implementations."""
        
        return {
            "original_service": {
                "calls": self.performance_metrics["original_calls"],
                "avg_response_time": self.performance_metrics["original_avg_time"],
                "total_time": (
                    self.performance_metrics["original_calls"] * 
                    self.performance_metrics["original_avg_time"]
                )
            },
            "modular_service": {
                "calls": self.performance_metrics["modular_calls"],
                "avg_response_time": self.performance_metrics["modular_avg_time"],
                "total_time": (
                    self.performance_metrics["modular_calls"] * 
                    self.performance_metrics["modular_avg_time"]
                )
            },
            "fallback_count": self.performance_metrics["fallback_count"],
            "architecture_enabled": self.enable_new_architecture,
            "fallback_enabled": self.fallback_to_original
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on both implementations."""
        
        health_status = {
            "overall_status": "healthy",
            "original_service": {"status": "unknown"},
            "modular_service": {"status": "unknown"}
        }
        
        # Check original service
        try:
            if hasattr(self.original_service, 'initialized') and self.original_service.initialized:
                health_status["original_service"] = {"status": "healthy"}
            else:
                health_status["original_service"] = {"status": "not_initialized"}
        except Exception as e:
            health_status["original_service"] = {"status": "unhealthy", "error": str(e)}
        
        # Check modular service
        if self.modular_coordinator:
            try:
                modular_health = await self.modular_coordinator.health_check()
                health_status["modular_service"] = modular_health
            except Exception as e:
                health_status["modular_service"] = {"status": "unhealthy", "error": str(e)}
        else:
            health_status["modular_service"] = {"status": "not_enabled"}
        
        # Determine overall status
        if (health_status["original_service"]["status"] == "unhealthy" and 
            health_status["modular_service"]["status"] == "unhealthy"):
            health_status["overall_status"] = "unhealthy"
        elif (health_status["original_service"]["status"] in ["unhealthy", "not_initialized"] and
              health_status["modular_service"]["status"] in ["unhealthy", "not_enabled"]):
            health_status["overall_status"] = "degraded"
        
        return health_status
    
    async def close(self):
        """Clean up resources."""
        if self.original_service:
            await self.original_service.close()


class LLMServiceAdapter:
    """Adapter to make the original service compatible with the modular coordinator."""
    
    def __init__(self, original_service: RetrievalQAService):
        self.original_service = original_service
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = None
    ) -> str:
        """Generate response using the original service's LLM capabilities."""
        
        try:
            # Extract question from user prompt (simple extraction)
            question_match = user_prompt.split("Question:")
            if len(question_match) > 1:
                question = question_match[1].strip().split("\n")[0]
            else:
                question = "Please provide information based on the context."
            
            # Extract context from user prompt
            context_match = user_prompt.split("Context:")
            if len(context_match) > 1:
                context = context_match[1].split("Question:")[0].strip()
            else:
                context = ""
            
            # Use the original service's answer generation method
            if hasattr(self.original_service, '_generate_answer'):
                response = await self.original_service._generate_answer(question, context)
                return response.get("answer", "No response generated")
            else:
                # Fallback response
                return "I apologize, but I cannot generate a response at this time."
                
        except Exception as e:
            logger.error(f"LLM service adapter failed: {e}")
            return "I apologize, but I encountered an error while generating a response."


# Factory function for easy instantiation
def create_compatible_qa_service(
    embedding_service,
    storage_service=None,
    file_storage_service=None,
    enable_new_architecture: bool = False,
    fallback_to_original: bool = True
) -> RetrievalQAServiceCompat:
    """
    Create a compatible QA service with optional new architecture.
    
    Args:
        embedding_service: Embedding service instance
        storage_service: Storage service instance  
        file_storage_service: File storage service instance
        enable_new_architecture: Whether to enable the new modular architecture
        fallback_to_original: Whether to fallback to original on errors
        
    Returns:
        RetrievalQAServiceCompat instance
    """
    return RetrievalQAServiceCompat(
        embedding_service=embedding_service,
        storage_service=storage_service,
        file_storage_service=file_storage_service,
        enable_new_architecture=enable_new_architecture,
        fallback_to_original=fallback_to_original
    ) 