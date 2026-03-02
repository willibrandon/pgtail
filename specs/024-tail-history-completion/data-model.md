# Data Model: Tail Mode Command History & Autocomplete

**Feature Branch**: `024-tail-history-completion`
**Date**: 2026-03-01

## Entities

### 1. TailCommandHistory

Ordered collection of previously entered tail mode commands with a three-state cursor model for navigation.

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `_entries` | `list[str]` | `[]` | Ordered command list, oldest at index 0, newest at end |
| `_cursor` | `int` | `0` | Navigation cursor position (0..len(entries)) |
| `_saved_input` | `str \| None` | `None` | User's partial input saved on first backward navigation |
| `_max_entries` | `int` | `500` | Maximum entries in memory (FR-007) |
| `_history_path` | `Path \| None` | `None` | File path for persistence (None = in-memory only) |
| `_max_line_bytes` | `int` | `4096` | Safety limit for line length on load (FR-009) |
| `_compact_threshold` | `int` | `1000` | Compact when file exceeds this (2× max_entries) (FR-006) |

**State Machine (three-state cursor model)**:

```
                    ┌─────────────────────┐
                    │      AT REST        │
                    │ cursor == len(entries)│
                    │ saved_input == None  │
                    └─────┬──────┬────────┘
                   Up     │      │  type/delete/submit/
                   (save  │      │  accept ghost
                   input) │      │
                    ┌─────▼──────┘────────┐
                    │  AT HISTORY ENTRY   │
                    │ 0 <= cursor < len   │
                    │ saved_input preserved│◄──── Up (cursor--, clamped at 0)
                    └─────┬───────────────┘
                   Down   │        ▲
                   past   │        │ Down (cursor++)
                   newest │        │
                    ┌─────▼───────────────┐
                    │    PAST NEWEST      │
                    │ cursor == len(entries)│
                    │ restore saved_input  │──── immediately transitions to AT REST
                    │ clear saved_input    │     (saved_input cleared after restore)
                    └─────────────────────┘
```

**Transitions**:

| From | Trigger | To | Action |
|------|---------|-----|--------|
| at-rest | Up | at-history-entry | Save current input; cursor = len-1; return entries[cursor] |
| at-rest | Down | at-rest | No-op (return None) |
| at-rest | type/delete/submit | at-rest | No-op |
| at-history-entry | Up | at-history-entry | cursor = max(0, cursor-1); return entries[cursor] |
| at-history-entry | Down (cursor+1 < len) | at-history-entry | cursor += 1; return entries[cursor] |
| at-history-entry | Down (cursor+1 == len) | past-newest → at-rest | Restore saved_input; clear saved_input; cursor = len |
| at-history-entry | type/delete/submit | at-rest | Clear cursor; clear saved_input |
| past-newest | (immediate) | at-rest | Transitional state only |

**Validation Rules**:
- `add()`: Rejects empty and whitespace-only strings (FR-001)
- `add()`: Deduplicates consecutive identical entries (FR-001)
- `load()`: Skips lines exceeding `_max_line_bytes` (FR-009)
- `load()`: Skips non-UTF-8 content gracefully (FR-009)
- `load()`: Retains only last `_max_entries` entries (FR-007)

**File Format**:
- UTF-8 encoded text file (FR-005)
- One entry per line (newline-delimited)
- Append-only for individual writes (FR-006)
- Compaction rewrites entire file with last `_max_entries` entries (FR-006)

### 2. CompletionSpec

Defines how to complete arguments for a single command or argument position.

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `static_values` | `list[str] \| None` | `None` | Fixed list of valid values, matched case-insensitive |
| `dynamic_source` | `str \| None` | `None` | Key into the `dynamic_sources` dict passed to TailCommandSuggester; resolved to a callable at suggestion time, matched case-sensitive |
| `subcommands` | `dict[str, CompletionSpec] \| None` | `None` | Subcommand name → nested spec |
| `flags` | `dict[str, CompletionSpec \| None] \| None` | `None` | Flag name → value spec (None = boolean flag) |
| `positionals` | `list[CompletionSpec \| None] \| None` | `None` | Ordered slots (None = free-form, no structural suggestion) |
| `no_args` | `bool` | `False` | Explicit marker: command takes no arguments |

**Composition Rules** (resolution order for mixed-type commands):

```
1. If partial starts with "--" → match against flags only
2. Otherwise → check positional sequence at current index
3. If positional slot is None (free-form) → skip structural, fall through to history
4. If positional slots exhausted → suggest "--" flags (if partial starts with "--") or nothing
5. Dual-role values (e.g., "clear" in errors) → model as positional, NOT subcommand
```

