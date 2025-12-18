# Research: Color Themes

**Feature**: 013-color-themes
**Date**: 2025-12-17

## Summary

Research findings for implementing the color theming system in pgtail. No critical unknowns identified - the technical approach is well-defined using existing prompt_toolkit infrastructure.

## Research Areas

### 1. prompt_toolkit Style System

**Decision**: Use prompt_toolkit's `Style` class with style rules list format.

**Rationale**:
- Existing `colors.py` already uses `Style([...])` with tuples of (class_name, style_string)
- Style strings support: `fg:COLOR`, `bg:COLOR`, `bold`, `italic`, `underline`, `dim`, `reverse`
- Colors support ANSI names (`ansiRed`, `ansibrightblue`) and hex codes (`#ff6b6b`)
- 140 named web colors supported (e.g., `DarkRed`, `Coral`, `Crimson`)

**Alternatives considered**:
- Pygments styles: Heavier dependency, not needed for simple log coloring
- Direct ANSI escape codes: Less portable, harder to maintain

**Key findings from prompt_toolkit source**:
- Style rules format: `Style([('class_name', 'fg:red bold'), ...])`
- Color formats: `ansicolor`, `#rrggbb`, `#rgb`, named colors
- Modifiers: `bold`, `italic`, `underline`, `dim`, `reverse`, `blink`, `hidden`
- ANSI colors: 16 base colors with bright variants

### 2. Theme File Format

**Decision**: Use TOML for custom themes, Python modules for built-in themes.

**Rationale**:
- TOML is already used for config (tomlkit dependency exists)
- Python modules for built-ins provide type safety and IDE support
- Clear separation: built-ins are code, user themes are data

**Theme TOML structure**:
```toml
[meta]
name = "Custom Theme"
description = "User-defined colors"

[levels]
PANIC = { fg = "white", bg = "red", bold = true }
FATAL = { fg = "red", bold = true }
ERROR = { fg = "#ff6b6b" }
WARNING = { fg = "#ffd93d" }
NOTICE = { fg = "#6bcb77" }
LOG = { fg = "default" }
INFO = { fg = "#4d96ff" }
DEBUG = { fg = "#888888" }

[ui]
prompt = { fg = "green" }
timestamp = { fg = "gray" }
pid = { fg = "gray" }
highlight = { bg = "yellow", fg = "black" }
slow_warning = { fg = "yellow" }
slow_slow = { fg = "yellow", bold = true }
slow_critical = { fg = "red", bold = true }
```

**Alternatives considered**:
- JSON: Less readable, no comments
- YAML: Additional dependency
- INI: Limited nested structure

### 3. Built-in Theme Color Palettes

**Decision**: Define 6 themes with carefully chosen color palettes.

**Theme specifications**:

| Theme | Background | Primary | Error | Warning | Success | Muted |
|-------|-----------|---------|-------|---------|---------|-------|
| dark | - | default | ansired | ansiyellow | ansigreen | ansibrightblack |
| light | - | ansiblack | DarkRed | DarkOrange | DarkGreen | ansigray |
| high-contrast | - | ansiwhite | ansired + bg | bold yellow | bold green | dim |
| monokai | - | #f8f8f2 | #f92672 | #fd971f | #a6e22e | #75715e |
| solarized-dark | - | #839496 | #dc322f | #b58900 | #859900 | #586e75 |
| solarized-light | - | #657b83 | #dc322f | #b58900 | #859900 | #93a1a1 |

**Rationale**:
- Dark: Current pgtail defaults, proven in use
- Light: Inverted for light terminal backgrounds
- High-contrast: WCAG AA compliance for accessibility
- Monokai: Popular editor theme, familiar to developers
- Solarized: Industry-standard, carefully designed color science

### 4. Theme Storage Location

**Decision**: Custom themes in `{config_dir}/themes/` subdirectory.

**Paths**:
- macOS: `~/Library/Application Support/pgtail/themes/*.toml`
- Linux: `~/.config/pgtail/themes/*.toml`
- Windows: `%APPDATA%/pgtail/themes/*.toml`

**Rationale**:
- Follows existing config path convention
- Separates custom themes from main config
- Easy to manage multiple themes
- Consistent with theme.name config setting

### 5. NO_COLOR Environment Variable

**Decision**: Respect NO_COLOR (https://no-color.org/) by bypassing all themes.

**Implementation**:
- Check `os.environ.get("NO_COLOR")` at style generation time
- Return plain/default styles when set
- Already partially implemented in `colors.py` `_is_color_disabled()`

**Rationale**: Industry standard for accessibility and piping output to files.

### 6. Theme Validation

**Decision**: Validate theme files before applying; fallback to default on errors.

**Validation rules**:
- All log levels must have style defined (or inherit from parent)
- Color values must be valid (ANSI names, hex codes, or named colors)
- Modifiers must be boolean
- Missing sections use defaults

**Error messages**:
- "Invalid color 'xyz' in theme.levels.ERROR.fg: expected ANSI name or hex code"
- "Theme file corrupt: TOML parse error at line 12"
- "Missing required section [levels] in theme file"

### 7. Dynamic Style Generation

**Decision**: Generate prompt_toolkit Style objects dynamically from theme data.

**Implementation approach**:
1. Load theme definition (built-in module or TOML file)
2. Convert to intermediate `Theme` dataclass
3. Generate style rules list for prompt_toolkit `Style([...])`
4. Cache generated Style object until theme changes

**Performance**: Style generation is O(n) where n = number of style rules (~20). Trivial overhead.

## Dependencies

No new dependencies required:
- `prompt_toolkit` >=3.0.0 (existing) - Style system
- `tomlkit` >=0.12.0 (existing) - TOML parsing with comments

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Invalid hex colors crash | Low | High | Validate all colors before Style creation |
| Theme file permissions | Low | Medium | Graceful fallback to default theme |
| Terminal doesn't support 256 colors | Medium | Low | Use ANSI fallbacks; document limitation |

## Next Steps

1. Create `Theme` and `ColorStyle` dataclasses in `theme.py`
2. Implement `ThemeManager` for loading/switching/validating
3. Define built-in themes as Python modules
4. Create `cli_theme.py` command handlers
5. Update `colors.py` to use ThemeManager
6. Add theme validation tests
