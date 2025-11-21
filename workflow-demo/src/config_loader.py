#!/usr/bin/env python3
"""
Configuration loader for AIOps nodes
Loads node configurations from external YAML file
"""

import os
import yaml
from typing import Dict, Any, Optional

class NodeConfig:
    """Configuration manager for AIOps nodes"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_file: Path to configuration file (defaults to config/nodes.yaml)
        """
        if config_file is None:
            # Default to config/nodes.yaml in project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_file = os.path.join(project_root, "config", "nodes.yaml")
        
        self.config_file = config_file
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def get_node_config(self, node_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific node
        
        Args:
            node_name: Name of the node (e.g., 'alarm_analyzer', 'decision')
            
        Returns:
            Dictionary with node configuration
        """
        if not self._config or 'nodes' not in self._config:
            raise ValueError("Invalid configuration: missing 'nodes' section")
        
        if node_name not in self._config['nodes']:
            raise ValueError(f"Node '{node_name}' not found in configuration")
        
        node_config = self._config['nodes'][node_name].copy()
        
        # Apply environment-specific overrides if available
        environment = os.getenv('AIOPS_ENV', 'development')
        if 'environments' in self._config and environment in self._config['environments']:
            env_config = self._config['environments'][environment]
            
            # Apply default model_id if not specified for the node
            if 'default_model_id' in env_config and 'model_id' not in node_config:
                node_config['model_id'] = env_config['default_model_id']
        
        return node_config
    
    def get_model_info(self, model_id: int) -> Dict[str, Any]:
        """
        Get model information by ID
        
        Args:
            model_id: Model ID (0-5)
            
        Returns:
            Dictionary with model information
        """
        if not self._config or 'models' not in self._config:
            raise ValueError("Invalid configuration: missing 'models' section")
        
        if model_id not in self._config['models']:
            raise ValueError(f"Model ID '{model_id}' not found in configuration")
        
        return self._config['models'][model_id]
    
    def get_unified_node_name(self, node_name: str) -> str:
        """
        Get unified/display name for a node
        
        Args:
            node_name: Internal node name
            
        Returns:
            Display name for the node
        """
        node_config = self.get_node_config(node_name)
        return node_config.get('display_name', node_name.replace('_', ' ').title())
    
    def list_nodes(self) -> Dict[str, str]:
        """
        List all configured nodes with their display names
        
        Returns:
            Dictionary mapping internal names to display names
        """
        if not self._config or 'nodes' not in self._config:
            return {}
        
        return {
            name: config.get('display_name', name.replace('_', ' ').title())
            for name, config in self._config['nodes'].items()
        }
    
    def validate_config(self) -> bool:
        """
        Validate the configuration file
        
        Returns:
            True if configuration is valid
        """
        try:
            # Check required sections
            required_sections = ['nodes', 'models']
            for section in required_sections:
                if section not in self._config:
                    raise ValueError(f"Missing required section: {section}")
            
            # Check each node has required fields
            for node_name, node_config in self._config['nodes'].items():
                required_fields = ['model_id', 'max_tokens']
                for field in required_fields:
                    if field not in node_config:
                        raise ValueError(f"Node '{node_name}' missing required field: {field}")
                
                # Check model_id exists in models section
                model_id = node_config['model_id']
                if model_id not in self._config['models']:
                    raise ValueError(f"Node '{node_name}' references unknown model_id: {model_id}")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

# Global configuration instance
_config_instance = None

def get_node_config(node_name: str) -> Dict[str, Any]:
    """
    Convenience function to get node configuration
    
    Args:
        node_name: Name of the node
        
    Returns:
        Node configuration dictionary
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = NodeConfig()
    
    return _config_instance.get_node_config(node_name)

def get_unified_node_name(node_name: str) -> str:
    """
    Convenience function to get unified node name
    
    Args:
        node_name: Internal node name
        
    Returns:
        Display name for the node
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = NodeConfig()
    
    return _config_instance.get_unified_node_name(node_name)
