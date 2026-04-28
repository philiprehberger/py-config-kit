# Changelog

## 0.4.0 (2026-04-27)

- Add `Config.on_change(callback)` observer hook that fires `(key, old, new)` for every dotted key whose value differs after a `reload()`
- Listener registration returns an unsubscribe callable
- Same-value reloads are silent — callbacks fire only on actual changes

## 0.3.0 (2026-04-01)

- Add schema validation with `ConfigSchema` for defining expected keys, types, required/optional, and allowed choices
- Add `SchemaError` exception with detailed error messages for all validation failures
- Add `reload()` method to refresh configuration from all sources at runtime
- Add `to_env()` export method for converting config to `UPPER_SNAKE_CASE` environment variable pairs
- Add `snapshot()` method and `ConfigSnapshot` class for capturing config state
- Add snapshot diffing via `ConfigSnapshot.diff()` to compare added, removed, and changed keys
- Add comprehensive test suite covering all features

## 0.2.1 (2026-03-31)

- Standardize README to 3-badge format with emoji Support section
- Update CI checkout action to v5 for Node.js 24 compatibility

## 0.2.0 (2026-03-27)

- Add `get_int_list()` and `get_float_list()` typed list getters
- Add `flatten()` for exporting nested config as flat dot-notation dict
- Add issue templates, PR template, and Dependabot config
- Add full badge set and Support section to README

## 0.1.8 (2026-03-22)

- Add pytest and mypy configuration to pyproject.toml

## 0.1.5

- Add basic import test

## 0.1.4

- Add Development section to README

## 0.1.1

- Add project URLs to pyproject.toml

## 0.1.0 (2026-03-10)

- Initial release
