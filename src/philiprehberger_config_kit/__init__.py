"""Layered configuration loader merging env vars, files, and defaults."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Config",
    "ConfigError",
    "ConfigSchema",
    "ConfigSnapshot",
    "SchemaError",
]


class ConfigError(Exception):
    """Raised when required config values are missing."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"Missing required config keys: {', '.join(missing)}"
        )


class SchemaError(Exception):
    """Raised when config values fail schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            "Schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


@dataclass
class _FieldSchema:
    """Schema definition for a single config field."""

    key: str
    expected_type: type | None = None
    required: bool = False
    choices: list[Any] | None = None


class ConfigSchema:
    """Define expected keys, types, and required/optional fields for validation.

    Example::

        schema = ConfigSchema()
        schema.required("host", str)
        schema.required("port", int)
        schema.optional("debug", bool)
        schema.optional("mode", str, choices=["dev", "prod", "test"])

        config.validate(schema)
    """

    def __init__(self) -> None:
        self._fields: list[_FieldSchema] = []

    def required(
        self,
        key: str,
        expected_type: type | None = None,
        *,
        choices: list[Any] | None = None,
    ) -> ConfigSchema:
        """Add a required field to the schema.

        Args:
            key: Config key (supports dot notation).
            expected_type: Expected Python type for the value.
            choices: If provided, value must be one of these.

        Returns:
            Self for chaining.
        """
        self._fields.append(
            _FieldSchema(key=key, expected_type=expected_type, required=True, choices=choices)
        )
        return self

    def optional(
        self,
        key: str,
        expected_type: type | None = None,
        *,
        choices: list[Any] | None = None,
    ) -> ConfigSchema:
        """Add an optional field to the schema.

        Args:
            key: Config key (supports dot notation).
            expected_type: Expected Python type for the value.
            choices: If provided, value must be one of these.

        Returns:
            Self for chaining.
        """
        self._fields.append(
            _FieldSchema(key=key, expected_type=expected_type, required=False, choices=choices)
        )
        return self


@dataclass
class ConfigSnapshot:
    """Immutable snapshot of config state at a point in time."""

    data: dict[str, Any] = field(default_factory=dict)

    def diff(self, other: ConfigSnapshot) -> dict[str, dict[str, Any]]:
        """Compare this snapshot with another and return differences.

        Returns a dict with three keys:

        - ``added``: keys present in *other* but not in this snapshot.
        - ``removed``: keys present in this snapshot but not in *other*.
        - ``changed``: keys present in both but with different values
          (each entry maps to ``{"old": ..., "new": ...}``).

        Both snapshots are flattened to dot-notation keys for comparison.
        """
        flat_self = _flatten_dict(self.data)
        flat_other = _flatten_dict(other.data)

        self_keys = set(flat_self)
        other_keys = set(flat_other)

        added: dict[str, Any] = {k: flat_other[k] for k in other_keys - self_keys}
        removed: dict[str, Any] = {k: flat_self[k] for k in self_keys - other_keys}
        changed: dict[str, Any] = {}
        for k in self_keys & other_keys:
            if flat_self[k] != flat_other[k]:
                changed[k] = {"old": flat_self[k], "new": flat_other[k]}

        return {"added": added, "removed": removed, "changed": changed}


def _flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict into dot-notation keys, preserving value types."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_dict(value, full_key))
        else:
            result[full_key] = value
    return result


class _Source:
    """Base class for configuration sources."""

    def load(self) -> dict[str, Any]:
        raise NotImplementedError


class _DefaultsSource(_Source):
    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values

    def load(self) -> dict[str, Any]:
        return dict(self._values)


class _JsonFileSource(_Source):
    def __init__(self, path: str | Path, optional: bool = False) -> None:
        self._path = Path(path)
        self._optional = optional

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            if self._optional:
                return {}
            raise FileNotFoundError(f"Config file not found: {self._path}")
        return json.loads(self._path.read_text())


class _EnvSource(_Source):
    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    def load(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        prefix_lower = self._prefix.lower()
        for key, value in os.environ.items():
            if self._prefix and key.lower().startswith(prefix_lower):
                # Strip prefix and convert to lowercase with dots
                clean_key = key[len(self._prefix):].lower().replace("__", ".")
                result[clean_key] = value
            elif not self._prefix:
                result[key.lower()] = value
        return result


class _EnvFileSource(_Source):
    def __init__(self, path: str | Path = ".env", optional: bool = True) -> None:
        self._path = Path(path)
        self._optional = optional

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            if self._optional:
                return {}
            raise FileNotFoundError(f".env file not found: {self._path}")

        result: dict[str, Any] = {}
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().lower()
            value = value.strip()
            # Remove surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            result[key] = value
        return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, handling nested dicts."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _unflatten(data: dict[str, Any]) -> dict[str, Any]:
    """Convert dot-notation keys into nested dicts."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def _get_nested(data: dict[str, Any], key: str) -> Any:
    """Get a value using dot notation."""
    parts = key.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return _MISSING
            current = current[part]
        else:
            return _MISSING
    return current


