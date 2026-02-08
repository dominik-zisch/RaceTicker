"""YAML configuration loader and persister."""

import os
import shutil
import yaml
from pathlib import Path
from typing import Any, Dict

from .schema import validate_config, validate_patch


class ConfigManager:
    """Manages YAML configuration with atomic writes."""
    
    def __init__(self, config_path: Path):
        """Initialize config manager.
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}
        
        validate_config(self._config)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration.
        
        Returns:
            Copy of current configuration dictionary
        """
        # Return a deep copy to prevent external modification
        import copy
        return copy.deepcopy(self._config)
    
    def update_config(self, patch: Dict[str, Any]) -> None:
        """Update configuration with a patch and persist to disk.
        
        Args:
            patch: Dictionary with nested keys to update (e.g., {"mode": {"source": "simulate"}})
        
        Raises:
            ValueError: If validation fails
        """
        validate_patch(patch)
        
        # Apply patch recursively
        self._apply_patch(self._config, patch)
        
        # Validate full config after patch
        validate_config(self._config)
        
        # Atomic write: write to temp file, then rename
        self._atomic_write()
    
    def _apply_patch(self, target: Dict[str, Any], patch: Dict[str, Any]) -> None:
        """Recursively apply patch to target dictionary."""
        for key, value in patch.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._apply_patch(target[key], value)
            else:
                target[key] = value
    
    def _atomic_write(self) -> None:
        """Write config to disk atomically using temp file + rename."""
        temp_path = self.config_path.with_suffix('.yaml.tmp')
        
        try:
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Atomic rename (works on POSIX systems)
            temp_path.replace(self.config_path)
        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise


# Global instance (will be initialized in app.py)
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    if _config_manager is None:
        raise RuntimeError("Config manager not initialized. Call init_config_manager() first.")
    return _config_manager


def init_config_manager(config_path: Path) -> None:
    """Initialize the global config manager.
    
    Args:
        config_path: Path to config.yaml file
    """
    global _config_manager
    _config_manager = ConfigManager(config_path)
