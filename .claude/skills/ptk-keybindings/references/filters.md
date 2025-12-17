# Filters Reference

Filters are callable objects that return True/False to conditionally enable functionality.

## Creating Filters

### From Lambda

```python
from prompt_toolkit.filters import Condition

my_filter = Condition(lambda: some_condition())
```

### From Function

```python
@Condition
def my_filter():
    return some_condition()
```

## Filter Operators

```python
# AND - both must be True
combined = filter1 & filter2

# OR - either can be True
combined = filter1 | filter2

# NOT - invert
inverted = ~filter1

# Complex combinations
complex_filter = (filter1 | filter2) & ~filter3
```

## Built-in Filters

### Focus Filters

```python
from prompt_toolkit.filters import (
    has_focus,           # Check if specific buffer/control has focus
    buffer_has_focus,    # Any buffer has focus
    has_selection,       # Text is selected
    is_read_only,        # Buffer is read-only
    is_multiline,        # Buffer accepts multiple lines
)

# Usage
@kb.add('enter', filter=has_focus('my_buffer'))
def _(event):
    pass
```

### Completion Filters

```python
from prompt_toolkit.filters import (
    has_completions,           # Completion menu is showing
    completion_is_selected,    # A completion is selected
)

@kb.add('tab', filter=has_completions())
def next_completion(event):
    event.current_buffer.complete_next()
```

### Search Filters

```python
from prompt_toolkit.filters import (
    is_searching,              # In search mode
    control_is_searchable,     # Current control supports search
)
```

### Validation Filters

```python
from prompt_toolkit.filters import (
    has_validation_error,      # Buffer has validation error
)
```

### Editing Mode Filters

```python
from prompt_toolkit.filters import (
    vi_mode,                   # Application in vi mode
    emacs_mode,                # Application in emacs mode
    vi_navigation_mode,        # Vi normal mode
    vi_insert_mode,            # Vi insert mode
    vi_insert_multiple_mode,   # Vi insert mode with multiple cursors
    vi_replace_mode,           # Vi replace mode
    vi_selection_mode,         # Vi visual mode
    vi_waiting_for_text_object_mode,  # Waiting for text object
    vi_digraph_mode,           # Entering digraph
    vi_recording_macro,        # Recording macro
)
```

### Input/Output Filters

```python
from prompt_toolkit.filters import (
    renderer_height_is_known,  # Terminal height is known
    in_paste_mode,             # Paste mode active
    is_done,                   # Application is exiting
)
```

### Application Filters

```python
from prompt_toolkit.filters import (
    has_arg,                   # Numeric argument is present
    is_returning,              # Application.exit() called
)
```

## Filter Functions

Some filters are functions that return Filter objects:

```python
from prompt_toolkit.filters import has_focus

# has_focus is a function
editor_focused = has_focus('editor')  # Returns Filter
```

## Creating Custom Filters

### Simple Condition

```python
from prompt_toolkit.filters import Condition

# From lambda
debug_mode = Condition(lambda: app.debug)

# From function
@Condition
def has_unsaved_changes():
    return document.is_modified
```

### Filter with Application Access

```python
from prompt_toolkit.filters import Condition

def create_mode_filter(mode_name):
    @Condition
    def filter():
        # Access app via get_app()
        from prompt_toolkit.application import get_app
        try:
            app = get_app()
            return getattr(app, 'mode', None) == mode_name
        except RuntimeError:
            return False
    return filter

edit_mode = create_mode_filter('edit')
view_mode = create_mode_filter('view')
```

### Parameterized Filter

```python
def has_minimum_lines(n: int):
    @Condition
    def filter():
        from prompt_toolkit.application import get_app
        try:
            buffer = get_app().current_buffer
            return buffer.document.line_count >= n
        except:
            return False
    return filter

@kb.add('c-s', filter=has_minimum_lines(10))
def save_if_substantial(event):
    pass
```

## Filter Class

For complex, reusable filters:

```python
from prompt_toolkit.filters import Filter

class BufferContainsText(Filter):
    def __init__(self, text: str):
        self.text = text

    def __call__(self) -> bool:
        from prompt_toolkit.application import get_app
        try:
            buffer = get_app().current_buffer
            return self.text in buffer.text
        except:
            return False

has_todo = BufferContainsText('TODO')
```

## Always/Never Filters

```python
from prompt_toolkit.filters import Always, Never

# Always returns True
always_active = Always()

# Never returns True (always False)
never_active = Never()
```

## to_filter Conversion

Convert various types to Filter:

```python
from prompt_toolkit.filters import to_filter

# Boolean -> Filter
f = to_filter(True)   # Returns Always()
f = to_filter(False)  # Returns Never()

# Callable -> Filter
f = to_filter(lambda: x > 5)

# Filter -> Filter (passthrough)
f = to_filter(existing_filter)
```

## Common Filter Patterns

### Feature Toggle

```python
class Features:
    autocomplete = True
    syntax_highlight = False

features = Features()

autocomplete_enabled = Condition(lambda: features.autocomplete)

@kb.add('tab', filter=autocomplete_enabled & has_focus('input'))
def trigger_completion(event):
    event.current_buffer.start_completion()
```

### Multi-Mode Application

```python
class AppMode:
    NORMAL = 'normal'
    INSERT = 'insert'
    COMMAND = 'command'

class State:
    mode = AppMode.NORMAL

state = State()

def in_mode(mode):
    return Condition(lambda: state.mode == mode)

normal_mode = in_mode(AppMode.NORMAL)
insert_mode = in_mode(AppMode.INSERT)
command_mode = in_mode(AppMode.COMMAND)

@kb.add(':', filter=normal_mode)
def enter_command_mode(event):
    state.mode = AppMode.COMMAND

@kb.add('escape', filter=insert_mode | command_mode)
def return_to_normal(event):
    state.mode = AppMode.NORMAL
```

### Compound Conditions

```python
# Can edit = has focus AND not read-only AND not searching
can_edit = has_focus('editor') & ~is_read_only() & ~is_searching()

@kb.add('c-d', filter=can_edit)
def delete_line(event):
    pass

# Show help = pressing ? in normal mode without selection
show_help = (
    Condition(lambda: state.mode == 'normal') &
    ~has_selection()
)

@kb.add('?', filter=show_help)
def show_help_dialog(event):
    pass
```

## Filter Evaluation

Filters are evaluated:
- Every time a key is pressed (for key bindings)
- Every render cycle (for ConditionalContainer)
- On demand when used in code

Keep filter functions fast and side-effect free.

```python
# Good - fast evaluation
@Condition
def is_valid():
    return cached_validation_result

# Bad - slow evaluation
@Condition
def is_valid():
    return expensive_validation()  # Called on every keypress!
```

## Debugging Filters

```python
# Check filter value
print(f"Filter active: {my_filter()}")

# Wrap for debugging
def debug_filter(f, name):
    @Condition
    def wrapper():
        result = f()
        print(f"{name}: {result}")
        return result
    return wrapper

debug_mode = debug_filter(
    Condition(lambda: state.mode == 'debug'),
    'debug_mode'
)
```
