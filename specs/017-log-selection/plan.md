# Implementation Plan: Log Entry Selection and Copy

**Branch**: `017-log-selection` | **Date**: 2025-12-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-log-selection/spec.md`

## Summary

Replace the current prompt_toolkit-based tail mode UI with Textual to enable built-in text selection and clipboard support. The Textual Log widget provides native mouse selection via `ALLOW_SELECT = True`, OSC 52 clipboard integration, and Rich text styling. This addresses the core pain point: users cannot currently select and copy log text in tail mode without exiting to `--stream` output.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textual>=0.89.0, pyperclip>=1.8.0 (new), prompt_toolkit>=3.0.0 (existing, for REPL), psutil>=5.9.0 (existing)
**Storage**: N/A (in-memory 10,000 line ring buffer)
**Testing**: pytest>=7.0.0 with pytest-asyncio for Textual app testing
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single Python package (pgtail_py/)
**Performance Goals**: 100+ entries/sec auto-scroll, <50ms key response, <500ms startup
**Constraints**: <10% memory increase over current, must preserve all existing tail commands
**Scale/Scope**: 10,000 line buffer limit, single local PostgreSQL instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Textual reduces complexity (built-in selection vs custom implementation) |
| II. Cross-Platform Parity | ✅ PASS | Textual supports macOS, Linux, Windows; pyperclip provides clipboard fallback |
| III. Graceful Degradation | ✅ PASS | OSC 52 → pyperclip → silent fail; clipboard degrades gracefully |
| IV. User-Friendly Feedback | ✅ PASS | Visual selection highlighting, status bar, color-coded output preserved |
| V. Focused Scope | ✅ PASS | Feature adds selection to existing tail mode; no scope creep |
| VI. Minimal Dependencies | ✅ PASS | Textual is approved in constitution (§VI); pyperclip justified for clipboard fallback |
| VII. Developer Workflow Priority | ✅ PASS | Selection enables faster error sharing; maintains 10-second goal |

**Gate Result**: All principles satisfied. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/017-log-selection/
├── plan.md              # This file
├── research.md          # Phase 0 output - Textual patterns research
├── data-model.md        # Phase 1 output - Component relationships
├── quickstart.md        # Phase 1 output - Development setup guide
├── contracts/           # Phase 1 output - Event/callback interfaces
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── tail_textual.py      # NEW: TailApp Textual Application
├── tail_log.py          # NEW: TailLog widget (Log subclass with vim bindings)
├── tail_input.py        # NEW: TailInput widget (command input)
├── tail_rich.py         # NEW: Rich text formatting for log entries
├── tail_app.py          # MODIFY: Deprecate, redirect to tail_textual
├── tail_layout.py       # MODIFY: Deprecate, redirect to Textual layout
├── tail_buffer.py       # MODIFY: Add format_as_rich_text() method
├── tail_status.py       # MODIFY: Adapt for Textual Static widget
├── cli.py               # MODIFY: Import new TailApp from tail_textual
├── cli_tail.py          # MODIFY: Adapt command handlers for Textual
└── display.py           # MODIFY: Add Rich Text output format

tests/
├── test_tail_textual.py # NEW: Textual app tests
├── test_tail_log.py     # NEW: TailLog widget tests
├── test_tail_rich.py    # NEW: Rich formatting tests
└── test_tail_visual.py  # NEW: Visual mode selection tests
```

**Structure Decision**: Single project structure maintained. New Textual modules added alongside existing prompt_toolkit modules for gradual migration. Old tail_app.py and tail_layout.py marked deprecated but retained for rollback capability.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| pyperclip dependency | Clipboard fallback for Terminal.app | OSC 52 alone would leave macOS Terminal.app users without clipboard support |
| Visual mode state | FR-009/FR-010 require keyboard selection | Mouse-only selection excludes keyboard-focused users; vim bindings expected for CLI tools |
| Rich text formatting | Textual uses Rich, not prompt_toolkit FormattedText | Converting existing FormattedText to plain strings would lose SQL highlighting |
