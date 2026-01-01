# Contracts: SQL Syntax Highlighting in Textual Tail Mode

**Date**: 2025-12-31
**Feature**: 018-textual-sql-highlighting

## Overview

This feature has no external API contracts. All new functionality consists of internal Python module functions that are called programmatically within the codebase.

## Internal Function Signatures

### highlight_sql_rich()

**Location**: `pgtail_py/sql_highlighter.py`

```python
def highlight_sql_rich(
    sql: str,
    theme: Theme | None = None
) -> str:
    """Convert SQL text to Rich console markup string.

    Args:
        sql: SQL text to highlight.
        theme: Theme for color lookup. If None, uses global ThemeManager.

    Returns:
        Rich markup string with styled tokens.
        Brackets in SQL are escaped to prevent Rich parsing errors.
        If NO_COLOR is set, returns SQL with only bracket escaping.

    Example:
        >>> highlight_sql_rich("SELECT id FROM users")
        "[bold blue]SELECT[/] [cyan]id[/] [bold blue]FROM[/] [cyan]users[/]"
    """
```

### _color_style_to_rich_markup()

**Location**: `pgtail_py/sql_highlighter.py`

```python
def _color_style_to_rich_markup(style: ColorStyle) -> str:
    """Convert ColorStyle to Rich markup tag content.

    Args:
        style: ColorStyle with color and modifier information.

    Returns:
        Rich markup content string (e.g., "bold blue", "dim", "#268bd2").
        Empty string if no styling defined.

    Note:
        This is a private helper function, not part of the public API.
    """
```

## No REST/GraphQL APIs

This feature operates entirely within the CLI application:
- No HTTP endpoints
- No network communication
- No external service integration

## Testing Contracts

Test functions are defined in:
- `tests/test_sql_highlighter.py` - Unit tests for Rich output
- `tests/test_tail_rich.py` - Integration tests for entry formatting
