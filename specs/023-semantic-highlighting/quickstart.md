# Quickstart: Semantic Log Highlighting Development

**Branch**: `023-semantic-highlighting` | **Date**: 2026-01-14

## Prerequisites

```bash
# Ensure you're on the feature branch
git checkout 023-semantic-highlighting

# Install dependencies including new pyahocorasick
pip install -e ".[dev]"
pip install pyahocorasick

# Verify installation
python -c "import ahocorasick; print('pyahocorasick ready')"
```

---

## Implementation Order

### Phase 1: Core Infrastructure

1. **highlighter.py** - Protocol and base classes
2. **OccupancyTracker** - Overlap prevention
3. **HighlighterChain** - Compositor

### Phase 2: Built-in Highlighters (by priority)

1. **structural.py** - Timestamp, PID, Context (priorities 100-199)
2. **diagnostic.py** - SQLSTATE, Error names (priorities 200-299)
3. **performance.py** - Duration, Memory, Stats (priorities 300-399)
4. **objects.py** - Identifiers, Relations, Schemas (priorities 400-499)
5. **wal.py** - LSN, WAL segments, TXIDs (priorities 500-599)
6. **connection.py** - Host/port, IPs, Backends (priorities 600-699)
7. **sql.py** - Migrate existing SQL highlighting (priorities 700-799)
8. **lock.py** - Lock types, Wait info (priorities 800-899)
9. **checkpoint.py** - Checkpoint, Recovery (priorities 900-999)
10. **misc.py** - Booleans, NULL, OIDs, Paths (priorities 1000+)

### Phase 3: Integration

1. **highlighter_registry.py** - Registration and enable/disable
2. **highlighting_config.py** - Configuration management
3. **cli_highlight.py** - Command handlers
4. **theme.py modifications** - Add get_style() and hl_* keys
5. **themes/ modifications** - Add colors to all 6 themes
6. **config.py modifications** - Add [highlighting] section
7. **tail_rich.py integration** - Use HighlighterChain
8. **display.py integration** - Use HighlighterChain
9. **export.py modifications** - Strip/preserve markup
10. **commands.py modifications** - Add autocomplete

### Phase 4: Migration & Cleanup

1. Remove sql_highlighter.py
2. Remove sql_tokenizer.py
3. Remove sql_detector.py
4. Update all imports across codebase

---

## Quick Reference: Creating a Highlighter

### Simple Regex Highlighter

```python
# pgtail_py/highlighters/misc.py

import re
from dataclasses import dataclass
from ..highlighter import Highlighter, Match, RegexHighlighter

class BooleanHighlighter(RegexHighlighter):
    """Highlights boolean values (on/off, true/false, yes/no)."""

    def __init__(self):
        super().__init__(
            name="boolean",
            priority=1000,
            pattern=r"\b(on|off|true|false|yes|no)\b",
            style="hl_bool_true"  # Will differentiate in find_matches
        )

    @property
    def description(self) -> str:
        return "Boolean values (on/off, true/false, yes/no)"

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        matches = []
        for m in self._pattern.finditer(text, re.IGNORECASE):
            value = m.group().lower()
            style = "hl_bool_true" if value in ("on", "true", "yes") else "hl_bool_false"
            matches.append(Match(
                start=m.start(),
                end=m.end(),
                style=style,
                text=m.group()
            ))
        return matches
```

### Grouped Regex Highlighter

```python
# pgtail_py/highlighters/structural.py

class TimestampHighlighter(GroupedRegexHighlighter):
    """Highlights timestamps with distinct styling for each component."""

    # Pattern: 2024-01-15 14:30:45.123 UTC
    PATTERN = r"""
        (?P<date>\d{4}-\d{2}-\d{2})
        [ T]
        (?P<time>\d{2}:\d{2}:\d{2})
        (?:\.(?P<ms>\d{3,6}))?
        (?:[ ]?(?P<tz>[A-Z]{2,4}|[+-]\d{2}:?\d{2}))?
    """

    GROUP_STYLES = {
        "date": "hl_timestamp_date",
        "time": "hl_timestamp_time",
        "ms": "hl_timestamp_ms",
        "tz": "hl_timestamp_tz",
    }

    def __init__(self):
        super().__init__(
            name="timestamp",
            priority=100,
            pattern=self.PATTERN,
            group_styles=self.GROUP_STYLES
        )

    @property
    def description(self) -> str:
        return "Timestamps with date, time, milliseconds, timezone"
```

### Keyword Highlighter (Aho-Corasick)

```python
# pgtail_py/highlighters/lock.py

import ahocorasick
from ..highlighter import Highlighter, Match

class LockTypeHighlighter:
    """Highlights lock type names with severity-based coloring."""

    SHARE_LOCKS = {
        "AccessShareLock": "hl_lock_share",
        "RowShareLock": "hl_lock_share",
        "ShareLock": "hl_lock_share",
        "ShareRowExclusiveLock": "hl_lock_share",
    }

    EXCLUSIVE_LOCKS = {
        "RowExclusiveLock": "hl_lock_exclusive",
        "ExclusiveLock": "hl_lock_exclusive",
        "AccessExclusiveLock": "hl_lock_exclusive",
    }

    def __init__(self):
        self._name = "lock_type"
        self._priority = 800
        self._automaton = ahocorasick.Automaton()

        all_locks = {**self.SHARE_LOCKS, **self.EXCLUSIVE_LOCKS}
        for lock_name, style in all_locks.items():
            self._automaton.add_word(lock_name, (len(lock_name), style))

        self._automaton.make_automaton()

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def description(self) -> str:
        return "Lock type names (share vs exclusive)"

    def find_matches(self, text: str, theme: "Theme") -> list[Match]:
        matches = []
        for end_pos, (length, style) in self._automaton.iter(text):
            start = end_pos - length + 1
            matches.append(Match(
                start=start,
                end=end_pos + 1,
                style=style,
                text=text[start:end_pos + 1]
            ))
        return matches
```

