# philiprehberger-config-kit

[![Tests](https://github.com/philiprehberger/py-config-kit/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-config-kit/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-config-kit.svg)](https://pypi.org/project/philiprehberger-config-kit/)
[![License](https://img.shields.io/github/license/philiprehberger/py-config-kit)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-ec6cb9)](https://github.com/sponsors/philiprehberger)

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

# Nested access (dot notation)
redis_host = config.get_str("redis.host")

# Validation
config.require("database_url", "secret_key")  # raises ConfigError if missing

# Check existence
if config.has("cache_ttl"):
    ttl = config.get_int("cache_ttl")
```

## Source Priority

Sources are applied in order — later sources override earlier ones:

```python
Config(sources=[
    Config.defaults({...}),       # lowest priority
    Config.json_file("..."),      # overrides defaults
    Config.env_file(".env"),      # overrides JSON
    Config.env(prefix="APP_"),    # highest priority
])
```

## Environment Variables

With `prefix="APP_"`, env vars are mapped:
- `APP_PORT` → `port`
- `APP_DATABASE__HOST` → `database.host` (double underscore = nested)

## .env Files

```env
DATABASE_URL=postgresql://localhost/mydb
SECRET_KEY="my-secret"
DEBUG=true
```

## Bool Coercion

`get_bool()` accepts: `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`


## API

| Function / Class | Description |
|------------------|-------------|
| `Config(sources)` | Layered configuration with typed access via `get()`, `get_str()`, `get_int()`, `get_float()`, `get_bool()`, `get_list()` |
| `ConfigError(missing)` | Raised when required config keys are missing |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## License

MIT
