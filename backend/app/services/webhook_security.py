"""
Webhook Security Service

Enhanced webhook security validation based on industry best practices,
inspired by Firefly III webhook implementation patterns.

Key Features:
- Timestamp-based signature validation (prevents replay attacks)
- Multiple signature format support
- Comprehensive logging for debugging
- No fallback arrangements - explicit failures only
"""

import hashlib
import hmac
import time
import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class WebhookSecurityValidator:
    """
    Webhook security validator with timestamp-based signature verification.
    
    Supports multiple webhook signature formats:
    - Fireflies format (if they implement signatures)
    - GitHub/Stripe style (x-hub-signature-256)
    - Custom timestamp-embedded signatures (t=timestamp,v1=hash)
    """
    
    def __init__(self, webhook_secret: str, max_timestamp_age: int = 300):
        """
        Initialize webhook security validator.
        
        Args:
            webhook_secret: Secret key for HMAC validation
            max_timestamp_age: Maximum age of timestamp in seconds (default: 5 minutes)
        """
        self.webhook_secret = webhook_secret
        self.max_timestamp_age = max_timestamp_age
    
    def extract_signature_components(self, signature_header: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract timestamp and hash from signature header.
        
        Supports formats:
        - "t=1234567890,v1=hash_value" (Stripe/Firefly III style)
        - "sha256=hash_value" (GitHub style - no timestamp)
        
        Args:
            signature_header: Raw signature header value
            
        Returns:
            Tuple of (timestamp, signature_hash) or (None, signature_hash)
        """
        if not signature_header:
            return None, None
        
        # Handle comma-separated format: "t=timestamp,v1=hash"
        if ',' in signature_header and 't=' in signature_header:
            timestamp = None
            signature_hash = None
            
            parts = signature_header.split(',')
            for part in parts:
                part = part.strip()
                if part.startswith('t='):
                    timestamp = part[2:]  # Remove 't=' prefix
                elif part.startswith('v1='):
                    signature_hash = part[3:]  # Remove 'v1=' prefix
                elif part.startswith('sha256='):
                    signature_hash = part[7:]  # Remove 'sha256=' prefix
            
            return timestamp, signature_hash
        
        # Handle simple format: "sha256=hash"
        elif signature_header.startswith('sha256='):
            return None, signature_header[7:]
        
        # Handle raw hash (no prefix)
        else:
            return None, signature_header
    
    def validate_timestamp(self, timestamp_str: str) -> bool:
        """
        Validate that timestamp is recent enough to prevent replay attacks.
        
        Args:
            timestamp_str: Unix timestamp as string
            
        Returns:
            True if timestamp is valid and recent
        """
        try:
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            age = current_time - timestamp
            
            if age < 0:
                logger.warning(f"Timestamp is in the future: {timestamp} vs {current_time}")
                return False
            
            if age > self.max_timestamp_age:
                logger.warning(f"Timestamp too old: {age} seconds (max: {self.max_timestamp_age})")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timestamp format: {timestamp_str} - {e}")
            return False
    
    def calculate_signature(self, payload: str, timestamp: Optional[str] = None) -> str:
        """
        Calculate HMAC signature for payload.
        
        Args:
            payload: Raw request body as string
            timestamp: Optional timestamp for timestamp-based signatures
            
        Returns:
            Calculated HMAC signature (hex)
        """
        if timestamp:
            # Timestamp-based signature: "timestamp.payload"
            message = f"{timestamp}.{payload}"
        else:
            # Simple payload signature
            message = payload
        
        # Use SHA-256 HMAC (more common than SHA3-256)
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def validate_signature(self, 
                         signature_header: str, 
                         payload: str,
                         require_timestamp: bool = False) -> Dict[str, Any]:
        """
        Validate webhook signature with comprehensive logging.
        
        Args:
            signature_header: Raw signature header value
            payload: Raw request body as string
            require_timestamp: Whether to require timestamp-based signatures
            
        Returns:
            Validation result with detailed information
        """
        result = {
            "valid": False,
            "timestamp": None,
            "signature_hash": None,
            "calculated_hash": None,
            "error": None,
            "debug_info": {}
        }
        
        try:
            # Extract components
            timestamp, signature_hash = self.extract_signature_components(signature_header)
            
            result["timestamp"] = timestamp
            result["signature_hash"] = signature_hash
            result["debug_info"]["signature_header"] = signature_header
            result["debug_info"]["payload_length"] = len(payload)
            
            # Validate signature hash exists
            if not signature_hash:
                result["error"] = "No signature hash found in header"
                return result
            
            # Validate timestamp if required or present
            if require_timestamp and not timestamp:
                result["error"] = "Timestamp required but not found in signature"
                return result
            
            if timestamp and not self.validate_timestamp(timestamp):
                result["error"] = "Invalid or expired timestamp"
                return result
            
            # Calculate expected signature
            calculated_hash = self.calculate_signature(payload, timestamp)
            result["calculated_hash"] = calculated_hash
            
            # Compare signatures (constant-time comparison)
            if hmac.compare_digest(calculated_hash, signature_hash):
                result["valid"] = True
                logger.info(f"Webhook signature validation successful (timestamp: {timestamp})")
            else:
                result["error"] = "Signature mismatch"
                logger.warning(f"Webhook signature validation failed - calculated: {calculated_hash[:8]}..., received: {signature_hash[:8]}...")
            
            return result
            
        except Exception as e:
            result["error"] = f"Signature validation error: {str(e)}"
            logger.error(f"Webhook signature validation exception: {e}")
            return result
    
    def get_webhook_timestamp(self, signature_header: str) -> Optional[datetime]:
        """
        Extract webhook timestamp from signature header.
        
        This is the key insight from Firefly III - timestamps come from
        the signature header, not the payload!
        
        Args:
            signature_header: Raw signature header value
            
        Returns:
            Datetime object if timestamp found, None otherwise
        """
        timestamp_str, _ = self.extract_signature_components(signature_header)
        
        if not timestamp_str:
            return None
        
        try:
            timestamp = int(timestamp_str)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse timestamp {timestamp_str}: {e}")
            return None

def create_webhook_validator(webhook_secret: Optional[str]) -> Optional[WebhookSecurityValidator]:
    """
    Factory function to create webhook validator.
    
    Args:
        webhook_secret: Webhook secret key
        
    Returns:
        WebhookSecurityValidator instance or None if no secret provided
    """
    if not webhook_secret:
        logger.warning("No webhook secret provided - signature validation disabled")
        return None
    
    return WebhookSecurityValidator(webhook_secret) 