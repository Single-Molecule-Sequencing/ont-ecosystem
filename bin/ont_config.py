#!/usr/bin/env python3
"""
ONT Ecosystem Configuration Management

Handles user configuration for the ONT Ecosystem, including:
- GitHub access settings (tokens, SSH URLs)
- Installation paths
- HPC cluster configurations
- Registry locations

Configuration file: ~/.ont-ecosystem/config.yaml
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# Configuration Paths
# =============================================================================

ONT_ECOSYSTEM_HOME = Path(os.environ.get("ONT_ECOSYSTEM_HOME", Path.home() / ".ont-ecosystem"))
CONFIG_FILE = ONT_ECOSYSTEM_HOME / "config.yaml"
REGISTRY_DIR = Path(os.environ.get("ONT_REGISTRY_DIR", Path.home() / ".ont-registry"))
MANUSCRIPT_DIR = Path(os.environ.get("ONT_MANUSCRIPT_DIR", Path.home() / ".ont-manuscript"))


# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class GitHubConfig:
    """GitHub access configuration"""
    enabled: bool = False  # Disabled by default for private repo
    token: Optional[str] = None  # GitHub Personal Access Token
    ssh_url: str = "git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git"
    https_url: str = "https://github.com/Single-Molecule-Sequencing/ont-ecosystem"
    registry_url: str = "https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/registry/experiments.yaml"


@dataclass
class HPCConfig:
    """HPC cluster configuration"""
    cluster: Optional[str] = None  # greatlakes, armis2, etc.
    default_partition: str = "standard"
    gpu_partition: str = "spgpu"
    dorado_models: Optional[str] = None
    references_dir: Optional[str] = None
    scratch_dir: Optional[str] = None


@dataclass
class PathConfig:
    """Installation and data paths"""
    ecosystem_home: str = str(ONT_ECOSYSTEM_HOME)
    registry_dir: str = str(REGISTRY_DIR)
    manuscript_dir: str = str(MANUSCRIPT_DIR)
    textbook_dir: Optional[str] = None  # Path to SMS_textbook repo


@dataclass
class OntConfig:
    """Main configuration container"""
    version: str = "1.0.0"
    github: GitHubConfig = field(default_factory=GitHubConfig)
    hpc: HPCConfig = field(default_factory=HPCConfig)
    paths: PathConfig = field(default_factory=PathConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        return {
            "version": self.version,
            "github": asdict(self.github),
            "hpc": asdict(self.hpc),
            "paths": asdict(self.paths)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OntConfig":
        """Create from dictionary"""
        config = cls()
        config.version = data.get("version", "1.0.0")

        if "github" in data:
            config.github = GitHubConfig(**data["github"])
        if "hpc" in data:
            config.hpc = HPCConfig(**data["hpc"])
        if "paths" in data:
            config.paths = PathConfig(**data["paths"])

        return config


# =============================================================================
# Configuration Loading/Saving
# =============================================================================

def load_config() -> OntConfig:
    """Load configuration from file or create default"""
    if not HAS_YAML:
        return OntConfig()

    if not CONFIG_FILE.exists():
        return OntConfig()

    try:
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        return OntConfig.from_dict(data)
    except Exception as e:
        print(f"Warning: Could not load config from {CONFIG_FILE}: {e}", file=sys.stderr)
        return OntConfig()


def save_config(config: OntConfig) -> bool:
    """Save configuration to file"""
    if not HAS_YAML:
        print("Error: PyYAML required for saving config", file=sys.stderr)
        return False

    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Error: Could not save config to {CONFIG_FILE}: {e}", file=sys.stderr)
        return False


def init_config(force: bool = False) -> OntConfig:
    """Initialize configuration with defaults and detect environment"""
    if CONFIG_FILE.exists() and not force:
        return load_config()

    config = OntConfig()

    # Detect HPC cluster
    if Path("/nfs/turbo").exists():
        config.hpc.cluster = "greatlakes"
        config.hpc.gpu_partition = "spgpu"
        config.hpc.dorado_models = "/nfs/turbo/umms-athey/dorado_models"
        config.hpc.references_dir = "/nfs/turbo/umms-athey/references"
    elif Path("/nfs/dataden").exists():
        config.hpc.cluster = "armis2"
        config.hpc.gpu_partition = "gpu"
        config.hpc.dorado_models = "/nfs/dataden/umms-bleu-secure/programs/dorado_models"
        config.hpc.references_dir = "/nfs/dataden/umms-bleu-secure/references"

    # Check for textbook location - internal first (consolidated monorepo)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    internal_textbook = repo_root / "textbook"

    textbook_paths = [
        internal_textbook,  # Internal (consolidated monorepo) - preferred
        Path("/mnt/d/repos/SMS_textbook"),
        Path.home() / "repos" / "SMS_textbook",
        Path("/mnt/d/Google_Drive_umich/SMS_textbook"),
    ]
    for p in textbook_paths:
        if p.exists() and (p / "equations.yaml").exists():
            config.paths.textbook_dir = str(p)
            break

    save_config(config)
    return config


def get_github_sync_enabled() -> bool:
    """Check if GitHub sync is enabled (env var overrides config)"""
    # Environment variable takes precedence
    env_sync = os.environ.get("ONT_GITHUB_SYNC")
    if env_sync is not None:
        return env_sync.lower() in ("1", "true", "yes")

    env_no_sync = os.environ.get("ONT_NO_GITHUB_SYNC")
    if env_no_sync is not None:
        return env_no_sync.lower() not in ("1", "true", "yes")

    # Fall back to config file
    config = load_config()
    return config.github.enabled


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment or config"""
    # Environment variable takes precedence
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token

    config = load_config()
    return config.github.token


