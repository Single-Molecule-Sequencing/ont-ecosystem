"""
ONT Ecosystem Validation Utilities - Data validation helpers

Usage:
    from lib.validation import (
        validate_path, validate_experiment_id, validate_required,
        Validator, Schema
    )

    # Simple validators
    validate_path("/path/to/file", must_exist=True)
    validate_experiment_id("exp-abc123")

    # Schema validation
    schema = Schema({
        "name": {"type": str, "required": True, "min_length": 1},
        "count": {"type": int, "min": 0, "max": 100},
        "tags": {"type": list, "items": str},
    })
    errors = schema.validate(data)
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union


@dataclass
class ValidationResult:
    """Result of a validation check"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid

    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge another result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False
        return self


# Simple validators

def validate_path(
    path: Union[str, Path],
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    must_be_readable: bool = False,
    must_be_writable: bool = False,
    extensions: Optional[List[str]] = None,
) -> ValidationResult:
    """
    Validate a file system path.

    Args:
        path: Path to validate
        must_exist: Path must exist
        must_be_file: Path must be a file
        must_be_dir: Path must be a directory
        must_be_readable: Path must be readable
        must_be_writable: Path must be writable
        extensions: Allowed file extensions (e.g., [".bam", ".fastq"])
    """
    result = ValidationResult(valid=True)
    path = Path(path)

    if must_exist and not path.exists():
        result.add_error(f"Path does not exist: {path}")
        return result

    if path.exists():
        if must_be_file and not path.is_file():
            result.add_error(f"Path is not a file: {path}")

        if must_be_dir and not path.is_dir():
            result.add_error(f"Path is not a directory: {path}")

        if must_be_readable and not os.access(path, os.R_OK):
            result.add_error(f"Path is not readable: {path}")

        if must_be_writable and not os.access(path, os.W_OK):
            result.add_error(f"Path is not writable: {path}")

    if extensions and path.suffix.lower() not in [e.lower() for e in extensions]:
        result.add_error(
            f"Invalid extension: {path.suffix} "
            f"(expected: {', '.join(extensions)})"
        )

    return result


def validate_experiment_id(exp_id: str) -> ValidationResult:
    """
    Validate an experiment ID format.

    Valid formats:
    - exp-XXXXXXXX (8 hex chars)
    - Custom IDs with alphanumeric, dash, underscore
    """
    result = ValidationResult(valid=True)

    if not exp_id:
        result.add_error("Experiment ID cannot be empty")
        return result

    if len(exp_id) > 100:
        result.add_error("Experiment ID too long (max 100 characters)")

    # Allow alphanumeric, dash, underscore
    if not re.match(r'^[a-zA-Z0-9_-]+$', exp_id):
        result.add_error(
            "Experiment ID contains invalid characters "
            "(allowed: alphanumeric, dash, underscore)"
        )

    return result


def validate_required(
    value: Any,
    name: str,
    allow_empty: bool = False
) -> ValidationResult:
    """Validate that a required value is present"""
    result = ValidationResult(valid=True)

    if value is None:
        result.add_error(f"Required field '{name}' is missing")
    elif not allow_empty:
        if isinstance(value, str) and not value.strip():
            result.add_error(f"Required field '{name}' is empty")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            result.add_error(f"Required field '{name}' is empty")

    return result


def validate_type(
    value: Any,
    name: str,
    expected_type: Union[Type, tuple],
    allow_none: bool = False
) -> ValidationResult:
    """Validate value type"""
    result = ValidationResult(valid=True)

    if value is None:
        if not allow_none:
            result.add_error(f"Field '{name}' cannot be None")
        return result

    if not isinstance(value, expected_type):
        result.add_error(
            f"Field '{name}' has wrong type: "
            f"expected {expected_type}, got {type(value).__name__}"
        )

    return result


