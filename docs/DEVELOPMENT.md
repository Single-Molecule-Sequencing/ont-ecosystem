# ONT Ecosystem Development Guide

This guide covers development setup, architecture, testing, and contribution guidelines for the ONT Ecosystem.

## Quick Start

```bash
# Clone repository
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Install in development mode
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Install git hooks
python bin/ont_hooks.py install
```

## Project Structure

```
ont-ecosystem/
├── bin/                      # CLI tools
│   ├── ont_experiments.py    # Main orchestrator
│   ├── ont_pipeline.py       # Pipeline execution
│   ├── ont_manuscript.py     # Figure/table generation
│   ├── ont_init.py           # Project initialization
│   └── ...
├── lib/                      # Shared library modules
│   ├── __init__.py           # Lazy exports
│   ├── cli.py                # CLI helpers
│   ├── io.py                 # I/O utilities
│   ├── cache.py              # Caching utilities
│   ├── validation.py         # Data validation
│   ├── errors.py             # Error classes
│   ├── timing.py             # Timing utilities
│   └── logging_config.py     # Logging setup
├── skills/                   # Skill definitions
│   ├── end-reason/
│   ├── ont-align/
│   ├── ont-pipeline/
│   └── ...
├── tests/                    # Test suite
│   ├── test_core.py
│   ├── test_utilities.py
│   ├── test_lib.py
│   └── test_endreason_qc.py
├── completions/              # Shell completions
├── docs/                     # Documentation
├── examples/                 # Example configurations
├── dashboards/               # React dashboards
└── data/                     # Registry data
```

## Architecture

### CLI Tools (`bin/`)

Each CLI tool follows a consistent pattern:

```python
#!/usr/bin/env python3
"""
Tool Description

Usage examples in docstring
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import __version__

def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    # Add subparsers for commands
    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
```

### Library Modules (`lib/`)

The library uses lazy imports to minimize startup overhead:

```python
# lib/__init__.py - Lazy import pattern
def load_json(path, **kwargs):
    """Load JSON file. Lazy import to avoid startup overhead."""
    from .io import load_json as _load_json
    return _load_json(path, **kwargs)
```

Available modules:
- `lib.cli` - Terminal colors, progress bars, table formatting
- `lib.io` - JSON/YAML I/O, atomic writes, checksums
- `lib.cache` - Memory and file-based caching
- `lib.validation` - Schema and data validation
- `lib.errors` - Standardized error classes
- `lib.timing` - Timer and timing decorators
- `lib.logging_config` - Logging configuration

### Skills

Skills are self-contained analysis modules in `skills/`:

```
skills/<skill-name>/
├── SKILL.md          # Skill documentation
├── scripts/          # Implementation scripts
├── assets/           # Configuration files
└── templates/        # Output templates
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-feature main
```

### 2. Make Changes

Follow the coding standards:
- PEP 8 style with 100 char line limit
- Type hints for function signatures
- Docstrings for public functions
- Tests for new functionality

### 3. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_utilities.py -v

# Run with coverage
python -m pytest tests/ --cov=bin --cov-report=html
```

### 4. Update Documentation

- Update relevant docs in `docs/`
- Add examples to `ont_help.py` COMMANDS registry
- Update shell completions in `completions/`

### 5. Commit Changes

```bash
# Use conventional commit messages
git commit -m "feat: add new feature

Description of what was added.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

### 6. Create Pull Request

```bash
git push origin feature/my-feature
# Create PR on GitHub
```

## Adding a New CLI Tool

1. Create the script in `bin/`:

```python
#!/usr/bin/env python3
"""ont_mytool.py - Description"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import __version__

def cmd_action(args):
    """Command implementation"""
    print(f"Running action: {args}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="My Tool")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    p_action = subparsers.add_parser("action", help="Do something")
    p_action.add_argument("input", help="Input argument")
    p_action.set_defaults(func=cmd_action)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
```

2. Add tests to `tests/test_utilities.py`:

```python
def test_mytool_imports():
    """Test that ont_mytool.py can be imported"""
    import importlib.util
    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location("ont_mytool", bin_dir / "ont_mytool.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'main')
```

3. Add to `pyproject.toml`:

```toml
[project.scripts]
ont-mytool = "bin.ont_mytool:main"
```

4. Add shell completion to `completions/ont-completion.bash`:

```bash
_ont_mytool() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="action"
    # ... completion logic
}
complete -F _ont_mytool ont_mytool.py
complete -F _ont_mytool ont-mytool
```

5. Add to help registry in `bin/ont_help.py`:

```python
COMMANDS = {
    "Utility Commands": {
        "ont_mytool.py": {
            "description": "Description of my tool",
            "examples": [
                "ont_mytool.py action input",
            ]
        },
    },
}
```

## Adding a Library Module

1. Create the module in `lib/`:

```python
# lib/mymodule.py
"""Description of module"""

def my_function(arg):
    """Function description"""
    return result
```

