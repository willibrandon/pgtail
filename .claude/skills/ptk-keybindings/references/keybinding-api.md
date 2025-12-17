# Key Binding API Reference

Complete API for prompt_toolkit key binding system.

## KeyBindings Class

```python
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()
```

### Adding Bindings

```python
@kb.add(*keys, **kwargs)
def handler(event):
    pass

# Or without decorator
def my_handler(event):
    pass
kb.add('c-t')(my_handler)
```

### Decorator Parameters

```python
kb.add(
    *keys: Keys | str,           # Key(s) to bind
    filter: FilterOrBool = True,  # Condition for activation
    eager: FilterOrBool = False,  # Handle immediately, skip longer sequences
    is_global: FilterOrBool = False,  # Ignore focus, always check
    save_before: Callable[[KeyPressEvent], bool] = (lambda e: True),
    record_in_macro: FilterOrBool = True,
)
```

**Parameters explained:**

- **keys**: One or more key names. Multiple keys create a sequence.
- **filter**: Only activate when filter returns True.
- **eager**: When True, execute immediately without waiting to see if user is typing a longer sequence.
- **is_global**: When True, binding is checked regardless of focus.
- **save_before**: Function called before handler. If returns True, undo state is saved.
- **record_in_macro**: Include in macro recording when True.

### Removing Bindings

```python
# Remove by handler function
kb.remove(my_handler)

# Remove by key (removes all handlers for that key)
kb.remove('c-t')
```

### Properties

```python
kb.bindings  # List of all Binding objects
```

## Binding Object

```python
class Binding:
    keys: tuple[Keys | str, ...]
    handler: Callable[[KeyPressEvent], None]
    filter: Filter
    eager: Filter
    is_global: Filter
    save_before: Callable[[KeyPressEvent], bool]
    record_in_macro: Filter
```

## KeyPressEvent

Passed to every handler:

```python
class KeyPressEvent:
    # Application access
    app: Application
    current_buffer: Buffer

    # Key information
    data: str              # Character data for Keys.Any
    key_sequence: list[KeyPress]  # Full sequence that triggered
    is_repeat: bool        # True if key held down

    # Vi-style numeric argument
    arg: int              # Default 1
    arg_present: bool     # True if user typed number prefix

    # Methods
    def invalidate() -> None  # Request UI redraw
```

### Using Key Data

```python
from prompt_toolkit.keys import Keys

@kb.add(Keys.Any)
def _(event):
    # Handle any key not matched by other bindings
    char = event.data
    if char.isprintable():
        event.current_buffer.insert_text(char)
```

## Merging Key Bindings

```python
from prompt_toolkit.key_binding import merge_key_bindings

merged = merge_key_bindings([
    application_bindings,
    mode_specific_bindings,
    user_bindings,
])
```

**Order matters**: Later bindings override earlier ones (for same key + filter).

## ConditionalKeyBindings

Wrap bindings to add a global filter:

```python
from prompt_toolkit.key_binding import ConditionalKeyBindings

editor_bindings = KeyBindings()
# ... define bindings ...

conditional = ConditionalKeyBindings(
    editor_bindings,
    filter=has_focus('editor'),
)
```

## DynamicKeyBindings

Switch bindings at runtime:

```python
from prompt_toolkit.key_binding import DynamicKeyBindings

def get_bindings():
    if mode == 'edit':
        return edit_bindings
    return view_bindings

dynamic = DynamicKeyBindings(get_bindings)
```

## Built-in Key Bindings

### Loading Defaults

```python
from prompt_toolkit.key_binding.defaults import load_key_bindings

# Returns KeyBindings with default emacs/vi bindings
defaults = load_key_bindings()
```

### Built-in Binding Modules

Located in `prompt_toolkit.key_binding.bindings`:

- `basic` - Basic editing (backspace, delete, etc.)
- `emacs` - Emacs key bindings
- `vi` - Vi key bindings
- `completion` - Completion menu navigation
- `search` - Search mode bindings
- `scroll` - Scrolling bindings
- `focus` - Focus navigation
- `mouse` - Mouse event handling
- `page_navigation` - Page up/down

