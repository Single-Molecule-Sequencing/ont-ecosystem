"""
ONT Ecosystem I/O Utilities - File handling and data serialization

Usage:
    from lib.io import (
        load_json, save_json, load_yaml, save_yaml,
        safe_write, atomic_write, ensure_dir,
        find_files, checksum
    )

    # Load/save data
    data = load_json("config.json")
    save_yaml("config.yaml", data)

    # Safe file operations
    with atomic_write("output.json") as f:
        json.dump(data, f)

    # File discovery
    files = find_files("*.bam", path="/data")
"""

import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Union

# Try to import yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# JSON Operations
# =============================================================================

def load_json(
    path: Union[str, Path],
    default: Any = None,
    encoding: str = "utf-8"
) -> Any:
    """
    Load JSON file.

    Args:
        path: File path
        default: Default value if file doesn't exist
        encoding: File encoding

    Returns:
        Parsed JSON data or default
    """
    path = Path(path)
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        if default is not None:
            return default
        raise


def save_json(
    path: Union[str, Path],
    data: Any,
    indent: int = 2,
    encoding: str = "utf-8",
    atomic: bool = True,
    default: Optional[Callable] = None
) -> None:
    """
    Save data to JSON file.

    Args:
        path: File path
        data: Data to save
        indent: JSON indentation
        encoding: File encoding
        atomic: Use atomic write
        default: JSON serializer for custom types
    """
    path = Path(path)

    # Default serializer for common types
    def json_default(obj):
        if default:
            try:
                return default(obj)
            except TypeError:
                pass
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    content = json.dumps(data, indent=indent, default=json_default)

    if atomic:
        with atomic_write(path, mode="w", encoding=encoding) as f:
            f.write(content)
    else:
        with open(path, "w", encoding=encoding) as f:
            f.write(content)


# =============================================================================
# YAML Operations
# =============================================================================

def load_yaml(
    path: Union[str, Path],
    default: Any = None,
    encoding: str = "utf-8"
) -> Any:
    """
    Load YAML file.

    Args:
        path: File path
        default: Default value if file doesn't exist
        encoding: File encoding

    Returns:
        Parsed YAML data or default
    """
    if not HAS_YAML:
        raise ImportError("pyyaml is required for YAML operations")

    path = Path(path)
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding=encoding) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError) as e:
        if default is not None:
            return default
        raise


def save_yaml(
    path: Union[str, Path],
    data: Any,
    encoding: str = "utf-8",
    atomic: bool = True,
    default_flow_style: bool = False
) -> None:
    """
    Save data to YAML file.

    Args:
        path: File path
        data: Data to save
        encoding: File encoding
        atomic: Use atomic write
        default_flow_style: YAML flow style
    """
    if not HAS_YAML:
        raise ImportError("pyyaml is required for YAML operations")

    path = Path(path)

    if atomic:
        with atomic_write(path, mode="w", encoding=encoding) as f:
            yaml.dump(data, f, default_flow_style=default_flow_style)
    else:
        with open(path, "w", encoding=encoding) as f:
            yaml.dump(data, f, default_flow_style=default_flow_style)


# =============================================================================
# Safe File Operations
# =============================================================================

