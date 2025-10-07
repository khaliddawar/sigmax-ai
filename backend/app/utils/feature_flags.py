"""
Feature flags for controlling application behavior
"""
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FeatureFlags:
    """Central feature flag management for application-wide toggles"""
    
    @staticmethod
    def is_premium_pipeline_enabled() -> bool:
        """
        Feature flag to enable/disable premium pipeline split
        
        When False: All users get full pipeline (current behavior)
        When True: Free users get limited pipeline, Premium users get full pipeline
        
        Returns:
            bool: True if premium pipeline split is enabled
        """
        enabled = os.getenv('ENABLE_PREMIUM_PIPELINE_SPLIT', 'false').lower() == 'true'
        if enabled:
            logger.info("🔀 Premium pipeline split is ENABLED")
        return enabled
    
    @staticmethod
    def get_pipeline_config() -> Dict[str, Any]:
        """
        Get pipeline configuration settings
        
        Returns:
            Dict containing pipeline configuration
        """
        config = {
            'split_enabled': FeatureFlags.is_premium_pipeline_enabled(),
            'premium_plans': ['premium', 'pro', 'enterprise'],
            'free_plans': ['free', 'trial'],
            'default_plan': 'free'
        }
        
        logger.debug(f"Pipeline config: {config}")
        return config
    
    @staticmethod
    def get_premium_plan_names() -> list:
        """Get list of plan names that should receive premium features"""
        return FeatureFlags.get_pipeline_config()['premium_plans']
    
    @staticmethod
    def get_free_plan_names() -> list:
        """Get list of plan names that should receive free features only"""
        return FeatureFlags.get_pipeline_config()['free_plans'] 