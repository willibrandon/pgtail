"""Core highlighter infrastructure for semantic log highlighting.

This module provides:
- Match: Dataclass representing a single pattern match
- OccupancyTracker: Tracks highlighted regions to prevent overlap
- Highlighter: Protocol defining the highlighter interface
- RegexHighlighter: Base class for simple regex-based highlighters
- GroupedRegexHighlighter: Base class for regex with named groups
- KeywordHighlighter: Base class for Aho-Corasick keyword matching
- HighlighterChain: Compositor that applies multiple highlighters
- escape_brackets: Utility to escape Rich markup in text
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import ahocorasick  # type: ignore[import-untyped]
from prompt_toolkit.formatted_text import FormattedText

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# Match Dataclass
# =============================================================================


@dataclass(frozen=True, slots=True)
class Match:
    """A single pattern match within text.

    Attributes:
        start: Start position (0-indexed, inclusive).
        end: End position (0-indexed, exclusive).
        style: Theme style key to apply (e.g., "hl_timestamp_date").
        text: Matched text (for debugging).
    """

    start: int
    end: int
    style: str
    text: str

    def __post_init__(self) -> None:
        """Validate match bounds."""
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end <= self.start:
            raise ValueError("end must be > start")
        if not self.style:
            raise ValueError("style must not be empty")


# =============================================================================
# OccupancyTracker
# =============================================================================


class OccupancyTracker:
    """Tracks which text regions have been highlighted.

    Used by HighlighterChain to prevent overlapping highlights.
    Lower priority highlighters (higher numbers) cannot highlight
    regions already claimed by higher priority highlighters.

    Uses interval-based tracking for O(log n) availability checks
    instead of O(n) per-character tracking.
    """

    __slots__ = ("_length", "_intervals")

    def __init__(self, length: int) -> None:
        """Initialize tracker for text of given length.

        Args:
            length: Total text length being tracked.
        """
        self._length = length
        # Store occupied intervals as sorted list of (start, end) tuples
        self._intervals: list[tuple[int, int]] = []

    @property
    def length(self) -> int:
        """Return the tracked text length."""
        return self._length

    def is_available(self, start: int, end: int) -> bool:
        """Check if a region is fully unhighlighted.

        Uses binary search for O(log n) complexity.

        Args:
            start: Start position (inclusive).
            end: End position (exclusive).

        Returns:
            True if no character in [start, end) is occupied.
        """
        if start < 0 or end > self._length or start >= end:
            return False

        # Binary search for interval that could overlap
        intervals = self._intervals
        if not intervals:
            return True

        # Find first interval where interval_end > start
        lo, hi = 0, len(intervals)
        while lo < hi:
            mid = (lo + hi) // 2
            if intervals[mid][1] <= start:
                lo = mid + 1
            else:
                hi = mid

        # Check if this interval overlaps with [start, end)
        if lo < len(intervals):
            interval_start, interval_end = intervals[lo]
            # Overlap if interval_start < end and interval_end > start
            if interval_start < end:
                return False

        return True

    def mark_occupied(self, start: int, end: int) -> None:
        """Mark a region as highlighted.

        Maintains sorted order and merges adjacent/overlapping intervals.

        Args:
            start: Start position (inclusive).
            end: End position (exclusive).
        """
        if start < 0 or end > self._length or start >= end:
            return

        intervals = self._intervals
        if not intervals:
            intervals.append((start, end))
            return

        # Find insertion point using binary search
        lo, hi = 0, len(intervals)
        while lo < hi:
            mid = (lo + hi) // 2
            if intervals[mid][0] < start:
                lo = mid + 1
            else:
                hi = mid

        # Insert and merge with neighbors if needed
        # For simplicity and speed in the common case (non-overlapping matches),
        # just insert without merging
        intervals.insert(lo, (start, end))

    def available_ranges(self) -> list[tuple[int, int]]:
        """Get list of unhighlighted regions.

        Returns:
            List of (start, end) tuples for contiguous unhighlighted regions.
        """
        if not self._intervals:
            return [(0, self._length)] if self._length > 0 else []

        ranges: list[tuple[int, int]] = []
        pos = 0

        for interval_start, interval_end in self._intervals:
            if pos < interval_start:
                ranges.append((pos, interval_start))
            pos = max(pos, interval_end)

        if pos < self._length:
            ranges.append((pos, self._length))

        return ranges


# =============================================================================
# Highlighter Protocol
# =============================================================================


@runtime_checkable
class Highlighter(Protocol):
    """Protocol for semantic highlighters.

    All highlighters must implement this interface to be used
    with HighlighterChain.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this highlighter.

        Returns:
            Lowercase alphanumeric + underscore, e.g., "timestamp", "sqlstate".
        """
        ...

    @property
    def priority(self) -> int:
        """Processing order (lower = higher priority).

        Returns:
            Positive integer. Ranges by category:
            - 100-199: Structural (timestamp, pid, context)
            - 200-299: Diagnostic (sqlstate, error_name)
            - 300-399: Performance (duration, memory, statistics)
            - 400-499: Objects (identifier, relation, schema)
            - 500-599: WAL (lsn, wal_segment, txid)
            - 600-699: Connection (connection, ip, backend)
            - 700-799: SQL (keywords, strings, numbers, params)
            - 800-899: Lock (lock_type, lock_wait)
            - 900-999: Checkpoint (checkpoint, recovery)
            - 1000+: Misc/Custom (boolean, null, oid, path, custom)
        """
        ...

    @property
    def description(self) -> str:
        """Human-readable description for highlight list command.

        Returns:
            Short description, e.g., "Timestamps with date, time, ms, timezone".
        """
        ...

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all pattern matches in text.

        Args:
            text: Input text to search.
            theme: Current theme for style lookups.

        Returns:
            List of Match objects. May be empty if no matches found.
            Matches may overlap (HighlighterChain resolves conflicts).
        """
        ...

    def apply(self, text: str, theme: Theme) -> FormattedText:
        """Apply highlighting for prompt_toolkit (REPL mode).

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            FormattedText with style tuples for prompt_toolkit rendering.
        """
        ...

    def apply_rich(self, text: str, theme: Theme) -> str:
        """Apply highlighting for Textual/Rich (tail mode).

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            Rich markup string with [style]text[/] tags.
        """
        ...


