# Application API Reference

Complete API for prompt_toolkit Application class.

## Constructor

```python
Application(
    layout: Layout | None = None,
    style: BaseStyle | None = None,
    include_default_pygments_style: bool = True,
    style_transformation: StyleTransformation | None = None,
    key_bindings: KeyBindingsBase | None = None,
    clipboard: Clipboard | None = None,
    full_screen: bool = False,
    color_depth: ColorDepth | Callable[[], ColorDepth | None] | None = None,
    mouse_support: FilterOrBool = False,
    enable_page_navigation_bindings: FilterOrBool | None = None,
    paste_mode: FilterOrBool = False,
    editing_mode: EditingMode = EditingMode.EMACS,
    erase_when_done: bool = False,
    reverse_vi_search_direction: FilterOrBool = False,
    min_redraw_interval: float | int | None = None,
    max_render_postpone_time: float | int | None = 0.01,
    refresh_interval: float | None = None,
    terminal_size_polling_interval: float | None = 0.5,
    cursor: AnyCursorShapeConfig = None,
    on_reset: Callable[[], None] | None = None,
    on_invalidate: Callable[[], None] | None = None,
    before_render: Callable[[Application], None] | None = None,
    after_render: Callable[[Application], None] | None = None,
    input: Input | None = None,
    output: Output | None = None,
)
```

## Key Parameters

### Display
- **`layout`** - Layout containing the UI tree
- **`style`** - Style object for colors/formatting
- **`full_screen`** - Use entire terminal vs inline
- **`erase_when_done`** - Clear screen on exit
- **`color_depth`** - Color support level (24-bit, 256, 16, mono)

### Input
- **`key_bindings`** - KeyBindings for keyboard handling
- **`mouse_support`** - Enable mouse events
- **`editing_mode`** - EMACS or VI mode
- **`clipboard`** - Clipboard implementation

### Performance
- **`min_redraw_interval`** - Minimum time between redraws (seconds)
- **`max_render_postpone_time`** - Max postpone time for batching
- **`refresh_interval`** - Auto-refresh interval for dynamic content

### Events
- **`on_reset`** - Called on app reset
- **`on_invalidate`** - Called when invalidated
- **`before_render`** - Called before each render
- **`after_render`** - Called after each render

## Methods

### Running

```python
# Synchronous (blocking)
result = app.run(
    pre_run: Callable[[], None] | None = None,
    set_exception_handler: bool = True,
    handle_sigint: bool = True,
    in_thread: bool = False,
) -> Any

# Asynchronous
result = await app.run_async(
    pre_run: Callable[[], None] | None = None,
    set_exception_handler: bool = True,
    handle_sigint: bool = True,
    slow_callback_duration: float = 0.5,
) -> Any
```

### Exiting

```python
# Exit with optional result
app.exit(result: Any = None)

# Exit with exception
app.exit(exception: BaseException)

# Check if exiting
if app.is_done:
    ...
```

### UI Control

```python
# Request redraw
app.invalidate()

# Suspend/resume
app.suspend_to_background(suspend_group: bool = True)

# Reset state
app.reset()

# Get rendering size
rows, cols = app.output.get_size()
```

### Background Tasks

```python
# Create managed background task
app.create_background_task(coroutine)

# Access all background tasks
tasks = app._background_tasks
```

## Properties

### State
```python
app.is_done: bool              # True if exit() called
app.is_running: bool           # True if app is running
app.current_buffer: Buffer     # Currently focused buffer
app.current_search_state       # Search state if searching
```

### Input/Output
```python
app.input: Input               # Input handler
app.output: Output             # Output handler
app.clipboard: Clipboard       # Clipboard instance
```

### Configuration
```python
app.layout: Layout             # Current layout
app.style: BaseStyle           # Current style
app.key_bindings: KeyBindings  # Key bindings
app.editing_mode: EditingMode  # VI or EMACS
```

### VI Mode State
```python
app.vi_state: ViState          # VI mode state
app.emacs_state: EmacsState    # Emacs mode state
```

## Events

Events are `Event` objects with `+=` and `-=` for handlers:

