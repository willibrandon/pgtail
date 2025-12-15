"""Regex pattern filtering for PostgreSQL log output.

Provides pattern-based filtering and highlighting that works alongside
level-based filtering. Supports include, exclude, AND/OR logic, and
visual highlighting of matched text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class FilterType(Enum):
    """Type of regex filter determining how it's applied."""

    INCLUDE = "include"  # Line must match (OR with other includes)
    EXCLUDE = "exclude"  # Line must NOT match
    AND = "and"  # Line must match (AND with other AND filters)


@dataclass
class RegexFilter:
    """A compiled regex filter.

    Attributes:
        pattern: Original pattern string
        filter_type: How this filter is applied
        case_sensitive: True if /pattern/c was used
        compiled: Pre-compiled regex for performance
    """

    pattern: str
    filter_type: FilterType
    case_sensitive: bool
    compiled: re.Pattern[str]

    @classmethod
    def create(
        cls,
        pattern: str,
        filter_type: FilterType,
        case_sensitive: bool = False,
    ) -> RegexFilter:
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


@dataclass
class Highlight:
    """A compiled highlight pattern.

    Attributes:
        pattern: Original pattern string
        case_sensitive: True if /pattern/c was used
        compiled: Pre-compiled regex
    """

    pattern: str
    case_sensitive: bool
    compiled: re.Pattern[str]

    @classmethod
    def create(cls, pattern: str, case_sensitive: bool = False) -> Highlight:
        """Create a highlight with compiled regex.

        Args:
            pattern: Regex pattern string
            case_sensitive: If False, compile with re.IGNORECASE

        Returns:
            Highlight instance

        Raises:
            re.error: If pattern is invalid
        """
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


@dataclass
class FilterState:
    """Session state for regex filters and highlights.

    Attributes:
        includes: OR-combined include filters
        excludes: Exclude filters (any match hides)
        ands: AND-combined filters (all must match)
        highlights: Visual highlight patterns
    """

    includes: list[RegexFilter] = field(default_factory=list)
    excludes: list[RegexFilter] = field(default_factory=list)
    ands: list[RegexFilter] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)

    @classmethod
    def empty(cls) -> FilterState:
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


def parse_filter_arg(arg: str) -> tuple[str, bool]:
    """Parse a filter argument in /pattern/ or /pattern/c syntax.

    Args:
        arg: Filter argument string

    Returns:
        Tuple of (pattern, case_sensitive)

    Raises:
        ValueError: If argument format is invalid or pattern is empty
    """
    if not arg.startswith("/"):
        raise ValueError(f"Filter pattern must start with /: {arg}")

    # Check for /pattern/c (case-sensitive) suffix
    if arg.endswith("/c"):
        inner = arg[1:-2]
        case_sensitive = True
    elif arg.endswith("/"):
        inner = arg[1:-1]
        case_sensitive = False
    else:
        raise ValueError(f"Filter pattern must end with / or /c: {arg}")

    if not inner:
        raise ValueError("Empty pattern not allowed")

    return inner, case_sensitive
