# Contract: Highlighter Protocol

**Branch**: `023-semantic-highlighting` | **Date**: 2026-01-14

## Overview

This document defines the internal API contract for semantic highlighters. All highlighters must conform to this protocol to integrate with the HighlighterChain compositor.

---

## Protocol Definition

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from prompt_toolkit.formatted_text import FormattedText

@dataclass(frozen=True, slots=True)
class Match:
    """A single pattern match within text."""
    start: int      # Start position (0-indexed, inclusive)
    end: int        # End position (0-indexed, exclusive)
    style: str      # Theme style key to apply
    text: str       # Matched text (for debugging)

@runtime_checkable
class Highlighter(Protocol):
    """Protocol for semantic highlighters."""

    @property
    def name(self) -> str:
        """Unique identifier for this highlighter.

        Returns:
            Lowercase alphanumeric + underscore, e.g., "timestamp", "sqlstate"
        """
        ...

    @property
    def priority(self) -> int:
        """Processing order (lower = higher priority).

        Returns:
            Positive integer. Ranges by category:
            - 100-199: Structural
            - 200-299: Diagnostic
            - 300-399: Performance
            - 400-499: Objects
            - 500-599: WAL
            - 600-699: Connection
            - 700-799: SQL
            - 800-899: Lock
            - 900-999: Checkpoint
            - 1000+: Misc/Custom
        """
        ...

    @property
    def description(self) -> str:
        """Human-readable description for highlight list command.

        Returns:
            Short description, e.g., "Timestamps with date, time, ms, timezone"
        """
        ...

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        """Find all pattern matches in text.

        Args:
            text: Input text to search
            theme: Current theme for style lookups

        Returns:
            List of Match objects. May be empty if no matches found.
            Matches may overlap (HighlighterChain resolves conflicts).
        """
        ...

    def apply(self, text: str, theme: "Theme") -> FormattedText:
        """Apply highlighting for prompt_toolkit (REPL mode).

        Args:
            text: Input text to highlight
            theme: Current theme for style lookups

        Returns:
            FormattedText with style tuples for prompt_toolkit rendering.
            Format: [("class:style_name", "text"), ...]
        """
        ...

    def apply_rich(self, text: str, theme: "Theme") -> str:
        """Apply highlighting for Textual/Rich (tail mode).

        Args:
            text: Input text to highlight
            theme: Current theme for style lookups

        Returns:
            Rich markup string with [style]text[/] tags.
            Brackets in text must be escaped as \\[
        """
        ...
```

---

## Implementation Requirements

### 1. Name Uniqueness

Each highlighter must have a unique name. Names are validated at registration:

```python
# Valid names
"timestamp"
"sql_keyword"
"duration"
"custom_request_id"

# Invalid names (rejected)
"Timestamp"      # Uppercase not allowed
"sql keyword"    # Spaces not allowed
"sql-keyword"    # Hyphens not allowed
""               # Empty not allowed
```

### 2. Priority Ranges

Priority determines processing order. Lower priority = processed first.

| Range | Category | Purpose |
|-------|----------|---------|
| 100-199 | Structural | Always-visible elements (timestamp, PID) |
| 200-299 | Diagnostic | Error information (SQLSTATE, error names) |
| 300-399 | Performance | Metrics (duration, memory, stats) |
| 400-499 | Objects | Database objects (identifiers, relations) |
| 500-599 | WAL | Replication data (LSN, segments, TXIDs) |
| 600-699 | Connection | Session info (IPs, backends, users) |
| 700-799 | SQL | SQL syntax (keywords, strings, numbers) |
| 800-899 | Lock | Locking info (types, waits) |
| 900-999 | Checkpoint | Checkpoint/recovery messages |
| 1000+ | Misc/Custom | Everything else + user patterns |

### 3. Match Requirements

Matches returned from `find_matches()` must satisfy:

```python
# Invariants
assert 0 <= match.start < match.end <= len(text)
assert match.text == text[match.start:match.end]
assert len(match.style) > 0

# Style must be valid theme key
# If not found in theme, will fallback to default color
```

### 4. Performance Requirements

Each highlighter should:

- Pre-compile regex patterns at instantiation
- Use Aho-Corasick for multi-keyword matching (>10 keywords)
- Return empty list quickly if no patterns could match
- Process typical log lines (<1KB) in <1ms

---

## Base Implementations

### RegexHighlighter

For simple regex-based patterns:

```python
class RegexHighlighter:
    """Base class for regex-based highlighters."""

    def __init__(self, name: str, priority: int, pattern: str, style: str):
        self._name = name
        self._priority = priority
        self._pattern = re.compile(pattern)
        self._style = style

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def description(self) -> str:
        return f"Pattern: {self._pattern.pattern}"

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        matches = []
        for m in self._pattern.finditer(text):
            matches.append(Match(
                start=m.start(),
                end=m.end(),
                style=self._style,
                text=m.group()
            ))
        return matches
```

### KeywordHighlighter

For multi-keyword matching using Aho-Corasick:

```python
import ahocorasick

