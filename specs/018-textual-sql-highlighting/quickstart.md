# Quickstart: SQL Syntax Highlighting in Textual Tail Mode

**Date**: 2025-12-31
**Feature**: 018-textual-sql-highlighting

## Implementation Summary

This guide provides step-by-step instructions for implementing SQL syntax highlighting in Textual tail mode. Total estimated implementation time: ~2 hours.

---

## Prerequisites

Before starting:

1. **Verify branch**: Ensure you're on `018-textual-sql-highlighting`
2. **Review existing code**:
   - `pgtail_py/sql_tokenizer.py` - SQL tokenization (no changes)
   - `pgtail_py/sql_detector.py` - SQL detection (no changes)
   - `pgtail_py/sql_highlighter.py` - Current prompt_toolkit version
   - `pgtail_py/tail_rich.py` - Entry formatting (needs modification)
   - `pgtail_py/theme.py` - Theme system (reference only)
   - `pgtail_py/themes/dark.py` - Example SQL color definitions

---

## Step 1: Add Rich Highlighter to sql_highlighter.py

Add these functions after the existing `highlight_sql()` function:

```python
# pgtail_py/sql_highlighter.py

from pgtail_py.theme import ColorStyle, Theme, ThemeManager

# Token type to theme key mapping for Rich output
TOKEN_TYPE_TO_THEME_KEY: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "sql_keyword",
    SQLTokenType.IDENTIFIER: "sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "sql_identifier",
    SQLTokenType.STRING: "sql_string",
    SQLTokenType.NUMBER: "sql_number",
    SQLTokenType.OPERATOR: "sql_operator",
    SQLTokenType.COMMENT: "sql_comment",
    SQLTokenType.FUNCTION: "sql_function",
    SQLTokenType.PUNCTUATION: "",
    SQLTokenType.WHITESPACE: "",
    SQLTokenType.UNKNOWN: "",
}

# Module-level theme manager for color lookups
_theme_manager: ThemeManager | None = None


def _get_theme_manager() -> ThemeManager:
    """Get or create the module-level ThemeManager."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def _color_style_to_rich_markup(style: ColorStyle) -> str:
    """Convert ColorStyle to Rich markup tag content.

    Args:
        style: ColorStyle with fg, bg, bold, dim, etc.

    Returns:
        Rich markup tag content (e.g., "bold blue").
        Empty string if no styling defined.
    """
    parts: list[str] = []

    # Add modifiers
    if style.bold:
        parts.append("bold")
    if style.dim:
        parts.append("dim")
    if style.italic:
        parts.append("italic")
    if style.underline:
        parts.append("underline")

    # Add foreground color
    if style.fg:
        # Strip "ansi" prefix for Rich compatibility
        fg = style.fg
        if fg.startswith("ansibright"):
            fg = "bright_" + fg[10:]  # ansibrightred → bright_red
        elif fg.startswith("ansi"):
            fg = fg[4:]  # ansired → red
        parts.append(fg)

    # Add background color
    if style.bg:
        bg = style.bg
        if bg.startswith("ansibright"):
            bg = "bright_" + bg[10:]
        elif bg.startswith("ansi"):
            bg = bg[4:]
        parts.append(f"on {bg}")

    return " ".join(parts)


def highlight_sql_rich(sql: str, theme: Theme | None = None) -> str:
    """Convert SQL text to Rich console markup string.

    Tokenizes SQL and wraps each token in Rich markup tags using
    colors from the active theme. Brackets in SQL text are escaped
    to prevent Rich parsing errors.

    Args:
        sql: SQL text to highlight.
        theme: Theme for color lookup. If None, uses global ThemeManager.

    Returns:
        Rich markup string with styled tokens.
        If NO_COLOR is set, returns SQL with only bracket escaping.

    Example:
        >>> highlight_sql_rich("SELECT id FROM users")
        "[bold blue]SELECT[/] [cyan]id[/] [bold blue]FROM[/] [cyan]users[/]"
    """
    # Respect NO_COLOR environment variable
    if is_color_disabled():
        return sql.replace("[", "\\[")

    # Get theme for color lookup
    if theme is None:
        theme = _get_theme_manager().current_theme

    # Tokenize SQL
    tokens = SQLTokenizer().tokenize(sql)

    # Build Rich markup string
    parts: list[str] = []
    for token in tokens:
        # Escape brackets in token text
        escaped_text = token.text.replace("[", "\\[")

        # Get theme key for this token type
        theme_key = TOKEN_TYPE_TO_THEME_KEY.get(token.type, "")

        if theme_key and theme:
            # Get color style from theme
            style = theme.get_ui_style(theme_key)
            markup = _color_style_to_rich_markup(style)

            if markup:
                parts.append(f"[{markup}]{escaped_text}[/]")
            else:
                parts.append(escaped_text)
        else:
            parts.append(escaped_text)

    return "".join(parts)
```

