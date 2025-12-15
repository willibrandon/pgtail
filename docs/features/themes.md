# Feature: Color Themes

## Problem

Users have different terminal setups and preferences:
- Dark vs light terminal backgrounds
- Color blindness considerations
- Corporate/minimal aesthetic preferences
- High contrast needs

The current hardcoded colors may not work well for all users.

## Proposed Solution

Support multiple built-in themes and custom theme definitions. Themes control all colors used in the interface: log levels, UI elements, highlights.

## User Scenarios

### Scenario 1: Switch to Light Theme
User with light terminal background:
```
pgtail> theme light
Theme set to: light
```

### Scenario 2: High Contrast
User needs more visible differentiation:
```
pgtail> theme high-contrast
Theme set to: high-contrast
```

### Scenario 3: Preview Themes
User wants to see available options:
```
pgtail> theme list
Available themes:
  dark (current)
  light
  high-contrast
  monokai
  solarized-dark
  solarized-light

pgtail> theme preview monokai
[Shows sample output in monokai colors]
```

### Scenario 4: Custom Theme
User wants specific colors:
```
pgtail> theme edit custom
Opening theme editor...
# Or edit ~/.config/pgtail/themes/custom.toml
```

## Built-in Themes

### Dark (Default)
Optimized for dark terminal backgrounds:
- ERROR: Red
- WARNING: Yellow
- NOTICE: Cyan
- LOG: Default
- INFO: Green
- DEBUG: Gray

### Light
Optimized for light terminal backgrounds:
- ERROR: Dark red
- WARNING: Dark orange
- NOTICE: Dark cyan
- LOG: Black
- INFO: Dark green
- DEBUG: Gray

### High Contrast
Maximum differentiation:
- ERROR: Bold red on dark red background
- WARNING: Bold yellow
- NOTICE: Bold cyan
- LOG: Bold white
- INFO: Bold green
- DEBUG: Dim

### Monokai
Popular code editor theme colors

### Solarized Dark/Light
Solarized color palette

## Theme File Format

```toml
# ~/.config/pgtail/themes/custom.toml
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
prompt = { fg = "green" }
timestamp = { fg = "gray" }
pid = { fg = "gray" }
highlight = { bg = "yellow", fg = "black" }
selection = { bg = "blue", fg = "white" }
```

## Commands

```
theme <name>           Switch to theme
theme list             Show available themes
theme preview <name>   Show sample with theme
theme edit <name>      Edit/create theme file
theme reload           Reload current theme
```

## Success Criteria

1. At least 3 built-in themes (dark, light, high-contrast)
2. Themes apply immediately without restart
3. Custom themes loadable from config directory
4. Invalid theme files show helpful errors
5. Preview shows representative sample of all colors
6. NO_COLOR=1 overrides all themes
7. Theme persists in config file

## Out of Scope

- Theme marketplace/sharing
- Automatic theme based on terminal detection
- Per-instance themes
- Animation/effects
