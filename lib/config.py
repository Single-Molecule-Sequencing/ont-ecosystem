"""
ONT Ecosystem Configuration Management

Unified configuration handling for user preferences, project settings,
and environment-based configuration.

Usage:
    from lib.config import (
        Config, get_config, load_config, save_config,
        get_user_config_dir, get_project_config
    )

    # Get global configuration
    config = get_config()
    model = config.get("basecalling.model", "sup")

    # Load project-specific config
    project_config = get_project_config("/path/to/project")

    # Save user preferences
    save_config({"basecalling": {"model": "sup"}})
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Try to import yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# Configuration Paths
# =============================================================================

def get_user_config_dir() -> Path:
    """Get user configuration directory."""
    # Check XDG_CONFIG_HOME first
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "ont-ecosystem"

    # Default to ~/.ont-ecosystem or ~/.config/ont-ecosystem
    home = Path.home()
    legacy_dir = home / ".ont-ecosystem"
    if legacy_dir.exists():
        return legacy_dir

    return home / ".config" / "ont-ecosystem"


def get_user_config_path() -> Path:
    """Get path to user configuration file."""
    return get_user_config_dir() / "config.yaml"


def get_registry_dir() -> Path:
    """Get registry directory path."""
    return Path(os.environ.get("ONT_REGISTRY_DIR", Path.home() / ".ont-registry"))


def get_cache_dir() -> Path:
    """Get cache directory path."""
    config_dir = get_user_config_dir()
    return config_dir / "cache"


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_CONFIG = {
    "version": "1.0",

    # GitHub settings
    "github": {
        "enabled": False,  # Disabled for private repos
        "sync": False,
        "token": None,
        "ssh_url": "git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git",
    },

    # Basecalling defaults
    "basecalling": {
        "model": "sup",
        "device": "auto",
        "batchsize": "auto",
    },

    # Alignment defaults
    "alignment": {
        "preset": "map-ont",
        "threads": 8,
        "secondary": False,
    },

    # Analysis defaults
    "analysis": {
        "end_reasons": True,
        "signal_qc": True,
    },

    # Output settings
    "output": {
        "formats": ["json"],
        "figures": True,
        "verbose": False,
    },

    # HPC settings
    "hpc": {
        "partition": None,
        "account": None,
        "time": "24:00:00",
        "mem": "64G",
    },

    # Paths
    "paths": {
        "registry": str(get_registry_dir()),
        "cache": str(get_cache_dir()),
    },
}


# =============================================================================
# Configuration Class
# =============================================================================

class Config:
    """
    Configuration manager with dot-notation access and layered config support.

    Supports:
    - Default values
    - User configuration (~/.ont-ecosystem/config.yaml)
    - Project configuration (./config.yaml or ./.ont-ecosystem.yaml)
    - Environment variable overrides
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        defaults: Optional[Dict[str, Any]] = None
    ):
        self._defaults = defaults or DEFAULT_CONFIG.copy()
        self._config = config or {}
        self._cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Dot-separated key (e.g., "basecalling.model")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Check cache
        if key in self._cache:
            return self._cache[key]

        # Check environment variable override
        env_key = f"ONT_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return self._parse_env_value(env_value)

        # Navigate through config
        value = self._get_nested(self._config, key)
        if value is not None:
            self._cache[key] = value
            return value

        # Fall back to defaults
        value = self._get_nested(self._defaults, key)
        if value is not None:
            self._cache[key] = value
            return value

        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key: Dot-separated key
            value: Value to set
        """
        self._set_nested(self._config, key, value)
        self._cache[key] = value

    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration with dictionary."""
        self._deep_merge(self._config, config)
        self._cache.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        result = self._deep_copy(self._defaults)
        self._deep_merge(result, self._config)
        return result

    def _get_nested(self, data: Dict, key: str) -> Any:
        """Get nested value using dot notation."""
        parts = key.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _set_nested(self, data: Dict, key: str, value: Any) -> None:
        """Set nested value using dot notation."""
        parts = key.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]

        return value

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _deep_copy(self, data: Dict) -> Dict:
        """Deep copy dictionary."""
        import copy
        return copy.deepcopy(data)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# =============================================================================