**Flag Scanning Algorithm** (FR-014):
```
For each completed token after command name:
  If token matches "--flag=value" pattern:
    Mark flag as consumed (always, regardless of type)
  Elif token starts with "--":
    Look up in flag map
    If boolean (None) → never consumes next token
    If value-taking (CompletionSpec) → consumed if followed by non-flag token
  Else:
    May be a positional value or a flag's value argument
Last unconsumed value-taking flag → determines completion context for partial
```

### 3. TailCommandSuggester

Custom Textual `Suggester` subclass combining structural completions with history fallback.

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `_history` | `TailCommandHistory` | Reference to history for prefix search fallback |
| `_completion_data` | `dict[str, CompletionSpec]` | Per-command completion specs |
| `_dynamic_sources` | `dict[str, Callable]` | Named dynamic source callables |

**Suggestion Pipeline**:

```
Input: full input string (e.g., "errors --since 5m --code ")

1. PARSE input:
   - tokens = input.str_split()
   - trailing_space = input[-1].isspace() (if input non-empty)
   - if trailing_space: all tokens complete, partial = ""
   - else: partial = tokens[-1], complete = tokens[:-1]

2. IDENTIFY command:
   - If no complete tokens and partial non-empty:
     → command name completion (case-insensitive prefix match)
   - command = first complete token (casefolded for lookup)

3. RESOLVE structural suggestion:
   a. Look up command in _completion_data
   b. If no spec found → skip to history fallback
   c. If spec.no_args → return None (no suggestion)
   d. Apply composition rules:
      - Check partial prefix for "--" → flag completion
      - Otherwise → positional/subcommand completion
   e. Apply flag scanning for consumed/unconsumed flags
   f. Match partial against resolved values (case-insensitive for static, case-sensitive for dynamic)
   g. If match found with non-empty suffix → build full-line suggestion

4. FALLBACK to history:
   - If structural produced no non-empty suggestion:
     → call _history.search_prefix(input_value) (case-sensitive)
   - If history match found → return it as full-line suggestion

5. RETURN full input line with suggestion appended, or None
```

### 4. NavigationState (conceptual enum, not necessarily a code artifact)

| State | Condition | Semantics |
|-------|-----------|-----------|
| `AT_REST` | cursor == len(entries), saved_input is None | Default state. Up triggers navigation. Down is no-op. |
| `AT_HISTORY_ENTRY` | 0 <= cursor < len(entries), saved_input preserved | Showing a history entry. Up/Down navigate. |
| `PAST_NEWEST` | cursor == len(entries), saved_input being restored | Transitional: restore input, clear saved, → AT_REST |

The state is derived from `_cursor` and `_saved_input` fields; no separate state field is stored.

## Relationships

```
TailApp (coordinator)
  ├── owns TailCommandHistory (creates, passes to TailInput)
  ├── owns TailCommandSuggester (creates with history ref, passes to TailInput)
  ├── provides dynamic_sources dict (callables closing over app state)
  └── calls history.add() on command submission

TailInput (widget)
  ├── receives TailCommandHistory via constructor (FR-023)
  ├── receives TailCommandSuggester via constructor (FR-023) [passed as `suggester` to parent Input]
  ├── binds Up/Down to history.navigate_back/forward
  ├── uses _navigating guard for programmatic value changes (FR-025)
  └── watch_value resets navigation on non-guarded changes (FR-004)

TailCommandSuggester
  ├── references TailCommandHistory._search_prefix for fallback (FR-016)
  ├── references TAIL_COMPLETION_DATA for structural completions
  └── calls dynamic_sources callables at suggestion time (FR-015)

CompletionSpec
  ├── defined per-command in TAIL_COMPLETION_DATA dict
  ├── may reference dynamic_sources by key
  └── nested via subcommands field (e.g., highlight → enable → highlighter_names)
```

## Storage Schema

### History File (`tail_history`)

```
# File: ~/.local/share/pgtail/tail_history (Linux example)
# Encoding: UTF-8
# Format: one command per line, newline-delimited
# Max entries: 500 (compaction at 1000)
# Max line bytes: 4096 (skip on load)

level error+
since 5m
filter /deadlock/i
errors --code 23505
highlight enable duration
```

No header, no metadata, no versioning. Entries are plain command strings exactly as entered by the user.

## Dynamic Source Specifications

| Source Key | Provider | Used By | Match Type |
|-----------|----------|---------|------------|
| `highlighter_names` | `HighlighterRegistry` or `HighlightingConfig` | highlight enable/disable/remove | case-sensitive |
| `setting_keys` | `ConfigSchema` SETTING_KEYS constant | set | case-sensitive |
| `help_topics` | `COMMAND_HELP.keys()` + `["keys"]` | help | case-sensitive |

Note: Per FR-018, dynamic sources use case-sensitive matching. Static values (level names, time presets, flag names, subcommand names) use case-insensitive matching.
