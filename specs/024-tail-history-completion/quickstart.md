# Quick Start: Tail Mode Command History & Autocomplete

**Feature Branch**: `024-tail-history-completion`
**Date**: 2026-03-01

## Architecture Overview

```
TailApp (coordinator)                           tail_textual.py (modified)
  ├── creates TailCommandHistory                tail_history.py (new)
  │     ├── load() from tail_history file
  │     ├── compact() if file oversized
  │     └── save() on each command submission
  ├── creates TailCommandSuggester              tail_suggester.py (new)
  │     ├── with history reference
  │     ├── with TAIL_COMPLETION_DATA           tail_completion_data.py (new)
  │     └── with dynamic_sources dict
  ├── passes both to TailInput                  tail_input.py (modified)
  │     ├── Up/Down → history.navigate_back/forward
  │     ├── _navigating guard prevents reset
  │     └── watch_value → reset navigation on typing
  └── on_input_submitted
        ├── history.add(command)
        └── history.save(command)

Textual Input (parent class)
  ├── _watch_value → clears suggestion, requests new via worker
  ├── _on_suggestion_ready → displays ghost text
  └── action_cursor_right → accepts suggestion (sets value)
```

## Implementation Order

### Step 1: TailCommandHistory (standalone, no UI)

**File**: `pgtail_py/tail_history.py` (~250 LOC)
**Tests**: `tests/test_tail_history.py` (~400 LOC)

Build and test independently. No Textual dependency.

```python
# Key patterns:
history = TailCommandHistory(max_entries=500, history_path=path)
history.load()

# Navigation: saves input on first back, restores on forward-past-newest
entry = history.navigate_back("current text")  # → "since 5m"
entry = history.navigate_back("current text")  # → "level error+"
text, restored = history.navigate_forward()    # → ("since 5m", False)
text, restored = history.navigate_forward()    # → ("current text", True)

# Search for suggestion fallback
match = history.search_prefix("level error")  # → "level error+" (case-sensitive)
```

**Critical test cases**:
- Three-state cursor transitions (all 7 transitions in data-model.md)
- Consecutive deduplication
- Empty/whitespace rejection
- File I/O (load, save, compact, error handling, corrupt files)
- search_prefix case sensitivity

### Step 2: Completion Data Definitions (standalone data)

**File**: `pgtail_py/tail_completion_data.py` (~350 LOC)
**Tests**: `tests/test_tail_completion_data.py` (~200 LOC)

Define all command specs. No runtime dependencies.

```python
# Key pattern:
TAIL_COMPLETION_DATA = {
    "level": CompletionSpec(positionals=[CompletionSpec(static_values=LEVEL_VALUES)]),
    "errors": CompletionSpec(
        positionals=[CompletionSpec(static_values=["clear"])],
        flags={
            "--trend": None,          # Boolean flag
            "--live": None,           # Boolean flag
            "--code": CompletionSpec(static_values=SQLSTATE_CODES),
            "--since": CompletionSpec(static_values=TIME_PRESETS),
        },
    ),
    "pause": CompletionSpec(no_args=True),
    # ...
}
```

**Critical test cases**:
- Every command has a spec entry
- Flag types (boolean vs value-taking) are correct
- Positional counts match command signatures
- Dynamic source keys match available sources

### Step 3: TailCommandSuggester (depends on steps 1 & 2)

**File**: `pgtail_py/tail_suggester.py` (~200 LOC)
**Tests**: `tests/test_tail_suggester.py` (~350 LOC)

```python
# Key patterns:
suggester = TailCommandSuggester(
    history=history,
    completion_data=TAIL_COMPLETION_DATA,
    dynamic_sources={
        "highlighter_names": lambda: ["duration", "sqlstate", "checkpoint"],
        "setting_keys": lambda: ["slow.warn", "slow.error", "theme.name"],
        "help_topics": lambda: ["level", "filter", "keys"],
    },
)

# Called by Textual's Input via worker:
result = await suggester.get_suggestion("le")       # → "level"
result = await suggester.get_suggestion("level ")    # → "level debug"
result = await suggester.get_suggestion("level e")   # → "level error"
result = await suggester.get_suggestion("xyz")       # → None
```

**Critical test cases**:
- Command name completion (case-insensitive prefix)
- Argument completion for each structural type
- Flag scanning (boolean vs value-taking, consumed vs unconsumed)
- `--flag=value` parsing
- History fallback when structural yields empty suffix
- Full-line return format (FR-017)

### Step 4: TailInput Modifications (depends on step 1)

**File**: `pgtail_py/tail_input.py` (modified, ~150 LOC total)
**Tests**: `tests/test_tail_input_history.py` (~250 LOC)

```python
# Key patterns:
class TailInput(Input):
    def action_history_back(self) -> None:
        if not self._history:
            return
        entry = self._history.navigate_back(self.value)
        if entry is not None:
            self._navigating = True          # Guard ON
            self.value = entry               # Triggers _watch_value
            self.cursor_position = len(entry)
            self._navigating = False         # Guard OFF

    def watch_value(self, value: str) -> None:
        if not self._navigating and self._history:
            self._history.reset_navigation()  # FR-004
```

**Critical test cases**:
- Up/Down navigation updates input value
- Guard prevents navigation reset during programmatic changes
- Typing resets navigation (guard not set)
- Ghost suggestion acceptance resets navigation (FR-026)
- Backward compatibility when history=None and suggester=None

### Step 5: TailApp Wiring (depends on steps 1-4)

**File**: `pgtail_py/tail_textual.py` (modified, ~10 new LOC)

```python
# In __init__ or compose:
self._history = TailCommandHistory(
    history_path=get_tail_history_path(),
)
self._suggester = TailCommandSuggester(
    history=self._history,
    completion_data=TAIL_COMPLETION_DATA,
    dynamic_sources={
        "highlighter_names": lambda: ...,
        "setting_keys": lambda: ...,
        "help_topics": lambda: ...,
    },
)

# In compose:
yield TailInput(history=self._history, suggester=self._suggester)

# In on_mount:
self._history.load()
self._history.compact()

# In on_input_submitted:
self._history.add(command)
self._history.save(command)
```

### Step 6: Refactor tail_textual.py (constitution compliance)

**File**: `pgtail_py/tail_command_handler.py` (new, ~200 LOC extracted)
**Modified**: `pgtail_py/tail_textual.py` (reduced from ~1145 to ~960 LOC)

Extract `_handle_command()`, `_handle_export_command()`, and related helpers into a separate module to bring `tail_textual.py` closer to the 900 LOC constitution limit.

## Key Implementation Notes

### Caching
The Suggester MUST be initialized with `use_cache=False`. History changes on every submission and dynamic sources change during the session (FR-020).

### Case Sensitivity
The Suggester MUST be initialized with `case_sensitive=True` to receive raw input. Casing is handled internally: case-insensitive for command names and static values, case-sensitive for history and dynamic sources (FR-018).

### Guard Pattern
The `_navigating` flag MUST be set/cleared synchronously around value assignment:
```python
self._navigating = True
try:
    self.value = entry
    self.cursor_position = len(entry)
finally:
    self._navigating = False
```
Using `try/finally` ensures the flag is cleared even if an exception occurs.

### Full-Line Return
The suggester returns the **complete input line** including the user's existing text, not just the completion suffix. Example: for input `"le"`, returns `"level"` (not `"vel"`). Textual's Input displays `suggestion[len(value):]` as ghost text.

### History File Concurrency
Append writes are not atomic. Compaction can lose concurrent entries. This is an accepted trade-off (FR-006, Edge Cases). No file locking is implemented.
