# Completer API Reference

Complete API for prompt_toolkit completion system.

## Completion Class

```python
Completion(
    text: str,
    start_position: int = 0,
    display: AnyFormattedText | None = None,
    display_meta: AnyFormattedText | None = None,
    style: str = "",
    selected_style: str = "",
)
```

**Parameters:**
- `text` - Text to insert when completion is selected
- `start_position` - **Negative offset** from cursor indicating where replacement starts
- `display` - Text to show in completion menu (defaults to `text`)
- `display_meta` - Meta information shown beside completion
- `style` - CSS-like style for this completion
- `selected_style` - Style when completion is selected

**Example:**
```python
# User typed "hel" and we want to complete to "hello"
Completion(
    text='hello',
    start_position=-3,  # Replace 3 chars before cursor ("hel")
    display='hello',
    display_meta='Greeting',
)
```

## Completer Base Class

```python
from abc import ABCMeta, abstractmethod

class Completer(metaclass=ABCMeta):
    @abstractmethod
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        """Return completions for current document state."""
        pass

    async def get_completions_async(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> AsyncGenerator[Completion, None]:
        """Async version of get_completions."""
        for completion in self.get_completions(document, complete_event):
            yield completion
```

## CompleteEvent

```python
class CompleteEvent:
    completion_requested: bool
    # True when user explicitly requested completion (Tab)
    # False when triggered by complete_while_typing
```

## WordCompleter

```python
WordCompleter(
    words: Sequence[str] | Callable[[], Sequence[str]],
    ignore_case: bool = False,
    meta_dict: Mapping[str, AnyFormattedText] | None = None,
    WORD: bool = False,
    sentence: bool = False,
    match_middle: bool = False,
    pattern: Pattern[str] | None = None,
)
```

**Parameters:**
- `words` - List of words or callable returning words
- `ignore_case` - Case-insensitive matching
- `meta_dict` - Map of word → meta description
- `WORD` - Use WORD characters (non-whitespace) vs word (alphanumeric)
- `sentence` - Match against entire input, not just word before cursor
- `match_middle` - Allow matching in middle of word, not just start
- `pattern` - Custom regex pattern for word extraction

**Example:**
```python
completer = WordCompleter(
    words=['SELECT', 'INSERT', 'UPDATE', 'DELETE'],
    ignore_case=True,
    meta_dict={
        'SELECT': 'Query data from tables',
        'INSERT': 'Add new rows',
        'UPDATE': 'Modify existing rows',
        'DELETE': 'Remove rows',
    }
)
```

## FuzzyCompleter

```python
FuzzyCompleter(
    completer: Completer,
    WORD: bool = False,
    pattern: str | None = None,
    enable_fuzzy: FilterOrBool = True,
)
```

**How it works:**
- Converts user input to regex: "oar" → `o.*a.*r`
- Matches "leopard", "dinosaur", etc.
- Results sorted by relevance (match position and length)

**Example:**
```python
base = WordCompleter(['configuration', 'connection', 'constructor'])
fuzzy = FuzzyCompleter(base)

# "cfg" matches "configuration" (c...f...g)
# "con" matches all three
```

## NestedCompleter

```python
NestedCompleter(
    options: dict[str, Completer | None],
    ignore_case: bool = True,
)

# Class method for dict syntax
NestedCompleter.from_nested_dict(data: dict)
```

**Example:**
```python
completer = NestedCompleter.from_nested_dict({
    'git': {
        'clone': None,
        'commit': {
            '--message': None,
            '--amend': None,
        },
        'push': {
            '--force': None,
            'origin': None,
        },
    },
    'cd': PathCompleter(),  # Mix in other completers
})
```

## PathCompleter

```python
PathCompleter(
    only_directories: bool = False,
    get_paths: Callable[[], list[str]] | None = None,
    file_filter: Callable[[str], bool] | None = None,
    min_input_len: int = 0,
    expanduser: bool = False,
)
```

**Example:**
```python
# Python files only
completer = PathCompleter(
    file_filter=lambda name: name.endswith('.py'),
    expanduser=True,  # Handle ~
)
```

## ExecutableCompleter