---

## Step 2: Integrate into tail_rich.py

Modify `format_entry_compact()` to detect and highlight SQL:

```python
# pgtail_py/tail_rich.py

from pgtail_py.sql_detector import detect_sql_content
from pgtail_py.sql_highlighter import highlight_sql_rich


def format_entry_compact(entry: LogEntry) -> str:
    """Convert LogEntry to Rich markup string for Textual Log widget.

    Formats a log entry as a single-line Rich markup string suitable for
    the Textual Log widget's write_line() method. Uses a compact
    format: timestamp [pid] LEVEL sql_state: message

    SQL statements detected in log messages are syntax highlighted.

    Args:
        entry: Parsed log entry to format.

    Returns:
        Rich markup string representation of the entry.
    """
    parts: list[str] = []

    # Timestamp (dim)
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(f"[dim]{ts_str}[/dim]")

    # PID (dim) - escape brackets
    if entry.pid:
        parts.append(f"[dim]\\[{entry.pid}][/dim]")

    # Level name with color (padded for alignment)
    level_style = LEVEL_MARKUP.get(entry.level, "")
    level_name = entry.level.name.ljust(7)
    if level_style:
        parts.append(f"[{level_style}]{level_name}[/]")
    else:
        parts.append(level_name)

    # SQL state code (cyan) and message
    if entry.sql_state:
        parts.append(f"[cyan]{entry.sql_state}[/]:")
    else:
        parts.append(":")

    # Message - detect and highlight SQL
    detection = detect_sql_content(entry.message)
    if detection:
        # SQL detected: escape prefix, highlight SQL, escape suffix
        prefix = detection.prefix.replace("[", "\\[")
        highlighted_sql = highlight_sql_rich(detection.sql)
        suffix = detection.suffix.replace("[", "\\[")
        parts.append(f"{prefix}{highlighted_sql}{suffix}")
    else:
        # No SQL: just escape brackets
        safe_message = entry.message.replace("[", "\\[")
        parts.append(safe_message)

    return " ".join(parts)
```

---

## Step 3: Add Unit Tests for Rich Output

Create or extend `tests/test_sql_highlighter.py`:

```python
# tests/test_sql_highlighter.py

import os
from unittest.mock import patch

import pytest

from pgtail_py.sql_highlighter import (
    _color_style_to_rich_markup,
    highlight_sql_rich,
)
from pgtail_py.theme import ColorStyle, Theme


class TestColorStyleToRichMarkup:
    """Tests for _color_style_to_rich_markup()."""

    def test_empty_style_returns_empty_string(self) -> None:
        style = ColorStyle()
        assert _color_style_to_rich_markup(style) == ""

    def test_fg_only(self) -> None:
        style = ColorStyle(fg="blue")
        assert _color_style_to_rich_markup(style) == "blue"

    def test_fg_with_bold(self) -> None:
        style = ColorStyle(fg="blue", bold=True)
        assert _color_style_to_rich_markup(style) == "bold blue"

    def test_ansi_color_stripped(self) -> None:
        style = ColorStyle(fg="ansicyan")
        assert _color_style_to_rich_markup(style) == "cyan"

    def test_ansibright_color_converted(self) -> None:
        style = ColorStyle(fg="ansibrightred")
        assert _color_style_to_rich_markup(style) == "bright_red"

    def test_hex_color_passed_through(self) -> None:
        style = ColorStyle(fg="#268bd2")
        assert _color_style_to_rich_markup(style) == "#268bd2"

    def test_background_color(self) -> None:
        style = ColorStyle(bg="yellow")
        assert _color_style_to_rich_markup(style) == "on yellow"

    def test_dim_modifier(self) -> None:
        style = ColorStyle(dim=True)
        assert _color_style_to_rich_markup(style) == "dim"


class TestHighlightSqlRich:
    """Tests for highlight_sql_rich()."""

    def test_keywords_highlighted(self) -> None:
        result = highlight_sql_rich("SELECT id FROM users")
        assert "[" in result  # Has markup tags
        assert "SELECT" in result
        assert "FROM" in result

    def test_brackets_escaped(self) -> None:
        result = highlight_sql_rich("SELECT arr[1] FROM table")
        assert "\\[1]" in result

    def test_empty_sql_returns_empty(self) -> None:
        result = highlight_sql_rich("")
        assert result == ""

    def test_no_color_respected(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            # Clear cached color check
            result = highlight_sql_rich("SELECT 1")
            # Should have escaped brackets but no markup tags
            assert "[/" not in result or "\\[" in result

    def test_string_literals_styled(self) -> None:
        result = highlight_sql_rich("WHERE name = 'John'")
        assert "'John'" in result

    def test_numbers_styled(self) -> None:
        result = highlight_sql_rich("WHERE count > 42")
        assert "42" in result

    def test_comments_styled(self) -> None:
        result = highlight_sql_rich("SELECT 1 -- comment")
        assert "-- comment" in result
```