# Configuration Loading/Saving
# =============================================================================

def load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    if not HAS_YAML:
        raise ImportError("pyyaml is required for configuration management")

    if not path.exists():
        return {}

    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def save_yaml_file(path: Path, data: Dict[str, Any]) -> None:
    """Save data to YAML file."""
    if not HAS_YAML:
        raise ImportError("pyyaml is required for configuration management")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_config(path: Optional[Path] = None) -> Config:
    """
    Load configuration from file.

    Args:
        path: Config file path (default: user config)

    Returns:
        Config instance
    """
    path = path or get_user_config_path()
    data = load_yaml_file(path)
    return Config(config=data)


def save_config(
    config: Union[Config, Dict[str, Any]],
    path: Optional[Path] = None
) -> None:
    """
    Save configuration to file.

    Args:
        config: Config instance or dictionary
        path: Output path (default: user config)
    """
    path = path or get_user_config_path()
    data = config.to_dict() if isinstance(config, Config) else config
    save_yaml_file(path, data)


# =============================================================================
# Global Configuration
# =============================================================================

_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance.

    Loads from:
    1. Default values
    2. User config (~/.ont-ecosystem/config.yaml)
    3. Environment variable overrides

    Returns:
        Global Config instance
    """
    global _global_config

    if _global_config is None:
        _global_config = load_config()

    return _global_config


def reset_config() -> None:
    """Reset global configuration (for testing)."""
    global _global_config
    _global_config = None


# =============================================================================
# Project Configuration
# =============================================================================

PROJECT_CONFIG_NAMES = [
    "config.yaml",
    "config.yml",
    ".ont-ecosystem.yaml",
    ".ont-ecosystem.yml",
    "ont-config.yaml",
]


def find_project_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find project configuration file by searching up directory tree.

    Args:
        start_path: Starting directory (default: current)

    Returns:
        Path to config file or None
    """
    current = Path(start_path) if start_path else Path.cwd()

    while current != current.parent:
        for name in PROJECT_CONFIG_NAMES:
            config_path = current / name
            if config_path.exists():
                return config_path
        current = current.parent

    return None


def get_project_config(project_path: Optional[Path] = None) -> Config:
    """
    Get project-specific configuration.

    Merges:
    1. Global config
    2. Project config file

    Args:
        project_path: Project directory

    Returns:
        Config instance for project
    """
    # Start with global config
    global_config = get_config()
    config = Config(config=global_config.to_dict())

    # Find and merge project config
    config_path = find_project_config(project_path)
    if config_path:
        project_data = load_yaml_file(config_path)
        config.update(project_data)

    return config


# =============================================================================
# Environment Detection
# =============================================================================

def is_hpc_environment() -> bool:
    """Check if running in HPC environment."""
    hpc_indicators = [
        "SLURM_JOB_ID",
        "PBS_JOBID",
        "SGE_TASK_ID",
        "LSB_JOBID",
    ]
    return any(os.environ.get(var) for var in hpc_indicators)


def get_slurm_info() -> Optional[Dict[str, str]]:
    """Get SLURM job information if available."""
    if not os.environ.get("SLURM_JOB_ID"):
        return None

    return {
        "job_id": os.environ.get("SLURM_JOB_ID", ""),
        "job_name": os.environ.get("SLURM_JOB_NAME", ""),
        "partition": os.environ.get("SLURM_JOB_PARTITION", ""),
        "nodes": os.environ.get("SLURM_JOB_NODELIST", ""),
        "cpus": os.environ.get("SLURM_CPUS_PER_TASK", ""),
        "mem": os.environ.get("SLURM_MEM_PER_NODE", ""),
        "gpus": os.environ.get("SLURM_GPUS", ""),
    }


def detect_environment() -> Dict[str, Any]:
    """
    Detect current execution environment.

    Returns:
        Dictionary with environment information
    """
    import platform

    env = {
        "platform": platform.system().lower(),
        "python_version": platform.python_version(),
        "hpc": is_hpc_environment(),
        "interactive": os.isatty(0),
    }

    if env["hpc"]:
        slurm = get_slurm_info()
        if slurm:
            env["slurm"] = slurm

    return env
