# Production Layout Patterns

Common layout patterns for prompt_toolkit applications.

## IDE-Style Layout

Three-pane layout with sidebar, editor, and terminal:

```python
from prompt_toolkit.layout import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import Frame

def create_ide_layout(file_tree_buffer, editor_buffer, terminal_buffer):
    """IDE-style layout with file tree, editor, and terminal."""

    file_tree = Frame(
        Window(BufferControl(file_tree_buffer)),
        title="Files",
        width=D(min=20, preferred=30, max=40),
    )

    editor = Frame(
        Window(BufferControl(editor_buffer), wrap_lines=True),
        title="Editor",
    )

    terminal = Frame(
        Window(BufferControl(terminal_buffer)),
        title="Terminal",
        height=D(min=5, preferred=10, max=20),
    )

    main_area = HSplit([
        VSplit([
            file_tree,
            editor,
        ]),
        terminal,
    ])

    return FloatContainer(
        content=main_area,
        floats=[],  # Add dialogs, menus here
    )
```

## REPL Layout

Input prompt with scrollable output history:

```python
def create_repl_layout(output_buffer, input_buffer):
    """REPL with output history above input."""

    output_window = Window(
        BufferControl(output_buffer),
        wrap_lines=True,
        # Fill available space
    )

    input_window = Window(
        BufferControl(input_buffer, focus_on_click=True),
        height=D(min=1, preferred=3, max=10),
        wrap_lines=True,
    )

    return HSplit([
        output_window,
        Window(height=1, char='─', style='class:separator'),
        input_window,
    ])
```

## Dashboard Layout

Grid of status panels:

```python
def create_dashboard_layout(panels: list[tuple[str, str]]):
    """Dashboard with grid of status panels."""

    def make_panel(title: str, content: str):
        return Frame(
            Window(FormattedTextControl(content)),
            title=title,
        )

    # Create 2x2 grid
    row1 = VSplit([
        make_panel(panels[0][0], panels[0][1]),
        make_panel(panels[1][0], panels[1][1]),
    ])

    row2 = VSplit([
        make_panel(panels[2][0], panels[2][1]),
        make_panel(panels[3][0], panels[3][1]),
    ])

    return HSplit([row1, row2])
```

## Modal Dialog Pattern

Dialog floating over main content:

```python
from prompt_toolkit.filters import Condition

class DialogManager:
    def __init__(self):
        self.dialog_visible = False
        self.dialog_content = None

    def show(self, content):
        self.dialog_content = content
        self.dialog_visible = True

    def hide(self):
        self.dialog_visible = False

dialog_manager = DialogManager()

def create_layout_with_dialog(main_content):
    dialog_filter = Condition(lambda: dialog_manager.dialog_visible)

    dialog = ConditionalContainer(
        content=Frame(
            DynamicContainer(lambda: dialog_manager.dialog_content or Window()),
            title="Dialog",
        ),
        filter=dialog_filter,
    )

    # Semi-transparent background
    dialog_background = ConditionalContainer(
        content=Window(style='class:dialog-background'),
        filter=dialog_filter,
    )

    return FloatContainer(
        content=main_content,
        floats=[
            Float(content=dialog_background),  # Background overlay
            Float(content=dialog),  # Centered dialog
        ]
    )
```

## Completion Menu Pattern

Completion menu that follows cursor:

```python
from prompt_toolkit.layout.menus import CompletionsMenu

def create_layout_with_completions(main_buffer):
    body = Window(BufferControl(main_buffer))

    return FloatContainer(
        content=body,
        floats=[
            Float(
                xcursor=True,
                ycursor=True,
                content=CompletionsMenu(max_height=16, scroll_offset=1),
            )
        ]
    )
```

## Sidebar Toggle Pattern

Toggleable sidebar:

```python
class AppState:
    sidebar_visible = True

state = AppState()

def toggle_sidebar():
    state.sidebar_visible = not state.sidebar_visible

sidebar_filter = Condition(lambda: state.sidebar_visible)

layout = VSplit([
    ConditionalContainer(
        content=Window(sidebar_control, width=30),
        filter=sidebar_filter,
    ),
    ConditionalContainer(
        content=Window(width=1, char='│'),
        filter=sidebar_filter,
    ),
    Window(main_control),
])
```

## Tab Container Pattern

Tabbed interface:

```python
class TabContainer:
    def __init__(self, tabs: dict[str, AnyContainer]):
        self.tabs = tabs
        self.active_tab = list(tabs.keys())[0]

    def get_tab_bar(self):
        parts = []
        for name in self.tabs:
            if name == self.active_tab:
                parts.append(('class:tab.active', f' {name} '))
            else:
                parts.append(('class:tab', f' {name} '))
            parts.append(('', ' '))
        return parts

    def get_content(self):
        return self.tabs[self.active_tab]

    def next_tab(self):
        names = list(self.tabs.keys())
        idx = names.index(self.active_tab)
        self.active_tab = names[(idx + 1) % len(names)]

    def create_layout(self):
        return HSplit([
            Window(
                FormattedTextControl(self.get_tab_bar),
                height=1,
                style='class:tab-bar',
            ),
            DynamicContainer(self.get_content),
        ])
```

## Resizable Split Pattern

User-adjustable split:

```python
# Note: prompt_toolkit doesn't have built-in resize handles,
# but you can implement with key bindings

class ResizableSplit:
    def __init__(self, left, right, initial_ratio=0.5):
        self.left = left
        self.right = right
        self.ratio = initial_ratio

    def create_layout(self):
        left_weight = int(self.ratio * 100)
        right_weight = 100 - left_weight

        return VSplit([
            HSplit([self.left], width=D(weight=left_weight)),
            Window(width=1, char='│', style='class:separator'),
            HSplit([self.right], width=D(weight=right_weight)),
        ])

    def increase_left(self, amount=0.05):
        self.ratio = min(0.9, self.ratio + amount)

    def decrease_left(self, amount=0.05):
        self.ratio = max(0.1, self.ratio - amount)
```

## Status Bar Pattern

Status bar with multiple sections:

```python
def create_status_bar(get_left, get_center, get_right):
    """Status bar with left, center, and right sections."""

    return VSplit([
        Window(
            FormattedTextControl(get_left),
            style='class:status',
            dont_extend_width=True,
        ),
        Window(
            FormattedTextControl(get_center),
            style='class:status',
            align=WindowAlign.CENTER,
        ),
        Window(
            FormattedTextControl(get_right),
            style='class:status',
            dont_extend_width=True,
            align=WindowAlign.RIGHT,
        ),
    ], height=1)
```

## Line Numbers Pattern

Editor with line numbers margin:

```python
from prompt_toolkit.layout.margins import NumberedMargin, ScrollbarMargin

editor_window = Window(
    BufferControl(editor_buffer),
    left_margins=[
        NumberedMargin(),
    ],
    right_margins=[
        ScrollbarMargin(display_arrows=True),
    ],
    wrap_lines=False,
    cursorline=True,
)
```

## Best Practices

1. **Use Dimension weights** for proportional sizing instead of fixed values
2. **Wrap with FloatContainer** at root for dialogs and menus
3. **Use ConditionalContainer** for show/hide, not rebuilding layout
4. **Keep layout tree shallow** for better performance
5. **Use DynamicContainer** sparingly - rebuilds on every render
6. **Test with different terminal sizes** to ensure responsive layout