@contextmanager
def atomic_write(
    path: Union[str, Path],
    mode: str = "w",
    encoding: Optional[str] = "utf-8",
    suffix: str = ".tmp"
) -> Generator:
    """
    Context manager for atomic file writes.

    Writes to a temporary file and renames on success.
    The original file is preserved if an error occurs.

    Usage:
        with atomic_write("output.json") as f:
            json.dump(data, f)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory for atomic rename
    fd, tmp_path = tempfile.mkstemp(
        suffix=suffix,
        dir=path.parent,
        prefix=f".{path.name}."
    )

    try:
        if "b" in mode:
            with os.fdopen(fd, mode) as f:
                yield f
        else:
            with os.fdopen(fd, mode, encoding=encoding) as f:
                yield f

        # Rename temp file to target
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def safe_write(
    path: Union[str, Path],
    content: Union[str, bytes],
    backup: bool = False,
    encoding: str = "utf-8"
) -> None:
    """
    Safely write content to file with optional backup.

    Args:
        path: File path
        content: Content to write
        backup: Create backup of existing file
        encoding: File encoding (for str content)
    """
    path = Path(path)

    # Create backup if requested
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

    # Write content
    mode = "wb" if isinstance(content, bytes) else "w"
    enc = None if isinstance(content, bytes) else encoding

    with atomic_write(path, mode=mode, encoding=enc) as f:
        f.write(content)


def ensure_dir(path: Union[str, Path], mode: int = 0o755) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path
        mode: Directory permissions

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path


def safe_remove(path: Union[str, Path]) -> bool:
    """
    Safely remove file or directory.

    Args:
        path: Path to remove

    Returns:
        True if removed, False if not found
    """
    path = Path(path)

    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            return False
        return True
    except OSError:
        return False


# =============================================================================
# File Discovery
# =============================================================================

def find_files(
    pattern: str,
    path: Optional[Union[str, Path]] = None,
    recursive: bool = True,
    include_hidden: bool = False
) -> List[Path]:
    """
    Find files matching pattern.

    Args:
        pattern: Glob pattern (e.g., "*.bam", "**/*.py")
        path: Base directory (default: current)
        recursive: Search recursively
        include_hidden: Include hidden files

    Returns:
        List of matching paths
    """
    base = Path(path) if path else Path.cwd()

    if recursive and "**" not in pattern:
        pattern = f"**/{pattern}"

    files = list(base.glob(pattern))

    if not include_hidden:
        files = [f for f in files if not any(p.startswith(".") for p in f.parts)]

    return sorted(files)


def list_dir(
    path: Union[str, Path],
    pattern: str = "*",
    dirs_only: bool = False,
    files_only: bool = False
) -> List[Path]:
    """
    List directory contents.

    Args:
        path: Directory path
        pattern: Glob pattern
        dirs_only: Only return directories
        files_only: Only return files

    Returns:
        List of paths
    """
    base = Path(path)
    items = list(base.glob(pattern))

    if dirs_only:
        items = [p for p in items if p.is_dir()]
    elif files_only:
        items = [p for p in items if p.is_file()]

    return sorted(items)


# =============================================================================
# Checksums
# =============================================================================

def checksum(
    path: Union[str, Path],
    algorithm: str = "sha256",
    chunk_size: int = 8192
) -> str:
    """
    Calculate file checksum.

    Args:
        path: File path
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    hasher = hashlib.new(algorithm)

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_checksum(
    path: Union[str, Path],
    expected: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Verify file checksum.

    Args:
        path: File path
        expected: Expected checksum
        algorithm: Hash algorithm

    Returns:
        True if checksum matches
    """
    actual = checksum(path, algorithm)
    return actual.lower() == expected.lower()


# =============================================================================
# File Metadata
# =============================================================================

def file_info(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get file information.

    Args:
        path: File path

    Returns:
        Dictionary with file info
    """
    path = Path(path)
    stat = path.stat()

    return {
        "path": str(path.absolute()),
        "name": path.name,
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "extension": path.suffix,
    }


def dir_size(path: Union[str, Path]) -> int:
    """
    Calculate total directory size.

    Args:
        path: Directory path

    Returns:
        Total size in bytes
    """
    path = Path(path)
    total = 0

    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size

    return total


# =============================================================================
# Text File Utilities
# =============================================================================

def read_lines(
    path: Union[str, Path],
    strip: bool = True,
    skip_empty: bool = False,
    skip_comments: bool = False,
    comment_char: str = "#",
    encoding: str = "utf-8"
) -> List[str]:
    """
    Read lines from text file.

    Args:
        path: File path
        strip: Strip whitespace from lines
        skip_empty: Skip empty lines
        skip_comments: Skip comment lines
        comment_char: Comment character
        encoding: File encoding

    Returns:
        List of lines
    """
    with open(path, "r", encoding=encoding) as f:
        lines = f.readlines()

    result = []
    for line in lines:
        if strip:
            line = line.strip()
        if skip_empty and not line:
            continue
        if skip_comments and line.startswith(comment_char):
            continue
        result.append(line)

    return result


def write_lines(
    path: Union[str, Path],
    lines: List[str],
    newline: str = "\n",
    encoding: str = "utf-8",
    atomic: bool = True
) -> None:
    """
    Write lines to text file.

    Args:
        path: File path
        lines: Lines to write
        newline: Line ending
        encoding: File encoding
        atomic: Use atomic write
    """
    content = newline.join(lines)
    if not content.endswith(newline):
        content += newline

    if atomic:
        with atomic_write(path, mode="w", encoding=encoding) as f:
            f.write(content)
    else:
        with open(path, "w", encoding=encoding) as f:
            f.write(content)


# =============================================================================
# Temporary Files
# =============================================================================

@contextmanager
def temp_file(
    suffix: str = "",
    prefix: str = "ont_",
    dir: Optional[Union[str, Path]] = None,
    delete: bool = True
) -> Generator[Path, None, None]:
    """
    Context manager for temporary file.

    Usage:
        with temp_file(suffix=".json") as tmp:
            save_json(tmp, data)
            process(tmp)
    """
    fd, path = tempfile.mkstemp(
        suffix=suffix,
        prefix=prefix,
        dir=str(dir) if dir else None
    )
    os.close(fd)
    path = Path(path)

    try:
        yield path
    finally:
        if delete and path.exists():
            path.unlink()


@contextmanager
def temp_dir(
    suffix: str = "",
    prefix: str = "ont_",
    dir: Optional[Union[str, Path]] = None,
    delete: bool = True
) -> Generator[Path, None, None]:
    """
    Context manager for temporary directory.

    Usage:
        with temp_dir() as tmpdir:
            process_files_in(tmpdir)
    """
    path = tempfile.mkdtemp(
        suffix=suffix,
        prefix=prefix,
        dir=str(dir) if dir else None
    )
    path = Path(path)

    try:
        yield path
    finally:
        if delete and path.exists():
            shutil.rmtree(path)
