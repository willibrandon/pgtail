# Quickstart: Regex Pattern Filtering

**Feature**: 003-regex-filter
**Date**: 2025-12-14
**Status**: COMPLETE

## Developer Setup

### Prerequisites

1. Python 3.10+ installed
2. Repository cloned
3. Virtual environment set up

```bash
cd /Users/brandon/src/pgtail
make shell  # Activates .venv
```

### Install Dependencies

```bash
uv sync  # or pip install -e ".[dev]"
```

### Run Tests

```bash
make test  # Run all tests
uv run pytest tests/test_regex_filter.py -v  # Run new tests only
```

### Run pgtail

```bash
make run  # or: uv run python -m pgtail_py
```

## Implementation Checklist

### Phase 1: Core Module (regex_filter.py)

- [x] Create `pgtail_py/regex_filter.py`
- [x] Implement `FilterType` enum
- [x] Implement `RegexFilter` dataclass with `create()` and `matches()`
- [x] Implement `Highlight` dataclass with `create()` and `find_spans()`
- [x] Implement `FilterState` dataclass with filter management methods
- [x] Implement `parse_filter_arg()` to parse `/pattern/` syntax
- [x] Add unit tests in `tests/test_regex_filter.py`

### Phase 2: CLI Integration (cli.py)

- [x] Add `regex_state: FilterState` to `AppState`
- [x] Implement `filter_command()` handler
- [x] Implement `highlight_command()` handler
- [x] Update `handle_command()` to dispatch filter/highlight
- [x] Update help text with new commands

### Phase 3: Commands & Completion (commands.py)

- [x] Add "filter" and "highlight" to `COMMANDS` dict
- [x] Add completion for filter subcommands (`clear`, pattern prefixes)
- [x] Add completion for highlight subcommands

### Phase 4: Output Integration (colors.py, tailer.py)

- [x] Add `HIGHLIGHT_STYLE` to `colors.py`
- [x] Implement `format_log_entry_with_highlights()`
- [x] Update `tailer.py` to check `FilterState.should_show()`
- [x] Update `cli.py` to pass highlights to formatting

### Phase 5: Testing & Documentation

- [x] Unit tests for all new functions (47 tests in test_regex_filter.py)
- [x] Update help command output
- [x] Manual testing with real PostgreSQL logs

## Key Files

| File | Change Type | Description |
|------|-------------|-------------|
| `pgtail_py/regex_filter.py` | NEW | Core regex filter logic |
| `pgtail_py/cli.py` | MODIFY | Add filter/highlight commands |
| `pgtail_py/commands.py` | MODIFY | Add commands to COMMANDS dict |
| `pgtail_py/colors.py` | MODIFY | Add highlight rendering |
| `pgtail_py/tailer.py` | MODIFY | Integrate filter checking |
| `tests/test_regex_filter.py` | NEW | Unit tests (47 tests) |

## Testing Commands

Once implemented, test with:

```
pgtail> filter /ERROR/
pgtail> filter -/connection/
pgtail> filter +/WARNING/
pgtail> filter &/users/
pgtail> filter
pgtail> filter clear
pgtail> highlight /SELECT/
pgtail> highlight
pgtail> highlight clear
```

## Architecture Notes

1. **Separation of Concerns**: `regex_filter.py` handles all regex logic; `cli.py` handles command parsing; `colors.py` handles rendering
2. **Performance**: Patterns compiled once at creation, reused for all matching
3. **Filter Order**: Level filter checked first (in `tailer.py`), then regex filters
4. **Highlight Rendering**: Applied after filter check, only to displayed lines
