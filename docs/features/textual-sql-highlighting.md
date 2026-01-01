# Feature: SQL Syntax Highlighting in Textual Tail Mode

## Status

**Current State: NOT IMPLEMENTED**

SQL syntax highlighting exists and works correctly in the legacy prompt_toolkit REPL mode, but it is **not integrated** into the Textual-based tail mode (`tail` command).

## Problem

The Textual tail mode displays log entries with colored log levels and timestamps, but SQL statements within log messages appear as plain monochrome text. This makes it difficult to:

- Quickly identify query structure (SELECT, JOIN, WHERE clauses)
- Spot table and column names in busy log output
- Find string literals and parameter values
- Distinguish SQL from surrounding log context

The original SQL highlighting feature (see `sql-syntax-highlighting.md`) was implemented for prompt_toolkit mode but not ported to Textual.

## Root Cause Analysis

### Existing Code (Working)

| Module | Purpose | Output Format |
|--------|---------|---------------|
| `sql_tokenizer.py` | Tokenizes SQL into typed tokens | `list[SQLToken]` |
| `sql_highlighter.py` | Converts tokens to styled output | `FormattedText` (prompt_toolkit) |
| `sql_detector.py` | Detects SQL in log messages | `SQLDetectionResult` |
| `display.py` | Integrates highlighting | `FormattedText` (prompt_toolkit) |

### Gap

The `sql_highlighter.py` returns `FormattedText`, which is a prompt_toolkit type incompatible with Textual/Rich:

```python
# prompt_toolkit FormattedText (current)
[("class:sql_keyword", "SELECT"), ("", " "), ("class:sql_identifier", "id")]

# Rich markup string (needed for Textual)
"[bold blue]SELECT[/] [cyan]id[/]"
```

### Integration Point

`tail_rich.py:format_entry_compact()` currently escapes brackets but does NOT apply SQL highlighting:

```python
# Current (line 157-158)
safe_message = entry.message.replace("[", "\\[")
parts.append(safe_message)
```

## Proposed Solution

### 1. Create Rich-Compatible SQL Highlighter

Add a new function to `sql_highlighter.py` (or new module `sql_highlighter_rich.py`):

```python
def highlight_sql_rich(sql: str) -> str:
    """Convert SQL to Rich markup string for Textual widgets.

    Args:
        sql: SQL text to highlight.

    Returns:
        Rich markup string with styled tokens.
    """
```

### 2. Token-to-Rich-Style Mapping

| Token Type | prompt_toolkit Class | Rich Markup |
|------------|---------------------|-------------|
| KEYWORD | `class:sql_keyword` | `[bold blue]...[/]` |
| IDENTIFIER | `class:sql_identifier` | `[cyan]...[/]` |
| STRING | `class:sql_string` | `[green]...[/]` |
| NUMBER | `class:sql_number` | `[magenta]...[/]` |
| OPERATOR | `class:sql_operator` | `[yellow]...[/]` |
| COMMENT | `class:sql_comment` | `[dim]...[/]` |
| FUNCTION | `class:sql_function` | `[blue]...[/]` |

### 3. Integrate into tail_rich.py

```python
def format_entry_compact(entry: LogEntry) -> str:
    # ... existing code ...

    # Message - detect and highlight SQL
    from pgtail_py.sql_detector import detect_sql_content
    from pgtail_py.sql_highlighter import highlight_sql_rich

    detection = detect_sql_content(entry.message)
    if detection:
        # Escape prefix, highlight SQL, escape suffix
        prefix = detection.prefix.replace("[", "\\[")
        sql_highlighted = highlight_sql_rich(detection.sql)
        suffix = detection.suffix.replace("[", "\\[")
        parts.append(f"{prefix}{sql_highlighted}{suffix}")
    else:
        safe_message = entry.message.replace("[", "\\[")
        parts.append(safe_message)

    return " ".join(parts)
```

## SQL Detection Patterns

The existing `sql_detector.py` correctly detects SQL in these PostgreSQL log patterns:

| Pattern | Example |
|---------|---------|
| Statement logging | `LOG: statement: SELECT * FROM users` |
| Prepared execute | `LOG: execute S_1: SELECT id FROM orders WHERE status = $1` |
| Prepared parse | `LOG: parse P_1: SELECT * FROM products` |
| Parameter binding | `LOG: bind P_1: $1 = 'active'` |
| Duration + statement | `LOG: duration: 12.345 ms statement: SELECT COUNT(*) FROM events` |
| Error detail | `DETAIL: Key (id)=(42) already exists` |

## Edge Cases

### Bracket Escaping

SQL may contain brackets that conflict with Rich markup:

```sql
SELECT arr[1], jsonb_col->'key'
```

Solution: The highlighter must escape unrelated brackets within SQL tokens:

```python
# In highlight_sql_rich()
token_text = token.text.replace("[", "\\[")
```

### Malformed SQL

Partial or malformed SQL should degrade gracefully:

- Recognized tokens: highlighted
- Unrecognized text: displayed plain (no style)
- Never throw exceptions from highlighting

### NO_COLOR Compliance

When `NO_COLOR=1` environment variable is set:

```python
def highlight_sql_rich(sql: str) -> str:
    if is_color_disabled():
        return sql.replace("[", "\\[")  # Just escape brackets
    # ... normal highlighting ...
```

## Success Criteria

1. SQL keywords highlighted in tail mode output (SELECT, FROM, WHERE, JOIN, etc.)
2. String literals visually distinct from identifiers
3. Numbers and operators have appropriate colors
4. Highlighting works in both FOLLOW and PAUSED modes
5. Visual mode selection correctly strips markup before copying
6. No performance degradation with high-volume log output
7. Respects NO_COLOR environment variable
8. Theme colors consistent with prompt_toolkit mode appearance

## Testing Plan

### Unit Tests

```python
class TestSQLHighlighterRich:
    def test_keywords_highlighted(self):
        result = highlight_sql_rich("SELECT id FROM users")
        assert "[bold blue]SELECT[/]" in result
        assert "[bold blue]FROM[/]" in result

    def test_strings_highlighted(self):
        result = highlight_sql_rich("WHERE name = 'John'")
        assert "[green]'John'[/]" in result

    def test_brackets_escaped(self):
        result = highlight_sql_rich("SELECT arr[1]")
        assert "\\[1]" in result  # Bracket escaped

    def test_no_color_respected(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = highlight_sql_rich("SELECT 1")
            assert "[" not in result or result.count("\\[") == result.count("[")
```

### Integration Tests

```python
async def test_tail_mode_sql_highlighting():
    """SQL in log entries is highlighted in tail mode."""
    app = TailApp(...)
    async with app.run_test() as pilot:
        # Write log entry with SQL
        app.tail_log.write_line(
            "[dim]10:00:00[/] [green]LOG[/]: statement: SELECT * FROM users"
        )
        # Verify SQL keywords are styled (check rendered output)
```

## Files to Modify

| File | Changes |
|------|---------|
| `pgtail_py/sql_highlighter.py` | Add `highlight_sql_rich()` function |
| `pgtail_py/tail_rich.py` | Integrate SQL detection and highlighting |
| `tests/test_sql_highlighter.py` | Add tests for Rich output |
| `tests/test_tail_rich.py` | Add integration tests |

## Dependencies

- Existing: `sql_tokenizer.py`, `sql_detector.py` (no changes needed)
- Existing: `utils.py` for `is_color_disabled()`
- Rich library (already a Textual dependency)

## Related Documents

- `sql-syntax-highlighting.md` - Original feature specification
- `log-entry-selection.md` - Visual mode must strip SQL markup before copying
