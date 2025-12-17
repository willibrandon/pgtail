# Implementation Plan: Connection Tracking Dashboard

**Branch**: `010-connection-tracking` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-connection-tracking/spec.md`

## Summary

Implement a connection tracking dashboard for pgtail that parses PostgreSQL connection/disconnection log events and provides visibility into active connections. The feature tracks connections by user, database, application, and source IP, with support for history trends, live watch mode, and filtering. Implementation follows the existing error_stats pattern with session-scoped, in-memory storage (max 10,000 events).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, tomlkit >=0.12.0
**Storage**: In-memory only (session-scoped, deque with maxlen=10,000)
**Testing**: pytest >=7.0.0 with pytest-cov
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single Python package (pgtail_py)
**Performance Goals**: Summary displays <1s with 10,000 events; watch latency <500ms
**Constraints**: Session-scoped only, no persistence, no external DB queries
**Scale/Scope**: Track up to 10,000 connection events per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Single command `connections` with intuitive flags; no config required |
| II. Cross-Platform Parity | PASS | Uses only stdlib + approved deps (prompt_toolkit, psutil) |
| III. Graceful Degradation | PASS | Handles missing/malformed log events gracefully |
| IV. User-Friendly Feedback | PASS | Clear output with aggregations; color-coded watch mode |
| V. Focused Scope | PASS | Log-based tracking only; no pg_stat_activity, no connection management |
| VI. Minimal Dependencies | PASS | No new dependencies required; reuses existing infrastructure |
| VII. Developer Workflow Priority | PASS | Quick access to connection info during development |

**Gate Status**: PASS - All principles satisfied. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/010-connection-tracking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── connection_event.py     # ConnectionEvent dataclass, event type enum
├── connection_stats.py     # ConnectionStats aggregator (follows error_stats pattern)
├── connection_parser.py    # Regex patterns for connection log messages
├── cli_connections.py      # connections command handlers
├── cli.py                  # Updated: register connections command, add callback
├── commands.py             # Updated: add connections to command list/completer
└── tailer.py               # Updated: add connection tracking callback

tests/
├── test_connection_event.py
├── test_connection_stats.py
├── test_connection_parser.py
└── test_cli_connections.py
```

**Structure Decision**: Single project structure following existing pgtail_py patterns. New modules mirror the error_stats implementation (error_stats.py → connection_stats.py, cli_errors.py → cli_connections.py).

## Complexity Tracking

> No violations to justify - all constitution gates passed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |
