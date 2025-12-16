# Quickstart: Configuration File Support

**Feature**: 005-config-file
**Date**: 2025-12-15

## Overview

This guide covers implementing persistent configuration file support for pgtail.

## Prerequisites

- Python 3.10+
- Existing pgtail codebase with `pgtail_py/` package
- Understanding of existing `config.py` (platform paths) and `commands.py` (command registration)

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    "prompt_toolkit>=3.0.0",
    "psutil>=5.9.0",
    "tomlkit>=0.12.0",  # NEW
]
```

## Implementation Order

### Phase 1: Core Config Module

1. **Expand `config.py`** with:
   - `get_config_path()` - Platform-specific config file location
   - `ConfigSchema` - Dataclass with all settings and defaults
   - `load_config()` - Read and validate TOML, return ConfigSchema
   - `save_config()` - Write ConfigSchema to TOML (preserve comments)

2. **Key Pattern - Graceful Loading**:
   ```python
   def load_config() -> ConfigSchema:
       path = get_config_path()
       if not path.exists():
           return ConfigSchema()  # All defaults

       try:
           doc = tomlkit.parse(path.read_text())
       except tomlkit.exceptions.ParseError as e:
           warn(f"Config error: {e}. Using defaults.")
           return ConfigSchema()

       return ConfigSchema.from_toml(doc)  # Validates per-key
   ```

### Phase 2: AppState Integration

1. **Modify `cli.py`** - Load config in `AppState.__init__()`:
   ```python
   class AppState:
       def __init__(self):
           self.config = load_config()
           # Apply config to existing state
           if self.config.default.levels:
               self.level_filter = set(self.config.default.levels)
           # etc.
   ```

### Phase 3: Commands

1. **Add to `commands.py`**:
   - Register `config`, `set`, `unset` commands
   - Add autocomplete for setting keys

2. **Add handlers to `cli.py`**:
   - `cmd_config()` - Display config
   - `cmd_config_edit()` - Open in $EDITOR
   - `cmd_config_reset()` - Reset with backup
   - `cmd_config_path()` - Show path
   - `cmd_set()` - Set or show value
   - `cmd_unset()` - Remove setting

### Phase 4: Feature Integration

1. **Update `slow_query.py`** - Read thresholds from config
2. **Update `filter.py`** - Apply default.levels on startup
3. **Update `colors.py`** - Apply theme.name

## Testing Strategy

### Unit Tests (`test_config.py`)

```python
def test_load_missing_config_returns_defaults():
    """Config loading without file uses defaults."""

def test_load_invalid_toml_warns_and_uses_defaults():
    """Invalid TOML syntax triggers warning, uses defaults."""

def test_load_invalid_value_uses_default_for_key():
    """Invalid value for one key doesn't affect others."""

def test_save_preserves_comments():
    """Updating config preserves existing comments."""

def test_validation_slow_thresholds_ordering():
    """warn < error < critical constraint enforced."""
```

### Integration Tests (`test_config_commands.py`)

```python
def test_set_creates_config_file():
    """First set command creates config file."""

def test_config_reset_creates_backup():
    """Reset preserves backup with timestamp."""

def test_config_edit_creates_template():
    """Edit creates commented template if no file exists."""
```

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `pyproject.toml` | MODIFY | Add tomlkit dependency |
| `pgtail_py/config.py` | EXPAND | Add config file loading/saving |
| `pgtail_py/cli.py` | MODIFY | Load config, add command handlers |
| `pgtail_py/commands.py` | MODIFY | Register new commands, autocomplete |
| `pgtail_py/slow_query.py` | MODIFY | Read thresholds from config |
| `pgtail_py/filter.py` | MODIFY | Apply default levels |
| `pgtail_py/colors.py` | MODIFY | Apply theme setting |
| `tests/test_config.py` | NEW | Config module unit tests |
| `tests/test_config_commands.py` | NEW | Command integration tests |

## Common Patterns

### Dotted Key Access

```python
def get_nested(doc: dict, key: str) -> Any:
    """Get value from nested dict using dotted key."""
    parts = key.split(".")
    value = doc
    for part in parts:
        if part not in value:
            return None
        value = value[part]
    return value

def set_nested(doc: dict, key: str, value: Any) -> None:
    """Set value in nested dict using dotted key."""
    parts = key.split(".")
    target = doc
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value
```

### Value Parsing

```python
def parse_value(key: str, raw: str) -> Any:
    """Parse command-line value to correct type."""
    schema = SETTINGS_SCHEMA[key]

    if schema.type == "bool":
        return raw.lower() in ("true", "1", "yes")
    elif schema.type == "int":
        return int(raw)
    elif schema.type == "list":
        return raw.split()  # Space-separated
    else:
        return raw  # String
```

## Verification

After implementation, verify:

1. `pgtail` starts without config file (uses defaults)
2. `set slow.warn 50` creates config file
3. Exit and restart - setting persists
4. `config` shows current settings
5. `config edit` opens editor (with template if new)
6. `config reset` creates backup and resets
7. Invalid config shows warning, uses defaults
