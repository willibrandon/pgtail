# Implementation Plan: Configuration File Support

**Branch**: `005-config-file` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-config-file/spec.md`

## Summary

Add persistent configuration file support to pgtail using TOML format. Users can save preferences (default log levels, slow query thresholds, display settings) that persist across sessions. Provides `config`, `set`, and `unset` commands for viewing and modifying settings. Configuration stored at platform-specific locations following OS conventions.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit>=3.0.0, psutil>=5.9.0, tomli (Python 3.10), tomllib (Python 3.11+), tomlkit (for preserving comments)
**Storage**: TOML file at platform-specific config directories
**Testing**: pytest>=7.0.0
**Target Platform**: macOS, Linux, Windows (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: Config loading <100ms on startup
**Constraints**: Must gracefully degrade with invalid config (warn and continue)
**Scale/Scope**: Single user, single config file per installation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Commands are minimal (`config`, `set`, `unset`), zero config required (defaults work) |
| II. Cross-Platform Parity | PASS | Platform-specific paths isolated in config.py, uses pathlib throughout |
| III. Graceful Degradation | PASS | Invalid config warns and continues with defaults (FR-016) |
| IV. User-Friendly Feedback | PASS | Helpful error messages required (FR-015), TOML format is readable |
| V. Focused Scope | PASS | Config is for existing features only, no new functionality |
| VI. Minimal Dependencies | REVIEW | New dependency: tomlkit for comment preservation |
| VII. Developer Workflow Priority | PASS | Settings persist without manual config file creation |

**Dependency Justification (VI)**:
- `tomli`/`tomllib`: TOML parsing - tomllib is stdlib in 3.11+, tomli is backport for 3.10
- `tomlkit`: Preserves comments and formatting when updating config - required by FR-014

## Project Structure

### Documentation (this feature)

```text
specs/005-config-file/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI command specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py
├── __main__.py
├── cli.py               # MODIFY: Add config/set/unset commands, load config on startup
├── colors.py            # MODIFY: Add theme support from config
├── commands.py          # MODIFY: Add config, set, unset command definitions
├── config.py            # EXPAND: Add config file path, schema, load/save functions
├── filter.py            # MODIFY: Apply default.levels from config
├── slow_query.py        # MODIFY: Apply slow.* thresholds from config
└── ... (other files unchanged)

tests/
├── test_config.py       # NEW: Config loading, saving, validation tests
├── test_config_commands.py  # NEW: Command integration tests
└── ... (existing tests)
```

**Structure Decision**: Single project layout (already established). Configuration module (`config.py`) will be expanded to handle file-based config in addition to existing path utilities.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| tomlkit dependency | FR-014 requires preserving comments when updating config | Simple tomllib read + full write would lose user comments |
