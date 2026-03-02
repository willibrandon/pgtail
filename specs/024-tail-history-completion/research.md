# Research: Tail Mode Command History & Autocomplete

**Feature Branch**: `024-tail-history-completion`
**Date**: 2026-03-01

## R-001: Textual Suggester API Integration

**Question**: How does Textual's Suggester API work and what constraints does it impose on our implementation?

**Decision**: Subclass `Suggester` with `use_cache=False` and `case_sensitive=True`.

**Rationale**:
- `use_cache=False` is required because history changes on every command submission and dynamic sources change during a session (FR-020). The Suggester's built-in LRU cache (1024 entries) would return stale results.
- `case_sensitive=True` is required because we need mixed case behavior: case-insensitive for command names and static arguments, but case-sensitive for history (FR-018). Setting `case_sensitive=True` passes the raw input value to `get_suggestion()`, allowing internal casing control.
- `get_suggestion()` is async but our implementation is synchronous (no I/O during suggestion). The async signature is satisfied trivially.
- The return value must be the **full suggested input line**, not just the completion portion (FR-017). The Input widget displays `suggestion[len(value):]` as ghost text.
- Race safety is built-in: Input validates `event.value == self.value` before applying a suggestion, so stale suggestions from rapid typing are discarded.

**Alternatives Considered**:
- `case_sensitive=False` with internal re-casing — Rejected: casefolding loses the original input needed for case-sensitive history matching
- Custom suggestion mechanism bypassing Suggester — Rejected: unnecessary complexity when the standard API fits perfectly

## R-002: Reactive Watcher Synchronicity (Guard Pattern)

**Question**: Are Textual's reactive watchers synchronous, enabling the boolean guard pattern required by FR-025?

**Decision**: Yes. Reactive watchers fire synchronously during `Reactive.__set__`, making the boolean guard pattern reliable.

**Rationale**:
- Textual's `Reactive` descriptor calls watchers synchronously in the `__set__` method chain
- Setting `_navigating = True` before `self.value = entry` guarantees the watcher sees the flag during assignment
- The sequence `self._navigating = True; self.value = entry; self._navigating = False` is atomic from the watcher's perspective
- Input's `_watch_value()` also fires synchronously, clearing the old suggestion and requesting a new one — this is desirable even during navigation (user sees ghost text for the navigated-to entry)

**Alternatives Considered**:
- Message-based approach (post a custom message with a "source" attribute) — Rejected: adds async complexity for a fundamentally synchronous operation
- Override `_watch_value` directly — Rejected: fragile coupling to Textual internals; our `watch_value` coexists cleanly
- `on(Input.Changed)` event handler — Rejected: events are async (posted to message queue), defeating the guard pattern's synchronous requirement

## R-003: History File Path Strategy

**Question**: Where should the tail mode history file be stored, and how should the path be resolved?

**Decision**: New `get_tail_history_path()` function in `tail_history.py` following the same platform-resolution pattern as `config.py`'s `get_history_path()`, but with filename `tail_history`.

**Rationale**:
- FR-005 defines: macOS `~/Library/Application Support/pgtail/tail_history`, Linux `~/.local/share/pgtail/tail_history`, Windows `%APPDATA%/pgtail/tail_history`
- Existing `get_history_path()` returns the REPL history file (`history`), which must remain separate (Non-Goal: no shared REPL history)
- Path resolution logic is ~15 lines and self-contained; duplication is acceptable vs. generalizing an existing API
- Parent directory creation reuses the same `os.makedirs(exist_ok=True)` pattern

**Alternatives Considered**:
- Generalize `get_history_path(filename)` — Rejected: changes the existing API used by REPL history
- Store alongside config file — Rejected: spec defines data directory paths, not config directory
- Use `pathlib.Path.home() / ".pgtail_tail_history"` — Rejected: violates platform conventions (XDG on Linux, Library on macOS)

## R-004: Input Parsing Strategy

**Question**: How should input text be parsed for suggestion resolution?

**Decision**: Use `str.split()` for whitespace tokenization with trailing-space detection for the partial word.

**Rationale**:
- `str.split()` with no arguments handles all whitespace types and collapses consecutive runs (FR-021)
- Parsing algorithm:
  1. If input is empty or whitespace-only → no suggestion
  2. Split input with `str.split()`
  3. If input ends with whitespace → all tokens are complete, partial is `""`
  4. If input does not end with whitespace → last token is the partial word, preceding tokens are complete
  5. First complete token identifies the command; subsequent complete tokens are consumed arguments
- `--flag=value` tokens: detected by `--` prefix + `=` presence, split on first `=` to extract flag name and attached value (FR-021)
- When partial itself matches `--flag=` (ends with `=`), suggest values for that flag using text after `=` as prefix

**Alternatives Considered**:
- `shlex.split()` — Rejected: fails on unbalanced quotes in partial input; quoting is not needed for tail mode commands
- Custom state-machine lexer — Rejected: over-engineering; whitespace-split with trailing-space detection handles all spec requirements
- Regex-based tokenizer — Rejected: less readable than split-based approach for no benefit

