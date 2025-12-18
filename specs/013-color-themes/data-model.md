# Data Model: Color Themes

**Feature**: 013-color-themes
**Date**: 2025-12-17

## Entities

### ColorStyle

Represents a single color style specification with foreground, background, and modifiers.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| fg | string | No | Foreground color (ANSI name, hex code, or named color) |
| bg | string | No | Background color (ANSI name, hex code, or named color) |
| bold | boolean | No | Bold text modifier (default: false) |
| dim | boolean | No | Dim/faint text modifier (default: false) |
| italic | boolean | No | Italic text modifier (default: false) |
| underline | boolean | No | Underline text modifier (default: false) |

**Color format examples**:
- ANSI: `"ansired"`, `"ansibrightblue"`, `"ansidefault"`
- Hex: `"#ff6b6b"`, `"#fff"`, `"#839496"`
- Named: `"DarkRed"`, `"Coral"`, `"Gray"`

**Conversion to prompt_toolkit style string**:
```
ColorStyle(fg="red", bg="yellow", bold=True) → "fg:red bg:yellow bold"
```

### Theme

A complete theme definition containing all style rules.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Theme identifier (e.g., "dark", "monokai") |
| description | string | No | Human-readable description |
| levels | dict[LogLevel, ColorStyle] | Yes | Styles for each log level |
| ui | dict[str, ColorStyle] | Yes | Styles for UI elements |

**Log levels (from filter.py)**:
- PANIC, FATAL, ERROR, WARNING, NOTICE, LOG, INFO
- DEBUG1, DEBUG2, DEBUG3, DEBUG4, DEBUG5

**UI elements**:
- `prompt` - REPL prompt
- `timestamp` - Log entry timestamps
- `pid` - Process ID display
- `highlight` - Search/regex highlights
- `slow_warning` - Slow query warning level
- `slow_slow` - Slow query slow level
- `slow_critical` - Slow query critical level
- `detail` - Secondary fields in full display mode

### ThemeManager

Singleton manager for theme operations. Not persisted - runtime only.

| Field | Type | Description |
|-------|------|-------------|
| current_theme | Theme | Currently active theme |
| builtin_themes | dict[str, Theme] | Loaded built-in themes |
| custom_themes | dict[str, Theme] | Loaded custom themes |
| style | Style | Generated prompt_toolkit Style for current theme |

**Operations**:
- `load_theme(name: str) -> Theme` - Load theme by name (built-in or custom)
- `switch_theme(name: str) -> bool` - Switch to named theme, returns success
- `reload_current() -> bool` - Reload current theme from disk
- `list_themes() -> list[str]` - List available theme names
- `get_style() -> Style` - Get prompt_toolkit Style for current theme
- `validate_theme(theme: Theme) -> list[str]` - Validate theme, returns errors

## State Transitions

```
┌─────────────────────────────────────────────────────────────────┐
│                        ThemeManager                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  switch_theme()  ┌──────────────┐                 │
│  │ Initial  │ ───────────────► │ Theme Active │                 │
│  │ (dark)   │                  │              │                 │
│  └──────────┘                  └──────────────┘                 │
│       │                              │  │                       │
│       │ load failure                 │  │ reload()              │
│       ▼                              │  ▼                       │
│  ┌──────────┐  fallback        ┌──────────────┐                 │
│  │ Fallback │ ◄──────────────  │ Theme Error  │                 │
│  │ (dark)   │                  │              │                 │
│  └──────────┘                  └──────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Validation Rules

### ColorStyle Validation

1. `fg` must be valid color or empty/null
2. `bg` must be valid color or empty/null
3. Boolean fields must be true/false (default false)

**Valid color formats**:
- ANSI: `ansi[bright]?(black|red|green|yellow|blue|magenta|cyan|gray|white|default)`
- Hex: `#[0-9a-fA-F]{3}` or `#[0-9a-fA-F]{6}`
- Named: Any of 140 CSS named colors

### Theme Validation

1. `name` must be non-empty string, lowercase, alphanumeric with hyphens
2. `levels` must define at least: ERROR, WARNING, LOG
3. `ui` must define at least: timestamp, highlight
4. Missing log levels inherit from nearest severity (ERROR → FATAL → PANIC)
5. Missing UI elements use theme defaults

### Theme File Validation

1. TOML must be parseable
2. `[meta]` section optional
3. `[levels]` section required
4. `[ui]` section required
5. Unknown sections ignored with warning
6. Unknown fields within sections ignored with warning

## Relationships

```
┌─────────────┐     has many      ┌─────────────┐
│   Theme     │ ─────────────────►│ ColorStyle  │
│             │                   │             │
│ - name      │                   │ - fg        │
│ - levels{}  │                   │ - bg        │
│ - ui{}      │                   │ - bold      │
└─────────────┘                   │ - dim       │
       │                          │ - italic    │
       │ generates                │ - underline │
       ▼                          └─────────────┘
┌─────────────┐
│   Style     │  (prompt_toolkit)
│             │
│ - rules[]   │
└─────────────┘
```

## File Format: Custom Theme TOML

```toml
# ~/.config/pgtail/themes/mytheme.toml

[meta]
name = "My Theme"
description = "Custom color scheme"

[levels]
PANIC = { fg = "white", bg = "red", bold = true }
FATAL = { fg = "red", bold = true }
ERROR = { fg = "#ff6b6b" }
WARNING = { fg = "#ffd93d" }
NOTICE = { fg = "#6bcb77" }
LOG = { fg = "default" }
INFO = { fg = "#4d96ff" }
DEBUG = { fg = "#888888" }
# DEBUG1-5 inherit from DEBUG if not specified

[ui]
prompt = { fg = "green" }
timestamp = { fg = "gray" }
pid = { fg = "gray" }
highlight = { bg = "yellow", fg = "black" }
slow_warning = { fg = "yellow" }
slow_slow = { fg = "yellow", bold = true }
slow_critical = { fg = "red", bold = true }
detail = { fg = "default" }
```

## Configuration Integration

Theme selection persists in main config:

```toml
# ~/.config/pgtail/config.toml
[theme]
name = "monokai"  # References built-in or custom theme
```

Theme precedence:
1. Custom themes (config_dir/themes/*.toml)
2. Built-in themes (pgtail_py/themes/*.py)
3. Fallback to "dark" if not found