_MISSING = object()


class Config:
    """Layered configuration with typed access.

    Sources are applied in order — later sources override earlier ones.
    """

    def __init__(self, sources: list[_Source] | None = None) -> None:
        self._sources: list[_Source] = list(sources) if sources else []
        self._data: dict[str, Any] = {}
        self._frozen = False
        self._load_sources()

    def _load_sources(self) -> None:
        """Load and merge all sources into internal data."""
        self._data = {}
        for source in self._sources:
            loaded = source.load()
            unflattened = _unflatten(loaded)
            self._data = _deep_merge(self._data, unflattened)

    # --- Source factories ---

    @staticmethod
    def defaults(values: dict[str, Any]) -> _Source:
        return _DefaultsSource(values)

    @staticmethod
    def json_file(path: str | Path, optional: bool = False) -> _Source:
        return _JsonFileSource(path, optional)

    @staticmethod
    def env(prefix: str = "") -> _Source:
        return _EnvSource(prefix)

    @staticmethod
    def env_file(path: str | Path = ".env", optional: bool = True) -> _Source:
        return _EnvFileSource(path, optional)

    # --- Typed getters ---

    def get(self, key: str, default: Any = _MISSING) -> Any:
        """Get a value by key (supports dot notation)."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is _MISSING:
                raise KeyError(f"Config key not found: {key}")
            return default
        return value

    def get_str(self, key: str, default: str | None = None) -> str:
        """Get a string value."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is not None:
                return default
            raise KeyError(f"Config key not found: {key}")
        return str(value)

    def get_int(self, key: str, default: int | None = None) -> int:
        """Get an integer value."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is not None:
                return default
            raise KeyError(f"Config key not found: {key}")
        return int(value)

    def get_float(self, key: str, default: float | None = None) -> float:
        """Get a float value."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is not None:
                return default
            raise KeyError(f"Config key not found: {key}")
        return float(value)

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        """Get a boolean value. Accepts true/false, 1/0, yes/no, on/off."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is not None:
                return default
            raise KeyError(f"Config key not found: {key}")
        if isinstance(value, bool):
            return value
        s = str(value).lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"Cannot convert '{value}' to bool for key '{key}'")

    def get_int_list(self, key: str, sep: str = ",") -> list[int]:
        """Get a list of integers by splitting a string value.

        Args:
            key: Config key (supports dot notation).
            sep: Separator to split on (default ``","``).

        Returns:
            List of integers.

        Raises:
            KeyError: If key is not found.
            ConfigError: If any element cannot be converted to int.
        """
        value = _get_nested(self._data, key)
        if value is _MISSING:
            raise KeyError(f"Config key not found: {key}")
        parts = [item.strip() for item in str(value).split(sep) if item.strip()]
        try:
            return [int(p) for p in parts]
        except ValueError as exc:
            raise ConfigError([key]) from exc

    def get_float_list(self, key: str, sep: str = ",") -> list[float]:
        """Get a list of floats by splitting a string value.

        Args:
            key: Config key (supports dot notation).
            sep: Separator to split on (default ``","``).

        Returns:
            List of floats.

        Raises:
            KeyError: If key is not found.
            ConfigError: If any element cannot be converted to float.
        """
        value = _get_nested(self._data, key)
        if value is _MISSING:
            raise KeyError(f"Config key not found: {key}")
        parts = [item.strip() for item in str(value).split(sep) if item.strip()]
        try:
            return [float(p) for p in parts]
        except ValueError as exc:
            raise ConfigError([key]) from exc

    def get_list(self, key: str, separator: str = ",", default: list | None = None) -> list[str]:
        """Get a list by splitting a string value."""
        value = _get_nested(self._data, key)
        if value is _MISSING:
            if default is not None:
                return default
            raise KeyError(f"Config key not found: {key}")
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(separator) if item.strip()]

    # --- Validation ---

    def require(self, *keys: str) -> None:
        """Raise ConfigError if any keys are missing."""
        missing = [k for k in keys if _get_nested(self._data, k) is _MISSING]
        if missing:
            raise ConfigError(missing)

    def has(self, key: str) -> bool:
        """Check if a key exists."""
        return _get_nested(self._data, key) is not _MISSING

    def validate(self, schema: ConfigSchema) -> None:
        """Validate the config against a schema.

        Checks required keys are present, values match expected types,
        and values are within allowed choices.

        Args:
            schema: A ``ConfigSchema`` defining expected fields.

        Raises:
            SchemaError: If any validation rule fails, with a list of
                all errors found.
        """
        errors: list[str] = []
        for f in schema._fields:
            value = _get_nested(self._data, f.key)
            if value is _MISSING:
                if f.required:
                    errors.append(f"Missing required key: '{f.key}'")
                continue
            if f.expected_type is not None and not isinstance(value, f.expected_type):
                errors.append(
                    f"Key '{f.key}' expected type {f.expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
            if f.choices is not None and value not in f.choices:
                errors.append(
                    f"Key '{f.key}' value {value!r} not in allowed choices: {f.choices}"
                )
        if errors:
            raise SchemaError(errors)

    # --- Utilities ---

    def reload(self) -> None:
        """Reload configuration from all sources.

        Re-reads every source (env vars, files, defaults) and rebuilds
        the merged config data. Useful when environment variables or
        config files change at runtime.
        """
        self._load_sources()

    def flatten(self, prefix: str = "") -> dict[str, str]:
        """Export the config as a flat dictionary with dot-notation keys.

        All values are converted to strings.

        Args:
            prefix: Optional prefix for all keys.

        Returns:
            Flat dictionary, e.g. ``{"db.host": "localhost", "db.port": "5432"}``.
        """

        def _flatten_recurse(data: dict[str, Any], current_prefix: str) -> dict[str, str]:
            result: dict[str, str] = {}
            for key, value in data.items():
                full_key = f"{current_prefix}.{key}" if current_prefix else key
                if isinstance(value, dict):
                    result.update(_flatten_recurse(value, full_key))
                else:
                    result[full_key] = str(value)
            return result

        return _flatten_recurse(self._data, prefix)

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the config data as a nested dictionary."""
        return copy.deepcopy(self._data)

    def to_env(self, prefix: str = "") -> dict[str, str]:
        """Export the config as environment-variable-style key-value pairs.

        Nested keys are joined with ``_`` and uppercased.
        All values are converted to strings.

        Args:
            prefix: Optional prefix prepended to all keys (e.g. ``"APP"``
                produces ``APP_DATABASE_HOST``).

        Returns:
            Dictionary of ``UPPER_SNAKE_CASE`` keys to string values.
        """

        def _to_env_recurse(data: dict[str, Any], parts: list[str]) -> dict[str, str]:
            result: dict[str, str] = {}
            for key, value in data.items():
                current_parts = [*parts, key.upper()]
                if isinstance(value, dict):
                    result.update(_to_env_recurse(value, current_parts))
                else:
                    result["_".join(current_parts)] = str(value)
            return result

        top_parts = [prefix.upper()] if prefix else []
        return _to_env_recurse(self._data, top_parts)

    def snapshot(self) -> ConfigSnapshot:
        """Capture the current config state as an immutable snapshot.

        Returns:
            A ``ConfigSnapshot`` that can be compared with another snapshot
            via its ``diff()`` method.
        """
        return ConfigSnapshot(data=copy.deepcopy(self._data))

    def freeze(self) -> Config:
        """Return a frozen copy that raises on mutation attempts."""
        self._frozen = True
        return self

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)
