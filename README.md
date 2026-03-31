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

### Basic Setup

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

### Source Priority

Sources are applied in order -- later sources override earlier ones:

```python
Config(sources=[
    Config.defaults({...}),       # lowest priority
    Config.json_file("..."),      # overrides defaults
    Config.env_file(".env"),      # overrides JSON
    Config.env(prefix="APP_"),    # highest priority
])
```

### Typed List Getters

Parse comma-separated values into typed lists:

```python
config = Config(sources=[
    Config.defaults({"ports": "8080,8081,8082", "rates": "1.5,2.0,3.7"}),
])

ports = config.get_int_list("ports")      # [8080, 8081, 8082]
rates = config.get_float_list("rates")    # [1.5, 2.0, 3.7]

# Custom separator
config2 = Config(sources=[Config.defaults({"ids": "1|2|3"})])
config2.get_int_list("ids", sep="|")      # [1, 2, 3]
```

### Config Flattening

Export nested config as a flat dictionary with dot-notation keys:

```python
config = Config(sources=[
    Config.defaults({"db": {"host": "localhost", "port": 5432}, "debug": True}),
])

flat = config.flatten()
# {"db.host": "localhost", "db.port": "5432", "debug": "True"}

# With a prefix
flat = config.flatten(prefix="app")
# {"app.db.host": "localhost", "app.db.port": "5432", "app.debug": "True"}
```

### Environment Variables

With `prefix="APP_"`, env vars are mapped:
- `APP_PORT` -> `port`
- `APP_DATABASE__HOST` -> `database.host` (double underscore = nested)

### .env Files

```env
DATABASE_URL=postgresql://localhost/mydb
SECRET_KEY="my-secret"
DEBUG=true
```

### Bool Coercion

`get_bool()` accepts: `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`

## API

| Function / Class | Description |
|------------------|-------------|
| `Config(sources)` | Layered configuration with typed access via `get()`, `get_str()`, `get_int()`, `get_float()`, `get_bool()`, `get_list()` |
| `Config.get_int_list(key, sep)` | Split a string value and convert each element to int |
| `Config.get_float_list(key, sep)` | Split a string value and convert each element to float |
| `Config.flatten(prefix)` | Export nested config as flat dict with dot-notation keys |
| `ConfigError(missing)` | Raised when required config keys are missing |

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