```python
# Add handler
app.on_invalidate += my_handler

# Remove handler
app.on_invalidate -= my_handler

# Available events
app.on_reset           # App reset
app.on_invalidate      # Invalidation requested
app.before_render      # Before rendering (receives app)
app.after_render       # After rendering (receives app)
```

## EditingMode

```python
from prompt_toolkit.enums import EditingMode

app = Application(
    editing_mode=EditingMode.EMACS,  # Default
    # or
    editing_mode=EditingMode.VI,
)

# Change at runtime
app.editing_mode = EditingMode.VI
```

## ColorDepth

```python
from prompt_toolkit.output import ColorDepth

app = Application(
    color_depth=ColorDepth.DEPTH_24_BIT,  # True color (16M colors)
    # ColorDepth.DEPTH_8_BIT,  # 256 colors
    # ColorDepth.DEPTH_4_BIT,  # 16 colors (ANSI)
    # ColorDepth.DEPTH_1_BIT,  # Monochrome
)

# Or dynamic
app = Application(
    color_depth=lambda: ColorDepth.DEPTH_24_BIT if supports_true_color() else ColorDepth.DEPTH_8_BIT,
)
```

## Cursor Shapes

```python
from prompt_toolkit.cursor_shapes import CursorShape

app = Application(
    cursor=CursorShape.BLOCK,
    # CursorShape.BEAM,
    # CursorShape.UNDERLINE,
    # CursorShape.BLINKING_BLOCK,
    # CursorShape.BLINKING_BEAM,
    # CursorShape.BLINKING_UNDERLINE,
)

# Or modal cursors
app = Application(
    cursor=ModalCursorShapeConfig(
        cursor=CursorShape.BEAM,
        vi_navigation=CursorShape.BLOCK,
    ),
)
```

## Input/Output Customization

```python
from prompt_toolkit.input import create_input
from prompt_toolkit.output import create_output

# Custom input
custom_input = create_input(stdin=my_stdin)

# Custom output
custom_output = create_output(stdout=my_stdout)

app = Application(
    input=custom_input,
    output=custom_output,
)
```

## Thread Safety

```python
# Call from another thread
from prompt_toolkit.application import call_from_executor

def background_thread():
    # Safe way to call app methods from another thread
    call_from_executor(lambda: app.invalidate())
```

## Global Application Access

```python
from prompt_toolkit.application import (
    get_app,
    get_app_or_none,
    get_app_session,
)

# Get current app (raises if none running)
app = get_app()

# Get current app or None
app = get_app_or_none()

# Get app session (context)
session = get_app_session()
```

## run_in_terminal

```python
from prompt_toolkit.application import run_in_terminal

async def handler(event):
    # Run code while app is suspended
    await run_in_terminal(
        func=lambda: print("Hello from terminal!"),
        render_cli_done: bool = False,
        in_executor: bool = True,
    )
```

**Parameters:**
- `func` - Callable to execute
- `render_cli_done` - Render UI before suspension
- `in_executor` - Run in thread pool (for blocking code)

## Application Lifecycle

```
1. Application() created
   └─ Layout, key bindings, style configured

2. app.run() or app.run_async() called
   └─ Event loop starts
   └─ on_reset event fired
   └─ First render

3. Running loop:
   ├─ Wait for input
   ├─ Process key bindings
   ├─ Update buffers
   ├─ If invalidated:
   │   ├─ on_invalidate event
   │   ├─ before_render event
   │   ├─ Render to terminal
   │   └─ after_render event
   └─ Repeat until exit()

4. app.exit() called
   └─ is_done = True
   └─ Event loop exits

5. app.run() returns
   └─ Result value returned
   └─ erase_when_done clears screen (if enabled)
```

## Error Handling

```python
async def main():
    try:
        result = await app.run_async()
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        pass
```

## Minimal Application Example

```python
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

kb = KeyBindings()

@kb.add('c-c')
def exit_(event):
    event.app.exit()

app = Application(
    layout=Layout(Window(FormattedTextControl('Press Ctrl-C to exit'))),
    key_bindings=kb,
    full_screen=True,
)

if __name__ == '__main__':
    app.run()
```
