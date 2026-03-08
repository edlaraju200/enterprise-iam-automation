"""Configuration Manager for IAM Platform"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigManager:
    """Centralized configuration management for all IAM integrations"""
    
    def __init__(self, config_path: str = "config/config.json"):
        """Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        load_dotenv()
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._substitute_env_vars()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}. "
                f"Please copy config/example.json to config/config.json"
            )
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _substitute_env_vars(self):
        """Replace placeholders with environment variables"""
        def replace_recursive(obj):
            if isinstance(obj, dict):
                return {k: replace_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                env_var = obj[2:-1]
                return os.getenv(env_var, obj)
            return obj
        
        self.config = replace_recursive(self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'sailpoint.base_url')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section
        
        Args:
            section: Section name (e.g., 'sailpoint', 'azure_ad')
        
        Returns:
            Configuration dictionary for the section
        """
        return self.config.get(section, {})
