# History & AutoSuggest API Reference

Complete API for prompt_toolkit history and auto-suggest systems.

## History Base Class

```python
from abc import ABCMeta, abstractmethod

class History(metaclass=ABCMeta):
    @abstractmethod
    def load_history_strings(self) -> Iterable[str]:
        """Load history strings (oldest first)."""
        pass

    @abstractmethod
    def store_string(self, string: str) -> None:
        """Store a new history entry."""
        pass

    async def load(self) -> AsyncGenerator[str, None]:
        """Async generator yielding history strings (newest first)."""
        for item in reversed(list(self.load_history_strings())):
            yield item

    def get_strings(self) -> list[str]:
        """Get all history strings as list (oldest first)."""
        return list(self.load_history_strings())

    def append_string(self, string: str) -> None:
        """Append string to history if not empty/duplicate."""
        if string and (not self._loaded or string != self._loaded[-1]):
            self.store_string(string)
```

## InMemoryHistory

```python
from prompt_toolkit.history import InMemoryHistory

# Empty history
history = InMemoryHistory()

# Pre-populated history
history = InMemoryHistory(history_strings=['cmd1', 'cmd2', 'cmd3'])

# Methods
history.append_string('new command')
strings = history.get_strings()  # ['cmd1', 'cmd2', 'cmd3', 'new command']
```

## FileHistory

```python
from prompt_toolkit.history import FileHistory

history = FileHistory(filename='~/.myapp_history')

# With explicit encoding
history = FileHistory(filename='.history')
```

**File format:**
```
# 2024-12-16 10:30:45.123456
+command one
# 2024-12-16 10:31:12.654321
+multi
+line
+command
```

## ThreadedHistory

```python
from prompt_toolkit.history import ThreadedHistory, FileHistory

# Wrap any history for background loading
history = ThreadedHistory(FileHistory('~/.history'))
```

**Benefits:**
- History loads in background thread
- Application starts immediately
- No UI blocking on large history files

## DummyHistory

```python
from prompt_toolkit.history import DummyHistory

history = DummyHistory()  # Never stores anything
```

## Buffer History Integration

```python
buffer = Buffer(
    history=FileHistory('.history'),
    enable_history_search=True,  # Up/Down search by prefix
)

# Manual history access
buffer.history.append_string('command')
strings = buffer.history.get_strings()

# History navigation (in key bindings)
buffer.history_backward()   # Previous entry
buffer.history_forward()    # Next entry
```

## AutoSuggest Base Class

```python
from abc import ABCMeta, abstractmethod

class AutoSuggest(metaclass=ABCMeta):
    @abstractmethod
    def get_suggestion(
        self,
        buffer: Buffer,
        document: Document,
    ) -> Suggestion | None:
        """Return suggestion for current input."""
        pass

    async def get_suggestion_async(
        self,
        buffer: Buffer,
        document: Document,
    ) -> Suggestion | None:
        """Async version (optional)."""
        return self.get_suggestion(buffer, document)
```

## Suggestion Class

```python
class Suggestion:
    def __init__(self, text: str):
        """
        text: The suggested completion text to append.
        """
        self.text = text
```

## AutoSuggestFromHistory

```python
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

auto_suggest = AutoSuggestFromHistory()

buffer = Buffer(
    history=FileHistory('.history'),
    auto_suggest=auto_suggest,
)
```

**Behavior:**
- Searches history for entries starting with current input
- Shows most recent match as gray suggestion
- User can accept with Right arrow or custom binding

## ThreadedAutoSuggest

```python
from prompt_toolkit.auto_suggest import ThreadedAutoSuggest

auto_suggest = ThreadedAutoSuggest(SlowAutoSuggest())
```

## DummyAutoSuggest

```python
from prompt_toolkit.auto_suggest import DummyAutoSuggest

auto_suggest = DummyAutoSuggest()  # No suggestions
```

## DynamicAutoSuggest

```python
from prompt_toolkit.auto_suggest import DynamicAutoSuggest

def get_auto_suggest():
    if mode == 'command':
        return command_suggestions
    return history_suggestions

auto_suggest = DynamicAutoSuggest(get_auto_suggest)
```

## ConditionalAutoSuggest

```python
from prompt_toolkit.auto_suggest import ConditionalAutoSuggest
from prompt_toolkit.filters import Condition

auto_suggest = ConditionalAutoSuggest(
    base_auto_suggest,
    filter=Condition(lambda: suggestions_enabled),
)
```

## Custom AutoSuggest

### Command Completion

