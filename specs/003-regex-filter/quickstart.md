# Quickstart: Regex Pattern Filtering

**Feature**: 003-regex-filter
**Date**: 2025-12-14

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

- [ ] Create `pgtail_py/regex_filter.py`
- [ ] Implement `FilterType` enum
- [ ] Implement `RegexFilter` dataclass with `create()` and `matches()`
- [ ] Implement `Highlight` dataclass with `create()` and `find_spans()`
- [ ] Implement `FilterState` dataclass with filter management methods
- [ ] Implement `parse_filter_arg()` to parse `/pattern/` syntax
- [ ] Add unit tests in `tests/test_regex_filter.py`

### Phase 2: CLI Integration (cli.py)

- [ ] Add `regex_state: FilterState` to `AppState`
- [ ] Implement `filter_command()` handler
- [ ] Implement `highlight_command()` handler
- [ ] Update `handle_command()` to dispatch filter/highlight
- [ ] Update help text with new commands

### Phase 3: Commands & Completion (commands.py)

- [ ] Add "filter" and "highlight" to `COMMANDS` dict
- [ ] Add completion for filter subcommands (`clear`, pattern prefixes)
- [ ] Add completion for highlight subcommands

### Phase 4: Output Integration (colors.py, tailer.py)

- [ ] Add `HIGHLIGHT_STYLE` to `colors.py`
- [ ] Implement `format_log_entry_with_highlights()`
- [ ] Update `tailer.py` to check `FilterState.should_show()`
- [ ] Update `tailer.py` to pass highlights to formatting

### Phase 5: Testing & Documentation

- [ ] Integration tests for command flow
- [ ] Update help command output
- [ ] Manual testing with real PostgreSQL logs

## Key Files

| File | Change Type | Description |
|------|-------------|-------------|
| `pgtail_py/regex_filter.py` | NEW | Core regex filter logic |
| `pgtail_py/cli.py` | MODIFY | Add filter/highlight commands |
| `pgtail_py/commands.py` | MODIFY | Add commands to COMMANDS dict |
| `pgtail_py/colors.py` | MODIFY | Add highlight rendering |
| `pgtail_py/tailer.py` | MODIFY | Integrate filter checking |
| `tests/test_regex_filter.py` | NEW | Unit tests |

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
