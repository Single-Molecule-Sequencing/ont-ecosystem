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
    "manuscript": "1.0.0",  # Figure/table generation
    "ont-public-data": "1.0.0",  # Stream & analyze public ONT datasets
    "registry-browser": "1.1.0"  # Interactive registry browser with comprehensive metadata extraction
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


# CLI utilities - import on demand
def add_common_args(parser):
    """Add common CLI arguments. Lazy import to avoid startup overhead."""
    from .cli import add_common_args as _add_common_args
    return _add_common_args(parser)


def print_header(title, **kwargs):
    """Print formatted header. Lazy import to avoid startup overhead."""
    from .cli import print_header as _print_header
    return _print_header(title, **kwargs)


def print_table(headers, rows, **kwargs):
    """Print formatted table. Lazy import to avoid startup overhead."""
    from .cli import print_table as _print_table
    return _print_table(headers, rows, **kwargs)


def ProgressBar(total, **kwargs):
    """Progress bar. Lazy import to avoid startup overhead."""
    from .cli import ProgressBar as _ProgressBar
    return _ProgressBar(total, **kwargs)


# I/O utilities - import on demand
def load_json(path, **kwargs):
    """Load JSON file. Lazy import to avoid startup overhead."""
    from .io import load_json as _load_json
    return _load_json(path, **kwargs)


def save_json(path, data, **kwargs):
    """Save JSON file. Lazy import to avoid startup overhead."""
    from .io import save_json as _save_json
    return _save_json(path, data, **kwargs)


def load_yaml(path, **kwargs):
    """Load YAML file. Lazy import to avoid startup overhead."""
    from .io import load_yaml as _load_yaml
    return _load_yaml(path, **kwargs)


def save_yaml(path, data, **kwargs):
    """Save YAML file. Lazy import to avoid startup overhead."""
    from .io import save_yaml as _save_yaml
    return _save_yaml(path, data, **kwargs)


def atomic_write(path, **kwargs):
    """Atomic file write. Lazy import to avoid startup overhead."""
    from .io import atomic_write as _atomic_write
    return _atomic_write(path, **kwargs)


def checksum(path, **kwargs):
    """Calculate file checksum. Lazy import to avoid startup overhead."""
    from .io import checksum as _checksum
    return _checksum(path, **kwargs)


# Configuration utilities - import on demand
def get_config():
    """Get global configuration. Lazy import to avoid startup overhead."""
    from .config import get_config as _get_config
    return _get_config()


def load_config(path=None):
    """Load configuration from file. Lazy import to avoid startup overhead."""
    from .config import load_config as _load_config
    return _load_config(path)


def save_config(config, path=None):
    """Save configuration to file. Lazy import to avoid startup overhead."""
    from .config import save_config as _save_config
    return _save_config(config, path)


def get_project_config(project_path=None):
    """Get project-specific configuration. Lazy import to avoid startup overhead."""
    from .config import get_project_config as _get_project_config
    return _get_project_config(project_path)


def Config(config=None, defaults=None):
    """Configuration manager. Lazy import to avoid startup overhead."""
    from .config import Config as _Config
    return _Config(config, defaults)


# Q-score utilities - import on demand
def mean_qscore(qscores, **kwargs):
    """Calculate mean Q-score via probability space. Lazy import to avoid startup overhead.

    IMPORTANT: Q-scores are logarithmic and MUST NOT be averaged directly.
    This function correctly converts to probability space first.
    """
    from .qscore import mean_qscore as _mean_qscore
    return _mean_qscore(qscores, **kwargs)


def weighted_mean_qscore(qscores, weights, **kwargs):
    """Calculate weighted mean Q-score via probability space. Lazy import to avoid startup overhead."""
    from .qscore import weighted_mean_qscore as _weighted_mean_qscore
    return _weighted_mean_qscore(qscores, weights, **kwargs)


def qscore_to_probability(qscore):
    """Convert Q-score to error probability. Lazy import to avoid startup overhead."""
    from .qscore import qscore_to_probability as _qscore_to_probability
    return _qscore_to_probability(qscore)


def probability_to_qscore(probability, **kwargs):
    """Convert error probability to Q-score. Lazy import to avoid startup overhead."""
    from .qscore import probability_to_qscore as _probability_to_qscore
    return _probability_to_qscore(probability, **kwargs)


# Parallel processing utilities - import on demand
def parallel_map(func, items, **kwargs):
    """Parallel map function. Lazy import to avoid startup overhead."""
    from .parallel import parallel_map as _parallel_map
    return _parallel_map(func, items, **kwargs)


def parallel_process_files(files, processor, **kwargs):
    """Process files in parallel. Lazy import to avoid startup overhead."""
    from .parallel import parallel_process_files as _parallel_process_files
    return _parallel_process_files(files, processor, **kwargs)


def TaskQueue(workers=None, **kwargs):
    """Task queue for parallel execution. Lazy import to avoid startup overhead."""
    from .parallel import TaskQueue as _TaskQueue
    return _TaskQueue(workers, **kwargs)


def chunked(items, chunk_size):
    """Split items into chunks. Lazy import to avoid startup overhead."""
    from .parallel import chunked as _chunked
    return _chunked(items, chunk_size)


def with_retry(func, **kwargs):
    """Wrap function with retry logic. Lazy import to avoid startup overhead."""
    from .parallel import with_retry as _with_retry
    return _with_retry(func, **kwargs)