def validate_range(
    value: Union[int, float],
    name: str,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    exclusive_min: bool = False,
    exclusive_max: bool = False,
) -> ValidationResult:
    """Validate numeric range"""
    result = ValidationResult(valid=True)

    if min_value is not None:
        if exclusive_min:
            if value <= min_value:
                result.add_error(f"Field '{name}' must be > {min_value}")
        else:
            if value < min_value:
                result.add_error(f"Field '{name}' must be >= {min_value}")

    if max_value is not None:
        if exclusive_max:
            if value >= max_value:
                result.add_error(f"Field '{name}' must be < {max_value}")
        else:
            if value > max_value:
                result.add_error(f"Field '{name}' must be <= {max_value}")

    return result


def validate_length(
    value: Union[str, list, dict],
    name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> ValidationResult:
    """Validate collection length"""
    result = ValidationResult(valid=True)
    length = len(value)

    if min_length is not None and length < min_length:
        result.add_error(
            f"Field '{name}' too short: {length} < {min_length}"
        )

    if max_length is not None and length > max_length:
        result.add_error(
            f"Field '{name}' too long: {length} > {max_length}"
        )

    return result


def validate_pattern(
    value: str,
    name: str,
    pattern: str,
    message: Optional[str] = None
) -> ValidationResult:
    """Validate string against regex pattern"""
    result = ValidationResult(valid=True)

    if not re.match(pattern, value):
        msg = message or f"Field '{name}' does not match pattern: {pattern}"
        result.add_error(msg)

    return result


def validate_choices(
    value: Any,
    name: str,
    choices: Union[List, Set, tuple],
    case_sensitive: bool = True
) -> ValidationResult:
    """Validate value is in allowed choices"""
    result = ValidationResult(valid=True)

    if not case_sensitive and isinstance(value, str):
        value = value.lower()
        choices = [c.lower() if isinstance(c, str) else c for c in choices]

    if value not in choices:
        result.add_error(
            f"Field '{name}' has invalid value: {value} "
            f"(allowed: {', '.join(str(c) for c in choices)})"
        )

    return result


# Schema-based validation

class Schema:
    """
    Schema-based validator for dictionaries.

    Schema definition:
        {
            "field_name": {
                "type": str,           # Required type
                "required": True,      # Is field required?
                "default": None,       # Default value if missing
                "min": 0,              # Minimum value (numeric)
                "max": 100,            # Maximum value (numeric)
                "min_length": 1,       # Minimum length (str/list)
                "max_length": 50,      # Maximum length (str/list)
                "pattern": r"^[a-z]+$", # Regex pattern (str)
                "choices": ["a", "b"], # Allowed values
                "items": str,          # Type of list items
                "validator": func,     # Custom validator function
            }
        }
    """

    def __init__(self, schema: Dict[str, Dict[str, Any]]):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against schema"""
        result = ValidationResult(valid=True)

        if not isinstance(data, dict):
            result.add_error("Data must be a dictionary")
            return result

        # Check each field in schema
        for field_name, rules in self.schema.items():
            value = data.get(field_name)

            # Required check
            if rules.get("required", False) and field_name not in data:
                result.add_error(f"Required field '{field_name}' is missing")
                continue

            # Skip if not present and not required
            if value is None and not rules.get("required", False):
                continue

            # Type check
            if "type" in rules and value is not None:
                expected = rules["type"]
                if not isinstance(value, expected):
                    result.add_error(
                        f"Field '{field_name}' has wrong type: "
                        f"expected {expected.__name__}, got {type(value).__name__}"
                    )
                    continue

            # Numeric range
            if isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    result.add_error(
                        f"Field '{field_name}' value {value} < min {rules['min']}"
                    )
                if "max" in rules and value > rules["max"]:
                    result.add_error(
                        f"Field '{field_name}' value {value} > max {rules['max']}"
                    )

            # String/list length
            if isinstance(value, (str, list, dict)):
                if "min_length" in rules and len(value) < rules["min_length"]:
                    result.add_error(
                        f"Field '{field_name}' length {len(value)} "
                        f"< min {rules['min_length']}"
                    )
                if "max_length" in rules and len(value) > rules["max_length"]:
                    result.add_error(
                        f"Field '{field_name}' length {len(value)} "
                        f"> max {rules['max_length']}"
                    )

            # Pattern
            if "pattern" in rules and isinstance(value, str):
                if not re.match(rules["pattern"], value):
                    result.add_error(
                        f"Field '{field_name}' does not match pattern"
                    )

            # Choices
            if "choices" in rules:
                if value not in rules["choices"]:
                    result.add_error(
                        f"Field '{field_name}' has invalid value: {value}"
                    )

            # List items
            if "items" in rules and isinstance(value, list):
                item_type = rules["items"]
                for i, item in enumerate(value):
                    if not isinstance(item, item_type):
                        result.add_error(
                            f"Field '{field_name}[{i}]' has wrong type"
                        )

            # Custom validator
            if "validator" in rules:
                custom_result = rules["validator"](value, field_name)
                if isinstance(custom_result, ValidationResult):
                    result.merge(custom_result)
                elif isinstance(custom_result, str):
                    result.add_error(custom_result)
                elif custom_result is False:
                    result.add_error(f"Field '{field_name}' failed validation")

        # Check for unknown fields
        known_fields = set(self.schema.keys())
        for field_name in data.keys():
            if field_name not in known_fields:
                result.add_warning(f"Unknown field: {field_name}")

        return result

    def apply_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to data"""
        result = dict(data)
        for field_name, rules in self.schema.items():
            if field_name not in result and "default" in rules:
                result[field_name] = rules["default"]
        return result


class Validator:
    """
    Chainable validator for complex validation logic.

    Usage:
        result = (Validator(data)
            .require("name")
            .require("path")
            .check_type("count", int)
            .check_range("count", min_value=0)
            .custom("name", lambda v: len(v) > 0, "Name cannot be empty")
            .result())
    """

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self._result = ValidationResult(valid=True)

    def require(self, field: str, allow_empty: bool = False) -> 'Validator':
        """Require a field to be present"""
        value = self.data.get(field)
        self._result.merge(validate_required(value, field, allow_empty))
        return self

    def check_type(
        self,
        field: str,
        expected_type: Union[Type, tuple],
        allow_none: bool = False
    ) -> 'Validator':
        """Check field type"""
        value = self.data.get(field)
        self._result.merge(
            validate_type(value, field, expected_type, allow_none)
        )
        return self

    def check_range(
        self,
        field: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> 'Validator':
        """Check numeric range"""
        value = self.data.get(field)
        if value is not None and isinstance(value, (int, float)):
            self._result.merge(
                validate_range(value, field, min_value, max_value)
            )
        return self

    def check_length(
        self,
        field: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> 'Validator':
        """Check collection length"""
        value = self.data.get(field)
        if value is not None and isinstance(value, (str, list, dict)):
            self._result.merge(
                validate_length(value, field, min_length, max_length)
            )
        return self

    def check_pattern(
        self,
        field: str,
        pattern: str,
        message: Optional[str] = None
    ) -> 'Validator':
        """Check string pattern"""
        value = self.data.get(field)
        if value is not None and isinstance(value, str):
            self._result.merge(
                validate_pattern(value, field, pattern, message)
            )
        return self

    def check_choices(
        self,
        field: str,
        choices: Union[List, Set, tuple]
    ) -> 'Validator':
        """Check value is in choices"""
        value = self.data.get(field)
        if value is not None:
            self._result.merge(validate_choices(value, field, choices))
        return self

    def check_path(
        self,
        field: str,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False
    ) -> 'Validator':
        """Check file path"""
        value = self.data.get(field)
        if value is not None:
            self._result.merge(
                validate_path(value, must_exist, must_be_file, must_be_dir)
            )
        return self

    def custom(
        self,
        field: str,
        check: Callable[[Any], bool],
        message: str
    ) -> 'Validator':
        """Custom validation check"""
        value = self.data.get(field)
        if value is not None and not check(value):
            self._result.add_error(message)
        return self

    def result(self) -> ValidationResult:
        """Get validation result"""
        return self._result
