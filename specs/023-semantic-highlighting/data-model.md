# Data Model: Semantic Log Highlighting

**Branch**: `023-semantic-highlighting` | **Date**: 2026-01-14

## Overview

This document defines the core entities for the semantic log highlighting system. All entities are in-memory; the only persistence is via TOML configuration.

---

## Core Entities

### 1. Highlighter (Protocol)

**Purpose**: Defines the contract for all pattern-based highlighters.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Unique identifier (e.g., "timestamp", "sqlstate") |
| priority | int | Processing order (lower = first); ranges by category |
| enabled | bool | Whether this highlighter is active |
| description | str | Human-readable description for `highlight list` |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| find_matches | (text: str, theme: Theme) → list[Match] | Find all pattern matches |
| apply | (text: str, theme: Theme) → FormattedText | Render for prompt_toolkit |
| apply_rich | (text: str, theme: Theme) → str | Render for Textual/Rich |

**Validation Rules**:
- name must be unique across all highlighters
- name must be lowercase alphanumeric + underscore
- priority must be positive integer
- priority ranges reserved by category (see research.md)

---

### 2. Match

**Purpose**: Represents a single pattern match within text.

| Field | Type | Description |
|-------|------|-------------|
| start | int | Start position (0-indexed, inclusive) |
| end | int | End position (0-indexed, exclusive) |
| style | str | Theme style key to apply |
| text | str | Matched text (for debugging) |

**Invariants**:
- 0 ≤ start < end ≤ len(source_text)
- style must be valid theme key or will fallback

---

### 3. HighlighterChain

**Purpose**: Composes multiple highlighters with overlap prevention.

| Field | Type | Description |
|-------|------|-------------|
| highlighters | list[Highlighter] | Registered highlighters (sorted by priority) |
| max_length | int | Depth limit for highlighting (default 10240) |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| register | (highlighter: Highlighter) → None | Add highlighter to chain |
| unregister | (name: str) → None | Remove highlighter by name |
| apply | (text: str, theme: Theme) → FormattedText | Combined output for prompt_toolkit |
| apply_rich | (text: str, theme: Theme) → str | Combined output for Textual/Rich |

**Behavior**:
1. Collect all matches from all enabled highlighters
2. Sort by (start position, priority)
3. Process in order, skipping occupied regions
4. Build styled output

---

### 4. OccupancyTracker

**Purpose**: Tracks which text regions have been highlighted.

| Field | Type | Description |
|-------|------|-------------|
| length | int | Total text length being tracked |
| _occupied | list[bool] | Per-character occupancy flags |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| is_available | (start: int, end: int) → bool | Check if region is unhighlighted |
| mark_occupied | (start: int, end: int) → None | Mark region as highlighted |
| available_ranges | () → list[tuple[int, int]] | Get unhighlighted regions |

---

### 5. HighlightingConfig

**Purpose**: Runtime configuration state for highlighting.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| enabled | bool | True | Global highlighting toggle |
| max_length | int | 10240 | Depth limit in bytes |
| enabled_highlighters | dict[str, bool] | {all: True} | Per-highlighter toggles |
| duration_slow | int | 100 | Slow query threshold (ms) |
| duration_very_slow | int | 500 | Very slow threshold (ms) |
| duration_critical | int | 5000 | Critical threshold (ms) |
| custom_highlighters | list[CustomHighlighter] | [] | User-defined patterns |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| is_highlighter_enabled | (name: str) → bool | Check if specific highlighter active |
| enable_highlighter | (name: str) → None | Enable specific highlighter |
| disable_highlighter | (name: str) → None | Disable specific highlighter |
| get_duration_severity | (ms: float) → str | Get severity for duration value |
| add_custom | (config: CustomHighlighter) → None | Add custom highlighter |
| remove_custom | (name: str) → None | Remove custom highlighter |
| to_dict | () → dict | Serialize for TOML export |
| from_dict | (data: dict) → HighlightingConfig | Deserialize from TOML |

**State Transitions**:
```
                   highlight off
    ENABLED ─────────────────────→ DISABLED
       │                              │
       │ highlight on                 │
       ←──────────────────────────────┘
```

---

### 6. CustomHighlighter

**Purpose**: User-defined regex-based highlighter.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| name | str | Yes | - | Unique identifier |
| pattern | str | Yes | - | Regex pattern |
| style | str | No | "yellow" | Style to apply |
| priority | int | No | 1050 | Processing priority |
| enabled | bool | No | True | Whether active |

**Validation Rules**:
- name must be unique (not conflict with built-in names)
- pattern must be valid regex
- pattern must not match zero-length strings
- style must be valid color or theme key
- priority should be 1000+ to run after built-ins

---

