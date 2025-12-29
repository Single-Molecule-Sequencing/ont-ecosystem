"""Tests for lib/ modules: errors, cache, validation"""

import sys
import tempfile
import time
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))


# =============================================================================
# lib/errors.py Tests
# =============================================================================

def test_errors_imports():
    """Test that errors.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "errors",
        lib_dir / "errors.py"
    )
    errors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(errors)

    assert hasattr(errors, 'ONTError')
    assert hasattr(errors, 'ValidationError')
    assert hasattr(errors, 'ConfigurationError')
    assert hasattr(errors, 'AnalysisError')
    assert hasattr(errors, 'ErrorSeverity')
    assert hasattr(errors, 'ErrorCategory')


def test_ont_error_basic():
    """Test ONTError basic functionality"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "errors",
        lib_dir / "errors.py"
    )
    errors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(errors)

    err = errors.ONTError("Test error message")
    assert str(err) == "Test error message"
    assert err.code == "ONT_ERROR"
    assert err.severity == errors.ErrorSeverity.ERROR


def test_ont_error_with_details():
    """Test ONTError with details"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "errors",
        lib_dir / "errors.py"
    )
    errors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(errors)

    err = errors.ONTError(
        "Test error",
        code="TEST_001",
        details={"key": "value"},
        suggestions=["Try this", "Or this"]
    )
    assert err.code == "TEST_001"
    assert err.details["key"] == "value"
    assert len(err.suggestions) == 2


def test_validation_error():
    """Test ValidationError"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "errors",
        lib_dir / "errors.py"
    )
    errors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(errors)

    err = errors.ValidationError(
        "Invalid value",
        field="count",
        value="-5",
        expected="positive integer"
    )
    assert err.code == "VALIDATION_ERROR"
    assert err.details["field"] == "count"
    assert err.details["expected"] == "positive integer"


def test_error_to_dict():
    """Test error serialization to dict"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "errors",
        lib_dir / "errors.py"
    )
    errors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(errors)

    err = errors.ONTError("Test", code="TEST")
    d = err.to_dict()
    assert "error" in d
    assert "code" in d
    assert "message" in d
    assert "severity" in d


# =============================================================================
# lib/cache.py Tests
# =============================================================================

def test_cache_imports():
    """Test that cache.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache)

    assert hasattr(cache, 'MemoryCache')
    assert hasattr(cache, 'FileCache')
    assert hasattr(cache, 'memoize')
    assert hasattr(cache, 'timed_cache')
    assert hasattr(cache, 'disk_cache')


def test_memory_cache_basic():
    """Test MemoryCache basic operations"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    cache = cache_mod.MemoryCache()

    # Set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Has
    assert cache.has("key1")
    assert not cache.has("nonexistent")

    # Default value
    assert cache.get("nonexistent", "default") == "default"

    # Delete
    assert cache.delete("key1")
    assert not cache.has("key1")


def test_memory_cache_ttl():
    """Test MemoryCache TTL expiration"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    cache = cache_mod.MemoryCache()
    cache.set("key1", "value1", ttl=0.1)  # 100ms TTL

    assert cache.has("key1")
    time.sleep(0.15)
    assert not cache.has("key1")


def test_memory_cache_stats():
    """Test MemoryCache statistics"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    cache = cache_mod.MemoryCache()
    cache.set("key1", "value1")
    cache.get("key1")  # Hit
    cache.get("key1")  # Hit
    cache.get("nonexistent")  # Miss

    stats = cache.stats
    assert stats["size"] == 1
    assert stats["hits"] == 2
    assert stats["misses"] == 1


def test_file_cache_basic():
    """Test FileCache basic operations"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = cache_mod.FileCache("test", cache_dir=Path(tmpdir))

        # Set and get
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

        # Has
        assert cache.has("key1")

        # Delete
        assert cache.delete("key1")
        assert not cache.has("key1")


def test_memoize_decorator():
    """Test memoize decorator"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    call_count = 0

    @cache_mod.memoize
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert expensive_function(5) == 10
    assert expensive_function(5) == 10  # Cached
    assert call_count == 1  # Only called once


def test_timed_cache_decorator():
    """Test timed_cache decorator"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cache",
        lib_dir / "cache.py"
    )
    cache_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_mod)

    call_count = 0

    @cache_mod.timed_cache(ttl=0.1)
    def get_data():
        nonlocal call_count
        call_count += 1
        return "data"

    assert get_data() == "data"
    assert get_data() == "data"  # Cached
    assert call_count == 1

    time.sleep(0.15)
    get_data()  # Cache expired
    assert call_count == 2


