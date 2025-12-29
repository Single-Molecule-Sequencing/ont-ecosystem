"""
ONT Ecosystem Logging Configuration

Provides consistent logging setup across all CLI tools.

Usage:
    from lib.logging_config import setup_logging, get_logger

    # In main script
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    logger = get_logger(__name__)

    logger.info("Processing experiment...")
    logger.debug("Debug details...")
    logger.warning("Something unusual...")
    logger.error("Something failed!")
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Default log directory
LOG_DIR = Path.home() / ".ont-ecosystem" / "logs"

# Log format strings
CONSOLE_FORMAT = "%(levelname)s: %(message)s"
CONSOLE_FORMAT_VERBOSE = "%(asctime)s %(name)s %(levelname)s: %(message)s"
FILE_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"

# Custom log levels
TRACE = 5  # More detailed than DEBUG


def setup_logging(
    verbose: bool = False,
    quiet: bool = False,
    debug: bool = False,
    log_file: Optional[Path] = None,
    name: str = "ont"
) -> logging.Logger:
    """
    Configure logging for ONT Ecosystem tools.

    Args:
        verbose: Show INFO and above on console
        quiet: Only show WARNING and above
        debug: Show DEBUG and above (overrides verbose)
        log_file: Optional file to write logs to
        name: Logger name (default: "ont")

    Returns:
        Configured root logger
    """
    # Determine log level
    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING  # Default: warnings only

    # Get root logger for ont namespace
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)

    if debug or verbose:
        console_formatter = logging.Formatter(CONSOLE_FORMAT_VERBOSE, datefmt="%H:%M:%S")
    else:
        console_formatter = logging.Formatter(CONSOLE_FORMAT)

    console.setFormatter(console_formatter)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always capture everything to file
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        logger.addHandler(file_handler)

    # Also log to daily file if LOG_DIR exists
    if LOG_DIR.exists() or os.environ.get("ONT_LOG_TO_FILE"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        daily_log = LOG_DIR / f"ont-{datetime.now().strftime('%Y%m%d')}.log"

        daily_handler = logging.FileHandler(daily_log)
        daily_handler.setLevel(logging.DEBUG)
        daily_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        logger.addHandler(daily_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("Hello!")
    """
    # Ensure it's under the ont namespace
    if not name.startswith("ont"):
        name = f"ont.{name}"
    return logging.getLogger(name)


def add_logging_args(parser) -> None:
    """
    Add standard logging arguments to an argument parser.

    Args:
        parser: argparse.ArgumentParser instance

    Usage:
        parser = argparse.ArgumentParser()
        add_logging_args(parser)
        args = parser.parse_args()
        setup_logging(verbose=args.verbose, quiet=args.quiet, debug=args.debug)
    """
    log_group = parser.add_argument_group("logging")
    log_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    log_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Show only warnings and errors"
    )
    log_group.add_argument(
        "--debug",
        action="store_true",
        help="Show debug output"
    )
    log_group.add_argument(
        "--log-file",
        type=Path,
        help="Write logs to file"
    )


class LogContext:
    """
    Context manager for temporary log level changes.

    Usage:
        with LogContext(logging.DEBUG):
            logger.debug("This will be shown")
    """

    def __init__(self, level: int, logger_name: str = "ont"):
        self.level = level
        self.logger_name = logger_name
        self.old_level = None

    def __enter__(self):
        logger = logging.getLogger(self.logger_name)
        self.old_level = logger.level
        logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.old_level)
        return False


# Convenience functions for quick logging without setup
def log_info(message: str) -> None:
    """Quick info log"""
    get_logger("ont").info(message)


def log_warning(message: str) -> None:
    """Quick warning log"""
    get_logger("ont").warning(message)


def log_error(message: str) -> None:
    """Quick error log"""
    get_logger("ont").error(message)


def log_debug(message: str) -> None:
    """Quick debug log"""
    get_logger("ont").debug(message)
