# Quickstart: Color Themes

**Feature**: 013-color-themes
**Date**: 2025-12-17

## Overview

This guide helps you get started with pgtail's color theme system.

## Basic Usage

### Switch Themes

```bash
# See current theme
pgtail> theme
Current theme: dark

# Switch to light theme
pgtail> theme light
Theme set to: light

# Switch to high-contrast for accessibility
pgtail> theme high-contrast
Theme set to: high-contrast
```

### List Available Themes

```bash
pgtail> theme list
Available themes:

Built-in:
  dark (current)
  light
  high-contrast
  monokai
  solarized-dark
  solarized-light
```

### Preview Before Switching

```bash
pgtail> theme preview monokai
Preview: monokai

14:32:15.123 [12345] PANIC  : System crash imminent
14:32:15.124 [12345] FATAL  : Cannot connect to database
14:32:15.125 [12345] ERROR  : Query execution failed
...

Use 'theme monokai' to apply this theme.
```

## Built-in Themes

| Theme | Best For |
|-------|----------|
| `dark` | Dark terminal backgrounds (default) |
| `light` | Light terminal backgrounds |
| `high-contrast` | Accessibility, bright displays |
| `monokai` | Developers familiar with editor theme |
| `solarized-dark` | Dark terminals, reduced eye strain |
| `solarized-light` | Light terminals, reduced eye strain |

## Custom Themes

### Create a Custom Theme

```bash
# Create and edit a new theme
pgtail> theme edit mytheme
Created theme template: ~/.config/pgtail/themes/mytheme.toml
Opening in editor...
```

### Theme File Format

```toml
# ~/.config/pgtail/themes/mytheme.toml

[meta]
name = "My Custom Theme"
description = "Personal color preferences"

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
timestamp = { fg = "gray" }
pid = { fg = "gray" }
highlight = { bg = "yellow", fg = "black" }
```

### Color Formats

```toml
# ANSI colors (16-color palette)
fg = "ansired"
fg = "ansibrightblue"
fg = "ansidefault"

# Hex colors (256-color / true color)
fg = "#ff6b6b"
fg = "#fff"

# Named colors (140 CSS colors)
fg = "DarkRed"
fg = "Coral"
fg = "SlateGray"
```

### Style Modifiers

```toml
[levels]
PANIC = { fg = "white", bg = "red", bold = true }
ERROR = { fg = "red", italic = true }
DEBUG = { fg = "gray", dim = true }
```

Available modifiers: `bold`, `dim`, `italic`, `underline`

### Apply and Reload

```bash
# Apply custom theme
pgtail> theme mytheme
Theme set to: mytheme

# After editing externally
pgtail> theme reload
Theme 'mytheme' reloaded.
```

## Configuration

Theme preference is saved automatically:

```toml
# ~/.config/pgtail/config.toml
[theme]
name = "monokai"
```

Theme persists across sessions.

## Disabling Colors

To disable all colors (for piping, accessibility, etc.):

```bash
NO_COLOR=1 pgtail
```

This bypasses all theme settings and outputs plain text.

## Troubleshooting

### Theme Not Found

```
Unknown theme: badname
Available themes: dark, light, high-contrast, monokai, solarized-dark, solarized-light
```

Check spelling or verify custom theme file exists.

### Invalid Theme File

```
Failed to reload theme 'mytheme':
  Invalid color '#gggggg' in levels.ERROR.fg
```

Fix the invalid color value in your theme file.

### Colors Look Wrong

- Check your terminal's color scheme settings
- Try a different theme (`theme light` for light terminals)
- Some terminals don't support 256 colors; use ANSI colors instead

## Quick Reference

| Command | Description |
|---------|-------------|
| `theme` | Show current theme |
| `theme <name>` | Switch to theme |
| `theme list` | List available themes |
| `theme preview [name]` | Preview theme colors |
| `theme edit <name>` | Edit/create custom theme |
| `theme reload` | Reload current theme |
