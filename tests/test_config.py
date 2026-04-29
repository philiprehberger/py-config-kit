"""Comprehensive tests for philiprehberger_config_kit."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from philiprehberger_config_kit import (
    Config,
    ConfigError,
    ConfigSchema,
    ConfigSnapshot,
    SchemaError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_json(tmp_path: Path) -> Path:
    """Create a temporary JSON config file."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"host": "localhost", "port": 5432, "db": {"name": "mydb"}}))
    return p


@pytest.fixture()
def tmp_env_file(tmp_path: Path) -> Path:
    """Create a temporary .env file."""
    p = tmp_path / ".env"
    p.write_text('DATABASE_URL=postgres://localhost/test\nSECRET="s3cret"\nDEBUG=true\n')
    return p


# ---------------------------------------------------------------------------
# Basic Config
# ---------------------------------------------------------------------------


class TestBasicConfig:
    def test_defaults_source(self) -> None:
        config = Config(sources=[Config.defaults({"key": "value"})])
        assert config.get("key") == "value"

    def test_missing_key_raises(self) -> None:
        config = Config(sources=[Config.defaults({})])
        with pytest.raises(KeyError, match="Config key not found: missing"):
            config.get("missing")

    def test_default_value(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get("missing", "fallback") == "fallback"

    def test_source_priority(self) -> None:
        config = Config(
            sources=[
                Config.defaults({"k": "first"}),
                Config.defaults({"k": "second"}),
            ]
        )
        assert config.get("k") == "second"

    def test_json_file_source(self, tmp_json: Path) -> None:
        config = Config(sources=[Config.json_file(tmp_json)])
        assert config.get("host") == "localhost"
        assert config.get("port") == 5432
        assert config.get("db.name") == "mydb"

    def test_json_file_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Config(sources=[Config.json_file(tmp_path / "nope.json")])

    def test_json_file_optional(self, tmp_path: Path) -> None:
        config = Config(sources=[Config.json_file(tmp_path / "nope.json", optional=True)])
        assert config.get("x", "default") == "default"

    def test_env_file_source(self, tmp_env_file: Path) -> None:
        config = Config(sources=[Config.env_file(tmp_env_file)])
        assert config.get("database_url") == "postgres://localhost/test"
        assert config.get("secret") == "s3cret"
        assert config.get("debug") == "true"

    def test_env_file_optional_missing(self, tmp_path: Path) -> None:
        config = Config(sources=[Config.env_file(tmp_path / "missing.env", optional=True)])
        assert config.get("x", "default") == "default"

    def test_env_file_required_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Config(sources=[Config.env_file(tmp_path / "missing.env", optional=False)])

    def test_env_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_HOST", "127.0.0.1")
        monkeypatch.setenv("APP_DB__PORT", "3306")
        config = Config(sources=[Config.env(prefix="APP_")])
        assert config.get("host") == "127.0.0.1"
        assert config.get("db.port") == "3306"

    def test_contains(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        assert "a" in config
        assert "b" not in config

    def test_getitem(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        assert config["a"] == 1


# ---------------------------------------------------------------------------
# Typed Getters
# ---------------------------------------------------------------------------


class TestTypedGetters:
    def test_get_str(self) -> None:
        config = Config(sources=[Config.defaults({"k": 42})])
        assert config.get_str("k") == "42"

    def test_get_str_default(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get_str("k", "fallback") == "fallback"

    def test_get_str_missing_raises(self) -> None:
        config = Config(sources=[Config.defaults({})])
        with pytest.raises(KeyError):
            config.get_str("k")

    def test_get_int(self) -> None:
        config = Config(sources=[Config.defaults({"k": "42"})])
        assert config.get_int("k") == 42

    def test_get_int_default(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get_int("k", 10) == 10

    def test_get_float(self) -> None:
        config = Config(sources=[Config.defaults({"k": "3.14"})])
        assert config.get_float("k") == pytest.approx(3.14)

    def test_get_float_default(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get_float("k", 1.0) == 1.0

    def test_get_bool_true_values(self) -> None:
        for val in ("true", "1", "yes", "on", True):
            config = Config(sources=[Config.defaults({"k": val})])
            assert config.get_bool("k") is True

    def test_get_bool_false_values(self) -> None:
        for val in ("false", "0", "no", "off", False):
            config = Config(sources=[Config.defaults({"k": val})])
            assert config.get_bool("k") is False

    def test_get_bool_invalid(self) -> None:
        config = Config(sources=[Config.defaults({"k": "maybe"})])
        with pytest.raises(ValueError, match="Cannot convert"):
            config.get_bool("k")

    def test_get_bool_default(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get_bool("k", True) is True

    def test_get_list(self) -> None:
        config = Config(sources=[Config.defaults({"k": "a, b, c"})])
        assert config.get_list("k") == ["a", "b", "c"]

    def test_get_list_default(self) -> None:
        config = Config(sources=[Config.defaults({})])
        assert config.get_list("k", default=[]) == []

    def test_get_list_from_list(self) -> None:
        config = Config(sources=[Config.defaults({"k": ["x", "y"]})])
        assert config.get_list("k") == ["x", "y"]

    def test_get_int_list(self) -> None:
        config = Config(sources=[Config.defaults({"k": "1, 2, 3"})])
        assert config.get_int_list("k") == [1, 2, 3]

    def test_get_int_list_custom_sep(self) -> None:
        config = Config(sources=[Config.defaults({"k": "1|2|3"})])
        assert config.get_int_list("k", sep="|") == [1, 2, 3]

    def test_get_int_list_invalid(self) -> None:
        config = Config(sources=[Config.defaults({"k": "1,two,3"})])
        with pytest.raises(ConfigError):
            config.get_int_list("k")

    def test_get_float_list(self) -> None:
        config = Config(sources=[Config.defaults({"k": "1.1, 2.2, 3.3"})])
        assert config.get_float_list("k") == [pytest.approx(1.1), pytest.approx(2.2), pytest.approx(3.3)]


# ---------------------------------------------------------------------------
# Dot-Notation Access
# ---------------------------------------------------------------------------


class TestDotNotation:
    def test_nested_get(self) -> None:
        config = Config(sources=[Config.defaults({"db": {"host": "localhost", "port": 5432}})])
        assert config.get("db.host") == "localhost"
        assert config.get("db.port") == 5432

    def test_deeply_nested(self) -> None:
        config = Config(sources=[Config.defaults({"a": {"b": {"c": {"d": "deep"}}}})])
        assert config.get("a.b.c.d") == "deep"

    def test_nested_missing_with_default(self) -> None:
        config = Config(sources=[Config.defaults({"a": {"b": 1}})])
        assert config.get("a.c", "nope") == "nope"

    def test_nested_has(self) -> None:
        config = Config(sources=[Config.defaults({"x": {"y": 1}})])
        assert config.has("x.y")
        assert not config.has("x.z")

    def test_nested_require(self) -> None:
        config = Config(sources=[Config.defaults({"x": {"y": 1}})])
        config.require("x.y")
        with pytest.raises(ConfigError):
            config.require("x.z")

    def test_nested_typed_getters(self) -> None:
        config = Config(sources=[Config.defaults({"db": {"port": "5432", "ssl": "true"}})])
        assert config.get_int("db.port") == 5432
        assert config.get_bool("db.ssl") is True


# ---------------------------------------------------------------------------
# Validation / require
# ---------------------------------------------------------------------------


class TestRequire:
    def test_require_present(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1, "b": 2})])
        config.require("a", "b")

    def test_require_missing(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        with pytest.raises(ConfigError) as exc_info:
            config.require("a", "b", "c")
        assert exc_info.value.missing == ["b", "c"]

    def test_has(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        assert config.has("a")
        assert not config.has("b")


# ---------------------------------------------------------------------------
# Schema Validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_valid_schema(self) -> None:
        config = Config(sources=[Config.defaults({"host": "localhost", "port": 5432})])
        schema = ConfigSchema()
        schema.required("host", str)
        schema.required("port", int)
        config.validate(schema)

    def test_missing_required(self) -> None:
        config = Config(sources=[Config.defaults({"host": "localhost"})])
        schema = ConfigSchema()
        schema.required("host", str)
        schema.required("port", int)
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert len(exc_info.value.errors) == 1
        assert "Missing required key: 'port'" in exc_info.value.errors[0]

    def test_wrong_type(self) -> None:
        config = Config(sources=[Config.defaults({"port": "not_an_int"})])
        schema = ConfigSchema()
        schema.required("port", int)
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert "expected type int" in exc_info.value.errors[0]

    def test_optional_missing_ok(self) -> None:
        config = Config(sources=[Config.defaults({})])
        schema = ConfigSchema()
        schema.optional("debug", bool)
        config.validate(schema)

    def test_optional_wrong_type(self) -> None:
        config = Config(sources=[Config.defaults({"debug": "yes"})])
        schema = ConfigSchema()
        schema.optional("debug", bool)
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert "expected type bool" in exc_info.value.errors[0]

    def test_choices_valid(self) -> None:
        config = Config(sources=[Config.defaults({"mode": "prod"})])
        schema = ConfigSchema()
        schema.required("mode", str, choices=["dev", "prod", "test"])
        config.validate(schema)

    def test_choices_invalid(self) -> None:
        config = Config(sources=[Config.defaults({"mode": "staging"})])
        schema = ConfigSchema()
        schema.required("mode", str, choices=["dev", "prod", "test"])
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert "not in allowed choices" in exc_info.value.errors[0]

    def test_multiple_errors(self) -> None:
        config = Config(sources=[Config.defaults({"port": "bad"})])
        schema = ConfigSchema()
        schema.required("host", str)
        schema.required("port", int)
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert len(exc_info.value.errors) == 2

    def test_nested_key_validation(self) -> None:
        config = Config(sources=[Config.defaults({"db": {"host": "localhost"}})])
        schema = ConfigSchema()
        schema.required("db.host", str)
        schema.required("db.port", int)
        with pytest.raises(SchemaError) as exc_info:
            config.validate(schema)
        assert "Missing required key: 'db.port'" in exc_info.value.errors[0]

    def test_schema_chaining(self) -> None:
        schema = ConfigSchema()
        result = schema.required("a", str).optional("b", int)
        assert result is schema

    def test_schema_no_type_check(self) -> None:
        config = Config(sources=[Config.defaults({"key": 123})])
        schema = ConfigSchema()
        schema.required("key")
        config.validate(schema)

    def test_schema_error_message(self) -> None:
        config = Config(sources=[Config.defaults({})])
        schema = ConfigSchema()
        schema.required("a")
        schema.required("b")
        with pytest.raises(SchemaError, match="Schema validation failed"):
            config.validate(schema)


# ---------------------------------------------------------------------------
# Reload
# ---------------------------------------------------------------------------


class TestReload:
    def test_reload_picks_up_new_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_VALUE", "old")
        config = Config(sources=[Config.env(prefix="APP_")])
        assert config.get("value") == "old"

        monkeypatch.setenv("APP_VALUE", "new")
        config.reload()
        assert config.get("value") == "new"

    def test_reload_picks_up_file_changes(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps({"x": 1}))
        config = Config(sources=[Config.json_file(p)])
        assert config.get("x") == 1

        p.write_text(json.dumps({"x": 2}))
        config.reload()
        assert config.get("x") == 2

    def test_reload_preserves_source_order(self) -> None:
        config = Config(
            sources=[
                Config.defaults({"k": "first"}),
                Config.defaults({"k": "second"}),
            ]
        )
        assert config.get("k") == "second"
        config.reload()
        assert config.get("k") == "second"


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


class TestToDict:
    def test_returns_deep_copy(self) -> None:
        config = Config(sources=[Config.defaults({"a": {"b": 1}})])
        d = config.to_dict()
        assert d == {"a": {"b": 1}}
        d["a"]["b"] = 999
        assert config.get("a.b") == 1

    def test_preserves_types(self) -> None:
        config = Config(sources=[Config.defaults({"n": 42, "f": 3.14, "b": True})])
        d = config.to_dict()
        assert isinstance(d["n"], int)
        assert isinstance(d["f"], float)
        assert isinstance(d["b"], bool)


# ---------------------------------------------------------------------------
# to_env
# ---------------------------------------------------------------------------


class TestToEnv:
    def test_flat_keys(self) -> None:
        config = Config(sources=[Config.defaults({"host": "localhost", "port": 5432})])
        env = config.to_env()
        assert env == {"HOST": "localhost", "PORT": "5432"}

    def test_nested_keys(self) -> None:
        config = Config(sources=[Config.defaults({"db": {"host": "localhost", "port": 5432}})])
        env = config.to_env()
        assert env["DB_HOST"] == "localhost"
        assert env["DB_PORT"] == "5432"

    def test_with_prefix(self) -> None:
        config = Config(sources=[Config.defaults({"host": "localhost"})])
        env = config.to_env(prefix="APP")
        assert env == {"APP_HOST": "localhost"}

    def test_deeply_nested(self) -> None:
        config = Config(sources=[Config.defaults({"a": {"b": {"c": "val"}}})])
        env = config.to_env()
        assert env == {"A_B_C": "val"}

    def test_bool_values(self) -> None:
        config = Config(sources=[Config.defaults({"debug": True})])
        env = config.to_env()
        assert env["DEBUG"] == "True"


# ---------------------------------------------------------------------------
# Flatten
# ---------------------------------------------------------------------------


class TestFlatten:
    def test_flat(self) -> None:
        config = Config(sources=[Config.defaults({"db": {"host": "localhost", "port": 5432}})])
        flat = config.flatten()
        assert flat == {"db.host": "localhost", "db.port": "5432"}

    def test_with_prefix(self) -> None:
        config = Config(sources=[Config.defaults({"k": "v"})])
        flat = config.flatten(prefix="app")
        assert flat == {"app.k": "v"}


# ---------------------------------------------------------------------------
# Snapshot and Diffing
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_snapshot_captures_state(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        snap = config.snapshot()
        assert snap.data == {"a": 1}

    def test_snapshot_is_independent(self) -> None:
        config = Config(sources=[Config.defaults({"a": {"b": 1}})])
        snap = config.snapshot()
        snap.data["a"]["b"] = 999
        assert config.get("a.b") == 1

    def test_diff_no_changes(self) -> None:
        snap1 = ConfigSnapshot(data={"a": 1})
        snap2 = ConfigSnapshot(data={"a": 1})
        diff = snap1.diff(snap2)
        assert diff == {"added": {}, "removed": {}, "changed": {}}

    def test_diff_added(self) -> None:
        snap1 = ConfigSnapshot(data={"a": 1})
        snap2 = ConfigSnapshot(data={"a": 1, "b": 2})
        diff = snap1.diff(snap2)
        assert diff["added"] == {"b": 2}
        assert diff["removed"] == {}
        assert diff["changed"] == {}

    def test_diff_removed(self) -> None:
        snap1 = ConfigSnapshot(data={"a": 1, "b": 2})
        snap2 = ConfigSnapshot(data={"a": 1})
        diff = snap1.diff(snap2)
        assert diff["added"] == {}
        assert diff["removed"] == {"b": 2}
        assert diff["changed"] == {}

    def test_diff_changed(self) -> None:
        snap1 = ConfigSnapshot(data={"a": 1})
        snap2 = ConfigSnapshot(data={"a": 2})
        diff = snap1.diff(snap2)
        assert diff["changed"] == {"a": {"old": 1, "new": 2}}

    def test_diff_nested(self) -> None:
        snap1 = ConfigSnapshot(data={"db": {"host": "old", "port": 5432}})
        snap2 = ConfigSnapshot(data={"db": {"host": "new", "port": 5432}, "cache": {"ttl": 60}})
        diff = snap1.diff(snap2)
        assert diff["added"] == {"cache.ttl": 60}
        assert diff["removed"] == {}
        assert diff["changed"] == {"db.host": {"old": "old", "new": "new"}}

    def test_diff_full_workflow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_PORT", "3000")
        config = Config(
            sources=[
                Config.defaults({"host": "localhost", "debug": False}),
                Config.env(prefix="APP_"),
            ]
        )
        before = config.snapshot()

        monkeypatch.setenv("APP_PORT", "8080")
        monkeypatch.setenv("APP_NEW_KEY", "added")
        config.reload()
        after = config.snapshot()

        diff = before.diff(after)
        assert diff["added"] == {"new_key": "added"}
        assert diff["changed"]["port"] == {"old": "3000", "new": "8080"}


# ---------------------------------------------------------------------------
# Freeze
# ---------------------------------------------------------------------------


class TestFreeze:
    def test_freeze_returns_self(self) -> None:
        config = Config(sources=[Config.defaults({"a": 1})])
        assert config.freeze() is config


# ---------------------------------------------------------------------------
# Deep Merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_nested_merge(self) -> None:
        config = Config(
            sources=[
                Config.defaults({"db": {"host": "a", "port": 1}}),
                Config.defaults({"db": {"port": 2}}),
            ]
        )
        assert config.get("db.host") == "a"
        assert config.get("db.port") == 2

    def test_override_dict_with_scalar(self) -> None:
        config = Config(
            sources=[
                Config.defaults({"k": {"nested": 1}}),
                Config.defaults({"k": "flat"}),
            ]
        )
        assert config.get("k") == "flat"


# ---------------------------------------------------------------------------
# Import test (existing)
# ---------------------------------------------------------------------------


class TestImport:
    def test_all_exports(self) -> None:
        import philiprehberger_config_kit

        assert hasattr(philiprehberger_config_kit, "Config")
        assert hasattr(philiprehberger_config_kit, "ConfigError")
        assert hasattr(philiprehberger_config_kit, "ConfigSchema")
        assert hasattr(philiprehberger_config_kit, "ConfigSnapshot")
        assert hasattr(philiprehberger_config_kit, "SchemaError")

    def test_all_list(self) -> None:
        from philiprehberger_config_kit import __all__

        assert "Config" in __all__
        assert "ConfigError" in __all__
        assert "ConfigSchema" in __all__
        assert "ConfigSnapshot" in __all__
        assert "SchemaError" in __all__


class TestOnChange:
    def test_listener_fires_on_changed_value(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"db": {"host": "a"}}))
        config = Config([Config.json_file(cfg_file)])

        events: list[tuple[str, object, object]] = []
        config.on_change(lambda key, old, new: events.append((key, old, new)))

        cfg_file.write_text(json.dumps({"db": {"host": "b"}}))
        config.reload()

        assert ("db.host", "a", "b") in events

    def test_listener_fires_on_added_and_removed_keys(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"x": 1}))
        config = Config([Config.json_file(cfg_file)])

        events: list[tuple[str, object, object]] = []
        config.on_change(lambda key, old, new: events.append((key, old, new)))

        cfg_file.write_text(json.dumps({"y": 2}))
        config.reload()

        keys = {key for key, _old, _new in events}
        assert "x" in keys  # removed
        assert "y" in keys  # added

    def test_no_change_no_event(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"x": 1}))
        config = Config([Config.json_file(cfg_file)])

        events: list[tuple[str, object, object]] = []
        config.on_change(lambda key, old, new: events.append((key, old, new)))

        # No content change
        config.reload()
        assert events == []

    def test_multiple_listeners_fire_in_registration_order(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"x": 1}))
        config = Config([Config.json_file(cfg_file)])

        order: list[str] = []
        config.on_change(lambda k, o, n: order.append(f"first:{k}"))
        config.on_change(lambda k, o, n: order.append(f"second:{k}"))

        cfg_file.write_text(json.dumps({"x": 2}))
        config.reload()

        # Both listeners fire for the changed key, in registration order
        assert order == ["first:x", "second:x"]

    def test_unsubscribe_stops_notifications(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"x": 1}))
        config = Config([Config.json_file(cfg_file)])

        events: list[tuple[str, object, object]] = []
        unsubscribe = config.on_change(lambda k, o, n: events.append((k, o, n)))
        unsubscribe()

        cfg_file.write_text(json.dumps({"x": 2}))
        config.reload()
        assert events == []