```python
class CommandAutoSuggest(AutoSuggest):
    def __init__(self, commands: list[str]):
        self.commands = sorted(commands)

    def get_suggestion(self, buffer, document):
        text = document.text_before_cursor

        # Find first matching command
        for cmd in self.commands:
            if cmd.startswith(text) and cmd != text:
                return Suggestion(cmd[len(text):])

        return None
```

### Multi-Source Suggestions

```python
class MultiSourceAutoSuggest(AutoSuggest):
    def __init__(self, sources: list[AutoSuggest]):
        self.sources = sources

    def get_suggestion(self, buffer, document):
        for source in self.sources:
            suggestion = source.get_suggestion(buffer, document)
            if suggestion:
                return suggestion
        return None
```

### AI-Powered Suggestions

```python
class AIAutoSuggest(AutoSuggest):
    def __init__(self, model):
        self.model = model
        self._cache = {}

    async def get_suggestion_async(self, buffer, document):
        text = document.text_before_cursor

        # Check cache
        if text in self._cache:
            return Suggestion(self._cache[text])

        # Get AI suggestion
        try:
            completion = await self.model.complete(text)
            if completion:
                self._cache[text] = completion
                return Suggestion(completion)
        except Exception:
            pass

        return None

    def get_suggestion(self, buffer, document):
        # Sync fallback - use cache only
        text = document.text_before_cursor
        if text in self._cache:
            return Suggestion(self._cache[text])
        return None
```

## Suggestion Display

Auto-suggestions appear as dimmed text after cursor. Style with:

```python
style = Style.from_dict({
    'auto-suggestion': '#666666',  # Gray suggestion text
})
```

## Accepting Suggestions

### Right Arrow (Default)

```python
from prompt_toolkit.filters import has_suggestion

@kb.add('right', filter=has_suggestion)
def accept_suggestion(event):
    suggestion = event.current_buffer.suggestion
    if suggestion:
        event.current_buffer.insert_text(suggestion.text)
```

### Tab to Accept

```python
@kb.add('tab', filter=has_suggestion & ~has_completions)
def accept_suggestion_tab(event):
    suggestion = event.current_buffer.suggestion
    if suggestion:
        event.current_buffer.insert_text(suggestion.text)
```

### Ctrl+Right for Word

```python
@kb.add('c-right', filter=has_suggestion)
def accept_suggestion_word(event):
    suggestion = event.current_buffer.suggestion
    if suggestion:
        # Accept first word only
        word = suggestion.text.split()[0] if ' ' in suggestion.text else suggestion.text
        event.current_buffer.insert_text(word + ' ')
```

## History Search Patterns

### Prefix Search (Default)

```python
buffer = Buffer(
    history=history,
    enable_history_search=True,  # Up/Down search by prefix
)
```

### Full-Text Search

```python
class FullTextHistorySearch:
    def __init__(self, buffer, history):
        self.buffer = buffer
        self.history = history
        self.matches = []
        self.index = 0

    def search(self, query):
        self.matches = [
            entry for entry in self.history.get_strings()
            if query.lower() in entry.lower()
        ]
        self.matches.reverse()  # Newest first
        self.index = 0

    def next_match(self):
        if self.matches and self.index < len(self.matches) - 1:
            self.index += 1
            return self.matches[self.index]

    def prev_match(self):
        if self.matches and self.index > 0:
            self.index -= 1
            return self.matches[self.index]
```

## Custom History Implementation

### SQLite History

```python
import sqlite3
from prompt_toolkit.history import History

class SQLiteHistory(History):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY,
                    command TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def load_history_strings(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT command FROM history ORDER BY id'
            )
            return [row[0] for row in cursor]

    def store_string(self, string: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO history (command) VALUES (?)',
                (string,)
            )
```

### Deduplicated History

```python
class DeduplicatedHistory(History):
    def __init__(self, base_history: History, max_size: int = 1000):
        self.base = base_history
        self.max_size = max_size

    def load_history_strings(self):
        seen = set()
        result = []
        for entry in reversed(list(self.base.load_history_strings())):
            if entry not in seen:
                seen.add(entry)
                result.append(entry)
                if len(result) >= self.max_size:
                    break
        return list(reversed(result))

    def store_string(self, string: str):
        self.base.store_string(string)
```

## Best Practices

1. **Use ThreadedHistory** for FileHistory to avoid startup delay
2. **Limit history size** to prevent memory issues
3. **Deduplicate entries** to keep history useful
4. **Cache suggestions** to avoid repeated computation
5. **Handle errors gracefully** in async methods
6. **Provide fallback** sync methods for async suggest
