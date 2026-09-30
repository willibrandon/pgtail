---
title: Themes
description: Built-in color themes, switching and previewing them, and writing your own in TOML.
---

Themes set the colors of log levels, highlighting, and pgtail's own interface.

## Built-in themes

| Theme | Description |
|-------|-------------|
| `dark` | Default dark theme for dark terminal backgrounds |
| `light` | Light theme for light terminal backgrounds |
| `high-contrast` | High contrast theme for accessibility |
| `monokai` | Monokai editor color scheme |
| `solarized-dark` | Solarized dark color scheme for reduced eye strain |
| `solarized-light` | Solarized light color scheme for reduced eye strain |

## Switching themes

```pgtail
pgtail> theme light
pgtail> theme monokai
```

The choice is saved to the configuration file as `theme.name`, so pgtail starts with it next time. `theme <name>`
works in tail mode too, and redraws the log. `theme` on its own shows the current theme.

## Previewing themes

```pgtail
pgtail> theme preview solarized-dark
```

Shows sample log lines in a theme without switching to it.

## Listing themes

```pgtail
pgtail> theme list
```

Lists the built-in themes and your custom themes, marking the current one.

## Custom themes

### Creating a custom theme

```pgtail
pgtail> theme edit mytheme
```

For a new name this writes a theme file from a template, then opens it in pgtail's built-in editor, which highlights
the TOML. **Ctrl+S** checks the theme and saves it only when it is valid, showing any problems in the status line;
**Esc** (or **Ctrl+Q**) closes the editor, and a second **Esc** discards unsaved changes. Built-in themes cannot be
edited; give your copy a new name, such as `theme edit my-dark`.

Then switch to it:

```pgtail
pgtail> theme mytheme
```

### Theme file location

Custom themes are TOML files named after the theme, in:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/pgtail/themes/` |
| Linux | `~/.config/pgtail/themes/` (or `$XDG_CONFIG_HOME/pgtail/themes/`) |
| Windows | `%APPDATA%\pgtail\themes\` |

Theme names use lowercase letters, digits, and hyphens.

### Theme file format

Each style is a table with `fg` and `bg` colors and `bold`, `dim`, `italic`, and `underline` flags:

```toml
# mytheme.toml

[meta]
name = "mytheme"
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

# SQL colors
sql_keyword = { fg = "blue", bold = true }
sql_identifier = { fg = "cyan" }
sql_string = { fg = "green" }
sql_number = { fg = "magenta" }
sql_operator = { fg = "yellow" }
sql_comment = { fg = "gray" }
sql_function = { fg = "blue" }
```

A theme needs at least the `ERROR`, `WARNING`, and `LOG` levels and the `timestamp` and `highlight` elements. A level
it leaves out uses `LOG`'s style, and `DEBUG1` through `DEBUG5` use `DEBUG`'s. The `[ui]` table also holds the
highlighting colors (the `hl_*` elements listed under [Highlighting](/guide/highlighting/#theme-integration)).

### Colors

- `default` for the terminal's own color
- ANSI names that follow your terminal's palette: `red`, `ansired`, `bright_black`, `ansibrightblue`
- 256-color palette names such as `dark_orange` or `grey50`, and `color(208)`
- CSS names such as `DarkRed` or `cornflowerblue`
- Hex codes (`#ff6b6b`, `#f66`) and `rgb(255,107,107)`

Names ignore case.

## Reloading themes

After editing a theme file in another editor:

```pgtail
pgtail> theme reload
```

## NO_COLOR

pgtail follows the `NO_COLOR` convention:

```sh
NO_COLOR=1 pgtail
```

With `NO_COLOR` set, output keeps bold, dim, and the other attributes but uses no colors.