class TestDictSourceAndSet:
    def test_dict_source_loads_flat(self) -> None:
        config = Config([Config.dict_source({"host": "x", "port": 5432})])
        assert config.get("host") == "x"
        assert config.get_int("port") == 5432

    def test_dict_source_loads_nested(self) -> None:
        config = Config([Config.dict_source({"db": {"host": "x", "port": 5432}})])
        assert config.get("db.host") == "x"
        assert config.get_int("db.port") == 5432

    def test_dict_source_layers_under_other_sources(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"port": 8080}))
        config = Config([
            Config.dict_source({"host": "x", "port": 5432}),
            Config.json_file(cfg_file),
        ])
        # File overrides dict source
        assert config.get("host") == "x"
        assert config.get_int("port") == 8080

    def test_set_creates_new_key(self) -> None:
        config = Config([Config.dict_source({})])
        config.set("port", 5432)
        assert config.get_int("port") == 5432

    def test_set_overrides_existing_key(self) -> None:
        config = Config([Config.dict_source({"port": 1})])
        config.set("port", 99)
        assert config.get_int("port") == 99

    def test_set_supports_dot_notation(self) -> None:
        config = Config([Config.dict_source({"db": {"host": "x"}})])
        config.set("db.host", "y")
        assert config.get("db.host") == "y"

    def test_set_fires_on_change_listener(self) -> None:
        config = Config([Config.dict_source({"a": 1})])
        events: list[tuple[str, object, object]] = []
        config.on_change(lambda k, o, n: events.append((k, o, n)))

        config.set("a", 2)
        assert events == [("a", 1, 2)]

    def test_set_does_not_fire_for_same_value(self) -> None:
        config = Config([Config.dict_source({"a": 1})])
        events: list[tuple[str, object, object]] = []
        config.on_change(lambda k, o, n: events.append((k, o, n)))

        config.set("a", 1)
        assert events == []

    def test_set_for_new_key_reports_none_old(self) -> None:
        config = Config([Config.dict_source({})])
        events: list[tuple[str, object, object]] = []
        config.on_change(lambda k, o, n: events.append((k, o, n)))

        config.set("new", "value")
        assert events == [("new", None, "value")]

