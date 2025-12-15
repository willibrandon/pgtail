# Data Model: Regex Pattern Filtering

**Feature**: 003-regex-filter
**Date**: 2025-12-14

## Entities

### RegexFilter

Represents a single regex filter with its type and compiled pattern.

```python
from dataclasses import dataclass
from enum import Enum
import re

class FilterType(Enum):
    """Type of regex filter determining how it's applied."""
    INCLUDE = "include"      # Line must match (OR with other includes)
    EXCLUDE = "exclude"      # Line must NOT match
    AND = "and"              # Line must match (AND with other AND filters)

@dataclass
class RegexFilter:
    """A compiled regex filter."""
    pattern: str                 # Original pattern string
    filter_type: FilterType      # How this filter is applied
    case_sensitive: bool         # True if /pattern/c was used
    compiled: re.Pattern         # Pre-compiled regex for performance

    @classmethod
    def create(cls, pattern: str, filter_type: FilterType, case_sensitive: bool = False) -> "RegexFilter":
        """Create a filter with compiled regex.

        Args:
            pattern: Regex pattern string
            filter_type: Type of filter
            case_sensitive: If False, compile with re.IGNORECASE

        Returns:
            RegexFilter instance

        Raises:
            re.error: If pattern is invalid
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
        return cls(
            pattern=pattern,
            filter_type=filter_type,
            case_sensitive=case_sensitive,
            compiled=compiled,
        )

    def matches(self, text: str) -> bool:
        """Check if text matches this filter's pattern."""
        return bool(self.compiled.search(text))
```

### Highlight

Represents a highlight pattern that marks matching text visually.

```python
@dataclass
class Highlight:
    """A compiled highlight pattern."""
    pattern: str                 # Original pattern string
    case_sensitive: bool         # True if /pattern/c was used
    compiled: re.Pattern         # Pre-compiled regex

    @classmethod
    def create(cls, pattern: str, case_sensitive: bool = False) -> "Highlight":
        """Create a highlight with compiled regex."""
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
        return cls(
            pattern=pattern,
            case_sensitive=case_sensitive,
            compiled=compiled,
        )

    def find_spans(self, text: str) -> list[tuple[int, int]]:
        """Find all match spans in text.

        Returns:
            List of (start, end) tuples for each match
        """
        return [(m.start(), m.end()) for m in self.compiled.finditer(text)]
```

### FilterState

Collection of all active filters and highlights for a session.

```python
@dataclass
class FilterState:
    """Session state for regex filters and highlights."""
    includes: list[RegexFilter]   # OR-combined include filters
    excludes: list[RegexFilter]   # Exclude filters (any match hides)
    ands: list[RegexFilter]       # AND-combined filters (all must match)
    highlights: list[Highlight]   # Visual highlight patterns

    @classmethod
    def empty(cls) -> "FilterState":
        """Create empty filter state."""
        return cls(
            includes=[],
            excludes=[],
            ands=[],
            highlights=[],
        )

    def has_filters(self) -> bool:
        """Check if any filters are active."""
        return bool(self.includes or self.excludes or self.ands)

    def has_highlights(self) -> bool:
        """Check if any highlights are active."""
        return bool(self.highlights)

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.includes.clear()
        self.excludes.clear()
        self.ands.clear()

    def clear_highlights(self) -> None:
        """Remove all highlights."""
        self.highlights.clear()

    def add_filter(self, f: RegexFilter) -> None:
        """Add a filter to the appropriate list."""
        if f.filter_type == FilterType.INCLUDE:
            self.includes.append(f)
        elif f.filter_type == FilterType.EXCLUDE:
            self.excludes.append(f)
        elif f.filter_type == FilterType.AND:
            self.ands.append(f)

    def set_include(self, f: RegexFilter) -> None:
        """Set single include filter, clearing previous includes."""
        self.includes = [f]

    def should_show(self, text: str) -> bool:
        """Check if text passes all filter rules.

        Logic:
        1. If includes exist, at least one must match (OR)
        2. If any exclude matches, hide the line
        3. If ANDs exist, all must match
        """
        # Check includes (OR logic)
        if self.includes:
            if not any(f.matches(text) for f in self.includes):
                return False

        # Check excludes (any match hides)
        if any(f.matches(text) for f in self.excludes):
            return False

        # Check ANDs (all must match)
        if self.ands:
            if not all(f.matches(text) for f in self.ands):
                return False

        return True
```

## Relationships

```
AppState (cli.py)
    ├── active_levels: set[LogLevel]     # Existing level filter
    └── regex_state: FilterState         # NEW: Regex filter state
            ├── includes: list[RegexFilter]
            ├── excludes: list[RegexFilter]
            ├── ands: list[RegexFilter]
            └── highlights: list[Highlight]
```

## State Transitions

### Filter State

```
Empty → Has Filters
  trigger: filter /pattern/ command

Has Filters → Empty
  trigger: filter clear command

Has Filters → Has Filters (modified)
  trigger: filter +/pattern/, filter -/pattern/, filter &/pattern/
```

### Highlight State

```
Empty → Has Highlights
  trigger: highlight /pattern/ command

Has Highlights → Empty
  trigger: highlight clear command
```

## Validation Rules

1. **Pattern Validation**: All patterns must be valid Python regex syntax
2. **Empty Pattern**: `/` or `//` is not allowed - display error
3. **Case Sensitivity**: Only `/c` suffix triggers case-sensitive mode
4. **Filter Interaction**: Level filters apply BEFORE regex filters
