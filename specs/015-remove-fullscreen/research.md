# Research: Remove Fullscreen TUI

**Date**: 2025-12-30
**Feature**: 015-remove-fullscreen

## Summary

This is a removal feature - no new technologies or patterns to research. All decisions are straightforward deletions.

## Decisions

### Decision 1: What to Remove

**Decision**: Remove all files in `pgtail_py/fullscreen/` directory and `pgtail_py/cli_fullscreen.py`

**Rationale**: These modules are exclusively used by the fullscreen TUI feature. No other part of the codebase depends on them.

**Evidence**:
- `fullscreen/__init__.py` exports: `LogBuffer`, `FullscreenState`, `DisplayMode`
- Only importer: `cli.py` (lines 33, 57)
- `cli_fullscreen.py` is only imported by `cli.py` (line 33)

### Decision 2: What to Keep

**Decision**: Keep theme and SQL highlighting modules

**Rationale**: These are used by the main REPL display, not fullscreen-specific.

**Evidence**:
- `display.py` imports `sql_detector` and `sql_highlighter` for all log formatting
- `cli.py` uses `ThemeManager` in `AppState` for REPL styling
- Theme commands work independently of fullscreen mode

### Decision 3: Fullscreen Pygments Lexer vs SQL Highlighting

**Decision**: Remove `fullscreen/lexer.py` (LogLineLexer), keep `sql_tokenizer.py`/`sql_highlighter.py`

**Rationale**: Two separate implementations exist:
- `fullscreen/lexer.py`: Pygments RegexLexer for prompt_toolkit TextArea (fullscreen-only)
- `sql_tokenizer.py`: Custom tokenizer for FormattedText output (used by display.py for REPL)

**Evidence**:
- `fullscreen/lexer.py` uses `pygments.lexer.RegexLexer` for TextArea widget
- `sql_tokenizer.py` uses custom `SQLTokenizer` class for inline highlighting
- `display.py:116-137` uses the custom tokenizer, not the Pygments lexer

## Alternatives Considered

### Alternative: Deprecation Warning

**Rejected Because**: User explicitly stated "Do not maintain any backwards compatibility"

### Alternative: Keep LogBuffer for Future Use

**Rejected Because**: No other feature needs a circular buffer for log entries. If needed later, it can be reimplemented.

## Unknowns Resolved

All unknowns from specification have been resolved:
- LogBuffer is fullscreen-only → Remove
- Themes are NOT fullscreen-only → Keep
- SQL highlighting is NOT fullscreen-only → Keep
- LogLineLexer is fullscreen-only → Remove