2. Add lazy exports to `lib/__init__.py`:

```python
def my_function(arg):
    """Function description. Lazy import to avoid startup overhead."""
    from .mymodule import my_function as _my_function
    return _my_function(arg)
```

3. Add tests to `tests/test_lib.py`:

```python
def test_mymodule_function():
    """Test my_function"""
    from lib.mymodule import my_function
    result = my_function("input")
    assert result == expected
```

## Testing Guidelines

### Test Structure

```python
def test_function_name():
    """Describe what this test verifies"""
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected
```

### Using Fixtures

```python
import pytest

@pytest.fixture
def sample_data(tmp_path):
    """Create sample data for testing"""
    data_file = tmp_path / "data.json"
    data_file.write_text('{"key": "value"}')
    return data_file

def test_with_fixture(sample_data):
    result = load_json(sample_data)
    assert result["key"] == "value"
```

### Testing CLI Commands

```python
def test_cli_command(tmp_path, capsys):
    """Test CLI command output"""
    import importlib.util

    bin_dir = Path(__file__).parent.parent / 'bin'
    spec = importlib.util.spec_from_file_location("module", bin_dir / "script.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Mock sys.argv if needed
    result = module.cmd_function(args)
    assert result == 0
```

## Error Handling

Use the standardized error classes from `lib.errors`:

```python
from lib.errors import ValidationError, ConfigurationError, AnalysisError

def validate_input(data):
    if not data:
        raise ValidationError(
            message="Input data is required",
            code="EMPTY_INPUT",
            suggestions=["Provide valid input data"]
        )
```

## Caching

Use the caching utilities for expensive operations:

```python
from lib.cache import memoize, FileCache, timed_cache

# Simple memoization
@memoize
def expensive_function(x):
    return compute_result(x)

# Time-limited cache
@timed_cache(ttl=3600)
def fetch_remote_data():
    return requests.get(url).json()

# File-based cache for persistence
cache = FileCache("my_namespace", default_ttl=3600)
cached_value = cache.get("key")
if cached_value is None:
    cached_value = compute_value()
    cache.set("key", cached_value)
```

## Logging

Use the logging configuration:

```python
from lib import get_logger, setup_logging

# Setup at script start
setup_logging(level="INFO", log_file="output.log")

# Get logger for module
logger = get_logger(__name__)

logger.info("Processing started")
logger.debug("Detailed info: %s", data)
logger.error("Error occurred: %s", error)
```

## Validation

Use the validation utilities:

```python
from lib.validation import validate_path, validate_experiment_id, Schema, Validator

# Path validation
path = validate_path("/path/to/file", must_exist=True, must_be_file=True)

# Experiment ID validation
validate_experiment_id("EXP-001")  # Raises ValidationError if invalid

# Schema validation
schema = Schema({
    "required": ["name", "type"],
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "number", "default": 0}
    }
})
result = schema.validate(data)
if not result.valid:
    print(result.errors)

# Chainable validation
result = (Validator(data)
    .require("name")
    .check_type("count", int)
    .in_range("count", 0, 100)
    .result())
```

## Version Management

```bash
# Check current version
python bin/ont_version.py

# Bump version (patch, minor, major)
python bin/ont_version.py bump patch --dry-run
python bin/ont_version.py bump patch

# Check skill versions
python bin/ont_version.py --skills
```

## Diagnostic Tools

```bash
# Run diagnostics
python bin/ont_doctor.py

# Fix common issues
python bin/ont_doctor.py --fix

# Generate project report
python bin/ont_report.py --format markdown --output report.md
```

## Git Hooks

```bash
# Install all hooks
python bin/ont_hooks.py install

# Check hook status
python bin/ont_hooks.py status

# Run a hook manually
python bin/ont_hooks.py run pre-commit
```

## Creating a Project

```bash
# Standard project
python bin/ont_init.py project my-project

# Full project with all directories
python bin/ont_init.py project my-project --full

# Experiment directory
python bin/ont_init.py experiment EXP-001

# Generate config file
python bin/ont_init.py config --type full > config.yaml
```

## Code Style

- Follow PEP 8 with 100 character line limit
- Use type hints for function parameters and return values
- Document public functions with docstrings
- Use meaningful variable names
- Keep functions focused and small

## Release Process

1. Update version in `VERSION`, `lib/__init__.py`, `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create git tag
5. Push to GitHub

```bash
# Bump version
python bin/ont_version.py bump minor

# Verify tests pass
python -m pytest tests/ -v

# Tag release
git tag -a v3.1.0 -m "Release v3.1.0"
git push origin v3.1.0
```

## Getting Help

- `python bin/ont_help.py` - List all commands
- `python bin/ont_help.py <command>` - Help for specific command
- `python bin/ont_doctor.py` - Diagnose issues
- Create issue on GitHub for bugs or feature requests
