# Implementation Plan: Full Screen TUI Mode

**Branch**: `012-fullscreen-tui` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-fullscreen-tui/spec.md`

## Summary

Add a full-screen terminal UI mode to pgtail that captures log output in a scrollable buffer with vim-style navigation, search, and mouse support. Users can toggle between "follow mode" (auto-scroll) and "browse mode" (manual navigation) to review historical log entries without stopping the tail.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (full-screen Application, KeyBindings, Layout, Buffer)
**Storage**: In-memory circular buffer (10,000 lines max, no persistence)
**Testing**: pytest with unit tests for buffer, search, and keybinding logic
**Target Platform**: macOS, Linux, Windows (cross-platform via prompt_toolkit)
**Project Type**: Single CLI application (pgtail_py package)
**Performance Goals**: 1,000 lines/sec throughput, <100ms search on 10,000 lines, <200ms mode transitions
**Constraints**: Memory bounded by 10,000 line limit (~5MB worst case), no external dependencies beyond existing stack
**Scale/Scope**: Single user, single log file at a time, session-scoped buffer

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Single command (`fullscreen`/`fs`) with standard vim keybindings; no configuration required |
| II. Cross-Platform Parity | ✅ PASS | prompt_toolkit handles terminal abstraction; mouse support degrades gracefully |
| III. Graceful Degradation | ✅ PASS | Falls back to REPL mode on unsupported terminals; mouse optional |
| IV. User-Friendly Feedback | ✅ PASS | Status bar shows mode, line count, search status; color-coded output preserved |
| V. Focused Scope | ✅ PASS | Tailing only, local only, session buffer only; explicitly out of scope: split panes, syntax highlighting, persistence |
| VI. Minimal Dependencies | ✅ PASS | Uses only existing prompt_toolkit dependency (already required for REPL); no new dependencies |
| VII. Developer Workflow Priority | ✅ PASS | Enables faster log review during pgrx development; scroll back without restarting tail |

**Gate Result**: PASS - All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/012-fullscreen-tui/
├── plan.md              # This file
├── research.md          # Phase 0 output - prompt_toolkit patterns
├── data-model.md        # Phase 1 output - LogBuffer, ViewState, etc.
├── quickstart.md        # Phase 1 output - developer guide
├── contracts/           # Phase 1 output - internal API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── cli.py               # Existing - add fullscreen command routing
├── cli_fullscreen.py    # NEW - fullscreen command handler
├── fullscreen/          # NEW - fullscreen module
│   ├── __init__.py
│   ├── app.py           # Full-screen Application setup
│   ├── buffer.py        # LogBuffer (circular buffer implementation)
│   ├── keybindings.py   # Vim-style key bindings
│   ├── layout.py        # HSplit layout (log view + status bar)
│   ├── search.py        # Search state and match navigation
│   └── controls.py      # Custom UIControl for log display
├── commands.py          # Existing - add fullscreen command definition
└── tailer.py            # Existing - may need callback hooks for buffer feeding

tests/
├── unit/
│   └── fullscreen/
│       ├── test_buffer.py      # Circular buffer tests
│       ├── test_search.py      # Search and match tests
│       └── test_keybindings.py # Key binding tests
└── integration/
    └── test_fullscreen.py      # End-to-end fullscreen mode tests
```

**Structure Decision**: Single project structure following existing pgtail_py layout. New fullscreen functionality isolated in `pgtail_py/fullscreen/` subpackage to maintain separation of concerns while reusing existing tailer and display infrastructure.

## Complexity Tracking

> No violations - all complexity is justified by existing approved dependencies and constitution principles.

| Addition | Justification |
|----------|---------------|
| New subpackage `fullscreen/` | Encapsulates fullscreen-specific logic; reuses existing prompt_toolkit dependency |
| LogBuffer class | Required for scrollback; simple circular buffer, no external dependencies |
| Key bindings module | Required for vim navigation; uses prompt_toolkit KeyBindings (already available) |