# =============================================================================
# lib/validation.py Tests
# =============================================================================

def test_validation_imports():
    """Test that validation.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    assert hasattr(validation, 'validate_path')
    assert hasattr(validation, 'validate_experiment_id')
    assert hasattr(validation, 'validate_required')
    assert hasattr(validation, 'Schema')
    assert hasattr(validation, 'Validator')


def test_validate_path():
    """Test validate_path function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    # Valid path (doesn't need to exist)
    result = validation.validate_path("/some/path")
    assert result.valid

    # Must exist (fails for nonexistent)
    result = validation.validate_path("/nonexistent/path", must_exist=True)
    assert not result.valid
    assert len(result.errors) == 1

    # Extension check
    result = validation.validate_path("file.txt", extensions=[".bam", ".fastq"])
    assert not result.valid


def test_validate_experiment_id():
    """Test validate_experiment_id function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    # Valid IDs
    assert validation.validate_experiment_id("exp-abc123").valid
    assert validation.validate_experiment_id("test_experiment").valid
    assert validation.validate_experiment_id("EXP-2024-001").valid

    # Invalid IDs
    assert not validation.validate_experiment_id("").valid
    assert not validation.validate_experiment_id("exp with spaces").valid
    assert not validation.validate_experiment_id("exp@special").valid


def test_validate_required():
    """Test validate_required function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    assert validation.validate_required("value", "field").valid
    assert not validation.validate_required(None, "field").valid
    assert not validation.validate_required("", "field").valid
    assert validation.validate_required("", "field", allow_empty=True).valid


def test_schema_validation():
    """Test Schema validation"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    schema = validation.Schema({
        "name": {"type": str, "required": True, "min_length": 1},
        "count": {"type": int, "min": 0, "max": 100},
        "tags": {"type": list, "items": str},
    })

    # Valid data
    result = schema.validate({
        "name": "test",
        "count": 50,
        "tags": ["a", "b"]
    })
    assert result.valid

    # Missing required field
    result = schema.validate({"count": 50})
    assert not result.valid

    # Wrong type
    result = schema.validate({"name": "test", "count": "not a number"})
    assert not result.valid

    # Out of range
    result = schema.validate({"name": "test", "count": 150})
    assert not result.valid


def test_validator_chainable():
    """Test Validator chainable interface"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    data = {
        "name": "test",
        "count": 50,
        "status": "active"
    }

    result = (validation.Validator(data)
        .require("name")
        .require("count")
        .check_type("count", int)
        .check_range("count", min_value=0, max_value=100)
        .check_choices("status", ["active", "inactive"])
        .result())

    assert result.valid

    # Test failure
    bad_data = {"name": "", "count": -5}
    result = (validation.Validator(bad_data)
        .require("name")
        .check_range("count", min_value=0)
        .result())

    assert not result.valid


def test_schema_defaults():
    """Test Schema apply_defaults"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "validation",
        lib_dir / "validation.py"
    )
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)

    schema = validation.Schema({
        "name": {"type": str, "required": True},
        "count": {"type": int, "default": 0},
        "enabled": {"type": bool, "default": True},
    })

    data = {"name": "test"}
    result = schema.apply_defaults(data)

    assert result["name"] == "test"
    assert result["count"] == 0
    assert result["enabled"] is True


# =============================================================================
# lib exports Tests
# =============================================================================

def test_lib_exports_errors():
    """Test that lib exports error utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'ONTError')
    assert hasattr(lib, 'handle_error')


def test_lib_exports_cache():
    """Test that lib exports cache utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'FileCache')
    assert hasattr(lib, 'MemoryCache')
    assert hasattr(lib, 'memoize')


def test_lib_exports_validation():
    """Test that lib exports validation utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'validate_path')
    assert hasattr(lib, 'validate_experiment_id')
    assert hasattr(lib, 'Schema')
    assert hasattr(lib, 'Validator')


# =============================================================================
# lib/cli.py Tests
# =============================================================================

def test_cli_imports():
    """Test that cli.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert hasattr(cli, 'add_common_args')
    assert hasattr(cli, 'print_header')
    assert hasattr(cli, 'print_table')
    assert hasattr(cli, 'ProgressBar')
    assert hasattr(cli, 'Spinner')
    assert hasattr(cli, 'format_size')


def test_cli_add_common_args():
    """Test add_common_args adds expected arguments"""
    import importlib.util
    import argparse
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    parser = argparse.ArgumentParser()
    cli.add_common_args(parser)

    # Parse empty args should work
    args = parser.parse_args([])
    assert hasattr(args, 'verbose')
    assert hasattr(args, 'quiet')
    assert hasattr(args, 'debug')


def test_cli_format_size():
    """Test format_size function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert "B" in cli.format_size(500)
    assert "KB" in cli.format_size(1500)
    assert "MB" in cli.format_size(1500000)
    assert "GB" in cli.format_size(1500000000)


