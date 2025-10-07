"""
Webhook Testing Utilities

Based on the Firefly III webhook repository patterns:
https://github.com/akyrey/firefly-iii-webhooks

Provides utilities for testing webhook signature validation
and generating test signatures for development.
"""

import hashlib
import hmac
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

def generate_firefly_signature(payload: str, webhook_secret: str, timestamp: Optional[int] = None) -> str:
    """
    Generate a Firefly III style webhook signature.
    
    Based on the official Firefly III webhook implementation:
    - Format: "t=timestamp,v1=hash"
    - Payload construction: "timestamp.body"
    - Algorithm: HMAC-SHA256 (we use SHA-256 instead of SHA3-256 for compatibility)
    
    Args:
        payload: Raw JSON payload as string
        webhook_secret: Secret key for HMAC
        timestamp: Unix timestamp (defaults to current time)
        
    Returns:
        Signature string in format "t=timestamp,v1=hash"
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    # Construct message as "timestamp.payload" (Firefly III format)
    message = f"{timestamp}.{payload}"
    
    # Calculate HMAC-SHA256 signature
    signature_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Return in Firefly III format
    return f"t={timestamp},v1={signature_hash}"

def generate_github_signature(payload: str, webhook_secret: str) -> str:
    """
    Generate a GitHub style webhook signature.
    
    Args:
        payload: Raw JSON payload as string
        webhook_secret: Secret key for HMAC
        
    Returns:
        Signature string in format "sha256=hash"
    """
    signature_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature_hash}"

def create_test_fireflies_webhook(meeting_id: str = "test_meeting_123", 
                                event_type: str = "Transcription completed",
                                client_reference_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a test Fireflies webhook payload.
    
    Based on the documented Fireflies webhook format:
    {
        "meetingId": "ASxwZxCstx",
        "eventType": "Transcription completed", 
        "clientReferenceId": "be582c46-4ac9-4565-9ba6-6ab4264496a8"
    }
    
    Args:
        meeting_id: Meeting identifier
        event_type: Type of event
        client_reference_id: Optional client reference
        
    Returns:
        Dictionary representing Fireflies webhook payload
    """
    payload = {
        "meetingId": meeting_id,
        "eventType": event_type
    }
    
    if client_reference_id:
        payload["clientReferenceId"] = client_reference_id
    
    return payload

def create_test_webhook_request(payload: Dict[str, Any], 
                              webhook_secret: str,
                              signature_style: str = "firefly") -> Dict[str, Any]:
    """
    Create a complete test webhook request with proper signatures.
    
    Args:
        payload: Webhook payload dictionary
        webhook_secret: Secret for signature generation
        signature_style: "firefly", "github", or "both"
        
    Returns:
        Dictionary with payload, headers, and raw_body for testing
    """
    # Convert payload to JSON string
    raw_body = json.dumps(payload, separators=(',', ':'))
    
    headers = {
        "content-type": "application/json",
        "user-agent": "Fireflies-Webhook/1.0"
    }
    
    # Generate signatures based on style
    if signature_style in ["firefly", "both"]:
        firefly_sig = generate_firefly_signature(raw_body, webhook_secret)
        headers["signature"] = firefly_sig
    
    if signature_style in ["github", "both"]:
        github_sig = generate_github_signature(raw_body, webhook_secret)
        headers["x-hub-signature-256"] = github_sig
    
    return {
        "payload": payload,
        "raw_body": raw_body,
        "headers": headers,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def validate_webhook_signature_test(raw_body: str, 
                                  signature_header: str, 
                                  webhook_secret: str) -> Dict[str, Any]:
    """
    Test webhook signature validation using our WebhookSecurityValidator.
    
    Args:
        raw_body: Raw request body as string
        signature_header: Signature header value
        webhook_secret: Secret key for validation
        
    Returns:
        Validation result dictionary
    """
    from services.webhook_security import create_webhook_validator
    
    validator = create_webhook_validator(webhook_secret)
    if not validator:
        return {"error": "Failed to create validator"}
    
    return validator.validate_signature(signature_header, raw_body)

# Test data based on Firefly III webhook repository examples
TEST_WEBHOOK_SECRET = "abcdef"
TEST_PAYLOAD = {"meetingId": "ASxwZxCstx", "eventType": "Transcription completed"}
TEST_RAW_BODY = '{"meetingId":"ASxwZxCstx","eventType":"Transcription completed"}'

def run_signature_validation_tests():
    """
    Run comprehensive signature validation tests.
    
    Tests our implementation against known good signatures
    from the Firefly III webhook repository.
    """
    print("🧪 Running Webhook Signature Validation Tests")
    print("=" * 50)
    
    # Test 1: Firefly III style signature
    print("\n1. Testing Firefly III Style Signature")
    firefly_sig = generate_firefly_signature(TEST_RAW_BODY, TEST_WEBHOOK_SECRET)
    print(f"Generated signature: {firefly_sig}")
    
    result = validate_webhook_signature_test(TEST_RAW_BODY, firefly_sig, TEST_WEBHOOK_SECRET)
    print(f"Validation result: {result}")
    print(f"✅ Valid: {result.get('valid', False)}")
    
    # Test 2: GitHub style signature  
    print("\n2. Testing GitHub Style Signature")
    github_sig = generate_github_signature(TEST_RAW_BODY, TEST_WEBHOOK_SECRET)
    print(f"Generated signature: {github_sig}")
    
    result = validate_webhook_signature_test(TEST_RAW_BODY, github_sig, TEST_WEBHOOK_SECRET)
    print(f"Validation result: {result}")
    print(f"✅ Valid: {result.get('valid', False)}")
    
    # Test 3: Invalid signature
    print("\n3. Testing Invalid Signature")
    invalid_sig = "t=1234567890,v1=invalid_hash"
    result = validate_webhook_signature_test(TEST_RAW_BODY, invalid_sig, TEST_WEBHOOK_SECRET)
    print(f"Validation result: {result}")
    print(f"❌ Valid: {result.get('valid', False)} (Expected: False)")
    
    # Test 4: Expired timestamp
    print("\n4. Testing Expired Timestamp")
    old_timestamp = int(time.time()) - 3600  # 1 hour ago
    expired_sig = generate_firefly_signature(TEST_RAW_BODY, TEST_WEBHOOK_SECRET, old_timestamp)
    result = validate_webhook_signature_test(TEST_RAW_BODY, expired_sig, TEST_WEBHOOK_SECRET)
    print(f"Validation result: {result}")
    print(f"❌ Valid: {result.get('valid', False)} (Expected: False - expired)")
    
    print("\n" + "=" * 50)
    print("🎉 Signature validation tests completed!")

if __name__ == "__main__":
    run_signature_validation_tests() 