"""
ONT Ecosystem CLI Utilities - Common CLI patterns and helpers

Usage:
    from lib.cli import (
        add_common_args, add_output_args, add_verbose_args,
        print_header, print_table, print_success, print_error,
        confirm, ProgressBar, Spinner
    )

    # Add common arguments
    add_common_args(parser)
    add_output_args(parser)

    # Formatted output
    print_header("Processing Files")
    print_success("Done!")
    print_error("Failed!")

    # Tables
    print_table(headers, rows)

    # Progress
    with ProgressBar(total=100) as bar:
        for i in range(100):
            bar.update(1)
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# Terminal Detection
# =============================================================================

def supports_color() -> bool:
    """Check if terminal supports color output"""
    # Check NO_COLOR environment variable
    if os.environ.get("NO_COLOR"):
        return False

    # Check TERM
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False

    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    return True


def terminal_width() -> int:
    """Get terminal width"""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


# =============================================================================
# ANSI Color Codes
# =============================================================================

class Colors:
    """ANSI color codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    @classmethod
    def disable(cls):
        """Disable all colors"""
        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                setattr(cls, attr, "")


# Disable colors if not supported
if not supports_color():
    Colors.disable()


def colorize(text: str, *codes: str) -> str:
    """Apply color codes to text"""
    if not supports_color():
        return text
    return "".join(codes) + text + Colors.RESET


# =============================================================================
# Argument Parsing Helpers
# =============================================================================

def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser"""
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-essential output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )


def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add output format arguments"""
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        metavar="FILE",
        help="Write output to file"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "csv", "tsv"],
        default="text",
        help="Output format (default: text)"
    )


def add_force_args(parser: argparse.ArgumentParser) -> None:
    """Add force/dry-run arguments"""
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operation without confirmation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Add common filter arguments"""
    parser.add_argument(
        "--tag", "-t",
        type=str,
        action="append",
        help="Filter by tag (can be repeated)"
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Filter by status"
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Filter by date (YYYY-MM-DD)"
    )


# =============================================================================
# Formatted Output
# =============================================================================

def print_header(
    title: str,
    char: str = "=",
    width: Optional[int] = None
) -> None:
    """Print a header with decoration"""
    width = width or min(terminal_width(), 70)
    print(char * width)
    print(f"  {title}")
    print(char * width)


def print_section(title: str, char: str = "-") -> None:
    """Print a section header"""
    width = min(terminal_width(), 70)
    print()
    print(char * width)
    print(title)
    print(char * width)


def print_success(message: str) -> None:
    """Print success message"""
    icon = colorize("✓", Colors.GREEN)
    print(f"{icon} {message}")


def print_error(message: str, file=None) -> None:
    """Print error message"""
    icon = colorize("✗", Colors.RED)
    print(f"{icon} {message}", file=file or sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message"""
    icon = colorize("⚠", Colors.YELLOW)
    print(f"{icon} {message}")


def print_info(message: str) -> None:
    """Print info message"""
    icon = colorize("ℹ", Colors.BLUE)
    print(f"{icon} {message}")


def print_item(key: str, value: Any, indent: int = 2) -> None:
    """Print a key-value item"""
    prefix = " " * indent
    key_str = colorize(f"{key}:", Colors.BOLD)
    print(f"{prefix}{key_str} {value}")


def print_list(items: List[str], indent: int = 2, bullet: str = "-") -> None:
    """Print a bullet list"""
    prefix = " " * indent
    for item in items:
        print(f"{prefix}{bullet} {item}")


# =============================================================================
# Table Formatting
# =============================================================================

def print_table(
    headers: List[str],
    rows: List[List[Any]],
    alignments: Optional[List[str]] = None,
    max_width: Optional[int] = None
) -> None:
    """
    Print a formatted table.

    Args:
        headers: Column headers
        rows: Table rows
        alignments: Column alignments ('l', 'r', 'c') per column
        max_width: Maximum table width
    """
    if not rows:
        print("(no data)")
        return

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Apply max width constraint
    if max_width:
        total = sum(col_widths) + len(col_widths) * 3 - 1
        if total > max_width:
            # Proportionally reduce column widths
            factor = max_width / total
            col_widths = [max(5, int(w * factor)) for w in col_widths]

    # Default alignments (left)
    if not alignments:
        alignments = ["l"] * len(headers)

    def format_cell(value: Any, width: int, align: str) -> str:
        """Format a cell value"""
        s = str(value)[:width]
        if align == "r":
            return s.rjust(width)
        elif align == "c":
            return s.center(width)
        return s.ljust(width)

    # Print header
    header_line = " | ".join(
        format_cell(h, col_widths[i], alignments[i])
        for i, h in enumerate(headers)
    )
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        row_line = " | ".join(
            format_cell(cell, col_widths[i], alignments[i])
            for i, cell in enumerate(row)
        )
        print(row_line)


