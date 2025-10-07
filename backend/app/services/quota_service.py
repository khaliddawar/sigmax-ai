"""
Quota Management Service
Handles user plan limits, usage tracking, and quota validation
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date
import asyncio
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class QuotaService:
    """Service for managing user quotas and usage tracking"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_user_limits(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's plan limits
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict containing user limits (monthly_tokens, daily_requests, max_video_duration, tier)
        """
        try:
            # Call the database function to get user limits
            result = self.supabase.rpc('get_user_quota_limits', {'p_user_id': user_id}).execute()
            
            if result.data:
                return result.data
            else:
                # Return default limits if user not found
                return {
                    "monthly_tokens": 50000,
                    "daily_requests": 100,
                    "max_video_duration": 3600,
                    "tier": "free"
                }
                
        except Exception as e:
            logger.error(f"Error getting user limits for {user_id}: {e}")
            # Return default limits on error
            return {
                "monthly_tokens": 50000,
                "daily_requests": 100,
                "max_video_duration": 3600,
                "tier": "free"
            }
    
    async def get_current_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's current period usage
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict containing current usage (tokens_used, requests_made, videos_processed, period_start, period_end)
        """
        try:
            # Call the database function to get current usage
            result = self.supabase.rpc('get_user_quota_usage', {'p_user_id': user_id}).execute()
            
            if result.data:
                return result.data
            else:
                # Return zero usage if no record found
                return {
                    "tokens_used": 0,
                    "requests_made": 0,
                    "videos_processed": 0,
                    "period_start": None,
                    "period_end": None
                }
                
        except Exception as e:
            logger.error(f"Error getting current usage for {user_id}: {e}")
            # Return zero usage on error
            return {
                "tokens_used": 0,
                "requests_made": 0,
                "videos_processed": 0,
                "period_start": None,
                "period_end": None
            }
    
    async def can_consume_tokens(self, user_id: str, tokens_needed: int) -> bool:
        """
        Check if user can consume the specified number of tokens
        
        Args:
            user_id: User UUID
            tokens_needed: Number of tokens to check
            
        Returns:
            True if user can consume tokens, False otherwise
        """
        try:
            # Get user limits and current usage using the existing database functions
            limits = await self.get_user_limits(user_id)
            usage = await self.get_current_usage(user_id)
            
            # Extract values with defaults
            monthly_limit = limits.get('monthly_tokens', 50000)
            current_tokens = usage.get('tokens_used', 0)
            
            # Check if user can consume the requested tokens
            return (current_tokens + tokens_needed) <= monthly_limit
            
        except Exception as e:
            logger.error(f"Error checking token consumption for {user_id}: {e}")
            return False
    
    async def increment_usage(
        self, 
        user_id: str, 
        tokens_consumed: int = 0, 
        requests_increment: int = 1, 
        videos_increment: int = 0
    ) -> bool:
        """
        Increment user's usage counters using the existing consume_user_quota function
        
        Args:
            user_id: User UUID
            tokens_consumed: Number of tokens consumed
            requests_increment: Number of requests to increment
            videos_increment: Number of videos to increment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Record different resource types separately using existing consume_user_quota function
            all_success = True
            
            # Record video processing if videos were processed
            if videos_increment > 0:
                result = self.supabase.rpc('consume_user_quota', {
                    'p_user_id': user_id,
                    'p_resource_type': 'video_processing',
                    'p_amount': videos_increment,
                    'p_metadata': {'source': 'youtube_extension'}
                }).execute()
                
                video_success = bool(result.data) if result.data is not None else False
                if not video_success:
                    logger.error(f"Failed to record video usage for user {user_id}")
                    all_success = False
                else:
                    logger.info(f"✅ Recorded {videos_increment} video(s) for user {user_id}")
            
            # Record tokens consumed if any
            if tokens_consumed > 0:
                result = self.supabase.rpc('consume_user_quota', {
                    'p_user_id': user_id,
                    'p_resource_type': 'tokens',
                    'p_amount': tokens_consumed,
                    'p_metadata': {'source': 'youtube_extension'}
                }).execute()
                
                token_success = bool(result.data) if result.data is not None else False
                if not token_success:
                    logger.error(f"Failed to record token usage for user {user_id}")
                    all_success = False
                else:
                    logger.info(f"✅ Recorded {tokens_consumed} tokens for user {user_id}")
            
            # Record requests if any
            if requests_increment > 0:
                result = self.supabase.rpc('consume_user_quota', {
                    'p_user_id': user_id,
                    'p_resource_type': 'requests',
                    'p_amount': requests_increment,
                    'p_metadata': {'source': 'youtube_extension'}
                }).execute()
                
                request_success = bool(result.data) if result.data is not None else False
                if not request_success:
                    logger.error(f"Failed to record request usage for user {user_id}")
                    all_success = False
                else:
                    logger.info(f"✅ Recorded {requests_increment} request(s) for user {user_id}")
            
            return all_success
            
        except Exception as e:
            logger.error(f"Error incrementing usage for {user_id}: {e}")
            return False
    
    async def check_quota_and_consume(
        self, 
        user_id: str, 
        estimated_tokens: int,
        video_duration: Optional[float] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Comprehensive quota check and consumption
        
        Args:
            user_id: User UUID
            estimated_tokens: Number of tokens to consume
            video_duration: Duration of video in seconds (optional)
            
        Returns:
            Tuple of (can_proceed, message, quota_info)
        """
        try:
            # Get user limits and current usage
            limits = await self.get_user_limits(user_id)
            usage = await self.get_current_usage(user_id)
            
            # Check token limits
            can_consume = await self.can_consume_tokens(user_id, estimated_tokens)
            if not can_consume:
                return False, f"Monthly token limit exceeded. Limit: {limits['monthly_tokens']}, Current: {usage['tokens_used']}, Requested: {estimated_tokens}", {
                    "limits": limits,
                    "usage": usage
                }
            
            # Check video duration limit if provided
            if video_duration and video_duration > limits.get('max_video_duration', 3600):
                return False, f"Video duration exceeds limit. Max: {limits['max_video_duration']}s, Video: {video_duration}s", {
                    "limits": limits,
                    "usage": usage
                }
            
            # Check daily request limits (simplified - using monthly for now)
            daily_limit = limits.get('daily_requests', 100)
            current_requests = usage.get('requests_made', 0)
            
            # For simplicity, we'll use a monthly request limit
            monthly_request_limit = daily_limit * 30
            if current_requests >= monthly_request_limit:
                return False, f"Monthly request limit exceeded. Limit: {monthly_request_limit}, Current: {current_requests}", {
                    "limits": limits,
                    "usage": usage
                }
            
            # All checks passed
            return True, "Quota check passed", {
                "limits": limits,
                "usage": usage,
                "remaining_tokens": limits['monthly_tokens'] - usage['tokens_used'],
                "remaining_requests": monthly_request_limit - current_requests
            }
            
        except Exception as e:
            logger.error(f"Error in quota check for {user_id}: {e}")
            return False, f"Quota check failed: {str(e)}", {}
    
    async def consume_quota(
        self, 
        user_id: str, 
        tokens_consumed: int,
        video_processed: bool = True
    ) -> bool:
        """
        Consume user's quota after successful processing
        
        Args:
            user_id: User UUID
            tokens_consumed: Number of tokens consumed
            video_processed: Whether a video was processed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            videos_increment = 1 if video_processed else 0
            success = await self.increment_usage(
                user_id=user_id,
                tokens_consumed=tokens_consumed,
                requests_increment=1,
                videos_increment=videos_increment
            )
            
            if success:
                logger.info(f"Quota consumed for user {user_id}: {tokens_consumed} tokens, {videos_increment} videos")
            else:
                logger.error(f"Failed to consume quota for user {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error consuming quota for {user_id}: {e}")
            return False
    
    async def get_quota_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive quota summary for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            Dict containing limits, usage, and remaining quota
        """
        try:
            limits = await self.get_user_limits(user_id)
            usage = await self.get_current_usage(user_id)
            
            # Calculate remaining quota
            remaining_tokens = limits['monthly_tokens'] - usage['tokens_used']
            monthly_request_limit = limits['daily_requests'] * 30
            remaining_requests = monthly_request_limit - usage['requests_made']
            
            return {
                "user_id": user_id,
                "tier": limits['tier'],
                "limits": limits,
                "usage": usage,
                "remaining": {
                    "tokens": max(0, remaining_tokens),
                    "requests": max(0, remaining_requests),
                    "videos": "unlimited"  # No specific video limit beyond tokens/requests
                },
                "usage_percentage": {
                    "tokens": min(100, (usage['tokens_used'] / limits['monthly_tokens']) * 100),
                    "requests": min(100, (usage['requests_made'] / monthly_request_limit) * 100)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting quota summary for {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }

# Initialize quota service instance
quota_service = QuotaService() 