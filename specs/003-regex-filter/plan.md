# Implementation Plan: Regex Pattern Filtering

**Branch**: `003-regex-filter` | **Date**: 2025-12-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-regex-filter/spec.md`

## Summary

Add regex-based filtering alongside existing level filtering. Users can include/exclude log lines matching patterns, combine multiple patterns with AND/OR logic, and highlight matches without filtering. Implementation extends existing `filter.py` and `cli.py` with new `regex_filter.py` module.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, re (stdlib)
**Storage**: N/A (session state only)
**Testing**: pytest >=7.0.0
**Target Platform**: macOS, Linux, Windows (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: 10,000+ log lines/minute with no visible delay (per SC-003)
**Constraints**: Regex compiled once and reused (FR-014)
**Scale/Scope**: Single-user CLI tool, session-based filter state

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ⚠️ REVIEW | Adds 2 new commands (`filter`, `highlight`) - small expansion but justified by clear user value |
| II. Cross-Platform Parity | ✅ PASS | Uses only stdlib `re` module - identical behavior across platforms |
| III. Graceful Degradation | ✅ PASS | Invalid regex shows error, doesn't crash |
| IV. User-Friendly Feedback | ✅ PASS | Error messages for invalid regex, filter status display |
| V. Focused Scope | ⚠️ EXCEPTION | Constitution says "no regex matching" but this is explicitly requested feature |
| VI. Minimal Dependencies | ✅ PASS | Uses only Python stdlib `re` - no new dependencies |
| VII. Developer Workflow Priority | ✅ PASS | Enhances log analysis for PostgreSQL developers |

**Exception Required**: Constitution V. Focused Scope explicitly excludes "regex matching". This feature directly contradicts that constraint. **Justification**: User has explicitly requested this feature. The constitution was written before this requirement. The feature adds significant value for filtering PostgreSQL logs by table names, query patterns, and error codes.

## Project Structure

### Documentation (this feature)

```text
specs/003-regex-filter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A (CLI tool, no API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py
├── __main__.py          # Entry point (no changes)
├── cli.py               # MODIFY: Add filter/highlight command handlers
├── colors.py            # MODIFY: Add highlight rendering support
├── commands.py          # MODIFY: Add filter/highlight commands, completions
├── config.py            # No changes
├── detector.py          # No changes
├── detector_unix.py     # No changes
├── detector_windows.py  # No changes
├── enable_logging.py    # No changes
├── filter.py            # EXISTING: LogLevel filtering (no changes)
├── instance.py          # No changes
├── parser.py            # No changes
├── regex_filter.py      # NEW: RegexFilter, Highlight, FilterState classes
└── tailer.py            # MODIFY: Integrate regex filtering into output

tests/
├── __init__.py
├── test_detector.py
├── test_filter.py
├── test_parser.py
└── test_regex_filter.py # NEW: Tests for regex filtering
```

**Structure Decision**: Single project structure maintained. New `regex_filter.py` module for regex-specific logic, keeping separation of concerns. Existing `filter.py` unchanged (handles log levels only).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution V exception | User-requested feature for log analysis | No simpler alternative - this is the requested functionality |

## Implementation Approach

### Core Design Decisions

1. **Separate Module**: New `regex_filter.py` keeps regex logic isolated from level filtering
2. **Compiled Patterns**: Store compiled `re.Pattern` objects for performance
3. **Filter Evaluation Order**: Level filter → Include filters (OR) → Exclude filters → AND filters
4. **Highlight Integration**: Modify `colors.py` to apply background color to matched spans
5. **State Location**: Add regex filter state to `AppState` in `cli.py`

### Filter Logic

```
should_display(line) =
    passes_level_filter(line)
    AND (no_include_filters OR any_include_matches(line))
    AND NOT any_exclude_matches(line)
    AND all_and_filters_match(line)
```

### Command Syntax

| Command | Action |
|---------|--------|
| `filter /pattern/` | Set single include filter (clears previous includes) |
| `filter -/pattern/` | Add exclude filter |
| `filter +/pattern/` | Add OR include filter |
| `filter &/pattern/` | Add AND include filter |
| `filter /pattern/c` | Case-sensitive filter |
| `filter clear` | Clear all filters |
| `filter` | Show active filters |
| `highlight /pattern/` | Set highlight pattern |
| `highlight clear` | Clear highlights |
| `highlight` | Show active highlights |

### Key Files to Modify

1. **regex_filter.py** (NEW)
   - `RegexFilter` dataclass: pattern, filter_type, case_sensitive
   - `Highlight` dataclass: pattern, compiled regex
   - `FilterState` dataclass: includes, excludes, ands, highlights
   - `parse_filter_command()`: Parse `/pattern/` syntax
   - `should_show_line()`: Evaluate all filters
   - `apply_highlights()`: Return spans to highlight

2. **cli.py** (MODIFY)
   - Add `regex_state: FilterState` to `AppState`
   - Add `filter_command()` handler
   - Add `highlight_command()` handler
   - Update `handle_command()` dispatch

3. **commands.py** (MODIFY)
   - Add "filter" and "highlight" to COMMANDS dict
   - Add completion for filter subcommands

4. **colors.py** (MODIFY)
   - Add `format_log_entry_with_highlights()` function
   - Add yellow background style for highlights

5. **tailer.py** (MODIFY)
   - Integrate regex filter check in log line processing
   - Pass filter state to output formatting

## Phase Outputs

### Phase 0: Research

- No external research needed - using Python stdlib `re`
- Pattern syntax: Standard Python regex
- Performance: Pre-compiled patterns, O(n) per filter per line

### Phase 1: Design

- data-model.md: RegexFilter, Highlight, FilterState entities
- quickstart.md: Developer setup for feature implementation
- contracts/: N/A (no API contracts for CLI tool)