### Example: Adding to Defaults

```python
from prompt_toolkit.key_binding.defaults import load_key_bindings

kb = load_key_bindings()

# Add custom binding on top of defaults
@kb.add('c-t')
def custom_binding(event):
    pass
```

## Key Names Reference

### Printable Characters
- Single characters: `'a'`, `'A'`, `'1'`, `'@'`, etc.
- With modifiers: `'c-a'`, `'m-a'`, `'c-s-a'`

### Special Keys

```python
# Navigation
'up', 'down', 'left', 'right'
'home', 'end'
'pageup', 'pagedown'

# Editing
'enter', 'tab', 'backspace', 'delete', 'insert'
'space'

# Escape
'escape'

# Function keys
'f1', 'f2', ..., 'f24'

# With modifiers
'c-left', 'c-right'  # Ctrl+Arrow
's-up', 's-down'     # Shift+Arrow
'c-home', 'c-end'    # Ctrl+Home/End
```

### Keys Enum

```python
from prompt_toolkit.keys import Keys

Keys.ControlA       # Same as 'c-a'
Keys.ControlC       # Same as 'c-c'
Keys.Enter          # Same as 'enter'
Keys.Tab            # Same as 'tab'
Keys.Escape         # Same as 'escape'
Keys.Backspace      # Same as 'backspace'
Keys.Delete         # Same as 'delete'
Keys.Up, Keys.Down, Keys.Left, Keys.Right
Keys.Home, Keys.End
Keys.PageUp, Keys.PageDown
Keys.F1, Keys.F2, ..., Keys.F24
Keys.Any            # Wildcard - matches any single key
Keys.CPRResponse    # Terminal cursor position response
Keys.Vt100MouseEvent  # Mouse event
Keys.BracketedPaste   # Bracketed paste start
```

## Handler Patterns

### Basic Handler
```python
@kb.add('c-s')
def save_handler(event):
    save_document(event.current_buffer.text)
```

### Async Handler
```python
@kb.add('c-r')
async def refresh_handler(event):
    data = await fetch_remote_data()
    event.current_buffer.set_document(Document(data))
```

### Handler with Numeric Argument
```python
@kb.add('c-d')
def delete_chars(event):
    # Vi-style: 3<C-d> deletes 3 characters
    count = event.arg
    event.current_buffer.delete(count)
```

### Return NotImplemented
```python
@kb.add(Keys.Any)
def fallback(event):
    if not handle_key(event.data):
        return NotImplemented  # Skip UI invalidation
```

## Common Patterns

### Modal Bindings (like Vim)

```python
from prompt_toolkit.filters import Condition

class AppState:
    mode = 'normal'

state = AppState()

normal_mode = Condition(lambda: state.mode == 'normal')
insert_mode = Condition(lambda: state.mode == 'insert')

@kb.add('i', filter=normal_mode)
def enter_insert(event):
    state.mode = 'insert'

@kb.add('escape', filter=insert_mode)
def exit_insert(event):
    state.mode = 'normal'

@kb.add(Keys.Any, filter=insert_mode)
def insert_char(event):
    if event.data.isprintable():
        event.current_buffer.insert_text(event.data)
```

### Leader Key Pattern

```python
# Space as leader key
@kb.add('space', 'w')  # <Space>w = save
def leader_save(event):
    save()

@kb.add('space', 'q')  # <Space>q = quit
def leader_quit(event):
    event.app.exit()
```

### Context-Sensitive Bindings

```python
@kb.add('enter', filter=has_completions())
def accept_completion(event):
    event.current_buffer.complete_state.accept()

@kb.add('enter', filter=~has_completions() & has_focus('input'))
def submit_input(event):
    process(event.current_buffer.text)
```

## Debugging Key Bindings

```python
# Print all active bindings
for binding in kb.bindings:
    print(f"Keys: {binding.keys}, Filter: {binding.filter}")

# In handler, log key sequence
@kb.add(Keys.Any)
def debug_handler(event):
    print(f"Key sequence: {event.key_sequence}")
    print(f"Data: {event.data!r}")
    return NotImplemented  # Let other handlers process
```
