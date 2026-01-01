# Research: Configuration File Support

**Feature**: 005-config-file
**Date**: 2025-12-15

## Research Topics

### 1. TOML Library Selection

**Decision**: Use `tomlkit` for all TOML operations (read and write)

**Rationale**:
- FR-014 requires preserving comments and formatting when updating config via `set` command
- Only `tomlkit` supports style-preserving roundtrip parsing
- `tomli`/`tomllib` are read-only and lose comments on parse
- Performance difference is acceptable for config file operations (single file, <1KB typical)

**Alternatives Considered**:

| Library | Read | Write | Preserves Comments | Performance | Decision |
|---------|------|-------|-------------------|-------------|----------|
| tomllib (stdlib 3.11+) | Yes | No | No | Fast | Rejected - no write, loses comments |
| tomli (PyPI) | Yes | No | No | Fast | Rejected - no write, loses comments |
| tomli-w (PyPI) | No | Yes | No | Fast | Rejected - write-only, loses comments |
| tomlkit | Yes | Yes | Yes | Slower (acceptable for config) | **Selected** |

**Implementation Notes**:
- Use `tomlkit.parse()` for reading (preserves structure)
- Use `tomlkit.dumps()` for writing (preserves comments)
- `tomlkit` objects behave like dicts for access but retain TOML structure

**Sources**:
- [Comparison of Python TOML parser libraries](https://dev.to/pypyr/comparison-of-python-toml-parser-libraries-595e)
- [Python and TOML: Read, Write, and Configure - Real Python](https://realpython.com/python-toml/)
- [PEP 680 - tomllib](https://peps.python.org/pep-0680/)

### 2. Platform-Specific Config Paths

**Decision**: Follow OS conventions exactly as specified in FR-001

**Rationale**:
- Existing `config.py` already implements platform detection for history path
- Same pattern can be reused for config file path
- XDG Base Directory spec for Linux, Application Support for macOS, APPDATA for Windows

**Implementation Pattern** (from existing `config.py`):
```python
def get_config_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "pgtail" / "config.toml"
```

**Note**: Linux uses `XDG_CONFIG_HOME` (not `XDG_DATA_HOME` like history) per XDG spec.

### 3. Default Config Template

**Decision**: Generate commented template on `config edit` when file doesn't exist

**Rationale**:
- Users editing config should see all available options with explanations
- Comments serve as inline documentation
- tomlkit preserves these comments on subsequent `set` operations

**Template Structure**:
```toml
# pgtail configuration file
# Documentation: https://github.com/willibrandon/pgtail#configuration

[default]
# levels = ["ERROR", "WARNING", "FATAL"]  # Filter to specific log levels
# follow = true                            # Auto-follow new log entries

[slow]
# warn = 100      # Yellow highlight threshold (ms)
# error = 500     # Orange highlight threshold (ms)
# critical = 1000 # Red highlight threshold (ms)

[display]
# timestamp_format = "%H:%M:%S.%f"  # strftime format
# show_pid = true                    # Show process ID
# show_level = true                  # Show log level

[theme]
# name = "dark"  # Options: dark, light

[notifications]
# enabled = false
# levels = ["FATAL", "PANIC"]
# quiet_hours = "22:00-08:00"
```

### 4. Graceful Degradation Strategy

**Decision**: Warn and continue with per-key fallback

**Rationale**:
- FR-016 requires graceful degradation
- Per-key fallback maximizes usable settings from partially valid config
- Clear error messages help users fix issues

**Implementation**:
```python
def load_config() -> Config:
    try:
        doc = tomlkit.parse(config_path.read_text())
    except TOMLDecodeError as e:
        warn(f"Config parse error: {e}. Using defaults.")
        return Config()  # All defaults

    config = Config()
    for key, validator in SCHEMA.items():
        try:
            value = get_nested(doc, key)
            if value is not None:
                config.set(key, validator(value))
        except (ValueError, TypeError) as e:
            warn(f"Invalid value for {key}: {e}. Using default.")
    return config
```

### 5. Backup Strategy for `config reset`

**Decision**: Timestamp-based backup with `.bak` extension

**Rationale**:
- Prevents accidental data loss
- Multiple backups allowed (no overwrite)
- Easy to identify and restore

**Format**: `config.toml.bak.YYYYMMDD-HHMMSS`

**Example**: `config.toml.bak.20251215-143022`

### 6. Integration with Existing Features

**Decision**: Apply config at AppState initialization, before REPL loop

**Files to Modify**:

| File | Changes |
|------|---------|
| `cli.py` | Load config in `AppState.__init__`, apply to existing state |
| `slow_query.py` | Read thresholds from `AppState.config` instead of hardcoded |
| `filter.py` | Apply `default.levels` from config on startup |
| `commands.py` | Add `config`, `set`, `unset` command definitions |

**Startup Flow**:
1. `AppState.__init__()` calls `load_config()`
2. Config values applied to state (level_filter, slow_thresholds, etc.)
3. REPL loop starts with config applied
4. `set` commands update both in-memory state and config file

## Dependency Addition

**New Dependency**: `tomlkit>=0.12.0`

**pyproject.toml Update**:
```toml
dependencies = [
    "prompt_toolkit>=3.0.0",
    "psutil>=5.9.0",
    "tomlkit>=0.12.0",
]
```

**Justification**: Required for FR-014 (preserve comments). No pure-stdlib alternative exists for roundtrip TOML with comment preservation.

## Open Questions (Resolved)

All research questions have been resolved. Ready for Phase 1.
