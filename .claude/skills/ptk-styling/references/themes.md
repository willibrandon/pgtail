# Theme Examples

Pre-built theme configurations for prompt_toolkit applications.

## Dark Theme

```python
from prompt_toolkit.styles import Style

DARK_THEME = Style.from_dict({
    # Base colors
    '':                     '#d4d4d4',
    'class:text':           '#d4d4d4',

    # Prompt
    'class:prompt':         'bold #569cd6',
    'class:prompt.arg':     '#9cdcfe',

    # Input
    'class:input':          '#d4d4d4',
    'class:input.cursor':   'reverse',

    # Completion menu
    'completion-menu':                      'bg:#252526 #cccccc',
    'completion-menu.completion':           '',
    'completion-menu.completion.current':   'bg:#094771 #ffffff',
    'completion-menu.meta.completion':      'bg:#1e1e1e #808080',
    'completion-menu.meta.completion.current': 'bg:#094771 #ffffff',

    # Scrollbar
    'scrollbar.background':  'bg:#1e1e1e',
    'scrollbar.button':      'bg:#424242',

    # Search
    'search':           'bg:#613214 #ffffff',
    'search.current':   'bg:#515c6a #ffffff',

    # Selection
    'selected':         'bg:#264f78',

    # Status bar
    'class:status':         'bg:#007acc #ffffff',
    'class:status.key':     'bold',
    'class:status.mode':    'bg:#68217a #ffffff bold',

    # Sidebar
    'class:sidebar':        'bg:#252526 #cccccc',
    'class:sidebar.title':  'bg:#3c3c3c #cccccc bold',
    'class:sidebar.item':   '',
    'class:sidebar.item.selected': 'bg:#094771 #ffffff',

    # Dialogs
    'class:dialog':         'bg:#252526',
    'class:dialog.body':    'bg:#1e1e1e #cccccc',
    'class:dialog-shadow':  'bg:#000000',

    # Borders
    'class:border':         '#3c3c3c',

    # Line numbers
    'line-number':          '#858585',
    'line-number.current':  '#c6c6c6',

    # Cursor line
    'cursor-line':          'bg:#282828',
})
```

## Light Theme

```python
LIGHT_THEME = Style.from_dict({
    # Base colors
    '':                     '#000000',
    'class:text':           '#000000',

    # Prompt
    'class:prompt':         'bold #0000ff',
    'class:prompt.arg':     '#001080',

    # Input
    'class:input':          '#000000',

    # Completion menu
    'completion-menu':                      'bg:#f3f3f3 #000000',
    'completion-menu.completion':           '',
    'completion-menu.completion.current':   'bg:#0060c0 #ffffff',
    'completion-menu.meta.completion':      'bg:#e8e8e8 #666666',
    'completion-menu.meta.completion.current': 'bg:#0060c0 #ffffff',

    # Scrollbar
    'scrollbar.background':  'bg:#e8e8e8',
    'scrollbar.button':      'bg:#c4c4c4',

    # Search
    'search':           'bg:#ffff00 #000000',
    'search.current':   'bg:#ff9632 #000000',

    # Selection
    'selected':         'bg:#add6ff',

    # Status bar
    'class:status':         'bg:#007acc #ffffff',
    'class:status.key':     'bold',
    'class:status.mode':    'bg:#68217a #ffffff bold',

    # Sidebar
    'class:sidebar':        'bg:#f3f3f3 #000000',
    'class:sidebar.title':  'bg:#e8e8e8 #000000 bold',
    'class:sidebar.item.selected': 'bg:#0060c0 #ffffff',

    # Dialogs
    'class:dialog':         'bg:#f3f3f3',
    'class:dialog.body':    'bg:#ffffff #000000',

    # Borders
    'class:border':         '#d4d4d4',

    # Line numbers
    'line-number':          '#237893',
    'line-number.current':  '#0b216f bold',

    # Cursor line
    'cursor-line':          'bg:#fffbdd',
})
```

## Monokai Theme

