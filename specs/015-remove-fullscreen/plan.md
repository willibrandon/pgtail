# Implementation Plan: Remove Fullscreen TUI

**Branch**: `015-remove-fullscreen` | **Date**: 2025-12-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-remove-fullscreen/spec.md`

## Summary

Remove the fullscreen TUI feature entirely from pgtail. This is a deletion-only feature with no new code added. All fullscreen-related modules, imports, commands, tests, and documentation must be removed. Themes and SQL highlighting are NOT affected as they are used by the main REPL.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, pygments >=2.0 (retained for SQL highlighting)
**Storage**: N/A
**Testing**: pytest
**Target Platform**: macOS, Linux, Windows
**Project Type**: Single CLI application
**Performance Goals**: N/A (removal feature)
**Constraints**: No backwards compatibility, no deprecation warnings
**Scale/Scope**: ~1200 lines of code to remove across 14 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Removing redundant feature simplifies codebase |
| II. Cross-Platform Parity | ✅ N/A | Removal affects all platforms equally |
| III. Graceful Degradation | ✅ PASS | Unknown command error is graceful |
| IV. User-Friendly Feedback | ✅ PASS | Standard "unknown command" feedback |
| V. Focused Scope | ✅ PASS | Aligns with keeping tool focused |
| VI. Minimal Dependencies | ✅ PASS | No dependency changes |
| VII. Developer Workflow Priority | ✅ PASS | Core tailing unaffected |

**Gate Result**: PASS - No violations. Proceed with implementation.

## Project Structure

### Documentation (this feature)

```text
specs/015-remove-fullscreen/
├── plan.md              # This file
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Specification validation checklist
└── tasks.md             # Implementation tasks (created by /speckit.tasks)
```

### Source Code (repository root)

```text
pgtail_py/
├── cli.py                    # MODIFY: Remove fullscreen imports and references
├── commands.py               # MODIFY: Remove fullscreen/fs command definitions
├── cli_fullscreen.py         # DELETE: Fullscreen command handler
└── fullscreen/               # DELETE: Entire directory
    ├── __init__.py
    ├── app.py
    ├── buffer.py
    ├── buffer_lexer.py
    ├── keybindings.py
    ├── layout.py
    ├── lexer.py
    └── state.py

tests/
├── unit/fullscreen/          # DELETE: Entire directory
│   ├── __init__.py
│   ├── test_buffer.py
│   ├── test_cli_fullscreen.py
│   ├── test_keybindings.py
│   └── test_state.py
└── integration/
    └── test_fullscreen.py    # DELETE: Integration test file

CLAUDE.md                     # MODIFY: Remove fullscreen documentation section
```

**Structure Decision**: Deletion-only changes to existing single-project structure. No new files created.

## Complexity Tracking

> No violations to justify. This is a simplification feature.

## Files to Delete

### Source Files (8 files)
1. `pgtail_py/fullscreen/__init__.py`
2. `pgtail_py/fullscreen/app.py`
3. `pgtail_py/fullscreen/buffer.py`
4. `pgtail_py/fullscreen/buffer_lexer.py`
5. `pgtail_py/fullscreen/keybindings.py`
6. `pgtail_py/fullscreen/layout.py`
7. `pgtail_py/fullscreen/lexer.py`
8. `pgtail_py/fullscreen/state.py`
9. `pgtail_py/cli_fullscreen.py`

### Test Files (5 files)
1. `tests/unit/fullscreen/__init__.py`
2. `tests/unit/fullscreen/test_buffer.py`
3. `tests/unit/fullscreen/test_cli_fullscreen.py`
4. `tests/unit/fullscreen/test_keybindings.py`
5. `tests/unit/fullscreen/test_state.py`
6. `tests/integration/test_fullscreen.py`

### Directories to Remove
1. `pgtail_py/fullscreen/` (after deleting files)
2. `tests/unit/fullscreen/` (after deleting files)

## Files to Modify

### pgtail_py/cli.py

**Changes Required:**
1. Remove import: `from pgtail_py.cli_fullscreen import fullscreen_command`
2. Remove import: `from pgtail_py.fullscreen import FullscreenState, LogBuffer`
3. Remove `fullscreen_buffer` and `fullscreen_state` fields from `AppState` class
4. Remove `get_or_create_buffer()` method
5. Remove `get_or_create_fullscreen_state()` method
6. Remove fullscreen command handling in `handle_command()` (lines 310-311)
7. Update pause message to not mention fullscreen (line 475-477)

### pgtail_py/commands.py

**Changes Required:**
1. Remove `"fullscreen"` entry from `COMMANDS` dict
2. Remove `"fs"` entry from `COMMANDS` dict

### CLAUDE.md

**Changes Required:**
1. Remove entire "## Fullscreen TUI Mode" section
2. Remove fullscreen references from "## Recent Changes" section
3. Remove fullscreen references from any other sections

## Components NOT Being Removed

The following components are **retained** because they serve the main REPL (not fullscreen-specific):

- `pgtail_py/theme.py` - ThemeManager used in AppState for REPL styling
- `pgtail_py/themes/` - Built-in themes used by REPL
- `pgtail_py/cli_theme.py` - Theme command handler
- `pgtail_py/sql_tokenizer.py` - SQL tokenization for display formatting
- `pgtail_py/sql_highlighter.py` - SQL highlighting in display.py
- `pgtail_py/sql_detector.py` - SQL detection in log messages
- `pgtail_py/display.py` - Display formatting with SQL highlighting

## Verification Steps

After implementation, verify:

1. **No import errors**: `python -c "from pgtail_py import cli"`
2. **Tests pass**: `make test` (remaining tests should pass)
3. **No fullscreen references**: `grep -r "fullscreen" pgtail_py/ --include="*.py"` returns nothing
4. **Unknown command**: Running `fullscreen` or `fs` in pgtail shows "Unknown command"
5. **Core functionality works**: Can list instances, tail logs, apply filters
