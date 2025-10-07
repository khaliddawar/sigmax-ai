"""Unified Configuration with Pydantic BaseSettings

This module provides a single source of truth for all application configuration
using Pydantic BaseSettings for proper environment variable handling, validation,
and type safety.

Replaces both app/settings.py and config/settings.py with a unified approach.
"""
from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import BaseSettings, Field, validator
from pydantic.env_settings import SettingsSourceCallable


class ApplicationSettings(BaseSettings):
    """Unified application settings using Pydantic BaseSettings."""
    
    # =============================================================================
    # Environment & Deployment
    # =============================================================================
    
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # =============================================================================
    # API Configuration
    # =============================================================================
    
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # CORS & Security
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    frontend_url: Optional[str] = Field(default=None, env="FRONTEND_URL")
    chrome_extension_id: Optional[str] = Field(default=None, env="CHROME_EXTENSION_ID")
    
    @validator('allowed_hosts', pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    # =============================================================================
    # AI Model Configuration
    # =============================================================================
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL_NAME")
    openai_max_tokens: int = Field(default=4000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # Azure OpenAI
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_version: str = Field(default="2023-12-01-preview", env="AZURE_OPENAI_VERSION")
    
    # Embedding Models
    embedding_model: str = Field(default="text-embedding-3-large", env="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    
    # Cross-encoder for re-ranking
    cross_encoder_model: str = Field(default="intfloat/e5-mistral-7b-instruct", env="CROSS_ENCODER_MODEL")
    cross_encoder_batch_size: int = Field(default=16, env="CROSS_ENCODER_BATCH_SIZE")
    
    # =============================================================================
    # Database Configuration
    # =============================================================================
    
    # Supabase
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, env="SUPABASE_KEY")
    supabase_service_key: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_KEY")
    
    # Database connection
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # =============================================================================
    # Redis Configuration
    # =============================================================================
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_ssl: bool = Field(default=False, env="REDIS_SSL")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    @validator('redis_url', pre=True, always=True)
    def build_redis_url(cls, v, values):
        if v:
            return v
        
        # Build Redis URL from components
        host = values.get('redis_host', 'localhost')
        port = values.get('redis_port', 6379)
        password = values.get('redis_password')
        db = values.get('redis_db', 0)
        ssl_prefix = 'rediss' if values.get('redis_ssl', False) else 'redis'
        
        if password:
            return f"{ssl_prefix}://:{password}@{host}:{port}/{db}"
        else:
            return f"{ssl_prefix}://{host}:{port}/{db}"
    
    # =============================================================================
    # Email Configuration
    # =============================================================================
    
    # Postmark
    postmark_api_token: Optional[str] = Field(default=None, env="POSTMARK_API_TOKEN")
    postmark_sender_email: Optional[str] = Field(default=None, env="POSTMARK_SENDER_EMAIL")
    postmark_sender_name: str = Field(default="Simply", env="POSTMARK_SENDER_NAME")
    
    # SMTP (fallback)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # =============================================================================
    # Authentication & Security
    # =============================================================================
    
    # JWT
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Admin
    admin_secret: str = Field(default="change-me-in-production", env="ADMIN_SECRET")
    
    # Webhook Security
    fireflies_webhook_secret: Optional[str] = Field(default=None, env="FIREFLIES_WEBHOOK_SECRET")
    webhook_verify_signatures: bool = Field(default=False, env="WEBHOOK_VERIFY_SIGNATURES")
    
    # =============================================================================
    # Domain & Content Processing
    # =============================================================================
    
    # Domain configuration
    domain_type: str = Field(default="generic", env="DOMAIN_TYPE")
    domain_config_path: str = Field(default="config/domains", env="DOMAIN_CONFIG_PATH")
    
    # Content processing limits
    default_chunk_size: int = Field(default=1000, env="DEFAULT_CHUNK_SIZE")
    default_chunk_overlap: int = Field(default=200, env="DEFAULT_CHUNK_OVERLAP")
    max_discovery_chars: int = Field(default=500000, env="MAX_DISCOVERY_CHARS")
    max_synthesis_chars: int = Field(default=240000, env="MAX_SYNTHESIS_CHARS")
    max_safe_tokens: int = Field(default=4000, env="MAX_SAFE_TOKENS")
    chars_per_token: float = Field(default=3.5, env="CHARS_PER_TOKEN")
    
    # =============================================================================
    # Retrieval Configuration
    # =============================================================================
    
    # BM25 parameters
    bm25_k1: float = Field(default=1.2, env="BM25_K1")
    bm25_b: float = Field(default=0.75, env="BM25_B")
    
    # Retrieval parameters
    initial_retrieval_k: int = Field(default=50, env="INITIAL_RETRIEVAL_K")
    cross_encoder_k: int = Field(default=20, env="CROSS_ENCODER_K")
    final_retrieval_k: int = Field(default=10, env="FINAL_RETRIEVAL_K")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Hybrid search weights
    vector_weight: float = Field(default=0.7, env="VECTOR_WEIGHT")
    keyword_weight: float = Field(default=0.3, env="KEYWORD_WEIGHT")
    
    # =============================================================================
    # Caching & Performance
    # =============================================================================
    
    enable_retrieval_cache: bool = Field(default=True, env="ENABLE_RETRIEVAL_CACHE")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # Request limits
    max_context_length: int = Field(default=12000, env="MAX_CONTEXT_LENGTH")
    request_timeout_seconds: int = Field(default=30, env="REQUEST_TIMEOUT_SECONDS")
    
    # =============================================================================
    # Validation & Quality
    # =============================================================================
    
    # Accuracy thresholds
    accuracy_threshold: float = Field(default=0.9, env="ACCURACY_THRESHOLD")
    faithfulness_threshold: float = Field(default=0.8, env="FAITHFULNESS_THRESHOLD")
    
    # PII Detection
    pii_detection_enabled: bool = Field(default=True, env="PII_DETECTION_ENABLED")
    pii_entities: List[str] = Field(
        default=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "SSN"],
        env="PII_ENTITIES"
    )
    pii_anonymization_method: str = Field(default="replace", env="PII_ANONYMIZATION_METHOD")
    
    @validator('pii_entities', pre=True)
    def parse_pii_entities(cls, v):
        if isinstance(v, str):
            return [entity.strip() for entity in v.split(",") if entity.strip()]
        return v
    
    # =============================================================================
    # External Services
    # =============================================================================
    
    # Fireflies API
    fireflies_api_key: Optional[str] = Field(default=None, env="FIREFLIES_API_KEY")
    
    # Slack
    slack_app_token: Optional[str] = Field(default=None, env="SLACK_APP_TOKEN")
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    
    # =============================================================================
    # Feature Flags
    # =============================================================================
    
    use_mock_responses: bool = Field(default=False, env="USE_MOCK_RESPONSES")
    use_mock_users: bool = Field(default=False, env="USE_MOCK_USERS")
    use_unified_transcript_handler: bool = Field(default=False, env="USE_UNIFIED_TRANSCRIPT_HANDLER")
    enable_observability: bool = Field(default=True, env="ENABLE_OBSERVABILITY")
    
    # =============================================================================
    # Configuration
    # =============================================================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True
        
        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            """Customize settings sources priority."""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )
    
    # =============================================================================
    # Computed Properties
    # =============================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def docs_enabled(self) -> bool:
        """Check if API docs should be enabled."""
        return self.is_development
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get AI model configuration."""
        return {
            "openai_model": self.openai_model_name,
            "embedding_model": self.embedding_model,
            "cross_encoder_model": self.cross_encoder_model,
            "max_tokens": self.openai_max_tokens,
            "temperature": self.openai_temperature
        }
    
    def get_retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration."""
        return {
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "initial_k": self.initial_retrieval_k,
            "cross_encoder_k": self.cross_encoder_k,
            "final_k": self.final_retrieval_k,
            "similarity_threshold": self.similarity_threshold,
            "vector_weight": self.vector_weight,
            "keyword_weight": self.keyword_weight
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration."""
        return {
            "accuracy_threshold": self.accuracy_threshold,
            "faithfulness_threshold": self.faithfulness_threshold,
            "pii_detection_enabled": self.pii_detection_enabled,
            "pii_entities": self.pii_entities,
            "pii_anonymization_method": self.pii_anonymization_method
        }


# =============================================================================
# Global Settings Instance
# =============================================================================

_settings: Optional[ApplicationSettings] = None


def get_settings() -> ApplicationSettings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    
    if _settings is None:
        _settings = ApplicationSettings()
    
    return _settings


def reload_settings() -> ApplicationSettings:
    """Reload settings (useful for testing)."""
    global _settings
    _settings = ApplicationSettings()
    return _settings


# =============================================================================
# Legacy Compatibility Functions
# =============================================================================

def get_model_config() -> Dict[str, str]:
    """Legacy compatibility function."""
    settings = get_settings()
    return settings.get_model_config()


def get_retrieval_config() -> Dict[str, Any]:
    """Legacy compatibility function."""
    settings = get_settings()
    return settings.get_retrieval_config()


def get_validation_config() -> Dict[str, Any]:
    """Legacy compatibility function."""
    settings = get_settings()
    return settings.get_validation_config()


def get_domain_config_path() -> str:
    """Legacy compatibility function."""
    settings = get_settings()
    return f"{settings.domain_config_path}/{settings.domain_type}.yaml"


def get_pii_config() -> Dict[str, Any]:
    """Legacy compatibility function."""
    settings = get_settings()
    return settings.get_validation_config()


# =============================================================================
# Environment Variable Validation
# =============================================================================

def validate_required_settings() -> Dict[str, Any]:
    """Validate that required settings are present for the current environment."""
    settings = get_settings()
    issues = []
    warnings = []
    
    # Required for all environments
    if not settings.jwt_secret_key:
        issues.append("JWT_SECRET_KEY is required for authentication")
    
    # Production-specific requirements
    if settings.is_production:
        if not settings.supabase_url or not settings.supabase_key:
            issues.append("SUPABASE_URL and SUPABASE_KEY are required in production")
        
        if not settings.openai_api_key:
            issues.append("OPENAI_API_KEY is required in production")
        
        if settings.admin_secret == "change-me-in-production":
            issues.append("ADMIN_SECRET must be changed in production")
        
        if not settings.postmark_api_token:
            warnings.append("POSTMARK_API_TOKEN not set - email notifications disabled")
    
    # Development warnings
    if settings.is_development:
        if not settings.openai_api_key:
            warnings.append("OPENAI_API_KEY not set - some features may not work")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "environment": settings.environment
    } 