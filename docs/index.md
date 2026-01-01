# pgtail

**Interactive PostgreSQL log tailer with auto-detection and color output.**

pgtail automatically discovers running PostgreSQL instances and provides real-time log streaming with powerful filtering, syntax highlighting, and an interactive terminal UI.

## Features

- **Auto-detection** - Automatically finds PostgreSQL instances (running processes, pgrx, PGDATA env)
- **Format support** - TEXT, CSV (csvlog), and JSON (jsonlog) log formats
- **Real-time filtering** - Filter by log level, regex patterns, time ranges, and fields
- **SQL highlighting** - Syntax highlighting for SQL in log messages
- **Vim navigation** - Navigate logs with vim-style keybindings (j/k, g/G, Ctrl+d/u)
- **Visual selection** - Select text with v/V and copy with y or Ctrl+c
- **Slow query detection** - Highlight slow queries based on configurable thresholds
- **Desktop notifications** - Get notified of errors, patterns, or slow queries
- **Themeable** - Built-in themes (dark, light, monokai, solarized) plus custom themes
- **Export** - Export filtered logs to files or pipe to external commands

## Quick Example

```bash
# Start pgtail
pgtail

# List detected instances
pgtail> list

# Tail instance 0
pgtail> tail 0

# In tail mode, filter to errors only
tail> level error

# Exit with 'q' or Ctrl+C
```

## Requirements

- Python 3.10+
- PostgreSQL with logging enabled (`log_destination = 'stderr'`, `csvlog`, or `jsonlog`)

## Installation

```bash
pip install pgtail
```

Or run from source:

```bash
git clone https://github.com/user/pgtail
cd pgtail
make run
```

## Getting Help

- [Getting Started Guide](getting-started/quickstart.md)
- [User Guide](guide/tail-mode.md)
- [CLI Reference](cli-reference.md)
- [Configuration](configuration.md)
