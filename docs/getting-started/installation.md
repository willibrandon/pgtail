# Installation

## Requirements

- Python 3.10 or higher
- PostgreSQL with logging enabled

## Install from PyPI

```bash
pip install pgtail
```

## Install from Source

```bash
git clone https://github.com/willibrandon/pgtail
cd pgtail
pip install -e .
```

## Development Setup

```bash
git clone https://github.com/willibrandon/pgtail
cd pgtail
make run  # Run from source
make test # Run tests
make lint # Lint code
```

## Verify Installation

```bash
pgtail --version
```

Or start the REPL:

```bash
pgtail
pgtail> help
```

## PostgreSQL Configuration

For pgtail to work, PostgreSQL logging must be enabled. The minimal configuration in `postgresql.conf`:

```ini
# Enable logging
logging_collector = on
log_directory = 'log'

# Choose your preferred format
log_destination = 'stderr'  # TEXT format (default)
# log_destination = 'csvlog'  # CSV format (26 fields)
# log_destination = 'jsonlog' # JSON format (PG15+)

# Recommended: log all statements for development
log_statement = 'all'
log_duration = on
```

Reload PostgreSQL after changes:

```bash
pg_ctl reload
```
