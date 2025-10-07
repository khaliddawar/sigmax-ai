"""Application-level settings

This wrapper delegates *shared* configuration (model names, chunk limits
etc.) to **config.settings** so that we have a single source of truth.
It still exposes the same attributes that other modules import, but the
values now come straight from the central settings module – avoiding
future divergence.
"""
from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

# Load .env file first so that config.settings picks them up as well
load_dotenv()

# Import central settings (single source of truth)
from config import settings as cfg  # noqa: E402  pylint: disable=wrong-import-position

# ---------------------------------------------------------------------------
# Direct re-exports – keep legacy variable names intact ----------------------
# ---------------------------------------------------------------------------

# API / model
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = cfg.OPENAI_MODEL_NAME  # delegated

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Postmark Email
POSTMARK_API_TOKEN = os.getenv("POSTMARK_API_TOKEN")
POSTMARK_SENDER_EMAIL = os.getenv("POSTMARK_SENDER_EMAIL")
POSTMARK_SENDER_NAME = os.getenv("POSTMARK_SENDER_NAME", "TubeVibe")

# Content Processing limits – delegate where overlaps exist
MAX_DISCOVERY_CHARS = int(os.getenv("MAX_DISCOVERY_CHARS", str(cfg.DEFAULT_CHUNK_SIZE * 500)))
MAX_SYNTHESIS_CHARS = int(os.getenv("MAX_SYNTHESIS_CHARS", str(cfg.DEFAULT_CHUNK_SIZE * 240)))
MAX_SAFE_TOKENS = int(os.getenv("MAX_SAFE_TOKENS", str(cfg.DEFAULT_MAX_TOKENS)))
CHARS_PER_TOKEN = float(os.getenv("CHARS_PER_TOKEN", "3.5"))

# Security / misc
CHROME_EXTENSION_ID = os.getenv("CHROME_EXTENSION_ID")
FRONTEND_URL = os.getenv("FRONTEND_URL")
ALLOWED_HOSTS: List[str] = (
    os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else ["*"]
)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Development settings
DEVELOPMENT_MODE: bool = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
ALLOW_TEST_EMAILS: bool = os.getenv("ALLOW_TEST_EMAILS", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Helper factory – still returns a Settings object but now sources central cfg
# ---------------------------------------------------------------------------

def get_settings():  # noqa: D401 – simple factory
    """Return a composite Settings object for legacy callers."""

    class Settings:  # pylint: disable=too-few-public-methods
        # API / model
        openai_api_key = OPENAI_API_KEY
        openai_model_name = OPENAI_MODEL_NAME

        # Redis
        redis_host = REDIS_HOST
        redis_port = REDIS_PORT
        redis_password = REDIS_PASSWORD
        redis_db = REDIS_DB

        # Postmark
        postmark_api_token = POSTMARK_API_TOKEN
        postmark_sender_email = POSTMARK_SENDER_EMAIL
        postmark_sender_name = POSTMARK_SENDER_NAME

        # Content Processing
        max_discovery_chars = MAX_DISCOVERY_CHARS
        max_synthesis_chars = MAX_SYNTHESIS_CHARS
        max_safe_tokens = MAX_SAFE_TOKENS
        chars_per_token = CHARS_PER_TOKEN

        # Security
        chrome_extension_id = CHROME_EXTENSION_ID
        frontend_url = FRONTEND_URL
        allowed_hosts = ALLOWED_HOSTS
        environment = ENVIRONMENT

        # JWT
        jwt_secret_key = JWT_SECRET_KEY
        jwt_algorithm = JWT_ALGORITHM
        jwt_expiration_hours = JWT_EXPIRATION_HOURS

    return Settings() 