## R-005: Completion Data Architecture

**Question**: How should per-command completion specs be structured?

**Decision**: `CompletionSpec` dataclass with optional fields for each structural type, stored in a module-level dictionary `TAIL_COMPLETION_DATA`.

**Rationale**:
- Dataclass provides clear structure with type annotations
- Optional fields allow flexible composition: a command can have both positionals and flags (`errors` has positional `clear` and flags `--code`, `--trend`)
- Dynamic sources stored as callables (`Callable[[], list[str]]`) for lazy resolution at suggestion time (FR-015)
- `None` value in flag map indicates boolean flag that never consumes the following token (FR-014)
- `None` value in positional sequence indicates free-form slot (FR-022)
- Module-level constant dictionary is easy to test, inspect, and maintain

**Alternatives Considered**:
- Nested dicts without dataclass — Rejected: no type safety, harder to document and validate
- Class hierarchy (FlagSpec, PositionalSpec, SubcommandSpec) — Rejected: over-engineering; a flat dataclass with optional fields is sufficient for the ~20 commands
- Declarative DSL (TOML/YAML) — Rejected: callables for dynamic sources require Python, and the data structure is code-adjacent

## R-006: Guard Pattern Scope Verification

**Question**: Exactly which operations need the synchronous guard?

**Decision**: Guard is set only around programmatic `self.value = ...` assignments during history navigation. Not during `reset_navigation()`.

**Rationale**:
- FR-025 specifies: guard around "programmatic assignment to the input widget's value during navigation state transitions"
- Operations requiring guard:
  - `navigate_back()` → sets input value to history entry
  - `navigate_forward()` → sets input value to next entry or restored saved input
- Operations NOT requiring guard:
  - `reset_navigation()` → clears cursor and saved input but does NOT change input value
  - `add()` → modifies history list, not input value
- Over-guarding `reset_navigation()` would be a no-op but misleading in code review
- Right arrow suggestion acceptance (`self.value = self._suggestion`) does NOT need the guard — it should reset navigation per FR-026, which happens naturally because the guard is not set

**Alternatives Considered**:
- Guard all history object method calls — Rejected: only value-changing operations need protection
- Context manager guard (`with self._navigating:`) — Considered viable but a simple `try/finally` with flag set/clear is equivalent and more explicit

## R-007: Dynamic Source Resolution

**Question**: What are the three dynamic completion sources and how should they be accessed?

**Decision**: Pass a dictionary of callables from TailApp to TailCommandSuggester:

```python
dynamic_sources = {
    "highlighter_names": Callable[[], list[str]],  # HighlighterRegistry.get_all_names()
    "setting_keys": Callable[[], list[str]],        # ConfigSchema key list
    "help_topics": Callable[[], list[str]],          # COMMAND_HELP.keys() + ["keys"]
}
```

**Rationale**:
- FR-015 specifies three dynamic sources resolved at suggestion time
- Highlighter names change during a session (user adds/removes custom highlighters via `highlight add`/`remove`)
- Setting keys are stable but sourced from config module at runtime
- Help topics include both `COMMAND_HELP` entries and the static `keys` entry
- Callables provide clean decoupling: the suggester doesn't import app modules directly
- TailApp creates the callables during initialization, closing over the live state

**Alternatives Considered**:
- Import source modules directly in suggester — Rejected: tight coupling to app internals
- Singleton registry pattern — Rejected: unnecessary indirection; callables are simpler
- Pre-compute all sources at startup — Rejected: violates FR-020 (no caching) and FR-015 (resolve at suggestion time)

## R-008: History Navigation Key Bindings

**Question**: How should Up/Down arrow keys be bound in TailInput?

**Decision**: Add `Binding("up", "history_back", show=False)` and `Binding("down", "history_forward", show=False)` to TailInput's BINDINGS list with corresponding action methods.

**Rationale**:
- Textual's Input widget does not bind Up/Down by default — they are available for custom use
- Using Textual's binding system is consistent with existing TailInput bindings (`q` → `action_quit_if_empty`, `escape` → `action_clear_and_blur`)
- Action methods have access to `self.value` (current input), `self._history` (history object), and can set `self._navigating` (guard flag)
- `show=False` prevents these from appearing in the footer binding bar

**Alternatives Considered**:
- Override `on_key()` handler — Rejected: bypasses Textual's binding system, inconsistent with existing code
- Define bindings on TailApp — Rejected: history navigation is input-widget-specific behavior, not app-level

## R-009: File I/O Error Handling

**Question**: How should history file I/O errors be handled?

**Decision**: All file I/O wrapped in try/except, logging at DEBUG level, never surfacing errors to the user.