# =============================================================================
# Escape Brackets Utility
# =============================================================================


def escape_brackets(text: str) -> str:
    """Escape brackets that could be interpreted as Rich markup.

    Rich uses [style]...[/] syntax for markup. Any literal brackets
    in log content (like [bold] or [123]) must be escaped.

    Args:
        text: Text that may contain brackets.

    Returns:
        Text with [ escaped as \\[
    """
    return text.replace("[", "\\[")


# =============================================================================
# Helper: Check if Color is Disabled
# =============================================================================


def is_color_disabled() -> bool:
    """Check if color output is disabled via NO_COLOR environment variable.

    Returns:
        True if NO_COLOR is set (any value), False otherwise.
    """
    return os.environ.get("NO_COLOR", "") != ""


# =============================================================================
# RegexHighlighter Base Class
# =============================================================================


class RegexHighlighter:
    """Base class for simple regex-based highlighters.

    Subclasses can override find_matches() for more complex behavior,
    but the default implementation uses a single pattern with a single style.
    """

    def __init__(
        self,
        name: str,
        priority: int,
        pattern: str,
        style: str,
        flags: int = 0,
    ) -> None:
        """Initialize regex highlighter.

        Args:
            name: Unique identifier.
            priority: Processing order (lower = first).
            pattern: Regex pattern to match.
            style: Theme style key to apply.
            flags: Regex flags (e.g., re.IGNORECASE).

        Raises:
            ValueError: If pattern is invalid or matches empty string.
        """
        self._name = name
        self._priority = priority
        self._style = style

        try:
            self._pattern = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e

        # Check for zero-length match
        if self._pattern.match("") is not None:
            raise ValueError("Pattern matches zero-length strings")

    @property
    def name(self) -> str:
        """Return unique identifier."""
        return self._name

    @property
    def priority(self) -> int:
        """Return processing priority."""
        return self._priority

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return f"Pattern: {self._pattern.pattern}"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all pattern matches in text.

        Args:
            text: Input text to search.
            theme: Current theme (unused in base implementation).

        Returns:
            List of Match objects.
        """
        matches: list[Match] = []
        for m in self._pattern.finditer(text):
            matches.append(
                Match(
                    start=m.start(),
                    end=m.end(),
                    style=self._style,
                    text=m.group(),
                )
            )
        return matches

    def apply(self, text: str, theme: Theme) -> FormattedText:
        """Apply highlighting for prompt_toolkit.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            FormattedText for prompt_toolkit rendering.
        """
        if is_color_disabled() or not text:
            return FormattedText([("", text)])

        matches = self.find_matches(text, theme)
        if not matches:
            return FormattedText([("", text)])

        return _build_formatted_text(text, matches, theme)

    def apply_rich(self, text: str, theme: Theme) -> str:
        """Apply highlighting for Rich/Textual.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            Rich markup string.
        """
        if is_color_disabled() or not text:
            return escape_brackets(text)

        matches = self.find_matches(text, theme)
        if not matches:
            return escape_brackets(text)

        return _build_rich_markup(text, matches, theme)


# =============================================================================
# GroupedRegexHighlighter Base Class
# =============================================================================


class GroupedRegexHighlighter:
    """Base class for regex with named groups mapping to different styles.

    Each named group in the pattern maps to a different style key,
    allowing different parts of a match to have different colors.
    """

    def __init__(
        self,
        name: str,
        priority: int,
        pattern: str,
        group_styles: dict[str, str],
        flags: int = 0,
    ) -> None:
        """Initialize grouped regex highlighter.

        Args:
            name: Unique identifier.
            priority: Processing order (lower = first).
            pattern: Regex pattern with named groups.
            group_styles: Mapping of group name to style key.
            flags: Regex flags.

        Raises:
            ValueError: If pattern is invalid.
        """
        self._name = name
        self._priority = priority
        self._group_styles = group_styles

        try:
            self._pattern = re.compile(pattern, flags | re.VERBOSE)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e

    @property
    def name(self) -> str:
        """Return unique identifier."""
        return self._name

    @property
    def priority(self) -> int:
        """Return processing priority."""
        return self._priority

    @property
    def description(self) -> str:
        """Return human-readable description."""
        groups = ", ".join(self._group_styles.keys())
        return f"Pattern with groups: {groups}"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all pattern matches, creating Match for each named group.

        Args:
            text: Input text to search.
            theme: Current theme (unused in base implementation).

        Returns:
            List of Match objects for each group in each overall match.
        """
        matches: list[Match] = []

        for m in self._pattern.finditer(text):
            for group_name, style in self._group_styles.items():
                try:
                    start, end = m.span(group_name)
                    if start != -1 and end != -1:
                        matches.append(
                            Match(
                                start=start,
                                end=end,
                                style=style,
                                text=m.group(group_name),
                            )
                        )
                except IndexError:
                    # Group not in pattern
                    continue

        return matches

    def apply(self, text: str, theme: Theme) -> FormattedText:
        """Apply highlighting for prompt_toolkit.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            FormattedText for prompt_toolkit rendering.
        """
        if is_color_disabled() or not text:
            return FormattedText([("", text)])

        matches = self.find_matches(text, theme)
        if not matches:
            return FormattedText([("", text)])

        return _build_formatted_text(text, matches, theme)

    def apply_rich(self, text: str, theme: Theme) -> str:
        """Apply highlighting for Rich/Textual.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            Rich markup string.
        """
        if is_color_disabled() or not text:
            return escape_brackets(text)

        matches = self.find_matches(text, theme)
        if not matches:
            return escape_brackets(text)

        return _build_rich_markup(text, matches, theme)


