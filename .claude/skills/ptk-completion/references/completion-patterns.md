# Completion Patterns

Production patterns for prompt_toolkit completion.

## CLI with Subcommands

Pattern for CLIs like `git`, `docker`, `kubectl`:

```python
from prompt_toolkit.completion import NestedCompleter, WordCompleter, PathCompleter

def create_cli_completer():
    return NestedCompleter.from_nested_dict({
        'git': {
            'clone': PathCompleter(only_directories=True),
            'add': PathCompleter(),
            'commit': {
                '-m': None,
                '--message': None,
                '--amend': None,
                '-a': None,
            },
            'push': {
                'origin': {
                    'main': None,
                    'master': None,
                },
                '--force': None,
                '-f': None,
            },
            'pull': {
                'origin': None,
                '--rebase': None,
            },
            'checkout': {
                '-b': None,
                # Could add branch completer here
            },
        },
        'docker': {
            'run': {
                '-it': None,
                '--rm': None,
                '-v': PathCompleter(),
                '-p': None,
            },
            'build': {
                '-t': None,
                '-f': PathCompleter(file_filter=lambda f: 'Dockerfile' in f),
            },
            'ps': {
                '-a': None,
                '--all': None,
            },
        },
    })
```

## SQL Query Completion

Context-aware SQL completion:

```python
from prompt_toolkit.completion import Completer, Completion
import re

class SQLCompleter(Completer):
    KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
                'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AND', 'OR',
                'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET']

    def __init__(self, schema):
        self.schema = schema  # {'table': ['col1', 'col2', ...], ...}

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.upper()
        word = document.get_word_before_cursor().upper()

        # Determine context
        if self._after_keyword(text, ['SELECT', 'WHERE', 'AND', 'OR', 'SET', 'ORDER BY']):
            yield from self._column_completions(document, word)
        elif self._after_keyword(text, ['FROM', 'JOIN', 'UPDATE', 'INTO']):
            yield from self._table_completions(document, word)
        else:
            yield from self._keyword_completions(document, word)

    def _after_keyword(self, text, keywords):
        for kw in keywords:
            if text.rstrip().endswith(kw):
                return True
            if re.search(rf'{kw}\s+\w*$', text):
                return True
        return False

    def _keyword_completions(self, document, word):
        for kw in self.KEYWORDS:
            if kw.startswith(word):
                yield Completion(kw, start_position=-len(word))

    def _table_completions(self, document, word):
        for table in self.schema.keys():
            if table.upper().startswith(word):
                cols = ', '.join(self.schema[table][:3])
                yield Completion(
                    table,
                    start_position=-len(word),
                    display_meta=f'({cols}...)',
                )

    def _column_completions(self, document, word):
        # Find table in query for context
        text = document.text_before_cursor.upper()
        match = re.search(r'FROM\s+(\w+)', text)
        if match:
            table = match.group(1)
            if table in self.schema:
                for col in self.schema[table]:
                    if col.upper().startswith(word):
                        yield Completion(col, start_position=-len(word))
        else:
            # Show all columns from all tables
            for table, cols in self.schema.items():
                for col in cols:
                    if col.upper().startswith(word):
                        yield Completion(
                            col,
                            start_position=-len(word),
                            display_meta=table,
                        )
```

## Multi-Stage Completion

Different completers based on parsing state:

```python
from prompt_toolkit.completion import Completer, Completion, merge_completers
import shlex

class CommandCompleter(Completer):
    def __init__(self, commands):
        """
        commands = {
            'connect': {'--host': HostCompleter(), '--port': None},
            'load': PathCompleter(),
            'query': SQLCompleter(schema),
        }
        """
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            parts = shlex.split(text)
        except ValueError:
            parts = text.split()

        if not parts or (len(parts) == 1 and not text.endswith(' ')):
            # Complete command name
            word = parts[0] if parts else ''
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
        else:
            # Delegate to command-specific completer
            cmd = parts[0]
            if cmd in self.commands:
                completer = self.commands[cmd]
                if isinstance(completer, dict):
                    # Handle options
                    yield from self._complete_options(completer, document, parts)
                elif completer:
                    yield from completer.get_completions(document, complete_event)

    def _complete_options(self, options, document, parts):
        word = document.get_word_before_cursor()
        for opt, completer in options.items():
            if opt.startswith(word):
                yield Completion(opt, start_position=-len(word))
```

## Fuzzy with Highlighting

Show fuzzy match highlights:

