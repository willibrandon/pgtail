# Quickstart: pgtail Python Rewrite

## Prerequisites

- Python 3.10 or later
- PostgreSQL installed (any method: Homebrew, apt, pgrx, source)

## Development Setup

```bash
# Clone and enter the repository
cd pgtail

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install prompt_toolkit psutil watchdog

# Install dev dependencies
pip install pytest ruff pyinstaller

# Run from source
python -m pgtail_py
```

## Basic Usage

```bash
# Launch pgtail
python -m pgtail_py

# Or after building executable
./dist/pgtail
```

### Commands

```
pgtail> list                    # Show detected PostgreSQL instances
pgtail> tail 1                  # Tail logs for instance #1
pgtail> tail /path/to/data      # Tail logs by data directory path
pgtail> levels ERROR WARNING    # Filter to only ERROR and WARNING
pgtail> levels                  # Show current filter settings
pgtail> levels ALL              # Show all log levels
pgtail> stop                    # Stop current tail
pgtail> refresh                 # Re-scan for instances
pgtail> enable-logging 1        # Enable logging_collector for instance
pgtail> clear                   # Clear screen
pgtail> help                    # Show help
pgtail> quit                    # Exit (or 'exit' or Ctrl+D)
```

### Keyboard Shortcuts

- `Tab` - Autocomplete commands and arguments
- `Up/Down` - Navigate command history
- `Ctrl+C` - Stop current tail
- `Ctrl+D` - Exit pgtail

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pgtail_py

# Run specific test file
pytest tests/test_parser.py

# Run with verbose output
pytest -v
```

## Building Executable

```bash
# Build single-file executable
pyinstaller --onefile --name pgtail pgtail_py/__main__.py

# Output in dist/pgtail (or dist/pgtail.exe on Windows)
ls -la dist/
```

## Linting

```bash
# Check code style
ruff check pgtail_py/

# Auto-fix issues
ruff check --fix pgtail_py/

# Format code
ruff format pgtail_py/
```

## Verification Checklist

After implementation, verify:

1. [ ] `python -m pgtail_py` launches within 1 second
2. [ ] `list` shows running PostgreSQL instances
3. [ ] `list` shows pgrx instances from `~/.pgrx/`
4. [ ] `tail 1` streams log output with colors
5. [ ] Colors render correctly on macOS, Linux, Windows
6. [ ] `levels ERROR` filters to only ERROR messages
7. [ ] `Tab` autocompletes commands
8. [ ] `Up` arrow recalls previous commands
9. [ ] History persists across sessions
10. [ ] `NO_COLOR=1 python -m pgtail_py` shows no colors
11. [ ] `stop` halts tail and returns to prompt
12. [ ] `Ctrl+C` during tail returns to prompt
13. [ ] `Ctrl+D` exits cleanly
14. [ ] `pytest` passes all tests
15. [ ] `ruff check pgtail_py/` reports no errors
16. [ ] PyInstaller executable runs standalone