---

## Quick Reference: Theme Style Keys

Add to each theme file (dark.py, light.py, etc.):

```python
# In theme UI section
"hl_timestamp_date": ColorStyle(fg="gray"),
"hl_timestamp_time": ColorStyle(fg="gray"),
"hl_timestamp_ms": ColorStyle(fg="gray", dim=True),
"hl_timestamp_tz": ColorStyle(fg="gray", dim=True),
"hl_pid": ColorStyle(fg="cyan"),
"hl_context": ColorStyle(fg="yellow", bold=True),
"hl_sqlstate_success": ColorStyle(fg="green"),
"hl_sqlstate_warning": ColorStyle(fg="yellow"),
"hl_sqlstate_error": ColorStyle(fg="red"),
"hl_sqlstate_internal": ColorStyle(fg="red", bold=True),
"hl_error_name": ColorStyle(fg="red"),
"hl_duration_fast": ColorStyle(fg="green"),
"hl_duration_slow": ColorStyle(fg="yellow"),
"hl_duration_very_slow": ColorStyle(fg="ansibrightyellow", bold=True),
"hl_duration_critical": ColorStyle(fg="red", bold=True),
"hl_memory_value": ColorStyle(fg="magenta"),
"hl_memory_unit": ColorStyle(fg="magenta", dim=True),
"hl_identifier": ColorStyle(fg="cyan"),
"hl_relation": ColorStyle(fg="cyan", bold=True),
"hl_schema": ColorStyle(fg="cyan"),
"hl_lsn_segment": ColorStyle(fg="blue"),
"hl_lsn_offset": ColorStyle(fg="blue", dim=True),
"hl_wal_segment": ColorStyle(fg="blue"),
"hl_txid": ColorStyle(fg="magenta"),
"hl_host": ColorStyle(fg="green"),
"hl_port": ColorStyle(fg="green", dim=True),
"hl_user": ColorStyle(fg="green"),
"hl_database": ColorStyle(fg="green", bold=True),
"hl_ip": ColorStyle(fg="green"),
"hl_backend": ColorStyle(fg="cyan"),
"hl_param": ColorStyle(fg="yellow"),
"hl_lock_share": ColorStyle(fg="yellow"),
"hl_lock_exclusive": ColorStyle(fg="red"),
"hl_lock_wait": ColorStyle(fg="ansibrightyellow"),
"hl_checkpoint": ColorStyle(fg="blue"),
"hl_recovery": ColorStyle(fg="green"),
"hl_bool_true": ColorStyle(fg="green"),
"hl_bool_false": ColorStyle(fg="red"),
"hl_null": ColorStyle(fg="gray", italic=True),
"hl_oid": ColorStyle(fg="magenta"),
"hl_path": ColorStyle(fg="cyan"),
```

---

## Quick Reference: Configuration

Add to `config.py`:

```python
@dataclass
class HighlightingSection:
    """Highlighting configuration."""
    enabled: bool = True
    max_length: int = 10240

@dataclass
class HighlightingDurationSection:
    """Duration threshold configuration."""
    slow: int = 100
    very_slow: int = 500
    critical: int = 5000

@dataclass
class HighlightingEnabledHighlightersSection:
    """Per-highlighter enable/disable."""
    timestamp: bool = True
    pid: bool = True
    sqlstate: bool = True
    duration: bool = True
    # ... all 29 highlighters
```

---

## Testing

### Run All Highlighting Tests

```bash
make test TESTS="tests/test_highlighter*.py tests/test_highlighting*.py"
```

### Run Specific Category Tests

```bash
pytest tests/test_highlighters_structural.py -v
pytest tests/test_highlighters_sql.py -v
```

### Performance Benchmark

```bash
pytest tests/test_highlighting_integration.py::test_throughput_10k_lines -v
```

---

## Common Patterns

### Pattern: Check Highlighting Disabled

```python
def apply_rich(self, text: str, theme: "Theme") -> str:
    if is_color_disabled():
        return escape_brackets(text)
    # ... highlighting logic
```

### Pattern: Theme Style Lookup with Fallback

```python
def get_style_markup(theme: "Theme", key: str, fallback: str = "") -> str:
    style = theme.get_style(key)
    if style:
        return _color_style_to_rich_markup(style)
    return fallback
```

### Pattern: Early Exit for No Matches

```python
def find_matches(self, text: str, theme: "Theme") -> list[Match]:
    if not text or not self._could_match(text):
        return []
    # ... expensive matching logic
```

### Pattern: Depth Limiting

```python
def apply_rich(self, text: str, theme: "Theme", max_length: int = 10240) -> str:
    if len(text) <= max_length:
        return self._highlight(text, theme)

    # Highlight truncated portion
    highlighted = self._highlight(text[:max_length], theme)
    plain = escape_brackets(text[max_length:])
    return highlighted + plain
```

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger("pgtail_py.highlighter").setLevel(logging.DEBUG)
```

### Inspect Match Results

```python
from pgtail_py.highlighter_registry import get_registry

registry = get_registry()
chain = registry.create_chain(config)

for h in chain.highlighters:
    matches = h.find_matches("test log line", theme)
    print(f"{h.name}: {len(matches)} matches")
    for m in matches:
        print(f"  [{m.start}:{m.end}] '{m.text}' -> {m.style}")
```

### Profile Highlighting Performance

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

for _ in range(1000):
    chain.apply_rich(test_line, theme)

profiler.disable()
stats = pstats.Stats(profiler).sort_stats("cumulative")
stats.print_stats(20)
```
