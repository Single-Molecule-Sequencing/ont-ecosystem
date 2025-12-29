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


# Error handling utilities - import on demand
def ONTError(*args, **kwargs):
    """Base exception class. Lazy import to avoid startup overhead."""
    from .errors import ONTError as _ONTError
    return _ONTError(*args, **kwargs)


def handle_error(exc, **kwargs):
    """Standard error handler. Lazy import to avoid startup overhead."""
    from .errors import handle_error as _handle_error
    return _handle_error(exc, **kwargs)


# Cache utilities - import on demand
def FileCache(namespace: str, **kwargs):
    """File-based cache. Lazy import to avoid startup overhead."""
    from .cache import FileCache as _FileCache
    return _FileCache(namespace, **kwargs)


def MemoryCache(**kwargs):
    """Memory-based cache. Lazy import to avoid startup overhead."""
    from .cache import MemoryCache as _MemoryCache
    return _MemoryCache(**kwargs)


def memoize(func):
    """Memoization decorator. Lazy import to avoid startup overhead."""
    from .cache import memoize as _memoize
    return _memoize(func)


# Validation utilities - import on demand
def validate_path(path, **kwargs):
    """Validate a file path. Lazy import to avoid startup overhead."""
    from .validation import validate_path as _validate_path
    return _validate_path(path, **kwargs)


def validate_experiment_id(exp_id):
    """Validate experiment ID. Lazy import to avoid startup overhead."""
    from .validation import validate_experiment_id as _validate_experiment_id
    return _validate_experiment_id(exp_id)


def Schema(schema):
    """Schema-based validator. Lazy import to avoid startup overhead."""
    from .validation import Schema as _Schema
    return _Schema(schema)


def Validator(data):
    """Chainable validator. Lazy import to avoid startup overhead."""
    from .validation import Validator as _Validator
    return _Validator(data)
