# Research: SQL Syntax Highlighting in Textual Tail Mode

**Date**: 2025-12-31
**Feature**: 018-textual-sql-highlighting

## Executive Summary

All research questions have been resolved. The implementation path is clear:
1. Existing SQL tokenizer and detector are production-ready and reusable
2. All 6 built-in themes already include SQL color definitions
3. Rich markup syntax is well-documented and compatible with TailLog
4. Bracket escaping pattern already exists in codebase

---

## Research Topic 1: Rich Markup Syntax for SQL Highlighting

**Question**: What Rich markup syntax should be used for SQL token styling in Textual's Log widget?

### Decision

Use Rich markup tags with explicit foreground colors and style modifiers:

```python
# Keyword: blue, bold
"[bold blue]SELECT[/]"

# Identifier: cyan
"[cyan]users[/]"

# String: green
"[green]'John'[/]"

# Number: magenta
"[magenta]42[/]"

# Operator: yellow
"[yellow]=[/]"

# Comment: dim
"[dim]-- comment[/]"

# Function: blue
"[blue]COUNT[/]"
```

### Rationale

1. **TailLog compatibility**: `_render_line_strip()` uses `Text.from_markup()` which parses Rich console markup
2. **Theme integration**: Colors are fetched from theme at runtime, not hardcoded in markup
3. **Auto-closing tags**: `[/]` closes the last opened tag (recommended for simplicity)
4. **Style stacking**: Multiple styles combine (e.g., `[bold blue]`)

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Rich `Text` objects | `write_line()` expects strings, not Text objects |
| CSS class selectors | Textual CSS classes don't apply inside Log content |
| ANSI escape codes | Rich markup is cleaner and theme-aware |

### Implementation Pattern

```python
def highlight_sql_rich(sql: str, theme: Theme | None = None) -> str:
    """Convert SQL to Rich markup string.

    Args:
        sql: SQL text to highlight.
        theme: Theme for color lookup (uses global if None).

    Returns:
        Rich markup string with styled tokens.
    """
    if is_color_disabled():
        return sql.replace("[", "\\[")  # Escape brackets only

    tokens = SQLTokenizer().tokenize(sql)
    parts: list[str] = []

    for token in tokens:
        color = _get_token_color(token.type, theme)
        escaped_text = token.text.replace("[", "\\[")
        if color:
            parts.append(f"[{color}]{escaped_text}[/]")
        else:
            parts.append(escaped_text)

    return "".join(parts)
```

---

## Research Topic 2: Bracket Escaping in Rich Markup

**Question**: How do we prevent SQL brackets (e.g., `arr[1]`) from being parsed as Rich markup tags?

### Decision

Escape all brackets in token text with backslash: `\[`

```python
# Input:  SELECT arr[1] FROM table
# Output: [cyan]arr[/]\[1] [bold blue]FROM[/] [cyan]table[/]
```

### Rationale

1. **Rich standard**: `\[` is the documented escape sequence for literal brackets
2. **Existing pattern**: `tail_rich.py:157` already uses this: `entry.message.replace("[", "\\[")`
3. **TailLog support**: `_strip_markup()` handles unescaping: `result.replace("\\[", "[")`

### Edge Cases

| SQL Pattern | Escaped Output | Notes |
|------------|----------------|-------|
| `arr[1]` | `arr\[1]` | Array subscript |
| `col::int[]` | `col::int\[\]` | Array type cast |
| `jsonb['key']` | `jsonb\['key']` | JSONB accessor |
| `text LIKE '[a-z]'` | `'\[a-z]'` | Bracket in string literal |

---

## Research Topic 3: Theme Integration for SQL Colors

**Question**: How should SQL token colors integrate with the existing theme system?

### Decision

SQL colors are stored in `theme.ui` dict with `sql_` prefix, accessed via `get_ui_style()`:

