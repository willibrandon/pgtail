# Color Themes

pgtail supports color themes for customizing log output appearance.

## Built-in Themes

| Theme | Description |
|-------|-------------|
| `dark` | Default dark background theme |
| `light` | Light background theme |
| `high-contrast` | Maximum contrast for accessibility |
| `monokai` | Monokai color scheme |
| `solarized-dark` | Solarized dark variant |
| `solarized-light` | Solarized light variant |

## Switching Themes

```
pgtail> theme light
pgtail> theme monokai
```

## Previewing Themes

```
pgtail> theme preview solarized-dark
```

Shows sample log output with the theme applied.

## Listing Themes

```
pgtail> theme list
```

Shows all available themes (built-in and custom).

## Custom Themes

### Creating a Custom Theme

```
pgtail> theme edit mytheme
```

Opens your `$EDITOR` with a theme template.

### Theme File Location

Custom themes are TOML files stored in:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/pgtail/themes/` |
| Linux | `~/.config/pgtail/themes/` |
| Windows | `%APPDATA%/pgtail/themes/` |

### Theme File Format

```toml
# mytheme.toml
[levels]
panic = "bold fg:white bg:red"
fatal = "bold fg:red"
error = "fg:red"
warning = "fg:yellow"
notice = "fg:cyan"
log = "fg:ansidefault"
info = "fg:green"
debug1 = "fg:ansibrightblack"

[ui]
timestamp = "fg:ansibrightblack"
pid = "fg:ansibrightblack"
highlight = "fg:black bg:yellow"

[sql]
keyword = "bold fg:blue"
identifier = "fg:cyan"
string = "fg:green"
number = "fg:magenta"
operator = "fg:yellow"
comment = "fg:ansibrightblack"
function = "fg:blue"
```

### Color Formats

Supported color formats:

- ANSI names: `ansiRed`, `ansiGreen`, `ansiBrightBlue`
- Hex codes: `#ff6b6b`, `#2ecc71`
- CSS names: `DarkRed`, `LimeGreen`
- Default: `ansidefault`

### Style Modifiers

- `bold` - Bold text
- `italic` - Italic text
- `underline` - Underlined text
- `fg:color` - Foreground color
- `bg:color` - Background color

## Persisting Theme Choice

```
pgtail> set theme.name monokai
```

Or in `config.toml`:

```toml
[theme]
name = "monokai"
```

## Reloading Themes

After editing a theme file externally:

```
pgtail> theme reload
```

## NO_COLOR Support

pgtail respects the `NO_COLOR` environment variable:

```bash
NO_COLOR=1 pgtail
```

This disables all color output.
