# Research: Regex Pattern Filtering

**Feature**: 003-regex-filter
**Date**: 2025-12-14

## Overview

This feature uses Python's built-in `re` module for regex pattern matching. No external research or dependency evaluation is required.

## Decisions

### 1. Regex Engine

**Decision**: Use Python `re` module (stdlib)

**Rationale**:
- Part of Python standard library - no additional dependencies
- Cross-platform identical behavior
- Well-documented and familiar to Python developers
- Sufficient performance for log filtering use case

**Alternatives Considered**:
- `regex` package: More features but adds dependency; overkill for simple pattern matching
- `re2`: Google's regex library; requires C extension; not justified for this use case

### 2. Pattern Syntax

**Decision**: Standard Python regex syntax enclosed in `/pattern/` delimiters

**Rationale**:
- Familiar syntax from sed, grep, vim, JavaScript
- Clear visual distinction from literal text
- Allows suffix modifiers (e.g., `/pattern/c` for case-sensitive)

**Alternatives Considered**:
- Bare patterns without delimiters: Ambiguous with command arguments
- Quoted strings: Less visually distinct, conflicts with shell quoting

### 3. Case Sensitivity Default

**Decision**: Case-insensitive matching by default, `/pattern/c` for case-sensitive

**Rationale**:
- PostgreSQL log messages have inconsistent casing
- Most users want to match content regardless of case
- Explicit `c` suffix is intuitive ("c" = case-sensitive)

**Alternatives Considered**:
- Case-sensitive default with `/i` for insensitive: More common in regex tools, but wrong default for log filtering
- Always case-insensitive: Removes user control when exact matching needed

### 4. Filter Combination Logic

**Decision**: OR for includes, AND for `&` prefix, exclude always wins

**Rationale**:
- OR for includes matches common "show lines matching any of these" use case
- AND prefix enables "must contain both X and Y" patterns
- Exclude precedence prevents confusion when patterns overlap

**Evaluation Order**:
```
1. Level filter (must pass)
2. Include filters (any must match, OR logic)
3. Exclude filters (any match hides line)
4. AND filters (all must match)
```

### 5. Highlight Rendering

**Decision**: Yellow background color using prompt_toolkit styles

**Rationale**:
- Yellow background is universal "highlighter" metaphor
- Works well on both dark and light terminal backgrounds
- prompt_toolkit already handles terminal color capabilities

**Implementation**:
```python
HIGHLIGHT_STYLE = "bg:yellow fg:black"
```

### 6. Performance Strategy

**Decision**: Compile regex patterns once at creation, reuse compiled patterns

**Rationale**:
- `re.compile()` has overhead that should be paid once
- Compiled patterns are thread-safe for matching
- Log lines arrive continuously; compilation must not happen per-line

**Implementation**:
```python
@dataclass
class RegexFilter:
    pattern: str
    compiled: re.Pattern  # Compiled at creation
```

## No Further Research Required

All technical decisions use Python stdlib or existing project dependencies. No external APIs, third-party services, or novel patterns require investigation.
