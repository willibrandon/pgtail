# Buffer API Reference

Complete API for prompt_toolkit Buffer class.

## Constructor

```python
Buffer(
    completer: Completer | None = None,
    auto_suggest: AutoSuggest | None = None,
    history: History | None = None,
    validator: Validator | None = None,
    tempfile_suffix: str | Callable[[], str] = "",
    tempfile: str | Callable[[], str] = "",
    name: str = "",
    complete_while_typing: FilterOrBool = False,
    validate_while_typing: FilterOrBool = False,
    enable_history_search: FilterOrBool = False,
    document: Document | None = None,
    accept_handler: BufferAcceptHandler | None = None,
    read_only: FilterOrBool = False,
    multiline: FilterOrBool = True,
    max_number_of_completions: int = 10000,
    on_text_changed: BufferEventHandler | None = None,
    on_text_insert: BufferEventHandler | None = None,
    on_cursor_position_changed: BufferEventHandler | None = None,
    on_completions_changed: BufferEventHandler | None = None,
    on_suggestion_set: BufferEventHandler | None = None,
)
```

## Properties

### Text Access
- `text: str` - Current buffer text (read/write)
- `document: Document` - Current Document instance (read-only)
- `cursor_position: int` - Cursor position in text (read/write)

### State
- `selection_state: SelectionState | None` - Current selection
- `validation_state: ValidationState` - Last validation result
- `validation_error: ValidationError | None` - Last validation error
- `complete_state: CompleteState | None` - Current completion state

### Components
- `completer: Completer | None`
- `auto_suggest: AutoSuggest | None`
- `history: History`
- `validator: Validator | None`

### Configuration
- `name: str` - Buffer name
- `read_only: bool` - Whether buffer is read-only
- `multiline: bool` - Whether buffer accepts multiple lines

## Text Manipulation Methods

### Insertion
```python
insert_text(
    data: str,
    overwrite: bool = False,
    move_cursor: bool = True,
    fire_event: bool = True,
) -> None
```

### Deletion
```python
delete_before_cursor(count: int = 1) -> str  # Returns deleted text
delete(count: int = 1) -> str
delete_after_cursor(count: int = 1) -> str

# Delete selection if any, otherwise single char
delete_selection() -> str
```

### Clipboard
```python
copy_selection(keep_selection: bool = False) -> ClipboardData
cut_selection() -> ClipboardData
paste_clipboard_data(
    data: ClipboardData,
    paste_mode: PasteMode = PasteMode.EMACS,
    count: int = 1,
) -> None
```

### Transform
```python
transform_current_line(transform_callback: Callable[[str], str]) -> None
transform_region(
    from_: int,
    to: int,
    transform_callback: Callable[[str], str],
) -> None

# Common transforms
swap_characters_before_cursor() -> None
uppercase_word() -> None
lowercase_word() -> None
capitalize_word() -> None
```

## Cursor Movement

```python
cursor_left(count: int = 1) -> None
cursor_right(count: int = 1) -> None
cursor_up(count: int = 1) -> None
cursor_down(count: int = 1) -> None

# Aliases for word movement
go_to_start_of_next_word() -> None
go_to_start_of_previous_word() -> None
go_to_end_of_word() -> None

# Line movement
go_to_start_of_document() -> None
go_to_end_of_document() -> None
```

## Selection

```python
start_selection(selection_type: SelectionType = SelectionType.CHARACTERS) -> None
# SelectionType: CHARACTERS, LINES, BLOCK

selection_state: SelectionState | None  # Current selection info
copy_selection(keep_selection: bool = False) -> ClipboardData
cut_selection() -> ClipboardData

# Selection info via Document
document.selection_range()  # Returns (start, end) tuple
document.selection_ranges()  # For block selections
```

## History

```python
# Navigation
history_backward(count: int = 1) -> None
history_forward(count: int = 1) -> None

# Search (requires enable_history_search=True)
history_search_backward() -> None
history_search_forward() -> None

# Direct access
history.get_strings()  # All history strings
history.append_string(string)
```

## Undo/Redo

```python
undo() -> None
redo() -> None

save_to_undo_stack(clear_redo_stack: bool = True) -> None
```

## Completion

```python
# Trigger completion
start_completion(
    select_first: bool = False,
    select_last: bool = False,
    insert_common_part: bool = False,
    complete_event: CompleteEvent | None = None,
) -> None

# Navigate completions
complete_next(count: int = 1, disable_wrap_around: bool = False) -> None
complete_previous(count: int = 1, disable_wrap_around: bool = False) -> None

# Apply completion
apply_completion(completion: Completion) -> None

# Cancel
cancel_completion() -> None

# State
complete_state: CompleteState | None
completions: list[Completion]
complete_index: int | None
```

## Validation

```python
validate(set_cursor: bool = False) -> bool
validate_async(set_cursor: bool = False) -> Coroutine[Any, Any, bool]

validation_state: ValidationState  # VALID, INVALID, UNKNOWN
validation_error: ValidationError | None
```

## Events

All events are `Event` objects supporting `+=` to add handlers:

```python
on_text_changed: Event[Buffer]
on_text_insert: Event[Buffer]
on_cursor_position_changed: Event[Buffer]
on_completions_changed: Event[Buffer]
on_suggestion_set: Event[Buffer]

# Usage
buffer.on_text_changed += my_handler
buffer.on_text_changed -= my_handler  # Remove handler
```

## Reset and State

```python
reset(
    document: Document | None = None,
    append_to_history: bool = False,
) -> None

# State for saving/restoring
get_state() -> BufferState
set_state(state: BufferState) -> None
```

## Accept Handler

```python
BufferAcceptHandler = Callable[[Buffer], bool]

def my_accept_handler(buff: Buffer) -> bool:
    """
    Called when user accepts input (usually Enter key).

    Return True to keep text in buffer after accept.
    Return False to clear buffer after accept.
    """
    process_input(buff.text)
    return False

buffer = Buffer(accept_handler=my_accept_handler)
```

## Practical Examples

### Read-Only Output Buffer
```python
output_buffer = Buffer(
    name='output',
    read_only=True,
    multiline=True,
)

def append_output(text: str):
    output_buffer.insert_text(text + '\n')
```

### Input with Validation
```python
from prompt_toolkit.validation import Validator, ValidationError

class NumberValidator(Validator):
    def validate(self, document):
        if not document.text.isdigit():
            raise ValidationError(message='Numbers only')

input_buffer = Buffer(
    validator=NumberValidator(),
    validate_while_typing=True,
)
```

### Synchronized Buffers
```python
main_buffer = Buffer(name='main')
preview_buffer = Buffer(name='preview', read_only=True)

def sync_preview(buff):
    # Update preview when main changes
    preview_buffer.reset(Document(transform(buff.text)))

main_buffer.on_text_changed += sync_preview
```
