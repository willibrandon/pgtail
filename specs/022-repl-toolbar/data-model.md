# Data Model: REPL Bottom Toolbar

**Feature**: 022-repl-toolbar
**Date**: 2026-01-12

## Overview

The REPL bottom toolbar is a read-only display component with no persistent storage. It derives its content entirely from existing `AppState` and renders using prompt_toolkit's `bottom_toolbar` parameter. The toolbar is always displayed.

## Entities

### 1. Theme UI Styles (MODIFY existing)

**Location**: `pgtail_py/themes/*.py` (built-in themes)

Add toolbar style keys to each theme's `ui` dictionary.

**New UI Style Keys**:

| Key | Purpose | Example Value |
|-----|---------|---------------|
| `toolbar` | Default toolbar text | `ColorStyle(bg="#1a1a1a", fg="#cccccc")` |
| `toolbar.dim` | Separators and hints | `ColorStyle(bg="#1a1a1a", fg="#666666")` |
| `toolbar.filter` | Filter values (accent) | `ColorStyle(bg="#1a1a1a", fg="#55ffff")` |
| `toolbar.warning` | "No instances" warning | `ColorStyle(bg="#1a1a1a", fg="#ffff55")` |
| `toolbar.shell` | Shell mode indicator | `ColorStyle(bg="#1a1a1a", fg="#ffffff", bold=True)` |

**Theme Validation**: These keys are optional; missing keys gracefully fall back to `toolbar` style.

### 2. Toolbar Content (runtime only)

The toolbar content is computed on-demand from `AppState`. No separate storage.

**Data Sources (read-only)**:

| Content | Source | Accessor |
|---------|--------|----------|
| Instance count | `state.instances` | `len(state.instances)` |
| Level filter | `state.active_levels` | Compare to `LogLevel.all_levels()` |
| Regex filter | `state.regex_state` | `state.regex_state.filters[0].pattern` |
| Time filter | `state.time_filter` | `state.time_filter.format_description()` |
| Slow query | `state.slow_query_config` | `state.slow_query_config.warning_ms` |
| Current theme | `state.theme_manager` | `state.theme_manager.current_theme.name` |
| Shell mode | `state.shell_mode` | Boolean flag |

## State Diagram

```
                    ┌─────────────────────┐
                    │     Idle Mode       │
                    │                     │
                    │ Display:            │
                    │ - Instance count    │
                    │ - Active filters    │
                    │ - Theme name        │
                    └─────────────────────┘
                             │
                    Press '!' with empty buffer
                             │
                             ▼
                    ┌─────────────────────┐
                    │    Shell Mode       │
                    │                     │
                    │ Display:            │
                    │ - "SHELL"           │
                    │ - "Press Escape..." │
                    └─────────────────────┘
                             │
                    Press Escape / Run command
                             │
                             ▼
                    (Return to Idle Mode)
```

## Relationships

```
AppState ─────────────────────┐
    │                         │
    ├── instances[]           │
    ├── active_levels         │
    ├── regex_state           │
    ├── time_filter           │
    ├── slow_query_config     │
    ├── theme_manager         │
    └── shell_mode            │
                              │
                              ▼
                    ┌─────────────────────┐
                    │   get_toolbar()     │
                    │                     │
                    │ Reads state,        │
                    │ returns             │
                    │ list[tuple[str,str]]│
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   PromptSession     │
                    │   bottom_toolbar=   │
                    └─────────────────────┘
```

## No Storage

This feature does not introduce any persistent storage. The toolbar is:
- Always displayed (no configuration option)
- Purely ephemeral - computed on each render from in-memory state
- Read-only - displays existing AppState, does not modify it