# =============================================================================
# CLI
# =============================================================================

def cmd_show(args):
    """Show current configuration"""
    config = load_config()
    print(f"ONT Ecosystem Configuration")
    print(f"{'='*50}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"")
    print(f"GitHub:")
    print(f"  Sync enabled: {config.github.enabled}")
    print(f"  Token set: {bool(config.github.token)}")
    print(f"  SSH URL: {config.github.ssh_url}")
    print(f"")
    print(f"HPC:")
    print(f"  Cluster: {config.hpc.cluster or 'not detected'}")
    print(f"  GPU partition: {config.hpc.gpu_partition}")
    print(f"  Dorado models: {config.hpc.dorado_models or 'not set'}")
    print(f"")
    print(f"Paths:")
    print(f"  Ecosystem home: {config.paths.ecosystem_home}")
    print(f"  Registry: {config.paths.registry_dir}")
    print(f"  Manuscript: {config.paths.manuscript_dir}")
    print(f"  Textbook: {config.paths.textbook_dir or 'not set'}")


def cmd_init(args):
    """Initialize configuration"""
    config = init_config(force=args.force)
    print(f"Configuration initialized at {CONFIG_FILE}")
    if config.hpc.cluster:
        print(f"Detected HPC cluster: {config.hpc.cluster}")


def cmd_set(args):
    """Set a configuration value"""
    config = load_config()

    key = args.key
    value = args.value

    # Parse key path (e.g., "github.enabled" -> github, enabled)
    parts = key.split(".")
    if len(parts) == 2:
        section, field = parts
        if section == "github" and hasattr(config.github, field):
            # Handle boolean conversion
            if field == "enabled":
                value = value.lower() in ("1", "true", "yes")
            setattr(config.github, field, value)
        elif section == "hpc" and hasattr(config.hpc, field):
            setattr(config.hpc, field, value)
        elif section == "paths" and hasattr(config.paths, field):
            setattr(config.paths, field, value)
        else:
            print(f"Error: Unknown config key: {key}")
            return
    else:
        print(f"Error: Key must be in format 'section.field' (e.g., 'github.enabled')")
        return

    if save_config(config):
        print(f"Set {key} = {value}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # show
    p_show = subparsers.add_parser("show", help="Show current configuration")
    p_show.set_defaults(func=cmd_show)

    # init
    p_init = subparsers.add_parser("init", help="Initialize configuration")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config")
    p_init.set_defaults(func=cmd_init)

    # set
    p_set = subparsers.add_parser("set", help="Set a configuration value")
    p_set.add_argument("key", help="Config key (e.g., github.enabled)")
    p_set.add_argument("value", help="Value to set")
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args()

    if args.command is None:
        cmd_show(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