```python
MONOKAI_THEME = Style.from_dict({
    # Base
    '':                     '#f8f8f2',
    'class:text':           '#f8f8f2 bg:#272822',

    # Prompt
    'class:prompt':         'bold #a6e22e',
    'class:prompt.arg':     '#fd971f',

    # Completion
    'completion-menu':                      'bg:#3e3d32 #f8f8f2',
    'completion-menu.completion.current':   'bg:#75715e #f8f8f2',
    'completion-menu.meta.completion':      'bg:#272822 #75715e',

    # Scrollbar
    'scrollbar.background':  'bg:#3e3d32',
    'scrollbar.button':      'bg:#75715e',

    # Search
    'search':           'bg:#e6db74 #272822',
    'search.current':   'bg:#f92672 #f8f8f2',

    # Selection
    'selected':         'bg:#49483e',

    # Status
    'class:status':         'bg:#3e3d32 #a6e22e',
    'class:status.mode':    'bg:#f92672 #f8f8f2 bold',

    # Line numbers
    'line-number':          '#75715e',
    'line-number.current':  '#f8f8f2',

    # Cursor
    'cursor-line':          'bg:#3e3d32',
})
```

## Solarized Dark Theme

```python
SOLARIZED_DARK = Style.from_dict({
    # Base colors (Solarized palette)
    '':                     '#839496',  # base0
    'class:text':           '#839496 bg:#002b36',  # base0 on base03

    # Prompt
    'class:prompt':         'bold #268bd2',  # blue
    'class:prompt.arg':     '#2aa198',  # cyan

    # Completion
    'completion-menu':                      'bg:#073642 #839496',  # base02/base0
    'completion-menu.completion.current':   'bg:#586e75 #fdf6e3',  # base01/base3
    'completion-menu.meta.completion':      'bg:#002b36 #657b83',  # base03/base00

    # Search
    'search':           'bg:#b58900 #002b36',  # yellow on base03
    'search.current':   'bg:#cb4b16 #fdf6e3',  # orange on base3

    # Selection
    'selected':         'bg:#073642',  # base02

    # Status
    'class:status':         'bg:#073642 #93a1a1',  # base02/base1
    'class:status.mode':    'bg:#268bd2 #fdf6e3 bold',  # blue/base3

    # Line numbers
    'line-number':          '#586e75',  # base01
    'line-number.current':  '#93a1a1',  # base1

    # Keywords and syntax
    'class:keyword':        '#859900',  # green
    'class:string':         '#2aa198',  # cyan
    'class:number':         '#d33682',  # magenta
    'class:comment':        '#586e75 italic',  # base01
    'class:function':       '#268bd2',  # blue
    'class:class':          '#b58900',  # yellow
    'class:error':          '#dc322f bold',  # red
})
```

## Nord Theme

```python
NORD_THEME = Style.from_dict({
    # Base (Nord palette)
    '':                     '#d8dee9',  # nord4
    'class:text':           '#d8dee9 bg:#2e3440',  # nord4 on nord0

    # Prompt
    'class:prompt':         'bold #88c0d0',  # nord8
    'class:prompt.arg':     '#81a1c1',  # nord9

    # Completion
    'completion-menu':                      'bg:#3b4252 #d8dee9',  # nord1/nord4
    'completion-menu.completion.current':   'bg:#4c566a #eceff4',  # nord3/nord6
    'completion-menu.meta.completion':      'bg:#2e3440 #4c566a',  # nord0/nord3

    # Search
    'search':           'bg:#ebcb8b #2e3440',  # nord13/nord0
    'search.current':   'bg:#bf616a #eceff4',  # nord11/nord6

    # Selection
    'selected':         'bg:#434c5e',  # nord2

    # Status
    'class:status':         'bg:#4c566a #d8dee9',  # nord3/nord4
    'class:status.mode':    'bg:#5e81ac #eceff4 bold',  # nord10/nord6

    # Accent colors
    'class:keyword':        '#81a1c1',  # nord9
    'class:string':         '#a3be8c',  # nord14
    'class:number':         '#b48ead',  # nord15
    'class:comment':        '#616e88 italic',
    'class:function':       '#88c0d0',  # nord8
    'class:error':          '#bf616a bold',  # nord11
    'class:warning':        '#ebcb8b',  # nord13
    'class:success':        '#a3be8c',  # nord14
})
```

