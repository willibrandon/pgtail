# Quickstart: SQL Syntax Highlighting

**Feature**: 014-sql-highlighting
**Date**: 2025-12-17

## Overview

SQL syntax highlighting is an **always-on** feature that automatically colors SQL statements in PostgreSQL log messages. No configuration is required - when you tail logs with `pgtail`, SQL will be highlighted using your current theme's colors.

## What Gets Highlighted

| Element | Example | Default Color |
|---------|---------|---------------|
| Keywords | `SELECT`, `FROM`, `WHERE`, `JOIN` | Blue (bold) |
| Identifiers | `users`, `created_at` | Cyan |
| Strings | `'hello world'`, `$$body$$` | Green |
| Numbers | `42`, `3.14` | Magenta |
| Operators | `=`, `<>`, `||`, `::` | Yellow |
| Comments | `-- comment`, `/* block */` | Gray |
| Functions | `COUNT()`, `NOW()` | Blue |

## Where SQL Is Detected

SQL highlighting activates in log messages containing:

- `LOG: statement:` - Statement logging
- `LOG: execute <name>:` - Prepared statement execution
- `LOG: duration: ... statement:` - Query timing
- `DETAIL:` - Error context details
- Query fragments in `ERROR:` messages

## Usage

```bash
# Just tail logs - SQL highlighting is automatic
pgtail
> tail 1

# Example output (colors shown as [color]):
# 10:23:45.123 [12345] LOG: statement: [blue]SELECT[/] [cyan]id[/], [cyan]name[/] [blue]FROM[/] [cyan]users[/] [blue]WHERE[/] [cyan]active[/] [yellow]=[/] [green]'yes'[/]
```

## Themes

Each built-in theme includes SQL colors optimized for its palette:

- **dark** (default): Vibrant colors for dark backgrounds
- **light**: Subdued colors for light backgrounds
- **monokai**: Matches Monokai code editor scheme
- **solarized-dark/light**: Matches Solarized palette
- **high-contrast**: Bold, high-saturation colors

Switch themes with:
```
> theme monokai
```

## Custom Theme SQL Colors

Add to your custom theme TOML file:

```toml
[ui]
sql_keyword = { fg = "blue", bold = true }
sql_identifier = { fg = "cyan" }
sql_string = { fg = "green" }
sql_number = { fg = "magenta" }
sql_operator = { fg = "yellow" }
sql_comment = { fg = "gray" }
sql_function = { fg = "blue" }
```

## Disabling Colors

Set `NO_COLOR=1` to disable all colors including SQL highlighting:

```bash
NO_COLOR=1 pgtail
```

## Fullscreen Mode

SQL highlighting works identically in fullscreen TUI mode:

```
> tail 1
> fs
```

Search highlighting and SQL highlighting layer together - search matches are highlighted on top of SQL-colored text.

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Malformed SQL | Recognized tokens highlighted, rest plain text |
| Very long SQL (10,000+ chars) | Highlighted without delay (<100ms) |
| Multi-line statements | Each line highlighted independently |
| Dollar-quoted strings | Content treated as string literal |
| Quoted identifiers ("Table") | Highlighted as identifier |

## Verification

To verify SQL highlighting is working:

1. Ensure PostgreSQL has `log_statement = 'all'` or similar
2. Run a query: `SELECT 1;`
3. In pgtail, you should see `SELECT` in blue and `1` in magenta

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No colors at all | Check `NO_COLOR` env var; try `theme dark` |
| SQL not detected | Verify log line starts with `LOG: statement:` |
| Wrong colors | Try a different theme or check custom theme syntax |
| Performance issue | Should not occur; report if highlighting causes lag |