---

## Step 4: Add Integration Tests for tail_rich.py

Extend `tests/test_tail_rich.py`:

```python
# tests/test_tail_rich.py

from datetime import datetime, timezone

from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry
from pgtail_py.tail_rich import format_entry_compact


class TestFormatEntryCompactSqlHighlighting:
    """Tests for SQL highlighting in format_entry_compact()."""

    def test_sql_statement_highlighted(self) -> None:
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: statement: SELECT * FROM users",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT * FROM users",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        # Should have Rich markup tags
        assert "[" in result
        # Should contain the SQL keywords
        assert "SELECT" in result
        assert "FROM" in result

    def test_no_sql_message_escaped(self) -> None:
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: connection received",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.LOG,
            message="connection received",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        assert "connection received" in result

    def test_sql_with_brackets_escaped(self) -> None:
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: statement: SELECT arr[1] FROM t",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT arr[1] FROM t",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        # Bracket should be escaped
        assert "\\[1]" in result

    def test_execute_statement_detected(self) -> None:
        entry = LogEntry(
            raw="LOG: execute S_1: SELECT id FROM orders WHERE status = $1",
            timestamp=None,
            pid=None,
            level=LogLevel.LOG,
            message="execute S_1: SELECT id FROM orders WHERE status = $1",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        assert "SELECT" in result
        assert "FROM" in result
```

---

## Step 5: Run Tests

```bash
# Run all tests
make test

# Run specific test files
uv run pytest tests/test_sql_highlighter.py -v
uv run pytest tests/test_tail_rich.py -v

# Run with coverage
uv run pytest tests/test_sql_highlighter.py tests/test_tail_rich.py --cov=pgtail_py --cov-report=term-missing
```

---

## Step 6: Manual Testing

1. Start PostgreSQL with statement logging:
   ```sql
   ALTER SYSTEM SET log_statement = 'all';
   SELECT pg_reload_conf();
   ```

2. Run pgtail in tail mode:
   ```bash
   python -m pgtail_py
   > list
   > tail 0
   ```

3. Execute SQL queries and verify:
   - Keywords (SELECT, FROM, WHERE) appear in blue/bold
   - Identifiers (table/column names) appear in cyan
   - String literals appear in green
   - Numbers appear in magenta

4. Test theme switching:
   ```
   tail> theme monokai
   # Verify SQL colors change
   tail> theme dark
   ```

5. Test copy functionality:
   - Press `v` to enter visual mode
   - Select a SQL statement
   - Press `y` to yank
   - Paste in editor - verify no Rich markup tags

---

## Verification Checklist

Before marking complete, verify:

- [ ] All tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] SQL keywords highlighted in tail mode
- [ ] String literals visually distinct from identifiers
- [ ] Numbers and operators colored appropriately
- [ ] Comments appear dim/gray
- [ ] Brackets in SQL (e.g., `arr[1]`) display correctly
- [ ] Copy via visual mode produces clean SQL
- [ ] NO_COLOR=1 disables all SQL highlighting
- [ ] Theme switching updates SQL colors immediately
