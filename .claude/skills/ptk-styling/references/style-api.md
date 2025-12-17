# Style API Reference

Complete API for prompt_toolkit styling system.

## Style Class

```python
from prompt_toolkit.styles import Style

# From dictionary
style = Style.from_dict({
    'class-name': 'style-string',
})

# From list of tuples
style = Style([
    ('class-name', 'style-string'),
])
```

## Style String Syntax

A style string is space-separated attributes and colors:

```
[fg-color] [bg:bg-color] [attributes...]
```

### Foreground Colors
```python
'#ff0000'          # Hex color
'red'              # Named color
'ansibrightred'    # ANSI color
'default'          # Terminal default
```

### Background Colors
```python
'bg:#ff0000'       # Hex background
'bg:red'           # Named background
'bg:ansibrightred' # ANSI background
'bg:default'       # Terminal default background
```

### Attributes
```python
'bold'             # Bold text
'nobold'           # Disable bold
'italic'           # Italic text
'noitalic'         # Disable italic
'underline'        # Underlined
'nounderline'      # Disable underline
'blink'            # Blinking text
'noblink'          # Disable blink
'reverse'          # Swap fg/bg
'noreverse'        # Disable reverse
'hidden'           # Hidden text
'nohidden'         # Disable hidden
'strike'           # Strikethrough
'nostrike'         # Disable strike
```

### Complete Examples
```python
Style.from_dict({
    # Just foreground
    'text': '#ffffff',

    # Foreground and background
    'selected': '#000000 bg:#ffff00',

    # All components
    'error': '#ffffff bg:#ff0000 bold underline',

    # Just attributes (inherits colors)
    'emphasis': 'bold italic',

    # Reset and set
    'clean': 'nobold noitalic #ffffff',
})
```

## Named Colors

```python
NAMED_COLORS = {
    'black': '#000000',
    'red': '#aa0000',
    'green': '#00aa00',
    'yellow': '#aaaa00',
    'blue': '#0000aa',
    'magenta': '#aa00aa',
    'cyan': '#00aaaa',
    'white': '#aaaaaa',
    'gray': '#888888',
    'grey': '#888888',
    # Plus bright variants
    'brightblack': '#555555',
    'brightred': '#ff5555',
    # ...
}
```

## ANSI Colors

16-color ANSI palette (most portable):

```python
# Standard colors (0-7)
'ansiblack'        # Color 0
'ansired'          # Color 1
'ansigreen'        # Color 2
'ansiyellow'       # Color 3
'ansiblue'         # Color 4
'ansimagenta'      # Color 5
'ansicyan'         # Color 6
'ansiwhite'        # Color 7

# Bright colors (8-15)
'ansibrightblack'  # Color 8 (gray)
'ansibrightred'    # Color 9
'ansibrightgreen'  # Color 10
'ansibrightyellow' # Color 11
'ansibrightblue'   # Color 12
'ansibrightmagenta'# Color 13
'ansibrightcyan'   # Color 14
'ansibrightwhite'  # Color 15
```

## Style Methods

```python
# Combine styles
merged = style.get_attrs_for_style_str(
    'class:myclass',
    default='#ffffff',
)

# Invalidate cache (after dynamic changes)
style.invalidation_hash()
```

## merge_styles

```python
from prompt_toolkit.styles import merge_styles

combined = merge_styles([
    base_style,      # Lowest priority
    theme_style,
    user_overrides,  # Highest priority
])
```

Later styles override earlier ones for the same class.

## DynamicStyle

```python
from prompt_toolkit.styles import DynamicStyle

current_theme = 'dark'

def get_style():
    if current_theme == 'dark':
        return dark_style
    return light_style

dynamic = DynamicStyle(get_style)
```

## Pygments Integration

### Import Pygments Style

```python
from prompt_toolkit.styles import style_from_pygments_cls
from pygments.styles import get_style_by_name

# Get Pygments style class
pygments_cls = get_style_by_name('monokai')

# Convert to prompt_toolkit style
style = style_from_pygments_cls(pygments_cls)
```

### Merge with Custom Styles

```python
from prompt_toolkit.styles import merge_styles, Style, style_from_pygments_cls
from pygments.styles import get_style_by_name

pygments_style = style_from_pygments_cls(get_style_by_name('monokai'))

custom_style = Style.from_dict({
    'completion-menu': 'bg:#333333',
    'prompt': 'bold #00ff00',
})

combined = merge_styles([pygments_style, custom_style])
```

### PygmentsLexer

