# philiprehberger-config-kit

[![Tests](https://github.com/philiprehberger/py-config-kit/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-config-kit/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-config-kit.svg)](https://pypi.org/project/philiprehberger-config-kit/)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-config-kit)](https://github.com/philiprehberger/py-config-kit/commits/main)

Layered configuration loader merging env vars, files, and defaults.

## Installation

```bash
pip install philiprehberger-config-kit
```

## Usage

```python
from philiprehberger_config_kit import Config

config = Config(
    sources=[
        Config.defaults({"port": 3000, "debug": False, "log_level": "info"}),
        Config.json_file("config.json", optional=True),
        Config.env_file(".env", optional=True),
        Config.env(prefix="APP_"),
    ]
)

# Typed access
port = config.get_int("port")
debug = config.get_bool("debug")
db_url = config.get_str("database_url")
timeout = config.get_float("timeout", default=5.0)
hosts = config.get_list("allowed_hosts")
```

### Dot-Notation Access

Retrieve nested values using dot-separated keys:

```python
from philiprehberger_config_kit import Config

config = Config(
    sources=[
        Config.defaults({
            "database": {"host": "localhost", "port": 5432},
            "cache": {"redis": {"url": "redis://localhost"}},
        }),
    ]
)

host = config.get("database.host")           # "localhost"
port = config.get_int("database.port")        # 5432
url = config.get_str("cache.redis.url")       # "redis://localhost"
```

### Source Priority

Sources are applied in order -- later sources override earlier ones:

```python
from philiprehberger_config_kit import Config

config = Config(sources=[
    Config.defaults({...}),       # lowest priority
    Config.json_file("..."),      # overrides defaults
    Config.env_file(".env"),      # overrides JSON
    Config.env(prefix="APP_"),    # highest priority
])
```

### Schema Validation

Define expected keys, types, and allowed values, then validate:

```python
from philiprehberger_config_kit import Config, ConfigSchema, SchemaError

config = Config(sources=[
    Config.defaults({"host": "localhost", "port": 5432, "mode": "dev"}),
])

schema = ConfigSchema()
schema.required("host", str)
schema.required("port", int)
schema.optional("debug", bool)
schema.required("mode", str, choices=["dev", "prod", "test"])

config.validate(schema)  # raises SchemaError with all failures listed
```

### Reload

Refresh configuration from all sources at runtime:

```python
from philiprehberger_config_kit import Config

config = Config(sources=[Config.env(prefix="APP_")])
port = config.get("port")

# After environment changes...
config.reload()
port = config.get("port")  # picks up the new value
```

### Change Listeners

Get notified when a value changes after `reload()`:

```python
from philiprehberger_config_kit import Config

config = Config(sources=[Config.json_file("config.json")])

def log_change(key, old, new):
    print(f"{key}: {old!r} -> {new!r}")

unsubscribe = config.on_change(log_change)

# Later, after the source file changes on disk:
config.reload()
# log_change is called once per dotted key whose value changed

unsubscribe()  # stop listening
```

### Export Methods

```python
from philiprehberger_config_kit import Config

config = Config(sources=[
    Config.defaults({"db": {"host": "localhost", "port": 5432}, "debug": True}),
])

# Deep copy as nested dict
data = config.to_dict()
# {"db": {"host": "localhost", "port": 5432}, "debug": True}

# Flat dict with dot-notation keys (string values)
flat = config.flatten()
# {"db.host": "localhost", "db.port": "5432", "debug": "True"}

# Environment variable format (UPPER_SNAKE_CASE, string values)
env = config.to_env(prefix="APP")
# {"APP_DB_HOST": "localhost", "APP_DB_PORT": "5432", "APP_DEBUG": "True"}
```

### Config Snapshot Diffing

Capture config state and compare snapshots to see what changed:

```python
from philiprehberger_config_kit import Config

config = Config(sources=[
    Config.defaults({"host": "localhost", "port": 3000}),
    Config.env(prefix="APP_"),
])

before = config.snapshot()

# ... environment changes, then reload ...
config.reload()
after = config.snapshot()

diff = before.diff(after)
# {"added": {...}, "removed": {...}, "changed": {"port": {"old": "3000", "new": "8080"}}}
```

### Typed List Getters

Parse comma-separated values into typed lists:

```python
from philiprehberger_config_kit import Config

config = Config(sources=[
    Config.defaults({"ports": "8080,8081,8082", "rates": "1.5,2.0,3.7"}),
])

ports = config.get_int_list("ports")      # [8080, 8081, 8082]
rates = config.get_float_list("rates")    # [1.5, 2.0, 3.7]

# Custom separator
config2 = Config(sources=[Config.defaults({"ids": "1|2|3"})])
config2.get_int_list("ids", sep="|")      # [1, 2, 3]
```

### Environment Variables

With `prefix="APP_"`, env vars are mapped:
- `APP_PORT` -> `port`
- `APP_DATABASE__HOST` -> `database.host` (double underscore = nested)

### Bool Coercion

`get_bool()` accepts: `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`

## API

| Function / Class | Description |
|------------------|-------------|
| `Config(sources)` | Layered configuration with typed access |
| `Config.get(key, default)` | Get a value by key with dot-notation support |
| `Config.get_str(key, default)` | Get a string value |
| `Config.get_int(key, default)` | Get an integer value |
| `Config.get_float(key, default)` | Get a float value |
| `Config.get_bool(key, default)` | Get a boolean value with coercion |
| `Config.get_list(key, separator, default)` | Get a list by splitting a string value |
| `Config.get_int_list(key, sep)` | Split a string value and convert each element to int |
| `Config.get_float_list(key, sep)` | Split a string value and convert each element to float |
| `Config.require(*keys)` | Raise `ConfigError` if any keys are missing |
| `Config.has(key)` | Check if a key exists |
| `Config.validate(schema)` | Validate config against a `ConfigSchema` |
| `Config.reload()` | Reload configuration from all sources |
| `Config.on_change(callback)` | Register `(key, old, new)` listener; returns unsubscribe |
| `Config.to_dict()` | Return a deep copy as a nested dictionary |
| `Config.to_env(prefix)` | Export as `UPPER_SNAKE_CASE` environment variable pairs |
| `Config.flatten(prefix)` | Export as flat dict with dot-notation keys |
| `Config.snapshot()` | Capture current state as a `ConfigSnapshot` |
| `Config.freeze()` | Freeze the config to prevent mutation |
| `ConfigSchema` | Define expected keys, types, required/optional, and choices |
| `ConfigSchema.required(key, type, choices)` | Add a required field to the schema |
| `ConfigSchema.optional(key, type, choices)` | Add an optional field to the schema |
| `ConfigSnapshot` | Immutable snapshot of config state |
| `ConfigSnapshot.diff(other)` | Compare two snapshots and return added/removed/changed keys |
| `ConfigError(missing)` | Raised when required config keys are missing |
| `SchemaError(errors)` | Raised when config values fail schema validation |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this project useful:

⭐ [Star the repo](https://github.com/philiprehberger/py-config-kit)

🐛 [Report issues](https://github.com/philiprehberger/py-config-kit/issues?q=is%3Aissue+is%3Aopen+label%3Abug)

💡 [Suggest features](https://github.com/philiprehberger/py-config-kit/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

❤️ [Sponsor development](https://github.com/sponsors/philiprehberger)

🌐 [All Open Source Projects](https://philiprehberger.com/open-source-packages)

💻 [GitHub Profile](https://github.com/philiprehberger)

🔗 [LinkedIn Profile](https://www.linkedin.com/in/philiprehberger)

## License

[MIT](LICENSE)
