# Implementation Plan: REPL Bottom Toolbar

**Branch**: `022-repl-toolbar` | **Date**: 2026-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-repl-toolbar/spec.md`

## Summary

Add a persistent bottom toolbar to the pgtail REPL that displays instance count, pre-configured filters (levels, regex, time, slow query), current theme name, and shell mode indicator. Uses prompt_toolkit's native `bottom_toolbar` parameter with a callable that returns FormattedText for dynamic updates.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (already in use for REPL)
**Storage**: N/A (extends existing config schema with `display.show_toolbar`)
**Testing**: pytest with prompt_toolkit test utilities
**Target Platform**: macOS, Linux, Windows (cross-platform parity)
**Project Type**: Single CLI application
**Performance Goals**: Toolbar updates within 100ms of state changes
**Constraints**: Terminal width >=80 columns for readable display
**Scale/Scope**: Single-user CLI tool, no concurrency concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Uses prompt_toolkit's built-in `bottom_toolbar` - no custom rendering |
| II. Cross-Platform Parity | ✅ PASS | prompt_toolkit handles terminal differences; no platform-specific code |
| III. Graceful Degradation | ✅ PASS | Toolbar can be disabled; NO_COLOR support; graceful truncation |
| IV. User-Friendly Feedback | ✅ PASS | Toolbar provides immediate state visibility per principle requirements |
| V. Focused Scope | ✅ PASS | Enhances existing REPL without expanding beyond core purpose |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies; uses existing prompt_toolkit |
| VII. Developer Workflow Priority | ✅ PASS | Reduces cognitive load by showing configuration at a glance |

**Technical Constraints Check**:
- ✅ Python 3.10+ compatible
- ✅ Works in standard terminals
- ✅ Minimum 80 column width supported (with graceful truncation)

**Quality Standards Check**:
- ✅ New module will have docstrings and type hints
- ✅ Unit tests planned for toolbar formatting logic
- ✅ File size well under 900 LOC limit (estimated ~150 LOC)

## Project Structure

### Documentation (this feature)

```text
specs/022-repl-toolbar/
├── plan.md              # This file
├── research.md          # Phase 0 output - prompt_toolkit patterns
├── data-model.md        # Phase 1 output - toolbar state and config
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - N/A (no APIs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── cli.py               # MODIFY: Add bottom_toolbar to PromptSession
├── repl_toolbar.py      # NEW: Toolbar rendering logic
└── themes/*.py          # MODIFY: Add toolbar styles to built-in themes

tests/
└── unit/
    └── test_repl_toolbar.py  # NEW: Unit tests for toolbar formatting
```

**Structure Decision**: Single project structure. New module `repl_toolbar.py` keeps toolbar logic isolated. Modifications to existing modules are minimal (theme styles, PromptSession integration).

## Post-Design Constitution Re-check

All principles remain satisfied after Phase 1 design:

| Principle | Post-Design Status | Verification |
|-----------|-------------------|--------------|
| I. Simplicity First | ✅ CONFIRMED | Single new module (~150 LOC), minimal changes to existing code |
| II. Cross-Platform Parity | ✅ CONFIRMED | No platform-specific code in design |
| III. Graceful Degradation | ✅ CONFIRMED | NO_COLOR support, optional toolbar, graceful truncation |
| IV. User-Friendly Feedback | ✅ CONFIRMED | Toolbar displays actionable state information |
| V. Focused Scope | ✅ CONFIRMED | Read-only display, no new features beyond visibility |
| VI. Minimal Dependencies | ✅ CONFIRMED | Zero new dependencies |
| VII. Developer Workflow Priority | ✅ CONFIRMED | Instant visibility into configuration state |

## Complexity Tracking

> No constitution violations requiring justification.
