# Implementation Plan: SQL Syntax Highlighting

**Branch**: `014-sql-highlighting` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-sql-highlighting/spec.md`

## Summary

Add SQL syntax highlighting to PostgreSQL log messages. SQL keywords, identifiers, strings, numbers, operators, comments, and functions will each display in distinct colors when viewing logs in streaming mode or fullscreen TUI. The feature integrates with the existing theme system and is always-on when colors are enabled (respects NO_COLOR).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (FormattedText styling), existing theme.py/ThemeManager
**Storage**: N/A (stateless highlighting)
**Testing**: pytest with unit tests for tokenizer and integration tests for display
**Target Platform**: macOS, Linux, Windows (cross-platform via prompt_toolkit)
**Project Type**: Single CLI application
**Performance Goals**: <100ms highlighting for 10,000-character SQL statements
**Constraints**: Must not introduce visible lag on high-volume log output
**Scale/Scope**: Single-line SQL detection and highlighting (no cross-line parsing)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
|-----------|--------|-----------|
| I. Simplicity First | PASS | Feature is always-on with no new commands; integrates with existing theme system |
| II. Cross-Platform Parity | PASS | Uses prompt_toolkit FormattedText which works identically on all platforms |
| III. Graceful Degradation | PASS | Malformed SQL shows recognizable tokens; unrecognized portions remain unhighlighted |
| IV. User-Friendly Feedback | PASS | Enhances log readability with color-coded SQL elements |
| V. Focused Scope | PASS | SQL highlighting aids log tailing workflow; no new features beyond display |
| VI. Minimal Dependencies | PASS | No new dependencies; uses existing prompt_toolkit for styling |
| VII. Developer Workflow Priority | PASS | SQL highlighting accelerates finding specific queries in logs |

**Gate Result**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/014-sql-highlighting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── sql_tokenizer.py     # NEW: SQL tokenizer (SQLTokenType enum, SQLToken dataclass, SQLTokenizer class)
├── sql_highlighter.py   # NEW: SQL highlighter (SQLHighlighter class, format_sql() function)
├── sql_detector.py      # NEW: SQL detection in log messages (detect_sql_content(), extract_sql_portion())
├── theme.py             # MODIFY: Add SQL color style keys to Theme.ui
├── themes/              # MODIFY: Add SQL colors to each built-in theme
│   ├── dark.py
│   ├── light.py
│   ├── high_contrast.py
│   ├── monokai.py
│   ├── solarized_dark.py
│   └── solarized_light.py
├── display.py           # MODIFY: Integrate SQL highlighting into format_entry_* functions
├── colors.py            # MODIFY: Add SQL style class names to color mapping (if needed)
└── fullscreen/
    └── layout.py        # MODIFY: Ensure FormattedText with SQL highlighting renders correctly

tests/
├── test_sql_tokenizer.py    # NEW: Unit tests for SQL tokenization
├── test_sql_highlighter.py  # NEW: Unit tests for SQL highlighting
├── test_sql_detector.py     # NEW: Unit tests for SQL detection
└── test_display_sql.py      # NEW: Integration tests for SQL in display formatting
```

**Structure Decision**: Single project structure with new SQL-related modules in pgtail_py/. Tests follow existing pytest convention in tests/ directory.

## Complexity Tracking

> No violations - this section is intentionally empty.
