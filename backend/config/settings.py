"""
Configuration settings for the enhanced domain-agnostic RAG system.

This module provides centralized configuration for:
- AI model selection (OpenAI, embedding models)
- Domain-specific configurations
- Retrieval pipeline parameters
- Validation and evaluation settings
"""

import os
from typing import Optional, Dict, Any

# =============================================================================
# AI Model Configuration
# =============================================================================

# Primary LLM for answer generation  
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

# Embedding model for semantic search
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# Cross-encoder model for re-ranking
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "intfloat/e5-mistral-7b-instruct")

# =============================================================================
# Domain Configuration
# =============================================================================

# Current domain type (generic, medical, legal, technical, etc.)
DOMAIN_TYPE = os.getenv("DOMAIN_TYPE", "generic")

# Path to domain configuration files
DOMAIN_CONFIG_PATH = os.getenv("DOMAIN_CONFIG_PATH", "config/domains")

# =============================================================================
# Retrieval Pipeline Configuration
# =============================================================================

# BM25 parameters
BM25_K1 = float(os.getenv("BM25_K1", "1.2"))  # Term frequency saturation point
BM25_B = float(os.getenv("BM25_B", "0.75"))   # Length normalization factor

# Retrieval parameters
INITIAL_RETRIEVAL_K = int(os.getenv("INITIAL_RETRIEVAL_K", "50"))  # BM25 candidates
CROSS_ENCODER_K = int(os.getenv("CROSS_ENCODER_K", "20"))          # Cross-encoder input
FINAL_RETRIEVAL_K = int(os.getenv("FINAL_RETRIEVAL_K", "10"))      # Final results

# MMR diversity parameter (0.0 = max diversity, 1.0 = max relevance)
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.6"))

# =============================================================================
# Chunking Configuration
# =============================================================================

# Chunk size parameters
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "500"))    # Characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))              # Characters
SENTENCES_PER_CHUNK = int(os.getenv("SENTENCES_PER_CHUNK", "4"))   # Sentences

# Token limits
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4000"))   # Max tokens for responses

# TextTiling parameters
TEXTTILING_W = int(os.getenv("TEXTTILING_W", "20"))     # Window size
TEXTTILING_K = int(os.getenv("TEXTTILING_K", "10"))     # Step size

# =============================================================================
# Validation Configuration
# =============================================================================

def get_validation_config() -> Dict[str, Any]:
    """
    Get validation configuration for prompt engineering and response validation.
    
    Returns:
        Dictionary containing validation settings
    """
    return {
        # Retry settings
        "max_retries": int(os.getenv("VALIDATION_MAX_RETRIES", "3")),
        
        # Evidence requirements
        "evidence_required": os.getenv("VALIDATION_EVIDENCE_REQUIRED", "true").lower() == "true",
        
        # Numeric validation
        "numeric_validation": os.getenv("VALIDATION_NUMERIC_CHECK", "true").lower() == "true",
        
        # Sentiment validation
        "sentiment_validation": os.getenv("VALIDATION_SENTIMENT_CHECK", "true").lower() == "true",
        
        # Response structure requirements
        "structured_format": os.getenv("VALIDATION_STRUCTURED_FORMAT", "true").lower() == "true",
        
        # Consistency checking
        "consistency_threshold": float(os.getenv("VALIDATION_CONSISTENCY_THRESHOLD", "0.8")),
        
        # Logging level for validation
        "validation_log_level": os.getenv("VALIDATION_LOG_LEVEL", "INFO")
    }

# =============================================================================
# PII Configuration
# =============================================================================

# Presidio PII detection
PII_DETECTION_ENABLED = os.getenv("PII_DETECTION_ENABLED", "true").lower() == "true"
PII_ENTITIES = os.getenv("PII_ENTITIES", "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,CREDIT_CARD,SSN").split(",")
PII_ANONYMIZATION_METHOD = os.getenv("PII_ANONYMIZATION_METHOD", "replace")  # replace, redact, hash

# =============================================================================
# Evaluation Configuration
# =============================================================================

# RAGAS metrics
RAGAS_METRICS = os.getenv("RAGAS_METRICS", "faithfulness,relevance,context_precision,answer_relevance").split(",")

# Accuracy thresholds
ACCURACY_THRESHOLD = float(os.getenv("ACCURACY_THRESHOLD", "0.9"))
FAITHFULNESS_THRESHOLD = float(os.getenv("FAITHFULNESS_THRESHOLD", "0.8"))

# =============================================================================
# Performance Configuration
# =============================================================================

# Caching
ENABLE_RETRIEVAL_CACHE = os.getenv("ENABLE_RETRIEVAL_CACHE", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# Batch processing
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
CROSS_ENCODER_BATCH_SIZE = int(os.getenv("CROSS_ENCODER_BATCH_SIZE", "16"))

# =============================================================================
# Helper Functions
# =============================================================================

def get_domain_config_path() -> str:
    """Get the path to the current domain configuration file."""
    return f"{DOMAIN_CONFIG_PATH}/{DOMAIN_TYPE}.yaml"

def get_model_config() -> Dict[str, str]:
    """Get the current model configuration."""
    return {
        "openai_model": OPENAI_MODEL_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "cross_encoder_model": CROSS_ENCODER_MODEL
    }

def get_retrieval_config() -> Dict[str, Any]:
    """Get the current retrieval pipeline configuration."""
    return {
        "bm25_k1": BM25_K1,
        "bm25_b": BM25_B,
        "initial_k": INITIAL_RETRIEVAL_K,
        "cross_encoder_k": CROSS_ENCODER_K,
        "final_k": FINAL_RETRIEVAL_K,
        "mmr_lambda": MMR_LAMBDA
    }

def get_pii_config() -> Dict[str, Any]:
    """Get the current PII configuration."""
    return {
        "enabled": PII_DETECTION_ENABLED,
        "entities": PII_ENTITIES,
        "anonymization_method": PII_ANONYMIZATION_METHOD
    } 