## Theme Manager Pattern

```python
from prompt_toolkit.styles import Style, DynamicStyle

class ThemeManager:
    THEMES = {
        'dark': DARK_THEME,
        'light': LIGHT_THEME,
        'monokai': MONOKAI_THEME,
        'solarized': SOLARIZED_DARK,
        'nord': NORD_THEME,
    }

    def __init__(self, default='dark'):
        self.current = default

    def get_style(self):
        return self.THEMES.get(self.current, self.THEMES['dark'])

    def set_theme(self, name):
        if name in self.THEMES:
            self.current = name

    def cycle_theme(self):
        themes = list(self.THEMES.keys())
        idx = themes.index(self.current)
        self.current = themes[(idx + 1) % len(themes)]

    def create_dynamic_style(self):
        return DynamicStyle(self.get_style)


# Usage
theme_manager = ThemeManager()

app = Application(
    style=theme_manager.create_dynamic_style(),
)

# In key binding
@kb.add('c-t')
def cycle_theme(event):
    theme_manager.cycle_theme()
    event.app.invalidate()
```

## High Contrast Theme

For accessibility:

```python
HIGH_CONTRAST = Style.from_dict({
    '':                     '#ffffff bg:#000000',
    'class:prompt':         'bold #00ff00',
    'class:input':          '#ffffff',

    'completion-menu':                      'bg:#000080 #ffffff',
    'completion-menu.completion.current':   'bg:#ffff00 #000000 bold',

    'search':           'bg:#ffff00 #000000 bold',
    'search.current':   'bg:#ff00ff #ffffff bold',

    'selected':         'bg:#0000ff #ffffff',

    'class:status':         'bg:#ffffff #000000',
    'class:error':          '#ff0000 bold underline',
    'class:warning':        '#ffff00 bold',
    'class:success':        '#00ff00 bold',

    'line-number':          '#00ffff',
    'cursor-line':          'bg:#333333',
})
```

## Custom Color Scheme Generator

```python
def generate_theme(
    bg_primary: str,
    bg_secondary: str,
    fg_primary: str,
    fg_secondary: str,
    accent: str,
    accent_alt: str,
    error: str,
    warning: str,
    success: str,
) -> Style:
    """Generate a theme from base colors."""
    return Style.from_dict({
        '':                     f'{fg_primary} bg:{bg_primary}',
        'class:prompt':         f'bold {accent}',
        'class:prompt.arg':     accent_alt,

        'completion-menu':                      f'bg:{bg_secondary} {fg_primary}',
        'completion-menu.completion.current':   f'bg:{accent} #ffffff bold',
        'completion-menu.meta.completion':      f'bg:{bg_primary} {fg_secondary}',

        'search':           f'bg:{warning} {bg_primary}',
        'search.current':   f'bg:{accent_alt} #ffffff',

        'selected':         f'bg:{bg_secondary}',

        'class:status':         f'bg:{bg_secondary} {fg_primary}',
        'class:status.mode':    f'bg:{accent} #ffffff bold',

        'class:error':          f'{error} bold',
        'class:warning':        f'{warning}',
        'class:success':        f'{success}',

        'line-number':          fg_secondary,
        'cursor-line':          f'bg:{bg_secondary}',
    })


# Create custom theme
my_theme = generate_theme(
    bg_primary='#1a1a2e',
    bg_secondary='#16213e',
    fg_primary='#eaeaea',
    fg_secondary='#7f8c8d',
    accent='#e94560',
    accent_alt='#0f3460',
    error='#ff6b6b',
    warning='#feca57',
    success='#1dd1a1',
)
```