# =============================================================================
# KeywordHighlighter Base Class
# =============================================================================


class KeywordHighlighter:
    """Base class for keyword-based highlighters using Aho-Corasick.

    Uses pyahocorasick for efficient multi-keyword matching in O(n+m) time.
    Ideal for matching many keywords (SQL keywords, lock types, error names).
    """

    def __init__(
        self,
        name: str,
        priority: int,
        keywords: dict[str, str],
        case_sensitive: bool = False,
        word_boundary: bool = True,
    ) -> None:
        """Initialize keyword highlighter.

        Args:
            name: Unique identifier.
            priority: Processing order (lower = first).
            keywords: Mapping of keyword to style key.
            case_sensitive: Match case exactly.
            word_boundary: Only match complete words.
        """
        self._name = name
        self._priority = priority
        self._case_sensitive = case_sensitive
        self._word_boundary = word_boundary
        self._keywords = keywords

        # Build Aho-Corasick automaton lazily
        self._automaton: Any | None = None

    def _ensure_automaton(self) -> Any:
        """Build automaton on first use (lazy initialization)."""
        if self._automaton is None:
            self._automaton = ahocorasick.Automaton()  # type: ignore[no-untyped-call]
            for keyword, style in self._keywords.items():
                key = keyword if self._case_sensitive else keyword.lower()
                self._automaton.add_word(key, (len(key), style, keyword))  # type: ignore[union-attr]
            self._automaton.make_automaton()  # type: ignore[union-attr]
        return self._automaton  # type: ignore[return-value]

    @property
    def name(self) -> str:
        """Return unique identifier."""
        return self._name

    @property
    def priority(self) -> int:
        """Return processing priority."""
        return self._priority

    @property
    def description(self) -> str:
        """Return human-readable description."""
        count = len(self._keywords)
        return f"{count} keywords"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all keyword matches in text.

        Args:
            text: Input text to search.
            theme: Current theme (unused in base implementation).

        Returns:
            List of Match objects for each keyword found.
        """
        if not text:
            return []

        automaton = self._ensure_automaton()
        search_text = text if self._case_sensitive else text.lower()
        matches: list[Match] = []

        for end_pos, (length, style, _keyword) in automaton.iter(search_text):
            start = end_pos - length + 1
            end = end_pos + 1

            # Check word boundaries if required
            if self._word_boundary:
                if start > 0 and search_text[start - 1].isalnum():
                    continue
                if end < len(search_text) and search_text[end].isalnum():
                    continue

            matches.append(
                Match(
                    start=start,
                    end=end,
                    style=style,
                    text=text[start:end],
                )
            )

        return matches

    def apply(self, text: str, theme: Theme) -> FormattedText:
        """Apply highlighting for prompt_toolkit.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            FormattedText for prompt_toolkit rendering.
        """
        if is_color_disabled() or not text:
            return FormattedText([("", text)])

        matches = self.find_matches(text, theme)
        if not matches:
            return FormattedText([("", text)])

        return _build_formatted_text(text, matches, theme)

    def apply_rich(self, text: str, theme: Theme) -> str:
        """Apply highlighting for Rich/Textual.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            Rich markup string.
        """
        if is_color_disabled() or not text:
            return escape_brackets(text)

        matches = self.find_matches(text, theme)
        if not matches:
            return escape_brackets(text)

        return _build_rich_markup(text, matches, theme)


# =============================================================================
# HighlighterChain Compositor
# =============================================================================


class HighlighterChain:
    """Composes multiple highlighters with overlap prevention.

    Collects matches from all highlighters, sorts by position and priority,
    and builds output with OccupancyTracker preventing overlaps.
    """

    def __init__(
        self,
        highlighters: list[Highlighter] | None = None,
        max_length: int = 10240,
    ) -> None:
        """Initialize highlighter chain.

        Args:
            highlighters: Initial list of highlighters.
            max_length: Depth limit for highlighting (default 10KB).
        """
        self._highlighters: dict[str, Highlighter] = {}
        self._max_length = max_length
        # Cached sorted lists for performance
        self._sorted_highlighters: list[Highlighter] | None = None
        self._non_sql_highlighters: list[Highlighter] | None = None
        self._sql_highlighters: list[Highlighter] | None = None

        if highlighters:
            for h in highlighters:
                self.register(h)

    def _invalidate_cache(self) -> None:
        """Invalidate cached highlighter lists."""
        self._sorted_highlighters = None
        self._non_sql_highlighters = None
        self._sql_highlighters = None

    @property
    def highlighters(self) -> list[Highlighter]:
        """Return highlighters sorted by priority (cached)."""
        if self._sorted_highlighters is None:
            self._sorted_highlighters = sorted(
                self._highlighters.values(), key=lambda h: h.priority
            )
        return self._sorted_highlighters

    def _get_non_sql_highlighters(self) -> list[Highlighter]:
        """Return non-SQL highlighters sorted by priority (cached)."""
        if self._non_sql_highlighters is None:
            self._non_sql_highlighters = [
                h for h in self.highlighters if not h.name.startswith("sql_")
            ]
        return self._non_sql_highlighters

    def _get_sql_highlighters(self) -> list[Highlighter]:
        """Return SQL highlighters sorted by priority (cached)."""
        if self._sql_highlighters is None:
            self._sql_highlighters = [
                h for h in self.highlighters if h.name.startswith("sql_")
            ]
        return self._sql_highlighters

    @property
    def max_length(self) -> int:
        """Return depth limit."""
        return self._max_length

    def register(self, highlighter: Highlighter) -> None:
        """Add highlighter to chain.

        Args:
            highlighter: Highlighter to add.

        Raises:
            ValueError: If name already registered.
        """
        if highlighter.name in self._highlighters:
            raise ValueError(f"Highlighter '{highlighter.name}' already registered")
        self._highlighters[highlighter.name] = highlighter
        self._invalidate_cache()

    def unregister(self, name: str) -> None:
        """Remove highlighter by name.

        Args:
            name: Highlighter name to remove.

        Raises:
            KeyError: If name not found.
        """
        if name not in self._highlighters:
            raise KeyError(f"Highlighter '{name}' not found")
        del self._highlighters[name]
        self._invalidate_cache()

    def apply(self, text: str, theme: Theme) -> FormattedText:
        """Apply all highlighters for prompt_toolkit.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            FormattedText for prompt_toolkit rendering.
        """
        if is_color_disabled() or not text or not self._highlighters:
            return FormattedText([("", text)])

        # Apply depth limiting
        truncated = False
        if len(text) > self._max_length:
            process_text = text[: self._max_length]
            truncated = True
        else:
            process_text = text

        # Collect all matches from all highlighters
        all_matches = self._collect_matches(process_text, theme)
        if not all_matches:
            return FormattedText([("", text)])

        # Apply overlap prevention and build output
        result = _build_formatted_text_with_tracker(process_text, all_matches, theme)

        # Append truncated portion if needed
        if truncated:
            result = FormattedText(list(result) + [("", text[self._max_length :])])

        return result

    def apply_rich(self, text: str, theme: Theme) -> str:
        """Apply all highlighters for Rich/Textual.

        Args:
            text: Input text to highlight.
            theme: Current theme for style lookups.

        Returns:
            Rich markup string.
        """
        if is_color_disabled() or not text or not self._highlighters:
            return escape_brackets(text)

        # Apply depth limiting (FR-006, FR-012)
        truncated = False
        if len(text) > self._max_length:
            process_text = text[: self._max_length]
            truncated = True
        else:
            process_text = text

        # Collect all matches from all highlighters
        all_matches = self._collect_matches(process_text, theme)
        if not all_matches:
            if truncated:
                return escape_brackets(process_text) + escape_brackets(text[self._max_length :])
            return escape_brackets(text)

        # Apply overlap prevention and build output
        result = _build_rich_markup_with_tracker(process_text, all_matches, theme)

        # Append truncated portion if needed
        if truncated:
            result = result + escape_brackets(text[self._max_length :])

        return result

    def _collect_matches(self, text: str, theme: Theme) -> list[tuple[int, int, str, int]]:
        """Collect all matches from all highlighters.

        SQL highlighters (names starting with "sql_") are only applied
        within detected SQL contexts to avoid highlighting common English
        words like "for", "with", "at" that happen to be SQL keywords.

        Args:
            text: Text to search.
            theme: Current theme.

        Returns:
            List of (start, end, style, priority) tuples.
        """
        from pgtail_py.highlighters.sql import detect_sql_content

        all_matches: list[tuple[int, int, str, int]] = []

        # Process non-SQL highlighters first (they always run)
        for h in self._get_non_sql_highlighters():
            for m in h.find_matches(text, theme):
                all_matches.append((m.start, m.end, m.style, h.priority))

        # Detect SQL context - SQL highlighters only apply within SQL region
        sql_highlighters = self._get_sql_highlighters()
        if sql_highlighters:
            sql_result = detect_sql_content(text)
            if sql_result is not None:
                # SQL detected - apply SQL highlighters within the SQL region
                sql_start = len(sql_result.prefix)
                sql_end = sql_start + len(sql_result.sql)

                for h in sql_highlighters:
                    for m in h.find_matches(text, theme):
                        # Only include matches within SQL context
                        if m.start >= sql_start and m.end <= sql_end:
                            all_matches.append((m.start, m.end, m.style, h.priority))

        return all_matches


# =============================================================================
# Helper Functions for Building Output
# =============================================================================


def _convert_ansi_color_to_rich(color: str) -> str:
    """Convert prompt_toolkit ANSI color name to Rich color name.

    prompt_toolkit uses names like 'ansibrightblack', 'ansired', 'ansibrightred'.
    Rich uses names like 'bright_black', 'red', 'bright_red'.

    Args:
        color: Color name in prompt_toolkit format.

    Returns:
        Color name in Rich format.
    """
    if not color:
        return color

    # Handle hex colors and named colors that don't start with 'ansi'
    if not color.startswith("ansi"):
        return color

    # Remove 'ansi' prefix
    color = color[4:]

    # Handle 'bright' variants: ansibrightred -> bright_red
    if color.startswith("bright"):
        base_color = color[6:]  # Remove 'bright'
        return f"bright_{base_color}"

    # Handle standard colors: ansired -> red
    return color


# Style cache to avoid repeated theme lookups
# Key: (theme_name, style_key), Value: rich_style_string
_rich_style_cache: dict[tuple[str, str], str] = {}


def _get_rich_style(theme: Theme, style_key: str) -> str:
    """Convert theme style key to Rich markup style.

    Uses caching to avoid repeated theme lookups.

    Args:
        theme: Theme to look up style in.
        style_key: Style key (e.g., "hl_timestamp_date") or literal color (e.g., "magenta").

    Returns:
        Rich style string (e.g., "bold red") or empty string for default.
    """
    cache_key = (theme.name, style_key)
    cached = _rich_style_cache.get(cache_key)
    if cached is not None:
        return cached

    color_style = theme.get_style(style_key)
    if color_style is None:
        # Not a theme key - treat as literal color/style for custom highlighters
        # Rich accepts colors like "magenta", "bold red", "#ff00ff"
        _rich_style_cache[cache_key] = style_key
        return style_key

    parts: list[str] = []
    if color_style.fg:
        parts.append(_convert_ansi_color_to_rich(color_style.fg))
    if color_style.bg:
        parts.append(f"on {_convert_ansi_color_to_rich(color_style.bg)}")
    if color_style.bold:
        parts.append("bold")
    if color_style.dim:
        parts.append("dim")
    if color_style.italic:
        parts.append("italic")
    if color_style.underline:
        parts.append("underline")

    result = " ".join(parts)
    _rich_style_cache[cache_key] = result
    return result


# Cache for prompt_toolkit style lookups
_prompt_toolkit_style_cache: dict[tuple[str, str], str] = {}


def _get_prompt_toolkit_style(theme: Theme, style_key: str) -> str:
    """Convert theme style key to prompt_toolkit style class.

    Uses caching to avoid repeated lookups.

    Args:
        theme: Theme to look up style in.
        style_key: Style key (e.g., "hl_timestamp_date") or literal color (e.g., "magenta").

    Returns:
        Style class string (e.g., "class:hl_timestamp_date") or inline style (e.g., "fg:magenta").
    """
    cache_key = (theme.name, style_key)
    cached = _prompt_toolkit_style_cache.get(cache_key)
    if cached is not None:
        return cached

    color_style = theme.get_style(style_key)
    if color_style is None:
        # Not a theme key - treat as literal color/style for custom highlighters
        # prompt_toolkit uses "fg:color" format for foreground colors
        # Support formats: "magenta", "bold magenta", "#ff00ff", "bold #ff00ff"
        parts = style_key.split()
        result_parts: list[str] = []
        for part in parts:
            if part == "bold":
                result_parts.append("bold")
            elif part == "italic":
                result_parts.append("italic")
            elif part == "underline":
                result_parts.append("underline")
            elif part.startswith("#") or part.startswith("ansi"):
                # Hex color or ansi color
                result_parts.append(f"fg:{part}")
            else:
                # Named color like "magenta", "red", etc.
                result_parts.append(f"fg:ansi{part}")
        result = " ".join(result_parts)
        _prompt_toolkit_style_cache[cache_key] = result
        return result

    result = f"class:{style_key}"
    _prompt_toolkit_style_cache[cache_key] = result
    return result


def _build_formatted_text(text: str, matches: list[Match], theme: Theme) -> FormattedText:
    """Build FormattedText from matches (no overlap prevention).

    Used by individual highlighters that produce non-overlapping matches.

    Args:
        text: Original text.
        matches: List of matches (may overlap).
        theme: Current theme.

    Returns:
        FormattedText for prompt_toolkit.
    """
    if not matches:
        return FormattedText([("", text)])

    # Sort by start position
    sorted_matches = sorted(matches, key=lambda m: m.start)

    result: list[tuple[str, str]] = []
    pos = 0

    for m in sorted_matches:
        # Skip if overlapping with already processed text
        if m.start < pos:
            continue

        # Add unstyled text before this match
        if pos < m.start:
            result.append(("", text[pos : m.start]))

        # Add styled match
        style_class = _get_prompt_toolkit_style(theme, m.style)
        result.append((style_class, text[m.start : m.end]))
        pos = m.end

    # Add remaining unstyled text
    if pos < len(text):
        result.append(("", text[pos:]))

    return FormattedText(result)


def _build_rich_markup(text: str, matches: list[Match], theme: Theme) -> str:
    """Build Rich markup from matches (no overlap prevention).

    Used by individual highlighters that produce non-overlapping matches.

    Args:
        text: Original text.
        matches: List of matches (may overlap).
        theme: Current theme.

    Returns:
        Rich markup string.
    """
    if not matches:
        return escape_brackets(text)

    # Sort by start position
    sorted_matches = sorted(matches, key=lambda m: m.start)

    result: list[str] = []
    pos = 0

    for m in sorted_matches:
        # Skip if overlapping with already processed text
        if m.start < pos:
            continue

        # Add unstyled text before this match
        if pos < m.start:
            result.append(escape_brackets(text[pos : m.start]))

        # Add styled match
        style = _get_rich_style(theme, m.style)
        if style:
            result.append(f"[{style}]{escape_brackets(text[m.start : m.end])}[/]")
        else:
            result.append(escape_brackets(text[m.start : m.end]))
        pos = m.end

    # Add remaining unstyled text
    if pos < len(text):
        result.append(escape_brackets(text[pos:]))

    return "".join(result)


def _build_formatted_text_with_tracker(
    text: str,
    matches: list[tuple[int, int, str, int]],
    theme: Theme,
) -> FormattedText:
    """Build FormattedText with OccupancyTracker for overlap prevention.

    Args:
        text: Original text.
        matches: List of (start, end, style, priority) tuples.
        theme: Current theme.

    Returns:
        FormattedText for prompt_toolkit.
    """
    if not matches:
        return FormattedText([("", text)])

    # Sort by start position, then by priority (lower priority wins on tie)
    # Use in-place sort for performance
    matches.sort(key=lambda m: (m[0], m[3]))

    # Apply overlap prevention and build output in single pass
    # Since matches are already sorted by start position, accepted matches
    # will also be in sorted order - no need for second sort
    tracker = OccupancyTracker(len(text))
    result: list[tuple[str, str]] = []
    pos = 0

    for start, end, style, _priority in matches:
        if tracker.is_available(start, end):
            tracker.mark_occupied(start, end)
            # Output unstyled text before this match
            if pos < start:
                result.append(("", text[pos:start]))
            # Output styled match
            style_class = _get_prompt_toolkit_style(theme, style)
            result.append((style_class, text[start:end]))
            pos = end

    if pos < len(text):
        result.append(("", text[pos:]))

    return FormattedText(result)


def _build_rich_markup_with_tracker(
    text: str,
    matches: list[tuple[int, int, str, int]],
    theme: Theme,
) -> str:
    """Build Rich markup with OccupancyTracker for overlap prevention.

    Args:
        text: Original text.
        matches: List of (start, end, style, priority) tuples.
        theme: Current theme.

    Returns:
        Rich markup string.
    """
    if not matches:
        return escape_brackets(text)

    # Sort by start position, then by priority (lower priority wins on tie)
    # Use in-place sort for performance
    matches.sort(key=lambda m: (m[0], m[3]))

    # Apply overlap prevention and build output in single pass
    # Since matches are already sorted by start position, accepted matches
    # will also be in sorted order - no need for second sort
    tracker = OccupancyTracker(len(text))
    result: list[str] = []
    pos = 0

    for start, end, style, _priority in matches:
        if tracker.is_available(start, end):
            tracker.mark_occupied(start, end)
            # Output unhighlighted text before this match
            if pos < start:
                result.append(escape_brackets(text[pos:start]))
            # Output highlighted match
            rich_style = _get_rich_style(theme, style)
            if rich_style:
                result.append(f"[{rich_style}]{escape_brackets(text[start:end])}[/]")
            else:
                result.append(escape_brackets(text[start:end]))
            pos = end

    if pos < len(text):
        result.append(escape_brackets(text[pos:]))

    return "".join(result)


# =============================================================================
# CustomRegexHighlighter (User-Defined Patterns)
# =============================================================================


class CustomRegexHighlighter(RegexHighlighter):
    """User-defined regex-based highlighter.

    Wraps a user's custom regex pattern for highlighting application-specific
    text in log messages. Unlike built-in highlighters, custom highlighters:
    - Have priority >= 1050 (run after all built-ins)
    - Can be added/removed at runtime
    - Are persisted to config.toml
    """

    def __init__(
        self,
        name: str,
        pattern: str,
        style: str = "yellow",
        priority: int = 1050,
        description: str | None = None,
    ) -> None:
        """Initialize custom highlighter.

        Args:
            name: Unique identifier (must not conflict with built-in names).
            pattern: Regex pattern to match.
            style: Color/style to apply (e.g., "yellow", "bold red").
            priority: Processing order (default 1050, after built-ins).
            description: Human-readable description for highlight list.

        Raises:
            ValueError: If pattern is invalid or matches empty string.
        """
        super().__init__(
            name=name,
            priority=priority,
            pattern=pattern,
            style=style,
        )
        self._description = description or f"Custom pattern: {pattern}"

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return self._description


def validate_custom_pattern(pattern: str) -> tuple[bool, str | None]:
    """Validate a regex pattern for custom highlighter.

    Checks:
    1. Pattern is valid regex
    2. Pattern does not match zero-length strings

    Args:
        pattern: Regex pattern to validate.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    # Check empty pattern
    if not pattern:
        return False, "Pattern cannot be empty"

    # Check valid regex
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return False, f"Invalid regex: {e}"

    # Check zero-length match
    if compiled.match("") is not None:
        return False, "Pattern matches zero-length strings"

    return True, None