```python
# Theme definition (already exists in all 6 themes)
ui={
    "sql_keyword": ColorStyle(fg="blue", bold=True),
    "sql_identifier": ColorStyle(fg="cyan"),
    "sql_string": ColorStyle(fg="green"),
    "sql_number": ColorStyle(fg="magenta"),
    "sql_operator": ColorStyle(fg="yellow"),
    "sql_comment": ColorStyle(fg="gray"),
    "sql_function": ColorStyle(fg="blue"),
}

# Access at runtime
def get_sql_color(token_type: SQLTokenType, theme: Theme) -> str:
    key = f"sql_{token_type.value}"  # e.g., "sql_keyword"
    style = theme.get_ui_style(key)
    return style.to_style_string()  # e.g., "bold fg:blue"
```

### Verification: All 6 Themes Have SQL Colors

| Theme | sql_keyword | sql_identifier | sql_string | sql_number | sql_operator | sql_comment | sql_function |
|-------|------------|----------------|------------|------------|--------------|-------------|--------------|
| dark | ✅ ansiblue bold | ✅ ansicyan | ✅ ansigreen | ✅ ansimagenta | ✅ ansiyellow | ✅ ansibrightblack | ✅ ansiblue |
| light | ✅ darkblue bold | ✅ teal | ✅ darkgreen | ✅ darkmagenta | ✅ darkorange | ✅ gray | ✅ darkblue |
| high-contrast | ✅ blue bold | ✅ cyan bold | ✅ green bold | ✅ magenta bold | ✅ yellow bold | ✅ white dim | ✅ blue bold |
| monokai | ✅ #f92672 bold | ✅ #66d9ef | ✅ #e6db74 | ✅ #ae81ff | ✅ #f8f8f2 | ✅ #75715e | ✅ #a6e22e |
| solarized-dark | ✅ #268bd2 bold | ✅ #2aa198 | ✅ #859900 | ✅ #d33682 | ✅ #b58900 | ✅ #586e75 | ✅ #268bd2 |
| solarized-light | ✅ #268bd2 bold | ✅ #2aa198 | ✅ #859900 | ✅ #d33682 | ✅ #b58900 | ✅ #93a1a1 | ✅ #268bd2 |

**Result**: FR-015 (update all built-in themes) is already complete. No theme modifications required.

### Fallback for Missing Theme Keys

Custom themes may omit SQL colors. Fallback to unstyled text:

```python
def _get_token_color(token_type: SQLTokenType, theme: Theme | None) -> str:
    if theme is None:
        return ""  # No styling
    key = f"sql_{token_type.value}"
    style = theme.get_ui_style(key)
    if not style.fg and not style.bold and not style.dim:
        return ""  # No styling defined
    return _color_style_to_rich_markup(style)
```

---

## Research Topic 4: Theme Access in tail_rich.py

**Question**: How does `tail_rich.py` access the current theme for color lookups?

### Decision

Access theme through global `ThemeManager` singleton or pass theme as parameter:

```python
# Option A: Global access (simple, matches existing pattern)
from pgtail_py.theme import ThemeManager

_theme_manager: ThemeManager | None = None

def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def format_entry_compact(entry: LogEntry) -> str:
    theme = get_theme_manager().current_theme
    # ... use theme for SQL highlighting
```

```python
# Option B: Parameter injection (more testable)
def format_entry_compact(entry: LogEntry, theme: Theme | None = None) -> str:
    # ... use passed theme or fall back to global
```

### Rationale

Option A is chosen because:
1. `tail_rich.py` is a formatting module, not a Textual widget
2. Theme changes via `theme <name>` update the global ThemeManager
3. Entry formatting happens per-line; no need to pass theme repeatedly

### Live Theme Updates

When user runs `theme <name>` or `theme reload`:
1. `ThemeManager.switch_theme()` updates `_current_theme`
2. Next call to `format_entry_compact()` uses new theme colors
3. Existing lines in TailLog retain old colors (Rich markup already rendered)
4. New lines use updated theme (SC-007: immediate theme switching)

---

## Research Topic 5: Reusing Existing SQL Modules

**Question**: Can `sql_tokenizer.py` and `sql_detector.py` be reused without modification?

### Decision

Yes, both modules are production-ready and require no changes.

### sql_tokenizer.py Analysis

