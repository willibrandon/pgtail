# Implementation Plan: Color Themes

**Branch**: `013-color-themes` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-color-themes/spec.md`

## Summary

Implement a color theming system for pgtail that provides 6 built-in themes (dark, light, high-contrast, monokai, solarized-dark, solarized-light) plus support for custom TOML-based theme files. Themes define colors for all log levels and UI elements, with immediate switching, persistence across sessions, and graceful fallback behavior.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (styling/FormattedText), tomlkit >=0.12.0 (config files)
**Storage**: TOML files at platform-specific config paths (existing config.py infrastructure)
**Testing**: pytest with unit tests for theme loading, validation, and style generation
**Target Platform**: macOS, Linux, Windows (cross-platform via existing platform abstraction)
**Project Type**: Single CLI project
**Performance Goals**: Theme switching under 100ms, no impact on log tailing performance
**Constraints**: NO_COLOR env var must disable all themes; invalid themes must fallback gracefully
**Scale/Scope**: 6 built-in themes, unlimited custom themes in user config directory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Single `theme` command with intuitive subcommands; zero config for defaults |
| II. Cross-Platform Parity | ✅ PASS | Uses existing platform-agnostic config paths; ANSI colors work everywhere |
| III. Graceful Degradation | ✅ PASS | Invalid themes fallback to default; missing files handled |
| IV. User-Friendly Feedback | ✅ PASS | Color-coded output; clear error messages for invalid themes |
| V. Focused Scope | ✅ PASS | Theme switching is display/UX feature, not expanding core functionality |
| VI. Minimal Dependencies | ✅ PASS | Uses existing prompt_toolkit and tomlkit; no new dependencies |
| VII. Developer Workflow | ✅ PASS | Themes apply instantly; no restart required |

## Project Structure

### Documentation (this feature)

```text
specs/013-color-themes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── theme.py             # NEW: Theme, ColorStyle dataclasses; ThemeManager
├── themes/              # NEW: Built-in theme definitions (Python modules)
│   ├── __init__.py
│   ├── dark.py
│   ├── light.py
│   ├── high_contrast.py
│   ├── monokai.py
│   ├── solarized_dark.py
│   └── solarized_light.py
├── cli_theme.py         # NEW: theme command handlers
├── colors.py            # MODIFY: Use ThemeManager instead of hardcoded styles
├── config.py            # MODIFY: Update validate_theme for new theme names
├── commands.py          # MODIFY: Register theme commands
└── cli.py               # MODIFY: Initialize ThemeManager in AppState

tests/
├── unit/
│   ├── test_theme.py         # NEW: Theme loading, validation, style generation
│   └── test_cli_theme.py     # NEW: Command handler tests
└── integration/
    └── test_theme_switch.py  # NEW: End-to-end theme switching tests
```

**Structure Decision**: Single project structure maintained. New theme module follows existing pattern (cli_notify.py, cli_connections.py for command handlers). Built-in themes as Python modules for type safety and IDE support; custom themes as TOML files in user config directory.

## Complexity Tracking

> No constitution violations requiring justification.
