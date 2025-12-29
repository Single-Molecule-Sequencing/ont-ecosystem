# ONT Ecosystem API Reference

This document provides API reference for the `lib/` modules.

## lib.cli - CLI Utilities

Terminal colors, progress indicators, and formatting helpers.

### Colors

```python
from lib.cli import Colors, colorize, supports_color

# Check color support
if supports_color():
    print(Colors.GREEN + "Success!" + Colors.RESET)

# Colorize helper
print(colorize("Error!", Colors.RED, Colors.BOLD))
```

Available colors:
- `Colors.RESET`, `Colors.BOLD`, `Colors.DIM`, `Colors.UNDERLINE`
- `Colors.BLACK`, `Colors.RED`, `Colors.GREEN`, `Colors.YELLOW`
- `Colors.BLUE`, `Colors.MAGENTA`, `Colors.CYAN`, `Colors.WHITE`
- `Colors.BRIGHT_RED`, `Colors.BRIGHT_GREEN`, etc.

### Argument Helpers

```python
from lib.cli import add_common_args, add_output_args, add_force_args

parser = argparse.ArgumentParser()
add_common_args(parser)    # --verbose, --quiet, --debug
add_output_args(parser)    # --json, --output, --format
add_force_args(parser)     # --force, --dry-run
```

### Output Functions

```python
from lib.cli import (
    print_header, print_section, print_success, print_error,
    print_warning, print_info, print_item, print_list
)

print_header("Processing Files")
print_success("All files processed!")
print_error("Failed to process file")
print_warning("File may be corrupted")
print_info("Processing 42 files...")
print_item("Count", 42)
print_list(["item1", "item2", "item3"])
```

### Table Formatting

```python
from lib.cli import print_table

headers = ["Name", "Status", "Count"]
rows = [
    ["exp-001", "complete", 1234],
    ["exp-002", "running", 567],
]
print_table(headers, rows, alignments=["l", "l", "r"])
```

### Progress Indicators

```python
from lib.cli import ProgressBar, Spinner

# Progress bar
with ProgressBar(total=100, desc="Processing") as bar:
    for i in range(100):
        do_work(i)
        bar.update(1)

# Spinner for indeterminate progress
with Spinner("Loading..."):
    long_operation()
```

### Formatting

```python
from lib.cli import format_size, format_duration, format_number, truncate

format_size(1234567890)    # "1.1 GB"
format_duration(125.5)     # "2m 5s"
format_number(1234567)     # "1.2M"
truncate("Long text...", 10)  # "Long te..."
```

---

## lib.io - I/O Utilities

File operations, serialization, and data handling.

### JSON Operations

```python
from lib.io import load_json, save_json

# Load with default
data = load_json("config.json", default={})

# Save with atomic write
save_json("output.json", data, indent=2, atomic=True)
```

### YAML Operations

```python
from lib.io import load_yaml, save_yaml

config = load_yaml("config.yaml", default={})
save_yaml("output.yaml", config, atomic=True)
```

### Safe File Operations

```python
from lib.io import atomic_write, safe_write, ensure_dir

# Atomic write (temp file + rename)
with atomic_write("output.txt") as f:
    f.write("content")

# Safe write with optional backup
safe_write("file.txt", "content", backup=True)

# Ensure directory exists
ensure_dir("/path/to/dir")
```

### File Discovery

```python
from lib.io import find_files, list_dir

# Find files by pattern
bam_files = find_files("*.bam", path="/data", recursive=True)

# List directory
dirs = list_dir("/data", dirs_only=True)
files = list_dir("/data", pattern="*.txt", files_only=True)
```

### Checksums

```python
from lib.io import checksum, verify_checksum

# Calculate checksum
sha256 = checksum("/path/to/file", algorithm="sha256")

# Verify checksum
if verify_checksum("/path/to/file", expected_hash):
    print("File integrity verified")
```

### Text File Utilities

```python
from lib.io import read_lines, write_lines

# Read lines with filtering
lines = read_lines("data.txt", skip_empty=True, skip_comments=True)

# Write lines
write_lines("output.txt", ["line1", "line2"], atomic=True)
```

### Temporary Files

```python
from lib.io import temp_file, temp_dir

# Temporary file (deleted on exit)
with temp_file(suffix=".json") as tmp:
    save_json(tmp, data)
    process(tmp)

# Temporary directory
with temp_dir() as tmpdir:
    process_files_in(tmpdir)
```

---

## lib.cache - Caching Utilities

Memory and file-based caching with TTL support.

### Memory Cache

```python
from lib.cache import MemoryCache

cache = MemoryCache(default_ttl=3600)  # 1 hour TTL

# Get/set
cache.set("key", value, ttl=600)  # 10 minute TTL
value = cache.get("key", default=None)

# Check existence
if cache.has("key"):
    value = cache.get("key")

# Delete
cache.delete("key")
cache.clear()
```

### File Cache