def test_cli_format_duration():
    """Test format_duration function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert "µs" in cli.format_duration(0.0001)
    assert "ms" in cli.format_duration(0.1)
    assert "s" in cli.format_duration(5)
    assert "m" in cli.format_duration(90)
    assert "h" in cli.format_duration(3700)


def test_cli_format_number():
    """Test format_number function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.format_number(500) == "500"
    assert "K" in cli.format_number(1500)
    assert "M" in cli.format_number(1500000)
    assert "G" in cli.format_number(1500000000)


def test_cli_truncate():
    """Test truncate function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.truncate("short", 10) == "short"
    assert cli.truncate("this is a long string", 10) == "this is..."
    assert len(cli.truncate("this is a long string", 10)) == 10


def test_cli_colors():
    """Test Colors class"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "cli",
        lib_dir / "cli.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    # Colors class should exist
    assert hasattr(cli, 'Colors')
    assert hasattr(cli.Colors, 'RED')
    assert hasattr(cli.Colors, 'GREEN')
    assert hasattr(cli.Colors, 'RESET')


# =============================================================================
# lib/io.py Tests
# =============================================================================

def test_io_imports():
    """Test that io.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    assert hasattr(io_mod, 'load_json')
    assert hasattr(io_mod, 'save_json')
    assert hasattr(io_mod, 'atomic_write')
    assert hasattr(io_mod, 'checksum')
    assert hasattr(io_mod, 'find_files')


def test_io_json_operations():
    """Test JSON load/save"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"
        data = {"key": "value", "number": 42}

        # Save
        io_mod.save_json(test_file, data)
        assert test_file.exists()

        # Load
        loaded = io_mod.load_json(test_file)
        assert loaded == data


def test_io_json_default():
    """Test JSON load with default value"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    # Non-existent file with default
    result = io_mod.load_json("/nonexistent/file.json", default={"default": True})
    assert result == {"default": True}


def test_io_atomic_write():
    """Test atomic write context manager"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        with io_mod.atomic_write(test_file) as f:
            f.write("test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"


def test_io_checksum():
    """Test checksum function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")

        # Calculate checksum
        cs = io_mod.checksum(test_file, algorithm="sha256")
        assert isinstance(cs, str)
        assert len(cs) == 64  # SHA256 hex digest length

        # Verify checksum
        assert io_mod.verify_checksum(test_file, cs)


def test_io_find_files():
    """Test find_files function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "file1.txt").touch()
        (Path(tmpdir) / "file2.txt").touch()
        (Path(tmpdir) / "file3.py").touch()

        # Find txt files
        files = io_mod.find_files("*.txt", path=tmpdir)
        assert len(files) == 2


def test_io_temp_file():
    """Test temp_file context manager"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with io_mod.temp_file(suffix=".txt") as tmp:
        assert isinstance(tmp, Path)
        tmp.write_text("test")
        assert tmp.exists()

    # Should be deleted after context
    assert not tmp.exists()


def test_io_temp_dir():
    """Test temp_dir context manager"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with io_mod.temp_dir() as tmpdir:
        assert isinstance(tmpdir, Path)
        assert tmpdir.exists()
        (tmpdir / "test.txt").touch()

    # Should be deleted after context
    assert not tmpdir.exists()


def test_io_read_lines():
    """Test read_lines function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "io_mod",
        lib_dir / "io.py"
    )
    io_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io_mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("line1\nline2\n# comment\n\nline3")

        # Read all lines
        lines = io_mod.read_lines(test_file)
        assert len(lines) == 5

        # Skip empty and comments
        lines = io_mod.read_lines(test_file, skip_empty=True, skip_comments=True)
        assert len(lines) == 3


def test_lib_exports_cli():
    """Test that lib exports CLI utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'add_common_args')
    assert hasattr(lib, 'print_header')
    assert hasattr(lib, 'print_table')
    assert hasattr(lib, 'ProgressBar')


def test_lib_exports_io():
    """Test that lib exports I/O utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'load_json')
    assert hasattr(lib, 'save_json')
    assert hasattr(lib, 'atomic_write')
    assert hasattr(lib, 'checksum')


# =============================================================================
# lib/config.py Tests
# =============================================================================

def test_config_imports():
    """Test that config.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)

    assert hasattr(config, 'Config')
    assert hasattr(config, 'get_config')
    assert hasattr(config, 'load_config')
    assert hasattr(config, 'save_config')
    assert hasattr(config, 'get_project_config')


