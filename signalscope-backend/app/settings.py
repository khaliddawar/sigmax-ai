"""
Application settings and configuration management
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = Field(default="SignalScope Backend")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    port: int = Field(default=8000)
    host: str = Field(default="0.0.0.0")
    
    # Security
    secret_key: str = Field(default="change-me-in-production")
    webhook_secret: str = Field(default="webhook-secret-key")
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080", "http://localhost:8000", "chrome-extension://*"])
    
    # Database
    supabase_url: Optional[str] = Field(default=None)
    supabase_key: Optional[str] = Field(default=None)
    supabase_service_key: Optional[str] = Field(default=None)
    supabase_anon_key: Optional[str] = Field(default=None)
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # LLM Providers
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    default_llm_provider: str = Field(default="openai")
    default_llm_model: str = Field(default="gpt-3.5-turbo")
    max_tokens_per_request: int = Field(default=4000)
    llm_temperature: float = Field(default=0.3)
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")
    
    # Batch Processing
    realtime_batch_seconds: int = Field(default=300)  # 5 minutes
    standard_batch_seconds: int = Field(default=900)  # 15 minutes
    archive_batch_seconds: int = Field(default=3600)  # 1 hour
    
    # Message Processing
    realtime_importance_threshold: int = Field(default=8)
    standard_importance_threshold: int = Field(default=5)
    max_messages_per_batch: int = Field(default=50)
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)
    
    # Email (Optional)
    email_enabled: bool = Field(default=False)
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    
    # Feature Flags
    enable_trading_signals: bool = Field(default=True)
    enable_sentiment_analysis: bool = Field(default=True)
    enable_llm_reports: bool = Field(default=False)
    enable_cache: bool = Field(default=True)
    
    # Telegram Configuration
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)
    telegram_enabled: bool = Field(default=False)
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Handle JSON-like string from env
            import json
            try:
                return json.loads(v)
            except:
                # Fallback to comma-separated
                return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Export commonly used settings
DEBUG = settings.debug
SECRET_KEY = settings.secret_key
REDIS_URL = settings.redis_url
SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key