```python
from lib.cache import FileCache

cache = FileCache("my_namespace", default_ttl=86400)  # 1 day

# Same API as MemoryCache
cache.set("key", {"data": "value"})
data = cache.get("key")

# Clean expired entries
removed = cache.cleanup()
```

### Decorators

```python
from lib.cache import memoize, timed_cache

# Simple memoization (no TTL)
@memoize
def expensive_computation(x, y):
    return compute(x, y)

# Time-limited cache
@timed_cache(ttl=300)  # 5 minutes
def fetch_remote_data(url):
    return requests.get(url).json()
```

---

## lib.validation - Validation Utilities

Data validation and schema checking.

### Path Validation

```python
from lib.validation import validate_path

# Returns Path or raises ValidationError
path = validate_path(
    "/path/to/file",
    must_exist=True,
    must_be_file=True,
    allowed_extensions=[".bam", ".sam"]
)
```

### Experiment ID Validation

```python
from lib.validation import validate_experiment_id

# Validates format, raises ValidationError if invalid
validate_experiment_id("EXP-001")
```

### Schema Validation

```python
from lib.validation import Schema, ValidationResult

schema = Schema({
    "required": ["name", "type"],
    "properties": {
        "name": {"type": "string", "min_length": 1},
        "count": {"type": "number", "min": 0, "default": 0},
        "tags": {"type": "array"}
    }
})

# Validate data
result = schema.validate(data)
if result.valid:
    print("Valid!")
else:
    for error in result.errors:
        print(f"Error: {error}")

# Apply defaults
data_with_defaults = schema.apply_defaults(data)
```

### Chainable Validator

```python
from lib.validation import Validator

result = (Validator(data)
    .require("name")
    .require("email")
    .check_type("name", str)
    .check_type("count", int)
    .in_range("count", 0, 100)
    .matches("email", r"^[\w.-]+@[\w.-]+\.\w+$")
    .one_of("status", ["pending", "active", "complete"])
    .custom("data", lambda x: len(x) > 0, "Data must not be empty")
    .result())

if not result.valid:
    for error in result.errors:
        print(error)
```

---

## lib.errors - Error Classes

Standardized error handling.

### Error Classes

```python
from lib.errors import (
    ONTError,           # Base class
    ValidationError,    # Input validation failures
    ConfigurationError, # Configuration issues
    FileNotFoundError,  # Missing files
    AnalysisError,      # Analysis failures
    PipelineError,      # Pipeline execution errors
    NetworkError,       # Network/API issues
)

# Raise with context
raise ValidationError(
    message="Invalid experiment ID",
    code="INVALID_EXP_ID",
    details={"id": exp_id, "pattern": "EXP-\\d{3}"},
    suggestions=["Use format: EXP-001", "Run ont_check.py to validate"]
)
```

### Error Handler

```python
from lib.errors import handle_error

try:
    risky_operation()
except Exception as e:
    # Logs error and optionally re-raises
    handle_error(e, exit_code=1, log=True)
```

### Error Formatting

```python
from lib.errors import ONTError

error = ValidationError("Invalid input")
print(error.to_dict())  # JSON-serializable dict
print(error.format())   # Human-readable string
```

---

## lib.timing - Timing Utilities

Performance measurement and timing.

### Timer Context Manager

```python
from lib.timing import Timer

with Timer("Processing files") as t:
    process_files()

print(f"Took {t.elapsed:.2f} seconds")
```

### Timing Decorator

```python
from lib.timing import timed

@timed
def my_function():
    do_work()

# Logs: "my_function completed in 1.234s"
```

### Step Timer

```python
from lib.timing import StepTimer

timer = StepTimer()
timer.start("Loading data")
load_data()
timer.stop()

timer.start("Processing")
process_data()
timer.stop()

timer.summary()  # Prints timing summary
```

### Duration Formatting

```python
from lib.timing import format_duration

format_duration(0.001)    # "1.0ms"
format_duration(65.5)     # "1m 5s"
format_duration(3725)     # "1h 2m"
```

---

## lib.logging_config - Logging

Logging configuration and setup.

### Setup Logging

```python
from lib import setup_logging, get_logger

# Configure logging
setup_logging(
    level="INFO",           # DEBUG, INFO, WARNING, ERROR
    log_file="app.log",     # Optional file output
    json_format=False,      # Use JSON format
    include_timestamp=True
)

# Get module logger
logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Error with traceback")
```

---

## Lazy Imports

All library functions can be imported directly from `lib`:

```python
from lib import (
    # I/O
    load_json, save_json, load_yaml, save_yaml,
    atomic_write, checksum,

    # CLI
    print_header, print_table, ProgressBar,
    format_size, format_duration,

    # Cache
    FileCache, MemoryCache, memoize,

    # Validation
    validate_path, validate_experiment_id,
    Schema, Validator,

    # Errors
    ONTError, ValidationError, handle_error,

    # Timing
    Timer, timed,

    # Logging
    get_logger, setup_logging,
)
```

These use lazy imports to minimize startup overhead - the actual module is only loaded when the function is first called.
