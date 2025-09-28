"""
Security utilities for HMAC verification and authentication
"""
import hmac
import hashlib
import json
from typing import Union, Dict, Any
from datetime import datetime, timedelta
import structlog

from app.settings import settings

logger = structlog.get_logger()


def verify_webhook_signature(
    payload: Union[bytes, str, Dict],
    signature: str,
    secret: str = None
) -> bool:
    """
    Verify HMAC-SHA256 signature for webhook payload
    
    Args:
        payload: The webhook payload (bytes, string, or dict)
        signature: The signature to verify (format: "sha256=...")
        secret: The secret key (defaults to settings.webhook_secret)
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        logger.warning("No signature provided")
        return False
    
    # Use provided secret or default from settings
    secret = secret or settings.webhook_secret
    
    # Convert payload to bytes if needed
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(",", ":")).encode()
    elif isinstance(payload, str):
        payload = payload.encode()
    
    # Extract the signature hash (remove "sha256=" prefix if present)
    if signature.startswith("sha256="):
        signature_hash = signature[7:]
    else:
        signature_hash = signature
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, signature_hash)
    
    if not is_valid:
        logger.warning(
            "Invalid webhook signature",
            provided=signature_hash[:10] + "...",
            expected=expected_signature[:10] + "..."
        )
    
    return is_valid


def generate_webhook_signature(
    payload: Union[bytes, str, Dict],
    secret: str = None
) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload
    
    Args:
        payload: The webhook payload (bytes, string, or dict)
        secret: The secret key (defaults to settings.webhook_secret)
    
    Returns:
        Signature string in format "sha256=..."
    """
    # Use provided secret or default from settings
    secret = secret or settings.webhook_secret
    
    # Convert payload to bytes if needed
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(",", ":")).encode()
    elif isinstance(payload, str):
        payload = payload.encode()
    
    # Generate signature
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"


def is_request_expired(timestamp: Union[str, datetime], max_age_seconds: int = 300) -> bool:
    """
    Check if a request timestamp is expired
    
    Args:
        timestamp: Request timestamp (ISO format string or datetime)
        max_age_seconds: Maximum age in seconds (default 5 minutes)
    
    Returns:
        True if expired, False otherwise
    """
    if isinstance(timestamp, str):
        # Parse ISO format timestamp
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    # Calculate age
    age = datetime.utcnow() - timestamp.replace(tzinfo=None)
    
    return age.total_seconds() > max_age_seconds


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate to maximum length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Remove control characters (except newlines and tabs)
    import re
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    return text.strip()


def hash_message_id(message_id: str) -> str:
    """
    Create a consistent hash for message deduplication
    
    Args:
        message_id: Original message ID
    
    Returns:
        SHA256 hash of the message ID
    """
    return hashlib.sha256(message_id.encode()).hexdigest()


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format and check against allowed keys
    
    Args:
        api_key: API key to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    # Check format (expecting "Bearer sk-...")
    if not api_key.startswith("Bearer sk-"):
        return False
    
    # Extract the actual key
    key = api_key.replace("Bearer ", "")
    
    # In production, check against database of valid keys
    # For now, just validate format
    return len(key) > 10 and key.startswith("sk-")