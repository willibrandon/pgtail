# Research: Semantic Log Highlighting

**Branch**: `023-semantic-highlighting` | **Date**: 2026-01-14

## 1. Aho-Corasick Library Selection

### Decision: pyahocorasick

### Rationale
- **Maturity**: Most established Python Aho-Corasick library, active since ~2010s
- **License**: BSD-3-Clause (compatible with pgtail's BSD/MIT codebase)
- **Distribution**: Pre-built wheels for macOS, Linux, Windows eliminate PyInstaller/Nuitka build friction
- **Performance**: O(n+m) complexity for multi-pattern matching vs O(n*k) for naive approach
- **Maintenance**: Active development (v2.3.0, December 2025), Python 3.9+ support
- **API**: Dict-like interface ideal for keyword→token_type mapping

### Alternatives Considered

| Library | Rejected Because |
|---------|-----------------|
| ahocorasick_rs | Apache-2.0 license adds legal complexity; newer with less ecosystem support |
| daachorse | Requires Rust compiler at install time; build complexity |
| ahocorapy | Pure Python performance insufficient for 10K lines/sec target |

### Implementation Pattern

```python
import ahocorasick

class KeywordMatcher:
    """Multi-keyword matcher using Aho-Corasick algorithm."""

    def __init__(self, keywords: dict[str, str]):
        """
        Args:
            keywords: Mapping of keyword (lowercase) to token/style type
        """
        self.automaton = ahocorasick.Automaton()
        self._lengths = {}
        for keyword, token_type in keywords.items():
            key = keyword.lower()
            self.automaton.add_word(key, (len(key), token_type))
            self._lengths[key] = len(key)
        self.automaton.make_automaton()

    def find_all(self, text: str) -> list[tuple[int, int, str]]:
        """Find all keyword matches.

        Returns:
            List of (start_pos, end_pos, token_type) tuples
        """
        results = []
        lower_text = text.lower()
        for end_pos, (length, token_type) in self.automaton.iter(lower_text):
            start_pos = end_pos - length + 1
            results.append((start_pos, end_pos + 1, token_type))
        return results
```

---

## 2. Overlap Prevention Strategy

### Decision: Chunk-based iteration with occupancy tracking

### Rationale
The spec (FR-003) requires highlighters to skip already-highlighted regions. Given:
- Multiple highlighters run in priority order (FR-002)
- Same text position must not be highlighted twice (edge case #3)
- Performance target of 10K lines/sec requires efficient tracking

### Implementation Pattern

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class HighlightChunk:
    """A segment of text with associated style."""
    start: int
    end: int
    style: str | None  # None = unhighlighted

class OccupancyTracker:
    """Tracks which regions have been highlighted."""

    def __init__(self, length: int):
        self._occupied = [False] * length

    def is_available(self, start: int, end: int) -> bool:
        """Check if region is fully unhighlighted."""
        return not any(self._occupied[start:end])

    def mark_occupied(self, start: int, end: int) -> None:
        """Mark region as highlighted."""
        for i in range(start, end):
            self._occupied[i] = True

    def available_ranges(self) -> list[tuple[int, int]]:
        """Return list of (start, end) for unhighlighted regions."""
        ranges = []
        start = None
        for i, occupied in enumerate(self._occupied):
            if not occupied and start is None:
                start = i
            elif occupied and start is not None:
                ranges.append((start, i))
                start = None
        if start is not None:
            ranges.append((start, len(self._occupied)))
        return ranges
```

### Alternative Considered: Interval tree
- Rejected because: More complex to implement, overkill for typical log line lengths (<10KB)
- Would only be beneficial for >100KB text with many overlapping patterns

---

## 3. Highlighter Protocol Design

### Decision: Protocol class with apply() and apply_rich() methods

### Rationale
- Matches existing pattern in sql_highlighter.py (FormattedText for prompt_toolkit, Rich markup for Textual)
- Protocol allows duck typing without inheritance hierarchy
- Priority field enables deterministic ordering

### Protocol Definition

```python
from typing import Protocol, runtime_checkable
from prompt_toolkit.formatted_text import FormattedText

@runtime_checkable
class Highlighter(Protocol):
    """Protocol for semantic highlighters."""

    @property
    def name(self) -> str:
        """Unique identifier for this highlighter."""
        ...

    @property
    def priority(self) -> int:
        """Lower number = higher priority (processed first)."""
        ...

    def apply(self, text: str, theme: "Theme") -> FormattedText:
        """Apply highlighting for prompt_toolkit (REPL mode)."""
        ...

    def apply_rich(self, text: str, theme: "Theme") -> str:
        """Apply highlighting for Rich/Textual (tail mode)."""
        ...
```

### Priority Ranges

| Range | Category | Examples |
|-------|----------|----------|
| 100-199 | Structural | Timestamp, PID, Context labels |
| 200-299 | Diagnostic | SQLSTATE, Error names |
| 300-399 | Performance | Duration, Memory, Statistics |
| 400-499 | Objects | Identifiers, Relations, Schemas |
| 500-599 | WAL | LSN, WAL segments, TXIDs |
| 600-699 | Connection | Host/port, IPs, Backend types |
| 700-799 | SQL | Keywords, Strings, Numbers, Params |
| 800-899 | Lock | Lock types, Wait info |
| 900-999 | Checkpoint | Checkpoint stats, Recovery |
| 1000+ | Misc/Custom | Booleans, NULL, OIDs, Paths, Custom |

---

## 4. HighlighterChain Compositor

### Decision: Single-pass iteration with occupancy tracking

### Rationale
- FR-002 requires priority-ordered processing
- FR-003 requires overlap prevention
- Single pass through text is more efficient than multiple passes

### Implementation Pattern

```python
class HighlighterChain:
    """Composes multiple highlighters with overlap prevention."""

    def __init__(self, highlighters: list[Highlighter]):
        # Sort by priority (lower = higher priority)
        self._highlighters = sorted(highlighters, key=lambda h: h.priority)

    def apply_rich(self, text: str, theme: "Theme") -> str:
        """Apply all highlighters with overlap prevention."""
        if not text or not self._highlighters:
            return text

        # Collect all matches from all highlighters
        matches: list[tuple[int, int, str, int]] = []  # start, end, style, priority
        for h in self._highlighters:
            for start, end, style in h.find_matches(text, theme):
                matches.append((start, end, style, h.priority))

        if not matches:
            return escape_brackets(text)

        # Sort by start position, then by priority
        matches.sort(key=lambda m: (m[0], m[3]))

        # Build output with overlap prevention
        tracker = OccupancyTracker(len(text))
        styled_matches = []

        for start, end, style, _ in matches:
            if tracker.is_available(start, end):
                tracker.mark_occupied(start, end)
                styled_matches.append((start, end, style))

        # Sort by position for output building
        styled_matches.sort(key=lambda m: m[0])

        # Build Rich markup output
        result = []
        pos = 0
        for start, end, style in styled_matches:
            if pos < start:
                result.append(escape_brackets(text[pos:start]))
            result.append(f"[{style}]{escape_brackets(text[start:end])}[/]")
            pos = end
        if pos < len(text):
            result.append(escape_brackets(text[pos:]))

        return "".join(result)
```

---

## 5. Theme Style Key Naming Convention

### Decision: Hierarchical dot notation with category prefix

### Rationale
- Consistent with existing sql_* keys
- Allows future expansion without key collision
- Self-documenting in theme files

### Key Format: `hl_{category}_{element}`

| Key | Usage |
|-----|-------|
| `hl_timestamp_date` | Date portion (YYYY-MM-DD) |
| `hl_timestamp_time` | Time portion (HH:MM:SS) |
| `hl_timestamp_ms` | Milliseconds |
| `hl_timestamp_tz` | Timezone |
| `hl_pid` | Process ID in brackets |
| `hl_context` | DETAIL:, HINT:, etc. |
| `hl_sqlstate_success` | 00xxx codes |
| `hl_sqlstate_warning` | 01xxx codes |
| `hl_sqlstate_error` | Other error codes |
| `hl_sqlstate_internal` | XXxxx codes |
| `hl_error_name` | unique_violation, etc. |
| `hl_duration_fast` | Below slow threshold |
| `hl_duration_slow` | slow ≤ x < very_slow |
| `hl_duration_very_slow` | very_slow ≤ x < critical |
| `hl_duration_critical` | Above critical threshold |
| `hl_memory_value` | Numeric value |
| `hl_memory_unit` | kB, MB, GB |
| `hl_identifier` | Double-quoted names |
| `hl_relation` | Table/index names |
| `hl_schema` | Schema-qualified names |
| `hl_lsn_segment` | LSN segment portion |
| `hl_lsn_offset` | LSN offset portion |
| `hl_wal_segment` | WAL filename |
| `hl_txid` | Transaction IDs |
| `hl_host` | Hostname/IP |
| `hl_port` | Port number |
| `hl_user` | Username |
| `hl_database` | Database name |
| `hl_ip` | IPv4/IPv6 addresses |
| `hl_backend` | Backend type names |
| `hl_param` | $1, $2 query params |
| `hl_lock_share` | Share-level locks |
| `hl_lock_exclusive` | Exclusive locks |
| `hl_lock_wait` | Lock wait info |
| `hl_checkpoint` | Checkpoint messages |
| `hl_recovery` | Recovery messages |
| `hl_bool_true` | on/true/yes |
| `hl_bool_false` | off/false/no |
| `hl_null` | NULL keyword |
| `hl_oid` | Object IDs |
| `hl_path` | File system paths |

### Migration: SQL Keys

Existing `sql_*` keys remain unchanged but become aliases:
- `sql_keyword` → used by SQL highlighter (priority 700)
- `sql_identifier` → maps to `hl_identifier` or remains separate
- `sql_string`, `sql_number`, `sql_operator`, `sql_comment`, `sql_function` → unchanged

---

## 6. Configuration Schema Extension

### Decision: Nested TOML structure under [highlighting]

### Rationale
- Consistent with existing config pattern (e.g., [slow], [display])
- Allows hierarchical organization without config.py restructuring
- Clear separation from other settings

### Schema

```toml
[highlighting]
enabled = true                 # Global toggle (FR-120)
max_length = 10240             # Depth limit in bytes (FR-121)

[highlighting.enabled_highlighters]
timestamp = true               # FR-122 - per-highlighter enable
pid = true
sqlstate = true
duration = true
# ... all 29 highlighters default to true

[highlighting.duration]
slow = 100                     # FR-123 - threshold in ms
very_slow = 500
critical = 5000

[[highlighting.custom]]        # FR-124 - custom patterns
name = "request_id"
pattern = "REQ-[0-9]{10}"
style = "yellow"
priority = 1050
```

### Config Dataclass

```python
@dataclass
class HighlightingSection:
    enabled: bool = True
    max_length: int = 10240

@dataclass
class HighlightingDurationSection:
    slow: int = 100
    very_slow: int = 500
    critical: int = 5000

@dataclass
class HighlightingEnabledHighlightersSection:
    timestamp: bool = True
    pid: bool = True
    # ... all 29 highlighters

@dataclass
class CustomHighlighter:
    name: str
    pattern: str
    style: str
    priority: int = 1050
```

---

## 7. Existing SQL Highlighter Migration

### Decision: Migrate sql_tokenizer.py and sql_highlighter.py into highlighters/sql.py

### Rationale
- FR-074 explicitly requires migration into new system
- SQL highlighting is the most complex highlighter (tokenization vs regex)
- Reuse existing tested tokenization logic

### Migration Steps

1. **Copy tokenization logic**: SQLTokenizer class moves to highlighters/sql.py
2. **Adapt to Highlighter protocol**: Implement apply() and apply_rich() methods
3. **Integrate with HighlighterChain**: Register SQL highlighters at priorities 700-799
4. **Preserve test coverage**: Migrate test_sql_highlighter.py tests
5. **Remove legacy modules**: Delete sql_highlighter.py, sql_tokenizer.py, sql_detector.py
6. **Update imports**: Grep for imports and update across codebase

### SQL Highlighter Breakdown

| Priority | Highlighter | Pattern Type |
|----------|-------------|--------------|
| 700 | SQLKeywordHighlighter | Aho-Corasick (120+ keywords) |
| 710 | SQLStringHighlighter | Regex (single/double/dollar quotes) |
| 720 | SQLNumberHighlighter | Regex (integers, decimals, hex, scientific) |
| 730 | SQLParamHighlighter | Regex ($1, $2, etc.) |
| 740 | SQLOperatorHighlighter | Character set |

**Note**: SQL detection (when to apply SQL highlighting) moves into HighlighterChain context detection. Messages with "statement:", "execute:", etc. prefixes trigger SQL-specific highlighters.

---

## 8. Performance Optimization Strategies

### Decision: Multi-level caching with lazy initialization

### Rationale
- FR-162 requires 10,000 lines/sec
- Regex compilation is expensive; compile once at instantiation
- Aho-Corasick automaton builds once, searches in O(n)

### Strategies

1. **Pre-compiled Patterns**: All regex patterns compiled at module load
2. **Singleton Highlighters**: One instance per highlighter type
3. **Lazy Automaton Building**: Build Aho-Corasick on first use
4. **Depth Limiting**: Stop processing after max_length (FR-006)
5. **Early Exit**: Return unchanged if no patterns could match

### Benchmark Target

| Operation | Target |
|-----------|--------|
| Single line highlight | <100μs |
| 10,000 lines batch | <1s |
| Complex SQL (10KB) | <10ms |
| Aho-Corasick build | <100ms (amortized over session) |

---

## 9. Export Integration

### Decision: Strip by default, preserve with --highlighted flag

### Rationale
- FR-152, FR-153, FR-154 define export behavior
- Most export use cases want clean text
- Power users may want highlighted output for specific tools

### Implementation

```python
def strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags from text."""
    import re
    return re.sub(r'\[/?[^\]]*\]', '', text)

def format_text_entry(entry: LogEntry, highlighted: bool = False) -> str:
    """Format entry for text export."""
    if highlighted:
        return format_entry_compact(entry)  # With markup
    return strip_rich_markup(format_entry_compact(entry))
```

---

## 10. Edge Case Handling

### Rich Markup Escaping (Edge Case #7)

When log content contains Rich-like brackets (e.g., `[bold]`), they must be escaped:

```python
def escape_brackets(text: str) -> str:
    """Escape brackets that could be interpreted as Rich markup."""
    return text.replace("[", "\\[")
```

### Zero-Length Regex (Edge Case #2)

Reject patterns that match zero-length strings:

```python
def validate_pattern(pattern: str) -> bool:
    """Reject patterns that could match zero-length strings."""
    import re
    try:
        compiled = re.compile(pattern)
        if compiled.match(""):
            return False  # Would match empty string
        return True
    except re.error:
        return False
```

### Long Line Handling (Edge Case #1)

```python
def apply_with_depth_limit(text: str, max_length: int = 10240) -> str:
    """Apply highlighting with depth limit."""
    if len(text) <= max_length:
        return highlight(text)

    # Highlight truncated portion, append rest unchanged
    highlighted_part = highlight(text[:max_length])
    plain_part = escape_brackets(text[max_length:])
    return highlighted_part + plain_part
```

---

## Summary

| Area | Decision | Key Rationale |
|------|----------|---------------|
| Aho-Corasick | pyahocorasick | BSD-3 license, pre-built wheels, mature |
| Overlap Prevention | Occupancy tracking | Simple, efficient for <10KB text |
| Protocol | apply() + apply_rich() | Matches existing dual-backend pattern |
| Theme Keys | hl_{category}_{element} | Hierarchical, self-documenting |
| Config | [highlighting] section | Consistent with existing patterns |
| SQL Migration | highlighters/sql.py | Reuse tokenization, integrate with chain |
| Performance | Pre-compile + singleton + depth limit | 10K lines/sec target |
| Export | Strip by default | Clean text for external tools |
