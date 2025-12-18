# Command Contracts: Color Themes

**Feature**: 013-color-themes
**Date**: 2025-12-17

## Commands

### theme [name]

Switch to a theme or show current theme.

**Syntax**:
```
theme              # Show current theme
theme <name>       # Switch to theme
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Theme name to switch to |

**Success Response** (no name):
```
Current theme: dark

Use 'theme <name>' to switch, 'theme list' to see options.
```

**Success Response** (with name):
```
Theme set to: monokai
```

**Error Response** (invalid name):
```
Unknown theme: badname
Available themes: dark, light, high-contrast, monokai, solarized-dark, solarized-light

Custom themes can be added to: ~/.config/pgtail/themes/
```

---

### theme list

List all available themes.

**Syntax**:
```
theme list
```

**Success Response**:
```
Available themes:

Built-in:
  dark (current)
  light
  high-contrast
  monokai
  solarized-dark
  solarized-light

Custom:
  mytheme
  company-brand
```

**No custom themes**:
```
Available themes:

Built-in:
  dark (current)
  light
  high-contrast
  monokai
  solarized-dark
  solarized-light

Custom themes can be added to: ~/.config/pgtail/themes/
```

---

### theme preview [name]

Preview a theme with sample log output.

**Syntax**:
```
theme preview           # Preview current theme
theme preview <name>    # Preview specific theme
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Theme name to preview (defaults to current) |

**Success Response**:
```
Preview: monokai

14:32:15.123 [12345] PANIC  : System crash imminent
14:32:15.124 [12345] FATAL  : Cannot connect to database
14:32:15.125 [12345] ERROR  : Query execution failed
14:32:15.126 [12345] WARNING: Connection pool exhausted
14:32:15.127 [12345] NOTICE : Configuration reloaded
14:32:15.128 [12345] LOG    : Checkpoint complete
14:32:15.129 [12345] INFO   : Server started
14:32:15.130 [12345] DEBUG  : Query plan generated

Use 'theme monokai' to apply this theme.
```

**Error Response**:
```
Unknown theme: badname
Use 'theme list' to see available themes.
```

---

### theme edit [name]

Edit or create a custom theme.

**Syntax**:
```
theme edit <name>
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Custom theme name to edit/create |

**Success Response** (file exists):
```
Opening theme file in editor: ~/.config/pgtail/themes/mytheme.toml
```

**Success Response** (new file):
```
Created theme template: ~/.config/pgtail/themes/newtheme.toml
Opening in editor...

After editing, use 'theme newtheme' to apply.
```

**Error Response** (no $EDITOR):
```
$EDITOR not set. Edit the theme file manually:
  ~/.config/pgtail/themes/mytheme.toml

Use 'theme reload' after making changes.
```

**Error Response** (built-in theme):
```
Cannot edit built-in theme 'dark'.
Use 'theme edit <custom-name>' to create a custom theme.
```

---

### theme reload

Reload the current theme from disk.

**Syntax**:
```
theme reload
```

**Success Response**:
```
Theme 'mytheme' reloaded.
```

**Error Response** (parse error):
```
Failed to reload theme 'mytheme':
  TOML parse error at line 12: expected '=' after key

Keeping previous theme active.
```

**Error Response** (validation error):
```
Failed to reload theme 'mytheme':
  Invalid color '#gggggg' in levels.ERROR.fg

Keeping previous theme active.
```

**Error Response** (file deleted):
```
Theme file not found: ~/.config/pgtail/themes/mytheme.toml
Falling back to default theme: dark
```

---

## Command Registration

Commands to add to `commands.py`:

```python
THEME_COMMANDS = {
    "theme": "Switch themes or show current: theme [name]",
    "theme list": "List available themes",
    "theme preview": "Preview a theme: theme preview [name]",
    "theme edit": "Edit/create custom theme: theme edit <name>",
    "theme reload": "Reload current theme from disk",
}
```

## Autocomplete

Theme command should provide autocomplete for:
- Subcommands: `list`, `preview`, `edit`, `reload`
- Theme names: All built-in + custom theme names
- Context-aware: `theme preview <TAB>` → theme names

## NO_COLOR Behavior

When `NO_COLOR=1` is set:

```
pgtail> theme monokai
Theme set to: monokai
Note: Colors disabled (NO_COLOR is set)

pgtail> theme preview
Preview: monokai (colors disabled)

14:32:15.123 [12345] PANIC  : System crash imminent
14:32:15.124 [12345] FATAL  : Cannot connect to database
...
```
