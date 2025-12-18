# Implementation Plan: Desktop Notifications for Alerts

**Branch**: `011-desktop-notifications` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-desktop-notifications/spec.md`

## Summary

Add desktop notification support to pgtail for alerting users when critical log events occur. The system supports level-based, pattern-based, rate-based, and slow-query notifications with rate limiting (1 per 5 seconds) and quiet hours. Leverages native OS notification mechanisms (osascript on macOS, notify-send on Linux, best-effort on Windows).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, tomlkit >=0.12.0
**Storage**: TOML config file (existing config.py infrastructure)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: macOS, Linux, Windows (best-effort)
**Project Type**: Single CLI application
**Performance Goals**: Notifications within 1 second of matching log entry
**Constraints**: Rate limit max 1 notification per 5 seconds; graceful degradation when notification system unavailable
**Scale/Scope**: Session-scoped, in-memory notification rules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | `notify on FATAL PANIC` is memorable; `notify test` verifies setup |
| II. Cross-Platform Parity | ✅ PASS | Platform-specific code isolated in `notifier_*.py` modules |
| III. Graceful Degradation | ✅ PASS | Spec requires graceful fallback when notification system unavailable |
| IV. User-Friendly Feedback | ✅ PASS | Test command provides clear feedback; status command shows config |
| V. Focused Scope | ⚠️ JUSTIFIED | Adds pattern matching (`/regex/`) but constrained to notifications only |
| VI. Minimal Dependencies | ✅ PASS | Uses stdlib subprocess for OS commands; no new dependencies |
| VII. Developer Workflow Priority | ✅ PASS | Enhances pgrx workflow by alerting on errors without watching logs |

**V. Focused Scope Justification**: The constitution states "Basic Filtering Only" and "no regex matching." However, this feature uses regex only for notification triggers, not log filtering. The existing `regex_filter.py` already implements regex filtering, so pattern-based notifications follow established patterns.

## Project Structure

### Documentation (this feature)

```text
specs/011-desktop-notifications/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI command specs)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
pgtail_py/
├── notify.py            # NotificationRule, NotificationConfig, NotificationManager
├── notifier.py          # Platform dispatcher (like detector.py)
├── notifier_unix.py     # macOS (osascript) and Linux (notify-send)
├── notifier_windows.py  # Windows notification (best-effort)
├── cli_notify.py        # notify command handlers
└── [existing modules]

tests/
├── unit/
│   ├── test_notify.py       # NotificationRule matching, rate limiting
│   ├── test_notifier.py     # Platform detection, command building
│   └── test_cli_notify.py   # Command parsing
└── integration/
    └── test_notify_integration.py  # End-to-end notification tests
```

**Structure Decision**: Single project structure following existing patterns. New modules follow the `cli_*.py` and `*_unix.py`/`*_windows.py` platform-split conventions.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Pattern matching in notifications | User requested feature; limited to notification triggers only | Level-only notifications miss important patterns like "deadlock detected" |

---

## Phase 0: Research

See [research.md](./research.md) for detailed findings.

### Research Topics

1. **macOS Notification Mechanisms**: osascript vs terminal-notifier vs native APIs
2. **Linux Notification Standards**: notify-send/libnotify availability and alternatives
3. **Windows Notification Options**: win10toast, plyer, or native PowerShell
4. **Rate Limiting Patterns**: Time-window vs sliding window for spam prevention
5. **Existing pgtail Integration Points**: Where to hook notification triggers

---

## Phase 1: Design

See individual design documents:
- [data-model.md](./data-model.md) - Entity definitions and relationships
- [quickstart.md](./quickstart.md) - Getting started guide
- [contracts/](./contracts/) - CLI command specifications