class KeywordHighlighter:
    """Base class for keyword-based highlighters."""

    def __init__(self, name: str, priority: int, keywords: dict[str, str]):
        """
        Args:
            keywords: Mapping of keyword → style
        """
        self._name = name
        self._priority = priority
        self._automaton = ahocorasick.Automaton()
        self._keyword_styles = {}

        for keyword, style in keywords.items():
            key = keyword.lower()
            self._automaton.add_word(key, (len(key), style))
            self._keyword_styles[key] = style

        self._automaton.make_automaton()

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        matches = []
        lower_text = text.lower()
        for end_pos, (length, style) in self._automaton.iter(lower_text):
            start = end_pos - length + 1
            matches.append(Match(
                start=start,
                end=end_pos + 1,
                style=style,
                text=text[start:end_pos + 1]
            ))
        return matches
```

### GroupedRegexHighlighter

For regex with named groups mapping to different styles:

```python
class GroupedRegexHighlighter:
    """Highlighter with named regex groups mapping to styles."""

    def __init__(self, name: str, priority: int, pattern: str, group_styles: dict[str, str]):
        """
        Args:
            pattern: Regex with named groups, e.g., r"(?P<date>\d{4}-\d{2}-\d{2})"
            group_styles: Mapping of group name → style
        """
        self._name = name
        self._priority = priority
        self._pattern = re.compile(pattern)
        self._group_styles = group_styles

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        matches = []
        for m in self._pattern.finditer(text):
            for group_name, style in self._group_styles.items():
                try:
                    start, end = m.span(group_name)
                    if start != -1:
                        matches.append(Match(
                            start=start,
                            end=end,
                            style=style,
                            text=m.group(group_name)
                        ))
                except IndexError:
                    continue
        return matches
```

---

## HighlighterChain Contract

The HighlighterChain composes highlighters:

```python
class HighlighterChain:
    """Composes multiple highlighters with overlap prevention."""

    def register(self, highlighter: Highlighter) -> None:
        """Add highlighter to chain.

        Args:
            highlighter: Must conform to Highlighter protocol

        Raises:
            ValueError: If name already registered
        """
        ...

    def unregister(self, name: str) -> None:
        """Remove highlighter by name.

        Args:
            name: Highlighter name to remove

        Raises:
            KeyError: If name not found
        """
        ...

    def apply_rich(self, text: str, theme: "Theme") -> str:
        """Apply all highlighters with overlap prevention.

        Processing Order:
        1. Collect all matches from all enabled highlighters
        2. Sort matches by (start position, highlighter priority)
        3. Process matches in order
        4. Skip matches that overlap with already-highlighted regions
        5. Build Rich markup output

        Args:
            text: Input text to highlight
            theme: Current theme for style lookups

        Returns:
            Rich markup string. Empty regions escaped with \\[
        """
        ...
```

---

## Theme Integration Contract

Highlighters access styles via theme:

```python
# Theme provides style lookups
class Theme:
    def get_style(self, key: str, fallback: ColorStyle | None = None) -> ColorStyle | None:
        """Get style by key from ui dictionary.

        Args:
            key: Style key, e.g., "hl_timestamp_date"
            fallback: Style to return if key not found

        Returns:
            ColorStyle if found, fallback otherwise
        """
        ...

# Highlighter uses theme
def find_matches(self, text: str, theme: Theme) -> list[Match]:
    style = theme.get_style("hl_duration_slow")
    if style:
        # Use theme-provided style
        return [Match(start=0, end=5, style="hl_duration_slow", text="100ms")]
    else:
        # Fallback to default
        return [Match(start=0, end=5, style="yellow", text="100ms")]
```

---

## Error Handling Contract

### Registration Errors

```python
# Duplicate name
registry.register(TimestampHighlighter())  # OK
registry.register(TimestampHighlighter())  # ValueError: "timestamp already registered"

# Invalid protocol
registry.register({"name": "bad"})  # TypeError: "does not implement Highlighter protocol"
```

### Pattern Errors

```python
# Invalid regex
CustomHighlighter(name="bad", pattern="[invalid", style="red")
# ValueError: "Invalid regex pattern: unterminated character class"

# Zero-length match
CustomHighlighter(name="bad", pattern=".*", style="red")
# ValueError: "Pattern matches zero-length strings"
```

### Match Errors

```python
# Out of bounds
Match(start=-1, end=5, style="red", text="x")
# ValueError: "start must be >= 0"

Match(start=10, end=5, style="red", text="x")
# ValueError: "start must be < end"
```

---

## Testing Contract

Each highlighter implementation must pass:

```python
def test_highlighter_protocol(highlighter: Highlighter):
    """Verify highlighter conforms to protocol."""
    # Has required properties
    assert isinstance(highlighter.name, str)
    assert len(highlighter.name) > 0
    assert isinstance(highlighter.priority, int)
    assert highlighter.priority > 0
    assert isinstance(highlighter.description, str)

    # find_matches returns valid matches
    matches = highlighter.find_matches("test input", theme)
    for match in matches:
        assert 0 <= match.start < match.end <= len("test input")
        assert isinstance(match.style, str)

    # apply returns FormattedText
    result = highlighter.apply("test input", theme)
    assert isinstance(result, FormattedText)

    # apply_rich returns string
    result = highlighter.apply_rich("test input", theme)
    assert isinstance(result, str)
```