**Rationale**:
- FR-008 requires silent handling: "without crashing or disrupting the user experience"
- History is a convenience feature; any failure mode should degrade to fresh-start (empty history)
- Error conditions and their handling:
  - **Load fails** (FileNotFoundError, PermissionError, UnicodeDecodeError) → empty history, DEBUG log
  - **Save fails** (PermissionError, OSError) → single entry lost, DEBUG log
  - **Compact fails** (any exception) → leave file unmodified, DEBUG log
- DEBUG level chosen over WARNING because silent handling means the user shouldn't see these unless they enable verbose logging

**Alternatives Considered**:
- Show warning in status bar on first error — Rejected: FR-008 says "without disrupting"; status bar messages are user-visible disruption
- Retry with backoff — Rejected: over-engineering for append-only writes to a local file
- In-memory-only fallback mode — This naturally happens: if load fails, history is empty; if save fails, in-memory history still works for the session

## R-010: Tail Mode Command Inventory

**Question**: What is the complete list of tail mode commands and their argument structures?

**Decision**: 20 commands with completion support + 7 no-argument commands. Inventory derived from `cli_tail.py` TAIL_MODE_COMMANDS list, `tail_textual.py` `_handle_command()` method, and `commands.py` PgtailCompleter:

| Command | Type | Positionals | Flags |
|---------|------|-------------|-------|
| level | positional | [level_values] | — |
| filter | positional | [free-form regex] | — |
| since | positional | [time_presets] | — |
| until | positional | [time_presets] | — |
| between | positional×2 | [time_presets, time_presets] | — |
| slow | positional | [threshold_presets] | — |
| clear | positional | ["force"] | — |
| errors | pos + flags | ["clear"] | --trend(bool), --live(bool), --code(value→SQLSTATE), --since(value→time) |
| connections | pos + flags | ["clear"] | --history(bool), --watch(bool), --db(value), --user(value), --app(value) |
| highlight | subcommands | — | — |
| set | positional×2 | [dynamic→setting_keys, free-form] | — |
| export | pos + flags | [free-form path] | --format(value→formats), --highlighted(bool), --append(bool), --follow(bool), --since(value→time) |
| theme | positional | [theme_names] | — |
| help | positional | [dynamic→help_topics] | — |
| pause | no_args | — | — |
| p | no_args | — | — |
| follow | no_args | — | — |
| f | no_args | — | — |
| stop | no_args | — | — |
| exit | no_args | — | — |
| q | no_args | — | — |

**Highlight subcommand tree**:
| Subcommand | Further Args |
|-----------|-------------|
| list | none |
| on | none |
| off | none |
| enable | [dynamic→highlighter_names] |
| disable | [dynamic→highlighter_names] |
| add | [free-form name, free-form pattern] |
| remove | [dynamic→highlighter_names] |
| export | [--file (value→free-form path)] |
| import | [free-form path] |
| preview | none |
| reset | none |

**Static value sets**:
- **level_values**: debug, error, fatal, info, log, notice, panic, warning (full names only; abbreviations are for power users, not discoverable via autocomplete)
- **time_presets**: 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d, clear
- **threshold_presets**: 50, 100, 200, 500, 1000
- **format_values**: text, json, csv
- **theme_names**: dark, light, high-contrast, monokai, solarized-dark, solarized-light (static built-in names; additionally resolve custom themes from filesystem as a dynamic source)
- **SQLSTATE_codes**: sourced from `error_stats.py` common code table (~23 codes)

**Rationale**: Inventory cross-referenced against three sources (TAIL_MODE_COMMANDS, `_handle_command()`, PgtailCompleter) to ensure completeness. Theme command is handled directly in `_handle_command()` outside the cli_tail dispatch but is a valid tail mode command.

## R-011: TailTextual File Size Concern

**Question**: `tail_textual.py` is already 1133 LOC, exceeding the constitution's 900 LOC limit. How should the integration code be added?

**Decision**: Add the minimal wiring code (~10 lines) to `tail_textual.py` and include a refactoring task in the implementation plan to extract command handling into a separate module.

**Rationale**:
- The constitution violation is pre-existing (1133 LOC before this feature)
- Integration code is minimal: 2 imports, 3 lines for object creation, 2 lines in on_mount, 2 lines in on_input_submitted
- Blocking the feature on a refactoring prerequisite would delay delivery with no user benefit
- The refactoring task extracts `_handle_command()` and its helper methods (lines 960-1133, ~173 LOC) into a new `tail_command_handler.py` module, bringing `tail_textual.py` under the 900 LOC limit

**Scope Expansion**: Add a refactoring task to extract command handling from `tail_textual.py` into `tail_command_handler.py`, reducing `tail_textual.py` to ~970 LOC (still slightly over, but the export handler at lines 787-874 is another candidate for extraction).

**Alternatives Considered**:
- Refactor first, then integrate — Viable but creates a two-phase dependency; parallel approach (refactor + integrate in same feature) is more efficient
- Leave as-is — Rejected: the plan must acknowledge constitution violations per scope expansion policy