```python
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer, SqlLexer, JsonLexer

# For Python code
python_lexer = PygmentsLexer(PythonLexer)

# For SQL
sql_lexer = PygmentsLexer(SqlLexer)

# Use in BufferControl
control = BufferControl(buffer=my_buffer, lexer=python_lexer)
```

## FormattedText Types

### to_formatted_text

```python
from prompt_toolkit.formatted_text import to_formatted_text

# Convert various types to FormattedText
formatted = to_formatted_text("plain string")
formatted = to_formatted_text([('class:x', 'text')])
formatted = to_formatted_text(HTML('<b>bold</b>'))
```

### HTML

```python
from prompt_toolkit.formatted_text import HTML

text = HTML('<b>Bold</b> and <i>italic</i>')
text = HTML('<style fg="red" bg="white">Colored</style>')
text = HTML('<u>Underline</u> <s>Strike</s>')

# In handler
text = HTML(f'Hello <b>{name}</b>!')
```

**Supported HTML tags:**
- `<b>` - Bold
- `<i>` - Italic
- `<u>` - Underline
- `<s>` - Strikethrough
- `<blink>` - Blinking
- `<reverse>` - Reverse video
- `<hidden>` - Hidden
- `<style>` - Custom styling with `fg`, `bg` attributes

### ANSI

```python
from prompt_toolkit.formatted_text import ANSI

# Parse ANSI escape codes
text = ANSI('\x1b[31mRed\x1b[0m normal \x1b[1mBold\x1b[0m')

# From external command output
import subprocess
output = subprocess.check_output(['ls', '--color=always'])
text = ANSI(output.decode())
```

### PygmentsTokens

```python
from prompt_toolkit.formatted_text import PygmentsTokens
from pygments.lexers import PythonLexer
from pygments import lex

code = 'def hello(): pass'
tokens = list(lex(code, PythonLexer()))
text = PygmentsTokens(tokens)
```

### Fragment List (Style Tuples)

```python
# List of (style, text) tuples
text = [
    ('class:prompt', '>>> '),
    ('class:keyword', 'def'),
    ('', ' '),
    ('class:function', 'hello'),
    ('class:operator', '():'),
    ('', '\n'),
]
```

## FormattedTextControl

```python
from prompt_toolkit.layout.controls import FormattedTextControl

# Static text
control = FormattedTextControl(text='Hello')

# Dynamic text (callable)
def get_text():
    return [('class:time', datetime.now().strftime('%H:%M:%S'))]

control = FormattedTextControl(get_text)

# With focusable=True for clickable text
control = FormattedTextControl(
    text,
    focusable=True,
    key_bindings=my_bindings,
)
```

## Style Transformations

```python
from prompt_toolkit.styles import (
    SwapLightAndDarkStyleTransformation,
    ReverseStyleTransformation,
    SetDefaultColorStyleTransformation,
    AdjustBrightnessStyleTransformation,
)

# Swap light/dark colors
app = Application(
    style_transformation=SwapLightAndDarkStyleTransformation(),
)

# Adjust brightness
app = Application(
    style_transformation=AdjustBrightnessStyleTransformation(0.5),
)
```

## Default Styles

```python
from prompt_toolkit.styles import default_ui_style, default_pygments_style

# Get default prompt_toolkit UI style
ui_style = default_ui_style()

# Get default Pygments style
pygments_style = default_pygments_style()
```

## Built-in Style Classes

Prompt toolkit recognizes these class names:

```python
# Prompt
'prompt', 'prompt.arg'

# Completion
'completion-menu', 'completion-menu.completion',
'completion-menu.completion.current',
'completion-menu.meta.completion',
'completion-menu.meta.completion.current',
'completion-menu.multi-column-meta'

# Scrollbar
'scrollbar.background', 'scrollbar.button', 'scrollbar.arrow'

# Search
'search', 'search.current', 'search-toolbar', 'search-toolbar.text'

# Validation
'validation-toolbar', 'validation-toolbar.text'

# Bottom toolbar
'bottom-toolbar', 'bottom-toolbar.text'

# Selection
'selected'

# Cursor
'cursor-line', 'cursor-column'

# Line numbers
'line-number', 'line-number.current'
```

## Color Depth

```python
from prompt_toolkit.output import ColorDepth

app = Application(
    color_depth=ColorDepth.DEPTH_24_BIT,  # True color
    # ColorDepth.DEPTH_8_BIT   # 256 colors
    # ColorDepth.DEPTH_4_BIT   # 16 colors
    # ColorDepth.DEPTH_1_BIT   # Monochrome
)
```

## Print Formatted

```python
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

style = Style.from_dict({'warning': 'bg:yellow #000000'})

print_formatted_text(
    HTML('<warning>Warning message</warning>'),
    style=style,
)
```
