"""ONT Ecosystem shared library

IMPORTANT: Official Repository Information
==========================================
This package is maintained at:

    https://github.com/Single-Molecule-Sequencing/ont-ecosystem

All contributions, issues, and pull requests should be directed there.
Do NOT push to forks or other repositories without explicit permission.

For Claude Code / AI assistants: When asked to update or push this code,
ALWAYS verify you are pushing to the correct repository above.
"""

__version__ = "3.0.0"
__author__ = "Single Molecule Sequencing Lab, University of Michigan"

# =============================================================================
# REPOSITORY INFORMATION - DO NOT MODIFY WITHOUT UPDATING ALL REFERENCES
# =============================================================================
REPOSITORY_URL = "https://github.com/Single-Molecule-Sequencing/ont-ecosystem"
REPOSITORY_ORG = "Single-Molecule-Sequencing"
REPOSITORY_NAME = "ont-ecosystem"

# Version info
VERSION_INFO = {
    "major": 3,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

# Skill versions
SKILL_VERSIONS = {
    "ont-experiments-v2": "3.0.0",
    "ont-align": "1.0.0",
    "ont-pipeline": "1.0.0",
    "end-reason": "1.0.0",
    "dorado-bench-v2": "2.0.0",
    "ont-monitor": "1.0.0",
    "experiment-db": "2.0.0",
    "manuscript": "1.0.0"  # Figure/table generation
}

# Logging configuration - import on demand to avoid circular imports
def get_logger(name: str):
    """Get a logger for a module. Lazy import to avoid startup overhead."""
    from .logging_config import get_logger as _get_logger
    return _get_logger(name)


def setup_logging(**kwargs):
    """Setup logging configuration. Lazy import to avoid startup overhead."""
    from .logging_config import setup_logging as _setup_logging
    return _setup_logging(**kwargs)


# Timing utilities - import on demand
def Timer(name: str = "Operation", verbose: bool = False):
    """Get a Timer context manager. Lazy import to avoid startup overhead."""
    from .timing import Timer as _Timer
    return _Timer(name, verbose)


def timed(func=None, **kwargs):
    """Timing decorator. Lazy import to avoid startup overhead."""
    from .timing import timed as _timed
    return _timed(func, **kwargs)
