"""
Pipeline utilities for user tier detection and routing decisions
"""
from typing import Optional, Dict, Any
import logging
from app.utils.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)

def is_premium_user(metadata: Optional[Dict[str, Any]]) -> bool:
    """
    Determine if user should get premium pipeline features
    
    SAFETY: If feature flag is disabled, ALL users get premium features (current behavior)
    SAFETY: If metadata is missing, defaults to premium features (safe fallback)
    
    Args:
        metadata: Request metadata containing user_plan and other info
        
    Returns:
        bool: True if user should get premium features
    """
    # SAFETY: If no metadata, default to premium features (safe fallback)
    if not metadata:
        logger.warning("No metadata provided for premium check, defaulting to premium features")
        return True
    
    config = FeatureFlags.get_pipeline_config()
    
    # SAFETY: If split disabled, everyone gets premium features (current behavior)
    if not config['split_enabled']:
        logger.debug("Pipeline split disabled, all users get premium features")
        return True
    
    user_plan = metadata.get("user_plan", config['default_plan']).lower()
    is_premium = user_plan in [plan.lower() for plan in config['premium_plans']]
    
    logger.info(f"👤 User plan: {user_plan}, Premium access: {is_premium}")
    return is_premium

def log_pipeline_decision(transcript_id: str, is_premium: bool, user_plan: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Log pipeline routing decision for monitoring and debugging
    
    Args:
        transcript_id: Unique transcript identifier
        is_premium: Whether user gets premium features
        user_plan: User's subscription plan
        metadata: Additional context for logging
    """
    pipeline_type = "PREMIUM" if is_premium else "FREE"
    user_id = metadata.get("user_id", "unknown") if metadata else "unknown"
    
    logger.info(
        f"🔀 Pipeline routing for {transcript_id}: {pipeline_type} "
        f"(plan: {user_plan}, user: {user_id})"
    )

def get_pipeline_steps_for_user(metadata: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Get which pipeline steps should be executed for a user
    
    Args:
        metadata: Request metadata containing user info
        
    Returns:
        Dict mapping step names to whether they should be executed
    """
    is_premium = is_premium_user(metadata)
    
    steps = {
        # Always execute these steps
        'chunk_transcript': True,
        'store_transcript': True, 
        'generate_summary': True,
        'store_summary': True,
        'send_email': True,
        
        # Premium-only steps
        'generate_embeddings': is_premium,
        'store_embeddings': is_premium,
        'semantic_chunking': is_premium,
        'store_semantic_chunks': is_premium
    }
    
    logger.debug(f"Pipeline steps for user: {steps}")
    return steps

def log_cost_savings(transcript_id: str, user_plan: str, skipped_operations: list):
    """
    Log cost savings from skipped operations for monitoring
    
    Args:
        transcript_id: Unique transcript identifier
        user_plan: User's subscription plan
        skipped_operations: List of operations that were skipped
    """
    if skipped_operations:
        savings_info = {
            'transcript_id': transcript_id,
            'user_plan': user_plan,
            'skipped_operations': skipped_operations,
            'estimated_api_calls_saved': len(skipped_operations)
        }
        logger.info(f"💰 COST_SAVINGS: {savings_info}")

def validate_pipeline_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and normalize pipeline metadata
    
    Args:
        metadata: Raw metadata from request
        
    Returns:
        Validated and normalized metadata
    """
    if not metadata:
        metadata = {}
    
    # Ensure required fields have safe defaults
    normalized = {
        'user_plan': metadata.get('user_plan', 'free'),
        'user_id': metadata.get('user_id', 'unknown'),
        'source': metadata.get('source', 'unknown'),
        **metadata  # Preserve all original fields
    }
    
    return normalized 