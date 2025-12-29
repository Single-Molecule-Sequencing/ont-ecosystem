"""
ONT Ecosystem Error Classes - Standardized exceptions and error handling

Usage:
    from lib.errors import (
        ONTError, ConfigurationError, ValidationError,
        RegistryError, AnalysisError, ExternalToolError
    )

    try:
        validate_experiment(exp)
    except ValidationError as e:
        print(f"Validation failed: {e}")
        print(f"Details: {e.details}")
"""

import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories for error classification"""
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    REGISTRY = "registry"
    ANALYSIS = "analysis"
    EXTERNAL_TOOL = "external_tool"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    operation: Optional[str] = None
    file_path: Optional[str] = None
    experiment_id: Optional[str] = None
    command: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {"timestamp": self.timestamp}
        if self.operation:
            result["operation"] = self.operation
        if self.file_path:
            result["file_path"] = self.file_path
        if self.experiment_id:
            result["experiment_id"] = self.experiment_id
        if self.command:
            result["command"] = self.command
        if self.extra:
            result.update(self.extra)
        return result


class ONTError(Exception):
    """
    Base exception for all ONT Ecosystem errors.

    Provides structured error information including:
    - Error message
    - Error code
    - Severity level
    - Category
    - Context information
    - Suggested fixes
    """

    default_code = "ONT_ERROR"
    default_category = ErrorCategory.UNKNOWN
    default_severity = ErrorSeverity.ERROR

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.severity = severity or self.default_severity
        self.category = category or self.default_category
        self.details = details or {}
        self.context = context or ErrorContext()
        self.suggestions = suggestions or []
        self.cause = cause

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization"""
        result = {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
        }
        if self.details:
            result["details"] = self.details
        if self.context:
            result["context"] = self.context.to_dict()
        if self.suggestions:
            result["suggestions"] = self.suggestions
        if self.cause:
            result["cause"] = str(self.cause)
        return result

    def format_message(self, verbose: bool = False) -> str:
        """Format error message for display"""
        lines = [f"[{self.code}] {self.message}"]

        if verbose:
            if self.details:
                lines.append("Details:")
                for key, value in self.details.items():
                    lines.append(f"  {key}: {value}")

            if self.suggestions:
                lines.append("Suggestions:")
                for suggestion in self.suggestions:
                    lines.append(f"  - {suggestion}")

            if self.cause:
                lines.append(f"Caused by: {self.cause}")

        return "\n".join(lines)


class ConfigurationError(ONTError):
    """Error in configuration settings"""
    default_code = "CONFIG_ERROR"
    default_category = ErrorCategory.CONFIGURATION

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details=details, **kwargs)


class ValidationError(ONTError):
    """Data validation error"""
    default_code = "VALIDATION_ERROR"
    default_category = ErrorCategory.VALIDATION

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        expected: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if expected:
            details["expected"] = expected
        super().__init__(message, details=details, **kwargs)


class RegistryError(ONTError):
    """Error with experiment registry"""
    default_code = "REGISTRY_ERROR"
    default_category = ErrorCategory.REGISTRY

    def __init__(
        self,
        message: str,
        experiment_id: Optional[str] = None,
        registry_path: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if experiment_id:
            details["experiment_id"] = experiment_id
        if registry_path:
            details["registry_path"] = registry_path
        super().__init__(message, details=details, **kwargs)


class AnalysisError(ONTError):
    """Error during analysis execution"""
    default_code = "ANALYSIS_ERROR"
    default_category = ErrorCategory.ANALYSIS

    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        input_file: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if analysis_type:
            details["analysis_type"] = analysis_type
        if input_file:
            details["input_file"] = input_file
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(message, details=details, **kwargs)


class ExternalToolError(ONTError):
    """Error from external tool execution"""
    default_code = "EXTERNAL_TOOL_ERROR"
    default_category = ErrorCategory.EXTERNAL_TOOL

    def __init__(
        self,
        message: str,
        tool: Optional[str] = None,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if tool:
            details["tool"] = tool
        if command:
            details["command"] = command
        if exit_code is not None:
            details["exit_code"] = exit_code
        if stderr:
            details["stderr"] = stderr[:500]  # Truncate long stderr
        super().__init__(message, details=details, **kwargs)


class FileSystemError(ONTError):
    """File system related error"""
    default_code = "FILESYSTEM_ERROR"
    default_category = ErrorCategory.FILE_SYSTEM

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if path:
            details["path"] = path
        if operation:
            details["operation"] = operation
        super().__init__(message, details=details, **kwargs)


class PermissionError(ONTError):
    """Permission denied error"""
    default_code = "PERMISSION_ERROR"
    default_category = ErrorCategory.PERMISSION

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        required_permission: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if path:
            details["path"] = path
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, details=details, **kwargs)


class ResourceError(ONTError):
    """Resource exhaustion error"""
    default_code = "RESOURCE_ERROR"
    default_category = ErrorCategory.RESOURCE

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        required: Optional[str] = None,
        available: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if required:
            details["required"] = required
        if available:
            details["available"] = available
        super().__init__(message, details=details, **kwargs)


class NetworkError(ONTError):
    """Network related error"""
    default_code = "NETWORK_ERROR"
    default_category = ErrorCategory.NETWORK

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if url:
            details["url"] = url
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(message, details=details, **kwargs)


# Error handling utilities

def format_exception(exc: Exception, verbose: bool = False) -> str:
    """Format an exception for display"""
    if isinstance(exc, ONTError):
        return exc.format_message(verbose=verbose)

    if verbose:
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return str(exc)


def handle_error(
    exc: Exception,
    exit_code: int = 1,
    verbose: bool = False,
    raise_error: bool = False
) -> None:
    """
    Standard error handler for CLI tools.

    Args:
        exc: The exception to handle
        exit_code: Exit code if exiting
        verbose: Whether to show verbose output
        raise_error: If True, re-raise instead of exiting
    """
    message = format_exception(exc, verbose=verbose)

    if isinstance(exc, ONTError):
        prefix = f"Error [{exc.code}]"
    else:
        prefix = f"Error [{type(exc).__name__}]"

    print(f"{prefix}: {message}", file=sys.stderr)

    if raise_error:
        raise exc
    sys.exit(exit_code)


def wrap_errors(func):
    """
    Decorator to wrap function errors in ONTError.

    Usage:
        @wrap_errors
        def my_function():
            ...
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ONTError:
            raise
        except Exception as e:
            raise ONTError(
                str(e),
                code="WRAPPED_ERROR",
                cause=e,
                context=ErrorContext(operation=func.__name__)
            ) from e

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
