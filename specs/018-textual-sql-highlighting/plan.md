# Implementation Plan: SQL Syntax Highlighting in Textual Tail Mode

**Branch**: `018-textual-sql-highlighting` | **Date**: 2025-12-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-textual-sql-highlighting/spec.md`

## Summary

Port SQL syntax highlighting from prompt_toolkit mode to Textual-based tail mode by creating a Rich-compatible SQL highlighter that integrates with the existing theme system. The existing `sql_tokenizer.py` and `sql_detector.py` modules are reused; a new `highlight_sql_rich()` function converts SQL tokens to Rich markup strings, which are then integrated into `tail_rich.py:format_entry_compact()`.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- `textual` >=0.89.0 (TailLog widget, Text.from_markup())
- `rich` (via textual, Rich markup strings)
- `prompt_toolkit` (existing sql_highlighter.py, theme.py)

**Storage**: N/A (no persistence required)
**Testing**: pytest with Textual's pilot for async widget tests
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single Python package
**Performance Goals**:
- <100ms render latency per log entry (SC-001)
- 100+ entries/sec without visible delay (SC-004)
- 50KB SQL statements without degradation (SC-006)

**Constraints**:
- Must reuse existing `sql_tokenizer.py` (300+ keywords, tested)
- Must reuse existing `sql_detector.py` (PostgreSQL log patterns, tested)
- Must integrate with existing theme system (`theme.py`, 6 built-in themes)
- Must preserve clipboard functionality (strip markup before copy)
- Must respect NO_COLOR environment variable

**Scale/Scope**:
- 10,000 line buffer in TailLog widget
- 7 SQL token types (KEYWORD, IDENTIFIER, STRING, NUMBER, OPERATOR, COMMENT, FUNCTION)
- 6 built-in themes to update (dark, light, high-contrast, monokai, solarized-dark, solarized-light)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | No configuration required; SQL highlighting is always-on. Reuses existing tokenizer/detector. |
| II. Cross-Platform Parity | ✅ PASS | Uses Rich markup (cross-platform). No platform-specific code. |
| III. Graceful Degradation | ✅ PASS | Malformed SQL shows unrecognized tokens plain. NO_COLOR disables all highlighting. |
| IV. User-Friendly Feedback | ✅ PASS | Color-coded SQL improves log readability. Consistent with IDE conventions. |
| V. Focused Scope | ✅ PASS | Extends existing tail mode; no new commands or features outside spec. |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies. Uses existing Rich (via Textual) and theme system. |
| VII. Developer Workflow Priority | ✅ PASS | Helps developers quickly identify SQL structure in PostgreSQL logs. |
| Quality Standards | ✅ PASS | All new code will have tests. Type hints required. <900 LOC per file. |

**Gate Result**: ✅ ALL GATES PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/018-textual-sql-highlighting/
├── plan.md              # This file
├── research.md          # Phase 0 output (Rich markup patterns, theme integration)
├── data-model.md        # Phase 1 output (SQLToken → Rich markup mapping)
├── quickstart.md        # Phase 1 output (implementation guide)
├── contracts/           # Phase 1 output (N/A - no APIs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── sql_tokenizer.py         # EXISTING - SQLToken, SQLTokenType, SQLTokenizer (NO CHANGES)
├── sql_detector.py          # EXISTING - detect_sql_content() (NO CHANGES)
├── sql_highlighter.py       # MODIFY - Add highlight_sql_rich() function
├── tail_rich.py             # MODIFY - Integrate SQL detection + highlighting
├── theme.py                 # EXISTING - Theme, ThemeManager (minimal changes for getters)
├── themes/
│   ├── __init__.py          # EXISTING - BUILTIN_THEMES registry
│   ├── dark.py              # EXISTING - Already has sql_* colors
│   ├── light.py             # VERIFY - Add sql_* colors if missing
│   ├── high_contrast.py     # VERIFY - Add sql_* colors if missing
│   ├── monokai.py           # VERIFY - Add sql_* colors if missing
│   ├── solarized_dark.py    # VERIFY - Add sql_* colors if missing
│   └── solarized_light.py   # VERIFY - Add sql_* colors if missing
└── utils.py                 # EXISTING - is_color_disabled() (NO CHANGES)

tests/
├── test_sql_highlighter.py  # EXTEND - Add tests for highlight_sql_rich()
├── test_tail_rich.py        # EXTEND - Add SQL highlighting integration tests
└── test_tail_textual.py     # EXTEND - Add async tests for SQL in tail mode
```

**Structure Decision**: Single project layout. Feature adds one new function to `sql_highlighter.py` and modifies `tail_rich.py`. Theme files already contain SQL color definitions (verified in dark.py).

## Complexity Tracking

No constitution violations. No complexity tracking required.

---

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Simplicity First | ✅ PASS | Minimal code changes: 1 new function + 1 modified function. Reuses 100% of existing tokenizer/detector. |
| II. Cross-Platform Parity | ✅ PASS | No platform-specific code. Rich markup works identically on macOS/Linux/Windows. |
| III. Graceful Degradation | ✅ PASS | Verified: missing theme keys return empty style → unstyled text. NO_COLOR checked first. |
| IV. User-Friendly Feedback | ✅ PASS | All 6 built-in themes have SQL colors. Theme customization documented in template. |
| V. Focused Scope | ✅ PASS | Only tail_rich.py and sql_highlighter.py modified. No new commands or CLI changes. |
| VI. Minimal Dependencies | ✅ PASS | Zero new dependencies. Uses existing Rich (bundled with Textual). |
| VII. Developer Workflow Priority | ✅ PASS | SQL highlighting helps identify query structure at a glance in PostgreSQL logs. |
| Quality Standards | ✅ PASS | New code has tests. <900 LOC verified (sql_highlighter.py: ~150 LOC). |

**Post-Design Gate Result**: ✅ ALL GATES PASS - Ready for task generation

---

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Implementation Plan | `specs/018-textual-sql-highlighting/plan.md` | ✅ Complete |
| Research Document | `specs/018-textual-sql-highlighting/research.md` | ✅ Complete |
| Data Model | `specs/018-textual-sql-highlighting/data-model.md` | ✅ Complete |
| Contracts | `specs/018-textual-sql-highlighting/contracts/README.md` | ✅ Complete (N/A - no APIs) |
| Quickstart Guide | `specs/018-textual-sql-highlighting/quickstart.md` | ✅ Complete |

**Next Step**: Run `/speckit.tasks` to generate tasks.md