### 7. HighlighterRegistry

**Purpose**: Singleton registry of all available highlighters.

| Field | Type | Description |
|-------|------|-------------|
| _highlighters | dict[str, Highlighter] | name → highlighter mapping |
| _categories | dict[str, list[str]] | category → highlighter names |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| register | (highlighter: Highlighter, category: str) → None | Register highlighter |
| get | (name: str) → Highlighter | None | Retrieve by name |
| get_by_category | (category: str) → list[Highlighter] | All in category |
| all_names | () → list[str] | All registered names |
| all_categories | () → list[str] | All category names |
| create_chain | (config: HighlightingConfig) → HighlighterChain | Build chain from config |

**Built-in Registration** (at module load):

| Category | Highlighters |
|----------|--------------|
| structural | timestamp, pid, context |
| diagnostic | sqlstate, error_name |
| performance | duration, memory, statistics |
| objects | identifier, relation, schema |
| wal | lsn, wal_segment, txid |
| connection | connection, ip, backend |
| sql | sql_keyword, sql_string, sql_number, sql_param, sql_operator |
| lock | lock_type, lock_wait |
| checkpoint | checkpoint, recovery |
| misc | boolean, null, oid, path |

---

## Theme Extensions

### New Style Keys (added to Theme.ui)

All keys prefixed with `hl_` for semantic highlighting:

| Key Pattern | Example Keys |
|-------------|--------------|
| hl_timestamp_* | hl_timestamp_date, hl_timestamp_time, hl_timestamp_ms, hl_timestamp_tz |
| hl_sqlstate_* | hl_sqlstate_success, hl_sqlstate_warning, hl_sqlstate_error, hl_sqlstate_internal |
| hl_duration_* | hl_duration_fast, hl_duration_slow, hl_duration_very_slow, hl_duration_critical |
| hl_* | hl_pid, hl_context, hl_identifier, hl_relation, hl_schema, etc. |

**Fallback Behavior**:
- If key missing, falls back to default text color
- Theme validation warns but does not fail on missing hl_* keys

---

## Configuration Schema

### TOML Structure

```toml
[highlighting]
enabled = true
max_length = 10240

[highlighting.duration]
slow = 100
very_slow = 500
critical = 5000

[highlighting.enabled_highlighters]
timestamp = true
pid = true
sqlstate = true
duration = true
memory = true
identifier = true
relation = true
schema = true
lsn = true
wal_segment = true
txid = true
connection = true
ip = true
backend = true
sql_keyword = true
sql_string = true
sql_number = true
sql_param = true
lock_type = true
lock_wait = true
checkpoint = true
recovery = true
boolean = true
null = true
oid = true
path = true
context = true
error_name = true
statistics = true

[[highlighting.custom]]
name = "example"
pattern = "EXAMPLE-\\d+"
style = "bold yellow"
priority = 1050
```

---

## Entity Relationships

```
┌────────────────────────────────────────────────────────────────────┐
│                         HighlighterRegistry                         │
│  (singleton - holds all registered highlighters)                    │
└───────────────────────────────┬────────────────────────────────────┘
                                │ creates
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         HighlighterChain                            │
│  (composes enabled highlighters with overlap prevention)            │
└───────────────────────────────┬────────────────────────────────────┘
                                │ contains
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                          Highlighter[]                              │
│  (29 built-in + N custom, sorted by priority)                       │
├────────────────────────────────────────────────────────────────────┤
│  TimestampHighlighter  │  SQLStateHighlighter  │  DurationHL  │ ...│
└───────────────────────────────┬────────────────────────────────────┘
                                │ produces
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                            Match[]                                  │
│  (start, end, style, text)                                          │
└───────────────────────────────┬────────────────────────────────────┘
                                │ consumed by
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        OccupancyTracker                             │
│  (prevents overlapping highlights)                                  │
└────────────────────────────────────────────────────────────────────┘

Configuration Flow:
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ config.toml  │────▶│ HighlightingConfig│────▶│ HighlighterChain │
│ [highlighting]│    │ (runtime state)   │     │ (filtered list)  │
└──────────────┘     └───────────────────┘     └──────────────────┘
```

---

## Validation Summary

| Entity | Validation |
|--------|------------|
| Highlighter.name | Unique, lowercase alphanumeric + underscore |
| Highlighter.priority | Positive integer, category ranges enforced |
| Match | 0 ≤ start < end ≤ len(text) |
| CustomHighlighter.pattern | Valid regex, non-zero-length match |
| CustomHighlighter.style | Valid color name or theme key |
| HighlightingConfig.max_length | Positive integer, reasonable limit (1KB-1MB) |
| Theme hl_* keys | Optional (graceful fallback) |