```python
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
import re

class HighlightingFuzzyCompleter(Completer):
    def __init__(self, words):
        self.words = words

    def get_completions(self, document, complete_event):
        query = document.get_word_before_cursor().lower()
        if not query:
            for word in self.words:
                yield Completion(word, start_position=0)
            return

        # Build fuzzy regex
        pattern = '.*'.join(re.escape(c) for c in query)
        regex = re.compile(pattern, re.IGNORECASE)

        matches = []
        for word in self.words:
            match = regex.search(word)
            if match:
                # Score by match position and length
                score = match.start() * 100 + (match.end() - match.start())
                matches.append((score, word, match))

        matches.sort(key=lambda x: x[0])

        for score, word, match in matches[:20]:
            # Highlight matched characters
            highlighted = self._highlight_match(word, query)
            yield Completion(
                text=word,
                start_position=-len(query),
                display=HTML(highlighted),
            )

    def _highlight_match(self, word, query):
        result = []
        query_idx = 0
        for char in word:
            if query_idx < len(query) and char.lower() == query[query_idx].lower():
                result.append(f'<b>{char}</b>')
                query_idx += 1
            else:
                result.append(char)
        return ''.join(result)
```

## Async with Caching

Cache expensive completion results:

```python
from prompt_toolkit.completion import Completer, Completion
import asyncio
from functools import lru_cache

class CachingAsyncCompleter(Completer):
    def __init__(self, fetch_func):
        self.fetch_func = fetch_func
        self._cache = {}
        self._cache_time = {}
        self.cache_ttl = 60  # seconds

    async def get_completions_async(self, document, complete_event):
        word = document.get_word_before_cursor()
        prefix = word[:2] if len(word) >= 2 else ''  # Cache by prefix

        # Check cache
        import time
        now = time.time()
        if prefix in self._cache:
            if now - self._cache_time[prefix] < self.cache_ttl:
                items = self._cache[prefix]
            else:
                items = await self._fetch_and_cache(prefix)
        else:
            items = await self._fetch_and_cache(prefix)

        # Filter and yield
        for item in items:
            if item.lower().startswith(word.lower()):
                yield Completion(item, start_position=-len(word))

    async def _fetch_and_cache(self, prefix):
        import time
        items = await self.fetch_func(prefix)
        self._cache[prefix] = items
        self._cache_time[prefix] = time.time()
        return items

    def get_completions(self, document, complete_event):
        # Sync fallback using cached data
        word = document.get_word_before_cursor()
        prefix = word[:2] if len(word) >= 2 else ''
        for item in self._cache.get(prefix, []):
            if item.lower().startswith(word.lower()):
                yield Completion(item, start_position=-len(word))
```

## REPL History Completion

Complete from command history:

```python
from prompt_toolkit.completion import Completer, Completion

class HistoryCompleter(Completer):
    def __init__(self, history):
        self.history = history

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        seen = set()
        for entry in reversed(list(self.history.get_strings())):
            if entry.startswith(text) and entry not in seen:
                seen.add(entry)
                yield Completion(
                    text=entry,
                    start_position=-len(text),
                    display_meta='history',
                )
                if len(seen) >= 20:
                    break
```

## Environment Variable Completion

Complete $VARIABLES:

```python
from prompt_toolkit.completion import Completer, Completion
import os
import re

class EnvVarCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Check if we're completing an env var
        match = re.search(r'\$(\w*)$', text)
        if not match:
            return

        prefix = match.group(1)
        start_pos = -len(prefix) - 1  # Include the $

        for name, value in os.environ.items():
            if name.startswith(prefix):
                yield Completion(
                    text=f'${name}',
                    start_position=start_pos,
                    display=f'${name}',
                    display_meta=value[:30] + '...' if len(value) > 30 else value,
                )
```

## Best Practices

1. **Return generators** - Don't build full lists for large completion sets
2. **Limit results** - Cap at 100-200 completions for performance
3. **Use ThreadedCompleter** for slow operations
4. **Cache expensive lookups** with appropriate TTL
5. **Provide display_meta** for helpful context
6. **Sort by relevance** - exact matches first, then prefix, then fuzzy
7. **Handle errors gracefully** - don't crash on bad input
8. **Test with complete_while_typing** - ensure fast enough for real-time

```python
class ProductionCompleter(Completer):
    MAX_COMPLETIONS = 100

    def get_completions(self, document, complete_event):
        count = 0
        try:
            for completion in self._get_all_completions(document):
                yield completion
                count += 1
                if count >= self.MAX_COMPLETIONS:
                    return
        except Exception as e:
            # Log error but don't crash
            logger.error(f"Completion error: {e}")
```
