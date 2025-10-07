"""
Domain Configuration Loader

This module provides functionality to load domain-specific settings from YAML files

```configuration/domain_loader.py
<code_block_to_apply_changes_from>
"""

import os
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DomainConfigurationLoader:
    """
    Loads and manages domain-specific configurations for the RAG system.
    
    This class enables the system to work across different domains (financial,
    medical, legal, technical, etc.) by loading domain-specific terminology,
    sentiment indicators, and processing rules from external YAML files.
    """
    
    def __init__(self, config_path: str = "config/domains"):
        """
        Initialize the domain configuration loader.
        
        Args:
            config_path: Path to the directory containing domain YAML files
        """
        self.config_path = Path(config_path)
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
        self._current_domain: Optional[str] = None
        self._current_config: Optional[Dict[str, Any]] = None
    
    def load_domain(self, domain_name: str) -> Dict[str, Any]:
        """
        Load configuration for a specific domain.
        
        Args:
            domain_name: Name of the domain (e.g., 'financial', 'medical')
            
        Returns:
            Dictionary containing domain configuration
            
        Raises:
            FileNotFoundError: If domain configuration file doesn't exist
            yaml.YAMLError: If YAML file is malformed
        """
        if domain_name in self._loaded_configs:
            logger.info(f"Using cached configuration for domain: {domain_name}")
            return self._loaded_configs[domain_name]
        
        config_file = self.config_path / f"{domain_name}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Domain configuration file not found: {config_file}\n"
                f"Available domains: {self.list_available_domains()}"
            )
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Validate configuration structure
            self._validate_config(config, domain_name)
            
            # Cache the configuration
            self._loaded_configs[domain_name] = config
            logger.info(f"Successfully loaded configuration for domain: {domain_name}")
            
            return config
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {config_file}: {e}")
    
    def set_current_domain(self, domain_name: str) -> None:
        """
        Set the current active domain and load its configuration.
        
        Args:
            domain_name: Name of the domain to activate
        """
        self._current_config = self.load_domain(domain_name)
        self._current_domain = domain_name
        logger.info(f"Set current domain to: {domain_name}")
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently active domain configuration."""
        return self._current_config
    
    def get_current_domain(self) -> Optional[str]:
        """Get the name of the currently active domain."""
        return self._current_domain
    
    def list_available_domains(self) -> List[str]:
        """
        List all available domain configurations.
        
        Returns:
            List of domain names that have configuration files
        """
        if not self.config_path.exists():
            return []
        
        domains = []
        for file_path in self.config_path.glob("*.yaml"):
            domains.append(file_path.stem)
        
        return sorted(domains)
    
    def get_entity_types(self, domain_name: Optional[str] = None) -> List[str]:
        """
        Get entity types for a domain.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            List of entity types for the domain
        """
        config = self._get_config(domain_name)
        return config.get('entity_types', [])
    
    def get_sentiment_indicators(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sentiment indicators for a domain.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Dictionary of sentiment indicators
        """
        config = self._get_config(domain_name)
        return config.get('sentiment_indicators', {})
    
    def get_topic_classification_rules(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get topic classification rules for a domain.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Dictionary of topic classification rules
        """
        config = self._get_config(domain_name)
        return config.get('topic_classification', {})
    
    def get_chunking_parameters(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get chunking parameters for a domain.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Dictionary of chunking parameters
        """
        config = self._get_config(domain_name)
        return config.get('chunking', {})
    
    def get_validation_rules(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get validation rules for a domain.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Dictionary of validation rules
        """
        config = self._get_config(domain_name)
        return config.get('validation', {})
    
    def get_domain_specific_terms(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get domain-specific terminology.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Dictionary of domain-specific terms
        """
        config = self._get_config(domain_name)
        
        # Different domains may have different term structures
        # Financial domain has 'financial_instruments'
        # Medical domain has 'medical_concepts'
        # Return the first non-standard key that contains terms
        
        standard_keys = {
            'domain_name', 'description', 'entity_types', 'sentiment_indicators',
            'topic_classification', 'chunking', 'validation'
        }
        
        for key, value in config.items():
            if key not in standard_keys and isinstance(value, dict):
                return {key: value}
        
        return {}
    
    def _get_config(self, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration for a domain, using current domain if none specified.
        
        Args:
            domain_name: Domain name, or None to use current domain
            
        Returns:
            Domain configuration dictionary
            
        Raises:
            ValueError: If no domain is specified and no current domain is set
        """
        if domain_name:
            return self.load_domain(domain_name)
        elif self._current_config:
            return self._current_config
        else:
            raise ValueError(
                "No domain specified and no current domain set. "
                "Call set_current_domain() first or specify domain_name parameter."
            )
    
    def _validate_config(self, config: Dict[str, Any], domain_name: str) -> None:
        """
        Validate that a domain configuration has required fields.
        
        Args:
            config: Configuration dictionary to validate
            domain_name: Name of the domain being validated
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['domain_name', 'description']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(
                f"Domain configuration '{domain_name}' is missing required fields: "
                f"{missing_fields}"
            )
        
        # Validate that domain_name in file matches filename
        if config['domain_name'] != domain_name:
            logger.warning(
                f"Domain name in file ('{config['domain_name']}') doesn't match "
                f"filename ('{domain_name}'). Using filename."
            )
            config['domain_name'] = domain_name


# Global instance for easy access
_domain_loader = DomainConfigurationLoader()

def get_domain_loader() -> DomainConfigurationLoader:
    """Get the global domain configuration loader instance."""
    return _domain_loader

def load_domain_config(domain_name: str) -> Dict[str, Any]:
    """
    Convenience function to load a domain configuration.
    
    Args:
        domain_name: Name of the domain to load
        
    Returns:
        Domain configuration dictionary
    """
    return _domain_loader.load_domain(domain_name)

def set_current_domain(domain_name: str) -> None:
    """
    Convenience function to set the current domain.
    
    Args:
        domain_name: Name of the domain to set as current
    """
    _domain_loader.set_current_domain(domain_name)

def get_current_domain_config() -> Optional[Dict[str, Any]]:
    """
    Convenience function to get the current domain configuration.
    
    Returns:
        Current domain configuration, or None if no domain is set
    """
    return _domain_loader.get_current_config() 