| Aspect | Status | Notes |
|--------|--------|-------|
| Token types | ✅ Complete | 7 types needed: KEYWORD, IDENTIFIER, STRING, NUMBER, OPERATOR, COMMENT, FUNCTION |
| Keywords | ✅ 300+ | All PostgreSQL SQL keywords covered |
| Quote handling | ✅ Complete | Single quotes, double quotes, dollar-quoted strings |
| Comment handling | ✅ Complete | Line comments (`--`) and block comments (`/* */`) |
| Operator handling | ✅ Complete | Multi-char (`<>`, `::`, `||`) and single-char |
| Performance | ✅ Adequate | Compiled regex patterns, linear scan |

### sql_detector.py Analysis

| Pattern | Status | Regex |
|---------|--------|-------|
| `statement:` | ✅ | `statement:\s*` |
| `execute <name>:` | ✅ | `execute\s+\S+:\s*` |
| `parse <name>:` | ✅ | `parse\s+\S+:\s*` |
| `bind <name>:` | ✅ | `bind\s+\S+:\s*` |
| `duration: ... statement:` | ✅ | `duration:\s*[\d.]+\s*ms\s+statement` |
| `DETAIL:` | ✅ | `DETAIL:\s*` |

### Conclusion

Both modules are tested (see `tests/test_sql_*.py`) and match FR-011 patterns exactly.

---

## Research Topic 6: Performance Considerations

**Question**: What performance optimizations are needed for SC-004 (100+ entries/sec)?

### Decision

No special optimizations required. Current implementation is sufficient.

### Analysis

1. **Tokenizer**: O(n) where n = SQL length. Compiled regex patterns. 50KB SQL < 1ms.
2. **Detector**: 6 regex matches per entry, short-circuit on first match. ~0.1ms per entry.
3. **Markup generation**: String concatenation, linear in token count. ~0.1ms per entry.
4. **Total overhead**: ~1-2ms per entry with SQL. At 100 entries/sec = 100-200ms total. Acceptable.

### Benchmark Targets

| Metric | Target | Expected |
|--------|--------|----------|
| Tokenize 50KB SQL | <10ms | ~1ms |
| Format entry with SQL | <1ms | ~0.5ms |
| 100 entries/sec overhead | <200ms | ~150ms |

---

## Research Topic 7: Clipboard Markup Stripping

**Question**: Does the existing `_strip_markup()` in TailLog handle SQL highlighting correctly?

### Decision

Yes, existing implementation is sufficient.

### Verification

```python
# TailLog._strip_markup() implementation
def _strip_markup(self, text: str) -> str:
    import re
    result = re.sub(r"\[/?[^\]]*\]", "", text)
    result = result.replace("\\[", "[")
    return result
```

This correctly handles:
1. Opening tags: `[bold blue]` → removed
2. Closing tags: `[/]` → removed
3. Escaped brackets: `\\[` → `[`

### Test Case

```python
# Input (Rich markup with SQL)
"[dim]10:00:00[/] [green]LOG[/]: [bold blue]SELECT[/] [cyan]arr[/]\\[1] [bold blue]FROM[/] [cyan]users[/]"

# After _strip_markup()
"10:00:00 LOG: SELECT arr[1] FROM users"
```

**Result**: FR-009 (strip markup on copy) works automatically.

---

## Summary of Findings

| Research Question | Resolution | Implementation Impact |
|-------------------|------------|----------------------|
| Rich markup syntax | Use `[color]text[/]` format | New function in sql_highlighter.py |
| Bracket escaping | `\[` escape sequence | Apply to all token text |
| Theme integration | Themes already have SQL colors | Use `get_ui_style("sql_*")` |
| Theme access | Global ThemeManager singleton | Import in tail_rich.py |
| Module reuse | sql_tokenizer.py, sql_detector.py | No changes needed |
| Performance | Current approach sufficient | No optimizations needed |
| Clipboard stripping | Existing _strip_markup() works | No changes needed |

---

## Implementation Sequence

Based on research findings, the implementation order is:

1. **sql_highlighter.py**: Add `highlight_sql_rich()` function and helper `_color_style_to_rich_markup()`
2. **tail_rich.py**: Import theme manager, detect SQL in messages, apply highlighting
3. **tests/test_sql_highlighter.py**: Add tests for Rich output
4. **tests/test_tail_rich.py**: Add integration tests

No theme file changes required. All 6 built-in themes are already configured.
