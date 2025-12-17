# Document API Reference

Complete API for prompt_toolkit Document class.

## Overview

Document is an **immutable** representation of text with cursor position. Documents are cached internally for performance - two Document instances with the same text share the same cache.

## Constructor

```python
Document(
    text: str = "",
    cursor_position: int | None = None,
    selection: SelectionState | None = None,
)
```

If `cursor_position` is None, cursor is placed at end of text.

## Basic Properties

### Text Access
```python
text: str                      # Full text content
cursor_position: int           # Cursor position (0-based index in text)
selection: SelectionState | None  # Selection state if any
```

### Text Around Cursor
```python
text_before_cursor: str        # Text from start to cursor
text_after_cursor: str         # Text from cursor to end
current_line_before_cursor: str  # Current line text before cursor
current_line_after_cursor: str   # Current line text after cursor
char_before_cursor: str        # Single character before cursor (or '')
current_char: str              # Character at cursor (or '')
```

### Line Information
```python
line_count: int                # Total number of lines
current_line: str              # Full text of current line
lines: list[str]               # All lines as list

cursor_position_row: int       # Current line number (0-based)
cursor_position_col: int       # Column in current line (0-based)
```

## Navigation Methods

All navigation methods return **offsets** (positive or negative integers) to add to cursor_position, not absolute positions.

### Character Navigation
```python
get_cursor_left_position(count: int = 1) -> int
get_cursor_right_position(count: int = 1) -> int
```

### Line Navigation
```python
get_cursor_up_position(count: int = 1, preferred_column: int | None = None) -> int
get_cursor_down_position(count: int = 1, preferred_column: int | None = None) -> int

get_start_of_line_position(after_whitespace: bool = False) -> int
get_end_of_line_position() -> int

get_start_of_document_position() -> int
get_end_of_document_position() -> int
```

### Word Navigation
```python
# WORD = non-whitespace characters (like Vim WORD)
# word = alphanumeric sequences (like Vim word)

get_word_before_cursor(WORD: bool = False, pattern: Pattern | None = None) -> str
get_word_under_cursor(WORD: bool = False) -> str

find_start_of_previous_word(count: int = 1, WORD: bool = False, pattern: Pattern | None = None) -> int | None
find_next_word_beginning(count: int = 1, WORD: bool = False, pattern: Pattern | None = None) -> int | None
find_next_word_ending(count: int = 1, WORD: bool = False, pattern: Pattern | None = None) -> int | None

find_previous_word_beginning(count: int = 1, WORD: bool = False, pattern: Pattern | None = None) -> int | None
find_previous_word_ending(count: int = 1, WORD: bool = False, pattern: Pattern | None = None) -> int | None

find_boundaries_of_current_word(WORD: bool = False, include_leading_whitespace: bool = False, include_trailing_whitespace: bool = False) -> tuple[int, int]
```

### Paragraph Navigation
```python
find_start_of_paragraph() -> int
find_end_of_paragraph() -> int
get_cursor_up_position_one_paragraph() -> int
get_cursor_down_position_one_paragraph() -> int
```

## Search Methods

```python
find(
    sub: str,
    in_current_line: bool = False,
    include_current_position: bool = False,
    ignore_case: bool = False,
    count: int = 1,
) -> int | None
# Returns cursor position offset, or None if not found

find_backwards(
    sub: str,
    in_current_line: bool = False,
    ignore_case: bool = False,
    count: int = 1,
) -> int | None

find_all(sub: str, ignore_case: bool = False) -> list[int]
# Returns list of absolute positions
```

## Selection Methods

```python
selection_range() -> tuple[int, int]
# Returns (from, to) of selection, ordered

selection_ranges() -> list[tuple[int, int]]
# For block selections, returns list of ranges per line

selection_range_at_line(row: int) -> tuple[int, int] | None
# Get selection range at specific line (for block selection)

cut_selection() -> tuple[Document, ClipboardData]
# Returns new Document without selection and clipboard data

paste_clipboard_data(
    data: ClipboardData,
    paste_mode: PasteMode = PasteMode.EMACS,
    count: int = 1,
) -> Document
# Returns new Document with pasted content
```

## Line Access Methods

```python
get_line(index: int) -> str
# Get specific line by index (0-based)

translate_index_to_position(index: int) -> tuple[int, int]
# Convert text index to (row, col)

translate_row_col_to_index(row: int, col: int) -> int
# Convert (row, col) to text index

on_first_line: bool
on_last_line: bool
is_cursor_at_the_end: bool
is_cursor_at_the_end_of_line: bool
```

## Transformation Methods

```python
insert_before(text: str) -> Document
insert_after(text: str) -> Document
# Return new Document with text inserted

new_document(
    text: str = "",
    cursor_position: int | None = None,
) -> Document
# Create new Document (useful for transforms)
```

## Whitespace and Indentation

```python
leading_whitespace_in_current_line: str
# Whitespace at start of current line

get_column_cursor_position(column: int) -> int
# Get cursor offset to reach specific column

empty_line_count_at_the_end() -> int
# Number of trailing empty lines
```

## Matching

```python
find_matching_bracket_position(
    start_pos: int | None = None,
    end_pos: int | None = None,
) -> int | None
# Find matching bracket, returns offset

find_enclosing_bracket_left(
    left_ch: str,
    right_ch: str,
    start_pos: int | None = None,
) -> int | None

find_enclosing_bracket_right(
    left_ch: str,
    right_ch: str,
    end_pos: int | None = None,
) -> int | None
```

## Usage Examples

### Creating Documents
```python
# Empty document
doc = Document()

# With text, cursor at end
doc = Document("Hello world")

# With specific cursor position
doc = Document("Hello world", cursor_position=5)  # After "Hello"

# From Buffer
doc = buffer.document
```

### Navigation Example
```python
doc = Document("Hello world", cursor_position=0)

# Move right by 5
offset = doc.get_cursor_right_position(count=5)
new_doc = Document(doc.text, cursor_position=doc.cursor_position + offset)

# In Buffer, this is simpler:
buffer.cursor_right(count=5)
```

### Search Example
```python
doc = Document("Hello world hello", cursor_position=0)

# Find next "hello" (case-insensitive)
offset = doc.find("hello", ignore_case=True, count=1)
if offset is not None:
    new_pos = doc.cursor_position + offset
    # new_pos = 12 (position of second "hello")

# Find all occurrences
positions = doc.find_all("hello", ignore_case=True)
# positions = [0, 12]
```

### Word Extraction Example
```python
doc = Document("def my_function():", cursor_position=6)

word_before = doc.get_word_before_cursor()  # "my"
full_word = doc.get_word_under_cursor()      # "my_function"

# With WORD (non-whitespace sequences)
doc2 = Document("hello-world test", cursor_position=7)
doc2.get_word_before_cursor()          # "world"
doc2.get_word_before_cursor(WORD=True) # "hello-world"
```

### Selection Example
```python
from prompt_toolkit.selection import SelectionState, SelectionType

doc = Document(
    "Hello world",
    cursor_position=11,  # End
    selection=SelectionState(original_cursor_position=6, type=SelectionType.CHARACTERS),
)

# Get selected text range
start, end = doc.selection_range()  # (6, 11)
selected_text = doc.text[start:end]  # "world"
```

## Performance Notes

1. Documents are cached by text content - creating many Documents with same text is cheap
2. Line-related properties are computed lazily and cached
3. Navigation methods return offsets to avoid creating intermediate Documents
4. For heavy editing, work through Buffer rather than creating Documents directly