def format_table_row(values: List[Any], widths: List[int]) -> str:
    """Format a single table row"""
    return " | ".join(
        str(v)[:w].ljust(w) for v, w in zip(values, widths)
    )


# =============================================================================
# User Interaction
# =============================================================================

def confirm(
    message: str,
    default: bool = False,
    force: bool = False
) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Question to ask
        default: Default answer if user just presses Enter
        force: If True, skip prompt and return True
    """
    if force:
        return True

    suffix = " [Y/n] " if default else " [y/N] "
    try:
        response = input(message + suffix).strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def prompt(
    message: str,
    default: Optional[str] = None,
    validator: Optional[Callable[[str], bool]] = None
) -> str:
    """
    Prompt user for input.

    Args:
        message: Prompt message
        default: Default value
        validator: Optional validation function
    """
    suffix = f" [{default}]: " if default else ": "

    while True:
        try:
            response = input(message + suffix).strip()
            if not response and default:
                return default
            if validator and not validator(response):
                print_error("Invalid input, please try again")
                continue
            return response
        except (EOFError, KeyboardInterrupt):
            print()
            return default or ""


def choose(
    message: str,
    options: List[str],
    default: int = 0
) -> int:
    """
    Let user choose from options.

    Args:
        message: Prompt message
        options: List of options
        default: Default option index

    Returns:
        Selected option index
    """
    print(message)
    for i, opt in enumerate(options):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {opt}")

    while True:
        try:
            response = input(f"Choice [1-{len(options)}]: ").strip()
            if not response:
                return default
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return idx
            print_error(f"Please enter 1-{len(options)}")
        except ValueError:
            print_error("Please enter a number")
        except (EOFError, KeyboardInterrupt):
            print()
            return default


# =============================================================================
# Progress Indicators
# =============================================================================

class ProgressBar:
    """
    Simple progress bar for terminal output.

    Usage:
        with ProgressBar(total=100, desc="Processing") as bar:
            for item in items:
                process(item)
                bar.update(1)
    """

    def __init__(
        self,
        total: int,
        desc: str = "",
        width: int = 40,
        show_percent: bool = True,
        show_count: bool = True
    ):
        self.total = total
        self.desc = desc
        self.width = width
        self.show_percent = show_percent
        self.show_count = show_count
        self.current = 0
        self.start_time = None
        self._is_tty = sys.stdout.isatty()

    def __enter__(self):
        self.start_time = time.time()
        self._render()
        return self

    def __exit__(self, *args):
        self._render(final=True)
        print()

    def update(self, n: int = 1) -> None:
        """Update progress by n"""
        self.current = min(self.current + n, self.total)
        self._render()

    def set(self, n: int) -> None:
        """Set progress to n"""
        self.current = min(n, self.total)
        self._render()

    def _render(self, final: bool = False) -> None:
        """Render the progress bar"""
        if not self._is_tty and not final:
            return

        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        parts = []
        if self.desc:
            parts.append(self.desc)
        parts.append(f"[{bar}]")
        if self.show_percent:
            parts.append(f"{percent * 100:5.1f}%")
        if self.show_count:
            parts.append(f"({self.current}/{self.total})")

        line = " ".join(parts)
        print(f"\r{line}", end="", flush=True)


class Spinner:
    """
    Simple spinner for indeterminate progress.

    Usage:
        with Spinner("Loading..."):
            long_operation()
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = ""):
        self.message = message
        self.running = False
        self.frame = 0
        self._is_tty = sys.stdout.isatty()

    def __enter__(self):
        self.running = True
        if self._is_tty:
            self._render()
        else:
            print(f"{self.message}...", end="", flush=True)
        return self

    def __exit__(self, *args):
        self.running = False
        if self._is_tty:
            print("\r" + " " * (len(self.message) + 5) + "\r", end="")
        print()

    def _render(self) -> None:
        """Render current frame"""
        if not self._is_tty:
            return
        frame_char = self.FRAMES[self.frame % len(self.FRAMES)]
        print(f"\r{frame_char} {self.message}", end="", flush=True)
        self.frame += 1

    def spin(self) -> None:
        """Advance to next frame"""
        if self.running:
            self._render()
            time.sleep(0.1)


# =============================================================================
# Output Formatting Utilities
# =============================================================================

def format_size(size_bytes: int) -> str:
    """Format byte size to human readable"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration to human readable"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}µs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_number(n: Union[int, float]) -> str:
    """Format number with suffixes"""
    if abs(n) >= 1e12:
        return f"{n / 1e12:.1f}T"
    elif abs(n) >= 1e9:
        return f"{n / 1e9:.1f}G"
    elif abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M"
    elif abs(n) >= 1e3:
        return f"{n / 1e3:.1f}K"
    elif isinstance(n, float):
        return f"{n:.2f}"
    return str(n)


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