def test_config_class():
    """Test Config class functionality"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    # Create config with values
    cfg = config_mod.Config(config={"basecalling": {"model": "hac"}})

    # Test get with dot notation
    assert cfg.get("basecalling.model") == "hac"

    # Test default value
    assert cfg.get("nonexistent.key", "default") == "default"

    # Test set
    cfg.set("analysis.threads", 8)
    assert cfg.get("analysis.threads") == 8


def test_config_defaults():
    """Test that DEFAULT_CONFIG is valid"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    defaults = config_mod.DEFAULT_CONFIG
    assert "version" in defaults
    assert "basecalling" in defaults
    assert "alignment" in defaults
    assert "github" in defaults


def test_config_to_dict():
    """Test Config.to_dict()"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    cfg = config_mod.Config(config={"custom": "value"})
    d = cfg.to_dict()

    assert isinstance(d, dict)
    assert "basecalling" in d  # From defaults
    assert "custom" in d       # From config


def test_config_environment_detection():
    """Test environment detection functions"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    # Test detect_environment
    env = config_mod.detect_environment()
    assert "platform" in env
    assert "python_version" in env
    assert "hpc" in env
    assert isinstance(env["hpc"], bool)


def test_config_path_functions():
    """Test configuration path functions"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "config",
        lib_dir / "config.py"
    )
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    # Test path functions return Path objects
    user_dir = config_mod.get_user_config_dir()
    assert isinstance(user_dir, Path)

    user_path = config_mod.get_user_config_path()
    assert isinstance(user_path, Path)
    assert user_path.name == "config.yaml"


def test_lib_exports_config():
    """Test that lib exports config utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'get_config')
    assert hasattr(lib, 'load_config')
    assert hasattr(lib, 'save_config')
    assert hasattr(lib, 'Config')


# =============================================================================
# lib/parallel.py Tests
# =============================================================================

def test_parallel_imports():
    """Test that parallel.py can be imported"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    assert hasattr(parallel, 'parallel_map')
    assert hasattr(parallel, 'parallel_process_files')
    assert hasattr(parallel, 'TaskQueue')
    assert hasattr(parallel, 'chunked')
    assert hasattr(parallel, 'with_retry')


def test_parallel_map():
    """Test parallel_map function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    # Simple test
    def square(x):
        return x * x

    items = [1, 2, 3, 4, 5]
    results = parallel.parallel_map(square, items, workers=2)

    assert results == [1, 4, 9, 16, 25]


def test_parallel_chunked():
    """Test chunked function"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    items = [1, 2, 3, 4, 5, 6, 7]
    chunks = list(parallel.chunked(items, 3))

    assert len(chunks) == 3
    assert chunks[0] == [1, 2, 3]
    assert chunks[1] == [4, 5, 6]
    assert chunks[2] == [7]


def test_parallel_task_result():
    """Test TaskResult dataclass"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    # Success result
    result = parallel.TaskResult(task_id="test", success=True, result=42)
    assert bool(result) is True
    assert result.result == 42

    # Failed result
    result = parallel.TaskResult(task_id="test", success=False, error=ValueError("test"))
    assert bool(result) is False


def test_parallel_batch_result():
    """Test BatchResult dataclass"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    results = [
        parallel.TaskResult(task_id="1", success=True),
        parallel.TaskResult(task_id="2", success=True),
        parallel.TaskResult(task_id="3", success=False),
    ]

    batch = parallel.BatchResult(
        total=3,
        succeeded=2,
        failed=1,
        results=results,
        duration=1.5
    )

    assert batch.success_rate == 2/3
    assert len(batch.failures()) == 1
    assert len(batch.successes()) == 2


def test_parallel_with_retry():
    """Test with_retry wrapper"""
    import importlib.util
    lib_dir = Path(__file__).parent.parent / 'lib'
    spec = importlib.util.spec_from_file_location(
        "parallel",
        lib_dir / "parallel.py"
    )
    parallel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parallel)

    call_count = 0

    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Flaky!")
        return "success"

    wrapped = parallel.with_retry(flaky_function, max_retries=3, delay=0.01)
    result = wrapped()

    assert result == "success"
    assert call_count == 3


def test_lib_exports_parallel():
    """Test that lib exports parallel utilities"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir.parent))

    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert hasattr(lib, 'parallel_map')
    assert hasattr(lib, 'parallel_process_files')
    assert hasattr(lib, 'TaskQueue')
    assert hasattr(lib, 'chunked')
    assert hasattr(lib, 'with_retry')