```python
from prompt_toolkit.completion import ExecutableCompleter

completer = ExecutableCompleter()
# Completes to executables in PATH
```

## DummyCompleter

```python
from prompt_toolkit.completion import DummyCompleter

completer = DummyCompleter()
# Returns no completions
```

## ThreadedCompleter

```python
from prompt_toolkit.completion import ThreadedCompleter

completer = ThreadedCompleter(SlowCompleter())
# Runs completion in background thread
```

## DynamicCompleter

```python
from prompt_toolkit.completion import DynamicCompleter

def get_completer():
    if mode == 'sql':
        return sql_completer
    return default_completer

completer = DynamicCompleter(get_completer)
```

## DeduplicateCompleter

```python
from prompt_toolkit.completion import DeduplicateCompleter

completer = DeduplicateCompleter(base_completer)
# Removes duplicate completion texts
```

## merge_completers

```python
from prompt_toolkit.completion import merge_completers

combined = merge_completers([
    completer1,
    completer2,
    completer3,
])
```

## ConditionalCompleter

```python
from prompt_toolkit.completion import ConditionalCompleter
from prompt_toolkit.filters import Condition

completer = ConditionalCompleter(
    base_completer,
    filter=Condition(lambda: settings.autocomplete_enabled),
)
```

## CompletionsMenu

```python
from prompt_toolkit.layout.menus import CompletionsMenu

menu = CompletionsMenu(
    max_height: int | None = None,
    scroll_offset: int = 0,
    extra_filter: FilterOrBool = True,
    display_arrows: bool = False,
    z_index: int = 10**8,
)
```

**Layout example:**
```python
from prompt_toolkit.layout import FloatContainer, Float

layout = FloatContainer(
    content=main_layout,
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(
                max_height=16,
                scroll_offset=1,
            ),
        )
    ]
)
```

## MultiColumnCompletionsMenu

```python
from prompt_toolkit.layout.menus import MultiColumnCompletionsMenu

menu = MultiColumnCompletionsMenu(
    min_rows: int = 3,
    suggested_max_column_width: int = 30,
    show_meta: bool = True,
    extra_filter: FilterOrBool = True,
)
```

## Buffer Completion Methods

```python
buffer.start_completion(
    select_first: bool = False,
    select_last: bool = False,
    insert_common_part: bool = False,
    complete_event: CompleteEvent | None = None,
)

buffer.complete_next(count: int = 1, disable_wrap_around: bool = False)
buffer.complete_previous(count: int = 1, disable_wrap_around: bool = False)
buffer.apply_completion(completion: Completion)
buffer.cancel_completion()

# Properties
buffer.complete_state  # CompleteState | None
buffer.completions     # list[Completion]
buffer.complete_index  # int | None
```

## CompleteState

```python
class CompleteState:
    original_document: Document
    completions: list[Completion]
    complete_index: int | None

    @property
    def current_completion(self) -> Completion | None
```

## Custom Completer Examples

### Database Table Completer

```python
class TableCompleter(Completer):
    def __init__(self, connection):
        self.connection = connection

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        tables = self.connection.get_tables()

        for table in tables:
            if table.lower().startswith(word.lower()):
                yield Completion(
                    text=table,
                    start_position=-len(word),
                    display_meta=f'{self.connection.get_row_count(table)} rows',
                )
```

### Context-Aware Completer

```python
class SQLCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.upper()

        # After SELECT, suggest columns
        if 'SELECT' in text and 'FROM' not in text:
            yield from self.get_column_completions(document)

        # After FROM, suggest tables
        elif 'FROM' in text and 'WHERE' not in text:
            yield from self.get_table_completions(document)

        # Otherwise suggest keywords
        else:
            yield from self.get_keyword_completions(document)
```

### Async Database Completer

```python
class AsyncDBCompleter(Completer):
    async def get_completions_async(self, document, complete_event):
        word = document.get_word_before_cursor()
        results = await self.db.fetch_completions(word)

        for name, description in results:
            yield Completion(
                text=name,
                start_position=-len(word),
                display_meta=description,
            )

    def get_completions(self, document, complete_event):
        # Sync fallback - return empty or cached results
        return []
```
