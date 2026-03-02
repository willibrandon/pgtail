# Tasks: Tail Mode Command History & Autocomplete

**Input**: Design documents from `/specs/024-tail-history-completion/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: Required per SC-008. All acceptance scenarios must have automated tests. Branch coverage >95% for navigation state transitions, structural-to-history fallback, and composition rules. Overall >90% for all new code.

**Organization**: Tasks grouped by user story (5 stories: US1–US5). Each story independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same phase)
- **[Story]**: Which user story (US1–US5)
- Exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization needed — extending existing `pgtail_py/` package with new modules. Existing test infrastructure (pytest, pytest-asyncio) already configured.

No setup tasks required.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No blocking prerequisites identified. All user stories can begin from their own phase.

**Note**: US1 and US2 are both P1 priority. Their core module work can run in parallel (T001 on tail_history.py, T006 on tail_completion_data.py, T007 on tail_suggester.py — all different files). However, T002 (US1) and T008 (US2) both modify tail_input.py and tail_textual.py, so integration/wiring tasks must be serialized. Recommended order: T002→T003 (US1 wiring), then T008 (US2 wiring). US3 depends on US2's suggester infrastructure. US4 depends on US1's history and US2's suggester. US5 depends on US1's history.

**Checkpoint**: Proceed directly to user story phases.

---

## Phase 3: User Story 1 — Command History Recall (Priority: P1) 🎯 MVP

**Goal**: Users can press Up/Down arrows to cycle through previously entered commands. Original input is saved on first backward navigation and restored when navigating past the newest entry. Typing resets navigation.

**Independent Test**: Enter commands (`level error+`, `since 5m`, `filter /deadlock/`) in tail mode, press Up to cycle backward, Down to cycle forward. Verify three-state cursor behavior (at-rest → at-history → past-newest → at-rest). Verify typing resets navigation. Verify consecutive dedup.

**Spec Coverage**: FR-001, FR-002, FR-003, FR-004, FR-007, FR-025, FR-026

### Implementation for User Story 1

- [ ] T001 [US1] Implement TailCommandHistory in-memory core in pgtail_py/tail_history.py
  - `__init__(max_entries: int = 500, history_path: Path | None = None)` with `_entries: list[str]`, `_cursor: int`, `_saved_input: str | None`, `_max_line_bytes: int = 4096`, `_compact_threshold: int = 1000`
  - `add(command: str)` — reject empty/whitespace-only (`if not command or not command.strip()`), consecutive dedup (`if _entries and _entries[-1] == command`), trim oldest when exceeding max_entries, reset navigation to at-rest
  - `navigate_back(current_input: str) -> str | None` — three-state cursor per data-model.md: from at-rest save current_input, set cursor=len-1, return entries[cursor]; from at-history-entry set cursor=max(0, cursor-1), return entries[cursor]; if history empty return None; at oldest entry (cursor 0) return entries[0] unchanged
  - `navigate_forward() -> tuple[str | None, bool]` — from at-rest return (None, False) no-op; from at-history-entry: if cursor+1 < len then cursor+=1 return (entries[cursor], False); if cursor+1 == len then restore saved_input, clear _saved_input, set cursor=len, return (saved_input, True)
  - `reset_navigation()` — set cursor=len(entries), clear _saved_input to None
  - Properties: `at_rest: bool` (cursor == len and _saved_input is None), `entries: list[str]` (copy of _entries), `__len__` (len of _entries)
  - Per contracts/interfaces.md §1, data-model.md state machine, quickstart.md §Step 1
- [ ] T002 [US1] Add history parameter, Up/Down bindings, and guard pattern to TailInput in pgtail_py/tail_input.py
  - Add `history: TailCommandHistory | None = None` to constructor (keyword-only, backward-compatible per FR-023); store as `self._history`
  - Add `self._navigating: bool = False` instance flag (synchronous guard per D-002, research.md R-002)
  - Add bindings to BINDINGS list: `Binding("up", "history_back", "History back", show=False)`, `Binding("down", "history_forward", "History forward", show=False)` per research.md R-008
  - Implement `action_history_back()` — if no `_history`, return; call `navigate_back(self.value)`; if result is not None: `self._navigating = True`, `try: self.value = entry; self.cursor_position = len(entry)`, `finally: self._navigating = False`
  - Implement `action_history_forward()` — if no `_history`, return; call `navigate_forward()`; if (text, restored) is not (None, False): set guard, try/finally set self.value and cursor_position, clear guard
  - Implement `watch_value(self, value: str)` — if not `_navigating` and `_history`: call `self._history.reset_navigation()` (FR-004, FR-025, FR-026)
  - `action_clear_and_blur()` — existing method already sets `self.value = ""`, which triggers watch_value → reset_navigation; no changes needed
  - Per contracts/interfaces.md §4, research.md R-002 (synchronous reactives), R-006 (guard scope), R-008 (key bindings)
- [ ] T003 [US1] Wire history creation and command recording in TailApp in pgtail_py/tail_textual.py
  - Import `TailCommandHistory` from `pgtail_py.tail_history`
  - In `__init__()` (after existing init code): `self._history = TailCommandHistory(max_entries=500)` (no path yet — persistence wired in US5)
  - In `compose()`: pass `history=self._history` to `TailInput()` constructor call (currently at line ~271)
  - In `on_input_submitted()` (line 476): after `command = event.value.strip()` and before `self._handle_command(command)`, add `self._history.add(command)` (only if command is non-empty, which is already guarded)
  - Per quickstart.md §Step 5, contracts/interfaces.md §5

### Tests for User Story 1

- [ ] T004 [US1] Write TailCommandHistory in-memory unit tests in tests/test_tail_history.py
  - **Navigation state transitions** (all 7 from data-model.md):
    - at-rest → Up → at-history-entry (saves input, returns newest entry)
    - at-rest → Down → at-rest (returns (None, False), no-op)
    - at-rest → type/submit → at-rest (no-op on navigation state)
    - at-history-entry → Up → at-history-entry (cursor decrements, clamped at 0)
    - at-history-entry → Down (cursor+1 < len) → at-history-entry (cursor increments)
    - at-history-entry → Down (cursor+1 == len) → past-newest → at-rest (restores saved input, True)
    - at-history-entry → type/submit → at-rest (reset clears cursor and saved_input)
  - **Edge cases**: empty history Up returns None; single entry Up/Down cycle; at-oldest Up returns same entry; navigate_back saves input only on first call from at-rest (subsequent calls preserve original saved_input)
  - **add() validation**: empty string rejected; whitespace-only rejected; consecutive dedup (same command twice → one entry); non-consecutive duplicate kept (A, B, A → three entries); max_entries trimming (501 adds with max=500 → 500 entries, oldest dropped); add resets navigation state to at-rest
  - **Properties**: at_rest True at init; False after navigate_back; True after reset_navigation; entries returns copy (mutation doesn't affect internal state); __len__ returns correct count
  - ~30 tests
- [ ] T005 [US1] Write TailInput history integration tests in tests/test_tail_input_history.py
  - **Constructor backward compatibility**: `TailInput()` with no args works (no history, no errors)
  - **Constructor with history**: `TailInput(history=history)` stores reference in `_history`
  - **Up navigation**: updates input value to history entry; cursor positioned at end of text
  - **Down navigation**: moves to newer entry; past-newest restores saved input
  - **Guard pattern**: programmatic value change during navigation does NOT trigger reset_navigation (watch_value sees _navigating=True and skips); user typing DOES trigger reset_navigation
  - **Ghost acceptance reset**: accepting a suggestion via Right arrow changes self.value, which triggers watch_value with _navigating=False → resets navigation (FR-026)
  - **Suggestions during navigation**: navigate to `"level error+"` via Up, verify ghost text still appears based on the navigated-to value (Textual's _watch_value requests new suggestion even when guard is set — the guard only prevents reset_navigation, not suggestion requests). Confirm the suggestion is correct for the history entry's content.
  - **Edge cases**: Up with empty history (no-op, value unchanged); Down at rest (no-op); Escape clears input and resets navigation (through watch_value triggered by value="")
  - **Existing bindings preserved**: q still quits when empty; q inserts character when input has content; Escape still clears and blurs
  - ~17 tests using Textual app/pilot testing patterns

**Checkpoint**: User Story 1 complete. Users can press Up/Down to recall commands in-memory. History is session-scoped only (persistence in US5).

---

## Phase 4: User Story 2 — Ghost Text Command Autocomplete (Priority: P1)

**Goal**: As users type, dimmed ghost text suggestions appear inline showing completed command names. Right arrow accepts the suggestion. Case-insensitive prefix matching, first alphabetical match shown.

**Independent Test**: Type partial command names (`le`, `hi`, `s`) and verify ghost text shows correct command completions. Press Right arrow to accept. Verify case-insensitive matching and first-alphabetical ordering.

**Spec Coverage**: FR-010, FR-011, FR-017, FR-018, FR-019, FR-020, FR-021

**Dependencies**: Core module tasks (T006, T007) can start in parallel with US1's core module task (T001) since they work on different files. However, T008 modifies tail_input.py and tail_textual.py which T002/T003 also modify — T008 must run after T002 and T003 complete.

### Implementation for User Story 2

- [ ] T006 [US2] Create CompletionSpec dataclass and initial TAIL_COMPLETION_DATA in pgtail_py/tail_completion_data.py
  - Import `dataclasses.dataclass`
  - Define `@dataclass(frozen=True) class CompletionSpec` with fields: `static_values: list[str] | None = None`, `dynamic_source: str | None = None`, `subcommands: dict[str, CompletionSpec] | None = None`, `flags: dict[str, CompletionSpec | None] | None = None`, `positionals: list[CompletionSpec | None] | None = None`, `no_args: bool = False`
  - Define `TAIL_COMPLETION_DATA: dict[str, CompletionSpec]` with entries for all tail mode commands: `level`, `filter`, `since`, `until`, `between`, `slow`, `clear`, `errors`, `connections`, `highlight`, `set`, `export`, `theme`, `help`, `pause`, `p`, `follow`, `f`, `stop`, `exit`, `q` — initially with `CompletionSpec()` placeholders for commands with arguments, `CompletionSpec(no_args=True)` for no-arg commands (pause, p, follow, f, stop, exit, q)
  - Note: Full command specs (static values, flags, positionals, subcommands) completed in US3 (T010)
  - Per contracts/interfaces.md §3, research.md R-005
- [ ] T007 [US2] Implement TailCommandSuggester with command name completion in pgtail_py/tail_suggester.py
  - Import `Suggester` from `textual.suggester`, `TailCommandHistory` from `pgtail_py.tail_history`, `CompletionSpec` from `pgtail_py.tail_completion_data`
  - `class TailCommandSuggester(Suggester):` with `super().__init__(use_cache=False, case_sensitive=True)` per D-001
  - `__init__(self, history: TailCommandHistory, completion_data: dict[str, CompletionSpec], dynamic_sources: dict[str, Callable[[], list[str]]])` — store all three as `_history`, `_completion_data`, `_dynamic_sources`
  - `_parse_input(self, value: str) -> tuple[str | None, list[str], str]`:
    - If value is empty or whitespace-only → return (None, [], "")
    - tokens = value.split()
    - If value ends with whitespace → command = tokens[0].lower() if tokens else None, completed_args = tokens[1:], partial = ""
    - If value does not end with whitespace and len(tokens) == 1 → command = None, completed_args = [], partial = tokens[0]
    - If value does not end with whitespace and len(tokens) > 1 → command = tokens[0].lower(), completed_args = tokens[1:-1], partial = tokens[-1]
    - Handle `--flag=value` token splitting in completed_args: detect `--` prefix + `=` → split on first `=` (deferred to US3 T012 for flag scanning)
    - **Docstring note**: `command=None` means "the user is still typing the first word" (no complete tokens yet). It does NOT mean "command not recognized" — unknown commands have command set to the casefolded first token and receive no structural suggestions (fall through to history).
    - Per contracts/interfaces.md §2, research.md R-004
  - `_match_values(self, values: list[str], partial: str, case_sensitive: bool) -> str | None`:
    - For each value in values (already sorted): if case-sensitive, check `value.startswith(partial)`; else check `value.lower().startswith(partial.lower())`
    - Return first match (original casing), or None
  - `async def get_suggestion(self, value: str) -> str | None`:
    - Parse input with `_parse_input(value)`
    - If command is None and partial is non-empty → case-insensitive prefix match against sorted `_completion_data.keys()` → if match found: compute `suffix = matched_command[len(partial):]`; if suffix is non-empty: return `value + suffix` (preserves user's casing, appends only the untyped portion)
    - If command is None and partial is empty → return None
    - If command is identified and partial is empty and no trailing space → return None (user is typing command name that exactly matches, e.g., `level` with no space — but `p` exactly matches `p` so no suggestion)
    - If exact command match with empty suffix (e.g., typing `p` matches command `p`) → return None
    - **CRITICAL full-line return formula (FR-017)**: ALWAYS compute `suffix = matched_value[len(partial):]` and return `value + suffix`. This preserves the user's exact input text and ensures `suggestion.startswith(self.value)` is True — required by Textual's Input widget which validates this before displaying ghost text. For case-mismatched input like `"LEV"` matching `"level"`: suffix = `"level"[3:]` = `"el"`, return = `"LEV" + "el"` = `"LEVel"`. Ghost text shows `"el"`. When accepted, the command parser lowercases.
    - Note: Argument completion (_resolve_structural) added in US3; history fallback added in US4
  - Per contracts/interfaces.md §2, research.md R-001
- [ ] T008 [US2] Add suggester parameter to TailInput and wire in TailApp in pgtail_py/tail_input.py and pgtail_py/tail_textual.py
  - **tail_input.py**: Add `suggester: Suggester | None = None` keyword param to `__init__`; import `Suggester` from `textual.suggester`; pass `suggester=suggester` to `super().__init__()` call
  - **tail_textual.py**: Import `TailCommandSuggester` from `pgtail_py.tail_suggester` and `TAIL_COMPLETION_DATA` from `pgtail_py.tail_completion_data`; in `__init__()`: create `self._suggester = TailCommandSuggester(history=self._history, completion_data=TAIL_COMPLETION_DATA, dynamic_sources={})` (empty dynamic_sources initially, populated in US3 T013); in `compose()`: pass `suggester=self._suggester` to `TailInput()` constructor
  - Per quickstart.md §Step 5, contracts/interfaces.md §4-5

### Tests for User Story 2

- [ ] T009 [US2] Write command name completion tests in tests/test_tail_suggester.py
  - **Input parsing**: empty string → (None, [], ""); single partial `"le"` → (None, [], "le"); command+space `"level "` → ("level", [], ""); trailing spaces `"level  "` → ("level", [], ""); command+partial `"level e"` → ("level", [], "e"); multiple tokens `"errors --since 5m "` → ("errors", ["--since", "5m"], "")
  - **Command name matching**: `"le"` → `"level"` (full-line); `"hi"` → `"highlight"`; `"s"` → `"set"` (first alphabetical before since, slow, stop); `"LEVEL"` → case-insensitive match suggests `"LEVEL"` completed to full command
  - **Exact command match (empty suffix)**: `"p"` → None (exactly matches `p` command); `"q"` → None; `"level"` (no trailing space) → None (exact match, no ghost text for empty suffix)
  - **No match**: `"xyz"` → None; `"zz"` → None
  - **First alphabetical**: `"s"` → `"set"` (not `since`, `slow`, or `stop`); `"c"` → `"clear"` (not `connections`)
  - **Full-line return format**: `"le"` returns `"level"` (not `"vel"`); returned string starts with input value
  - **Alias handling**: `"pa"` → `"pause"` (pa prefix-matches pause); `"fo"` → `"follow"`; `"ex"` → `"exit"` (exit < export alphabetically); `"st"` → `"stop"` (`"st"` does NOT prefix-match `"set"` since `"set"[0:2]` = `"se"` ≠ `"st"`, so only `"stop"` matches)
  - **Suggester configuration**: verify `use_cache=False` and `case_sensitive=True`
  - ~15 tests

**Checkpoint**: User Story 2 complete. Ghost text appears for command names as users type. Combined with US1, users have both history recall and command name suggestions.

---

## Phase 5: User Story 3 — Context-Aware Argument Autocomplete (Priority: P2)

**Goal**: After typing a command name and space, ghost text suggests valid arguments specific to that command: level values, subcommands, flags, time presets, SQLSTATE codes, setting keys, help topics, with correct composition rules and flag scanning.

**Independent Test**: Type `level ` and verify level suggestions; type `highlight ` and verify subcommand suggestions; type `errors --code ` and verify SQLSTATE suggestions; type `errors --since 5m --code ` and verify flag scanning identifies unconsumed `--code`.

**Spec Coverage**: FR-012, FR-013, FR-014, FR-015, FR-021, FR-022

**Dependencies**: US2 (TailCommandSuggester and CompletionSpec infrastructure must exist)

### Implementation for User Story 3

- [ ] T010 [US3] Complete TAIL_COMPLETION_DATA with full command specs in pgtail_py/tail_completion_data.py
  - Define static value constants (module-level, exported for testing):
    - `LEVEL_VALUES: list[str] = ["debug", "error", "fatal", "info", "log", "notice", "panic", "warning"]` (sorted alphabetically; full names only per R-010)
    - `TIME_PRESETS: list[str] = ["10m", "15m", "1d", "1h", "2h", "30m", "4h", "5m", "clear"]` (sorted alphabetically)
    - `THRESHOLD_PRESETS: list[str] = ["100", "1000", "200", "50", "500"]` (sorted alphabetically)
    - `FORMAT_VALUES: list[str] = ["csv", "json", "text"]` (sorted alphabetically)
    - `BUILTIN_THEME_NAMES: list[str] = ["dark", "high-contrast", "light", "monokai", "solarized-dark", "solarized-light"]` (sorted)
    - `SQLSTATE_CODES: list[str]` — import from `pgtail_py.error_stats` and extract common SQLSTATE code strings (sorted)
  - Update TAIL_COMPLETION_DATA entries with full specs:
    - `"level"`: `CompletionSpec(positionals=[CompletionSpec(static_values=LEVEL_VALUES)])`
    - `"filter"`: `CompletionSpec(positionals=[None])` (free-form regex, FR-022)
    - `"since"`: `CompletionSpec(positionals=[CompletionSpec(static_values=TIME_PRESETS)])`
    - `"until"`: `CompletionSpec(positionals=[CompletionSpec(static_values=TIME_PRESETS)])`
    - `"between"`: `CompletionSpec(positionals=[CompletionSpec(static_values=TIME_PRESETS), CompletionSpec(static_values=TIME_PRESETS)])`
    - `"slow"`: `CompletionSpec(positionals=[CompletionSpec(static_values=THRESHOLD_PRESETS)])`
    - `"clear"`: `CompletionSpec(positionals=[CompletionSpec(static_values=["force"])])`
    - `"errors"`: `CompletionSpec(positionals=[CompletionSpec(static_values=["clear"])], flags={"--trend": None, "--live": None, "--code": CompletionSpec(static_values=SQLSTATE_CODES), "--since": CompletionSpec(static_values=TIME_PRESETS)})`
    - `"connections"`: `CompletionSpec(positionals=[CompletionSpec(static_values=["clear"])], flags={"--history": None, "--watch": None, "--db": CompletionSpec(), "--user": CompletionSpec(), "--app": CompletionSpec()})`
    - `"highlight"`: `CompletionSpec(subcommands={"list": CompletionSpec(no_args=True), "on": CompletionSpec(no_args=True), "off": CompletionSpec(no_args=True), "enable": CompletionSpec(positionals=[CompletionSpec(dynamic_source="highlighter_names")]), "disable": CompletionSpec(positionals=[CompletionSpec(dynamic_source="highlighter_names")]), "add": CompletionSpec(positionals=[None, None]), "remove": CompletionSpec(positionals=[CompletionSpec(dynamic_source="highlighter_names")]), "export": CompletionSpec(flags={"--file": CompletionSpec()}), "import": CompletionSpec(positionals=[None]), "preview": CompletionSpec(no_args=True), "reset": CompletionSpec(no_args=True)})`
    - `"set"`: `CompletionSpec(positionals=[CompletionSpec(dynamic_source="setting_keys"), None])` (second positional is free-form value)
    - `"export"`: `CompletionSpec(positionals=[None], flags={"--format": CompletionSpec(static_values=FORMAT_VALUES), "--highlighted": None, "--append": None, "--follow": None, "--since": CompletionSpec(static_values=TIME_PRESETS)})`
    - `"theme"`: `CompletionSpec(positionals=[CompletionSpec(static_values=BUILTIN_THEME_NAMES)])`
    - `"help"`: `CompletionSpec(positionals=[CompletionSpec(dynamic_source="help_topics")])`
  - Per research.md R-010 (command inventory), contracts/interfaces.md §3
- [ ] T011 [P] [US3] Write completion data validation tests in tests/test_tail_completion_data.py
  - **Inventory**: every command from `cli_tail.py` TAIL_MODE_COMMANDS list plus `theme` has a spec entry in TAIL_COMPLETION_DATA
  - **Boolean flags**: `--trend`, `--live`, `--history`, `--watch`, `--highlighted`, `--append`, `--follow` all map to None
  - **Value-taking flags**: `--code`, `--since`, `--format`, `--db`, `--user`, `--app`, `--file` all map to CompletionSpec instances
  - **Positional counts**: level=1, filter=1, since=1, until=1, between=2, slow=1, clear=1, set=2, export=1, theme=1, help=1
  - **Free-form positions**: filter positional[0] is None; export positional[0] is None; highlight→add positional[0] and [1] are None; highlight→import positional[0] is None; set positional[1] is None
  - **No-argument commands**: pause, p, follow, f, stop, exit, q all have `no_args=True`
  - **Dynamic source keys**: only three keys used: "highlighter_names", "setting_keys", "help_topics"
  - **SQLSTATE_CODES**: non-empty list, each code is exactly 5 characters matching `[0-9A-Z]{5}` pattern
  - **Static value lists**: LEVEL_VALUES, TIME_PRESETS, THRESHOLD_PRESETS, FORMAT_VALUES, BUILTIN_THEME_NAMES are all non-empty and sorted alphabetically
  - **Highlight subcommands**: all 11 subcommands present (list, on, off, enable, disable, add, remove, export, import, preview, reset)
  - ~15 tests
- [ ] T012 [P] [US3] Implement _resolve_structural() and flag scanning in TailCommandSuggester in pgtail_py/tail_suggester.py
  - `_resolve_structural(self, command: str, completed_args: list[str], partial: str) -> str | None`:
    - Look up command (casefolded) in `_completion_data`; if not found → return None
    - If spec.no_args → return None
    - If spec.subcommands and completed_args: first arg matches a subcommand → recurse with sub-spec and remaining args
    - If spec.subcommands and not completed_args: match partial against sorted subcommand names (case-insensitive)
    - **Composition rules** (data-model.md §CompletionSpec):
      1. If partial starts with `"--"` → match against flag names only (case-insensitive)
      2. Otherwise → check positional sequence at current positional index
      3. If positional slot is None (free-form) → return None (skip structural)
      4. If positional slots exhausted → flag names for `"--"` partial, else return None
    - **Flag scanning algorithm** (FR-014, data-model.md):
      - Track consumed flags and positional index
      - For each token in completed_args: if matches `--flag=value` pattern → mark flag consumed; elif starts with `"--"` → look up in spec.flags: if boolean (None) → never consumes next; if value-taking (CompletionSpec) → mark as pending; else (non-flag token) → if pending value-taking flag → consume it; else → increment positional index
      - After scanning: if last unconsumed value-taking flag exists → resolve values from its CompletionSpec
    - **`--flag=value` partial handling**: when partial matches `--flag=...` (contains `=` after `--` prefix) → split on first `=`, look up flag, suggest values using text after `=` as prefix
    - **Value resolution**: if CompletionSpec has static_values → _match_values(values, partial, case_sensitive=False); if dynamic_source → call `_dynamic_sources[key]()` → _match_values(values, partial, case_sensitive=True) (FR-018)
    - Return matched value (full value, not suffix), or None
  - Per data-model.md §CompletionSpec, contracts/interfaces.md §2
- [ ] T013 [P] [US3] Wire dynamic_sources callables in TailApp in pgtail_py/tail_textual.py
  - In `__init__()` (or `compose()`), create `dynamic_sources` dict with three callables:
    - `"highlighter_names"`: `lambda: sorted(self._state.highlighting_config.get_all_names())` (or equivalent from HighlighterRegistry)
    - `"setting_keys"`: `lambda: sorted(list(SETTING_KEYS))` (import SETTING_KEYS from config module)
    - `"help_topics"`: `lambda: sorted(list(COMMAND_HELP.keys()) + ["keys"])` (import COMMAND_HELP from cli_tail_help)
  - Update TailCommandSuggester creation from T008: replace `dynamic_sources={}` with `dynamic_sources=dynamic_sources`
  - Per research.md R-007 (dynamic sources), contracts/interfaces.md §5
- [ ] T014 [US3] Integrate _resolve_structural() into get_suggestion() in pgtail_py/tail_suggester.py (depends on T012 — same file, must be sequential)
  - In `get_suggestion()`: after parsing input, if command is identified (not None) and we have a partial or trailing space:
    - Call `_resolve_structural(command, completed_args, partial)`
    - If structural returns a non-None matched value: compute `suffix = matched_value[len(partial):]`; if suffix is non-empty:
      - For trailing-space case (partial is ""): suffix = entire matched_value, return `value + matched_value`
      - For partial-word case: suffix = `matched_value[len(partial):]`, return `value + suffix` (preserves user's exact casing in the partial they typed)
      - Example: input `"level E"`, partial `"E"`, structural match `"error"` → suffix = `"error"[1:]` = `"rror"` → return `"level E" + "rror"` = `"level Error"`. Textual checks `"level Error".startswith("level E")` → True. Ghost text shows `"rror"`.
    - If structural returns None OR matched_value == partial (empty suffix) → fall through (to history fallback in US4, or None for now)
  - **CRITICAL**: The return formula `value + matched_value[len(partial):]` must be used consistently. Returning `value_before_partial + matched_value` would break Textual's `suggestion.startswith(self.value)` check for case-mismatched input (FR-017, FR-018).
  - Per contracts/interfaces.md §2, quickstart.md key implementation notes

### Tests for User Story 3

- [ ] T015 [US3] Write argument completion tests in tests/test_tail_suggester.py
  - **Static values**: `"level "` → `"level debug"` (first alphabetical); `"level e"` → `"level error"`; `"since "` → first time preset; `"slow "` → first threshold preset
  - **Subcommands**: `"highlight "` → `"highlight add"` (first alphabetical); `"highlight enable "` → dynamic highlighter name (mock dynamic_sources)
  - **Nested subcommand with no_args**: `"highlight list "` → None (list takes no args)
  - **Subcommand positional exhausted**: `"highlight enable duration "` → None (enable has 1 positional for highlighter name, now filled; no further args expected)
  - **Boolean flags skip**: `"errors --trend "` → `"errors --trend clear"` (--trend is boolean, doesn't consume, so positional index 0 is still active → suggests `"clear"` from positionals); `"errors --trend --code "` → SQLSTATE code (--trend boolean never consumes, --code is last unconsumed value-taking flag)
  - **Value-taking flags**: `"errors --code "` → SQLSTATE code; `"errors --since "` → time preset
  - **Flag scanning consumed**: `"errors --since 5m --code "` → SQLSTATE (--since consumed by 5m, --code unconsumed)
  - **--flag=value**: `"connections --db="` → falls back (no dynamic source for db values per Scenario 3.18); `"export --format="` → format values (csv, json, text)
  - **Positional tracking**: `"between 5m "` → second time preset; `"between 5m 15:00 "` → None (exhausted)
  - **Free-form skip**: `"filter /"` → None (free-form); `"export /tmp/file "` → flag suggestions for `--` prefix or None
  - **No-args after space**: `"pause "` → None; `"q "` → None
  - **Exhausted positionals + flag partial**: `"export /tmp/out.csv --"` → first flag (--append, --follow, --format, etc.)
  - **Dynamic sources**: `"set "` → setting key (mock); `"help "` → help topic (mock)
  - **Positional values**: `"errors c"` → `"errors clear"` (partial matches positional, not flag because no --)
  - **Case-insensitive static with user casing preserved**: `"level E"` → `"level Error"` (suffix = `"error"[1:]` = `"rror"`, preserving user's `"E"`); `"level ERROR"` → None (suffix = `"error"[5:]` = `""` — empty suffix, falls through to history; with no matching history entry, returns None); `"level Er"` → `"level Error"` (suffix = `"ror"`)
  - **Case-sensitive dynamic**: mock dynamic with ["Duration", "sqlstate"] → `"highlight enable D"` → `"highlight enable Duration"` (preserves case); `"highlight enable d"` → no match (case-sensitive)
  - **Theme command**: `"theme "` → first built-in theme; `"theme d"` → `"theme dark"`
  - **Unknown command args**: `"foobar "` → None (no spec found)
  - ~25 tests

**Checkpoint**: User Story 3 complete. Full structural argument completion operational for all 20+ commands with flags, positionals, subcommands, and dynamic sources.

---

## Phase 6: User Story 4 — History-Aware Suggestions (Priority: P2)

**Goal**: When structural completion produces no match or an empty suffix, the system falls back to suggesting previously entered commands from history via case-sensitive prefix matching.

**Independent Test**: Enter `level error+`, then type `level error` — ghost text suggests `+` from history. Enter `filter /deadlock/i`, type `filter /dead` — ghost text suggests `lock/i` from history. Verify structural takes priority over history when both match.

**Spec Coverage**: FR-016, FR-018

**Dependencies**: US1 (TailCommandHistory must exist), US2 (TailCommandSuggester must exist)

### Implementation for User Story 4

- [ ] T016 [US4] Implement search_prefix() in TailCommandHistory in pgtail_py/tail_history.py
  - `search_prefix(self, prefix: str) -> str | None`:
    - Iterate `_entries` from newest to oldest (reversed)
    - Find first entry where `entry.startswith(prefix)` and `entry != prefix` (must have non-empty suffix)
    - Case-sensitive matching per FR-018 (preserves regex patterns like `/Deadlock/`, usernames like `Admin`)
    - Return full entry string, or None if no match
  - Per contracts/interfaces.md §1
- [ ] T017 [P] [US4] Implement history fallback path in TailCommandSuggester.get_suggestion() in pgtail_py/tail_suggester.py
  - In `get_suggestion()`: after structural resolution returns None or empty-suffix result:
    - Call `self._history.search_prefix(value)` where value is the full raw input string
    - If history match found → return it as the full-line suggestion (it already includes the prefix)
    - If no match → return None
  - Fallback triggers when: no structural match found, structural match has empty suffix (e.g., `level error` matches `error` exactly), free-form position skipped structural, unknown command
  - Per contracts/interfaces.md §2, data-model.md suggestion pipeline step 4
- [ ] T018 [P] [US4] Write search_prefix() unit tests in tests/test_tail_history.py
  - **Case-sensitive**: `"level error"` matches history entry `"level error+"` → returns `"level error+"`; `"Level error"` does NOT match `"level error+"` (case-sensitive per FR-018)
  - **Most-recent-first**: entries ["level error+", "level error-"] → search `"level error"` returns `"level error-"` (most recent)
  - **Exact match excluded**: `"level error"` does NOT match history entry `"level error"` (requires non-empty suffix, entry != prefix)
  - **No match**: `"xyz"` with no matching history → returns None
  - **Empty history**: search_prefix on empty history → returns None
  - **Empty prefix**: `""` matches any entry (returns most recent, since all entries start with "")
  - **Special characters**: `"filter /dead"` matches `"filter /deadlock/i"` → returns `"filter /deadlock/i"`
  - ~8 tests

### Tests for User Story 4 (continued)

- [ ] T019 [US4] Write history fallback integration tests in tests/test_tail_suggester.py
  - **Structural empty suffix → history fallback**: history has `"level error+"`, type `"level error"` → structural matches `error` exactly (empty suffix) → fallback to history → suggests `"level error+"`
  - **No structural match → history fallback**: history has `"filter /deadlock/i"`, type `"filter /dead"` → structural returns None (free-form) → fallback → suggests `"filter /deadlock/i"`
  - **Structural takes priority**: history has `"since 5m"`, type `"since 5"` → structural suggests `5m` (from TIME_PRESETS) → NO fallback to history
  - **No match anywhere**: novel input with no matching history and no structural match → returns None
  - **History case-sensitive in fallback**: history has `"Level error+"`, type `"level error"` → structural matches `error` (empty suffix) → fallback → case-sensitive search fails (lowercase vs uppercase L) → returns None
  - ~5 tests

**Checkpoint**: User Story 4 complete. History-based suggestions fill gaps where structural completions don't apply. The full suggestion pipeline (structural → history fallback) is operational.

---

## Phase 7: User Story 5 — Persistent History Across Sessions (Priority: P3)

**Goal**: Command history persists to a platform-specific file and is loaded on next tail mode startup. History survives pgtail restarts. Corrupt/oversized entries handled gracefully.

**Independent Test**: Enter commands in tail mode, exit pgtail, restart, enter tail mode, press Up — previous commands are available. Verify file at correct platform path. Verify corrupt entries are skipped. Verify compaction at threshold.

**Spec Coverage**: FR-005, FR-006, FR-007, FR-008, FR-009

**Dependencies**: US1 (TailCommandHistory in-memory core must exist)

### Implementation for User Story 5

- [ ] T020 [US5] Implement get_tail_history_path() in pgtail_py/tail_history.py
  - Module-level function returning `Path`:
    - macOS (`sys.platform == "darwin"`): `Path.home() / "Library" / "Application Support" / "pgtail" / "tail_history"`
    - Windows (`sys.platform == "win32"`): `Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "pgtail" / "tail_history"`
    - Linux/other: `Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "pgtail" / "tail_history"`
  - Pattern mirrors existing `config.py` `get_history_path()` with different filename
  - Per research.md R-003, contracts/interfaces.md §1
- [ ] T021 [US5] Implement load() in TailCommandHistory in pgtail_py/tail_history.py
  - `load(self) -> None`:
    - If `_history_path` is None → return (in-memory only mode)
    - Wrap all in `try/except Exception:` with `logger.debug("Failed to load history: %s", e)`
    - Open file with `encoding="utf-8", errors="replace"` to handle non-UTF-8 bytes (FR-009)
    - Read line by line; for each line: strip trailing newline; skip if empty; skip if `len(line.encode("utf-8")) > self._max_line_bytes` (FR-009, 4096 byte safety limit)
    - Collect valid entries into list
    - If len > max_entries → take last max_entries (FR-007)
    - Replace `self._entries` with loaded entries
    - Reset navigation state
    - Handle FileNotFoundError specifically (first run → empty history, not even debug-logged as error)
  - Per contracts/interfaces.md §1, research.md R-009
- [ ] T022 [US5] Implement save() in TailCommandHistory in pgtail_py/tail_history.py
  - `save(self, command: str) -> None`:
    - If `_history_path` is None → return
    - Wrap all in `try/except Exception:` with `logger.debug("Failed to save history: %s", e)`
    - Create parent directories: `self._history_path.parent.mkdir(parents=True, exist_ok=True)`
    - Open file in append mode: `open(self._history_path, "a", encoding="utf-8")`
    - Write `command + "\n"`
  - Per contracts/interfaces.md §1, research.md R-009
- [ ] T023 [US5] Implement compact() in TailCommandHistory in pgtail_py/tail_history.py
  - `compact(self) -> None`:
    - If `_history_path` is None → return
    - If `_history_path` does not exist → return
    - Wrap all in `try/except Exception:` with `logger.debug("Failed to compact history: %s", e)`
    - Read all lines in a single pass; if line count <= `_compact_threshold` (default 1000, which is 2× max_entries) → return (no compaction needed)
    - Take last `_max_entries` entries from the already-read lines
    - Rewrite file with retained entries (overwrite mode, encoding="utf-8")
    - Not atomic with concurrent appenders (accepted per FR-006)
  - Per contracts/interfaces.md §1, research.md R-009
- [ ] T024 [US5] Wire persistence lifecycle in TailApp in pgtail_py/tail_textual.py
  - Import `get_tail_history_path` from `pgtail_py.tail_history`
  - Update TailCommandHistory creation in `__init__()`: change from `TailCommandHistory(max_entries=500)` to `TailCommandHistory(max_entries=500, history_path=get_tail_history_path())`
  - In `on_mount()` (line 277): add `self._history.load()` and `self._history.compact()` after existing mount setup
  - In `on_input_submitted()` (line 476): add `self._history.save(command)` after existing `self._history.add(command)` call from T003
  - Per quickstart.md §Step 5, contracts/interfaces.md §5

### Tests for User Story 5

- [ ] T025 [US5] Write file persistence unit tests in tests/test_tail_history.py
  - **get_tail_history_path (all three platforms via monkeypatch)**: monkeypatch `sys.platform` to `"darwin"` → path contains `"Library/Application Support/pgtail/tail_history"`; monkeypatch to `"linux"` → path contains `".local/share/pgtail/tail_history"` (or XDG_DATA_HOME override); monkeypatch to `"win32"` with APPDATA env → path contains `"pgtail/tail_history"` under APPDATA; verify XDG_DATA_HOME override on Linux; verify APPDATA fallback on Windows when env var missing
  - **load() normal**: write 5 lines to temp file → load() → 5 entries in correct order
  - **load() empty file**: empty temp file → load() → empty history, no error
  - **load() missing file**: non-existent path → load() → empty history, no error (graceful degradation)
  - **load() corrupt binary**: write mix of valid UTF-8 and binary bytes → load() → valid entries loaded, corrupt handled via errors="replace"
  - **load() oversized lines**: write one line >4096 bytes and one normal line → load() → normal line loaded, oversized skipped (FR-009)
  - **load() max_entries**: write 1000 lines to file with max_entries=500 → load() → last 500 retained (FR-007)
  - **save() normal**: save 3 commands → read file → 3 lines in order
  - **save() creates dir**: save to path with non-existent parent → parent created, file written
  - **save() appends**: existing file with 2 lines → save 1 more → file has 3 lines
  - **save() error**: set path to read-only location → save() → silently handled (FR-008), verify no exception raised
  - **compact() under threshold**: file with 500 lines, threshold=1000 → compact() → file unchanged
  - **compact() over threshold**: file with 1500 lines, max=500, threshold=1000 → compact() → file rewritten with last 500 lines
  - **compact() error**: simulate OSError during rewrite → file left unmodified (FR-008)
  - **Round-trip**: save 3 commands via save(), then load() → 3 entries in correct order
  - **Persistence integration**: create history with path, add commands, save, create new history with same path, load → entries recovered
  - ~16 tests

**Checkpoint**: User Story 5 complete. History persists across sessions. All 5 user stories are now functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Constitution compliance (file size extraction), full test coverage verification, linting, and success criteria validation

- [ ] T026 Extract command handler from tail_textual.py into pgtail_py/tail_command_handler.py
  - Create new file `pgtail_py/tail_command_handler.py`
  - Move `_handle_command()` method (lines 960–1133, ~173 LOC) from TailApp: extract as `handle_command(command_text, status, state, tailer, log_widget, ...)` top-level function receiving necessary context as parameters
  - Move `_handle_export_command()` method (lines 787–874, ~87 LOC) from TailApp: extract as `handle_export_command(args, log_widget, ...)` top-level function
  - In TailApp: replace method bodies with delegation calls to the new module functions (e.g., `handle_command(command_text, self._status, self._state, self._tailer, log_widget, ...)`)
  - Add necessary imports in the new module (shlex, TailLog, TailStatus, etc.)
  - Reduces tail_textual.py from ~1145 to ~885 LOC (under 900 LOC constitution limit per plan.md D-005, research.md R-011)
  - No behavioral changes — pure refactoring
- [ ] T027 Verify all existing tests pass after command handler extraction
  - Run `make test` — all existing tail mode tests must pass unchanged
  - Focus on: tests that exercise command handling (filter, level, since, errors, connections, export, theme, etc.)
  - Verify no import path changes break existing test files
- [ ] T028 [P] Run full test suite and verify coverage thresholds
  - Run `pytest --cov=pgtail_py --cov-report=term-missing tests/test_tail_history.py tests/test_tail_suggester.py tests/test_tail_completion_data.py tests/test_tail_input_history.py`
  - Verify >95% branch coverage for: TailCommandHistory navigation state transitions, TailCommandSuggester structural-to-history fallback path, _resolve_structural composition rules (flag vs positional vs subcommand)
  - Verify >90% overall branch coverage for all new code (tail_history.py, tail_suggester.py, tail_completion_data.py, tail_input.py modifications, tail_command_handler.py)
  - SC-008 compliance check
- [ ] T029 [P] Run linting and formatting on all new and modified files
  - Run `make lint` and `make format`
  - Files to check: pgtail_py/tail_history.py, pgtail_py/tail_suggester.py, pgtail_py/tail_completion_data.py, pgtail_py/tail_command_handler.py, pgtail_py/tail_input.py, pgtail_py/tail_textual.py
  - Test files: tests/test_tail_history.py, tests/test_tail_suggester.py, tests/test_tail_completion_data.py, tests/test_tail_input_history.py
  - Fix any issues found
- [ ] T030 Verify success criteria SC-001 through SC-007
  - **SC-001**: Most recent command in 1 Up press, Nth in N presses — verified by T004 tests
  - **SC-002**: Suggestion computation <1ms — add timing assertion in test_tail_suggester.py: call get_suggestion 100 times on complex input, verify average <1ms
  - **SC-003**: All commands discoverable via prefix typing — verified by T009 tests (every command in TAIL_COMPLETION_DATA)
  - **SC-004**: All argument types produce correct suggestions — verified by T015 tests
  - **SC-005**: History persists across sessions — verified by T025 round-trip tests
  - **SC-006**: No visible UI chrome changes — visual inspection (ghost text uses built-in Textual styling)
  - **SC-007**: Existing keybindings work — verified by T005 tests (q, Escape, Tab, Enter)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No setup needed
- **Foundational (Phase 2)**: No blocking prerequisites
- **US1 (Phase 3)**: Can start immediately — no dependencies on other stories
- **US2 (Phase 4)**: Core modules (T006, T007) can start in parallel with US1's T001. Integration task T008 must follow US1's T002/T003 (shared files: tail_input.py, tail_textual.py)
- **US3 (Phase 5)**: Depends on US2 completion (needs TailCommandSuggester and CompletionSpec)
- **US4 (Phase 6)**: Depends on US1 (TailCommandHistory) and US2 (TailCommandSuggester)
- **US5 (Phase 7)**: Depends on US1 (TailCommandHistory in-memory core)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
US1 (P1: History Recall) ──────────┬──── US4 (P2: History Suggestions)
                                   │
US2 (P1: Command Autocomplete) ────┤
                                   │
US2 ───────────────────────────────┼──── US3 (P2: Argument Autocomplete)
                                   │
US1 ───────────────────────────────┴──── US5 (P3: Persistent History)
```

### Within Each User Story

- Implementation tasks first (modules must exist before tests can import)
- Tasks modifying the same file are sequential (not marked [P])
- [P] marked tasks can run in parallel within the same phase (different files)
- Story complete before proceeding to dependent stories

### Parallel Opportunities

- **US1 + US2 core modules**: T001 (tail_history.py) can run in parallel with T006 (tail_completion_data.py) and T007 (tail_suggester.py) — different files, no dependencies. **But**: T002/T003 (US1, modify tail_input.py + tail_textual.py) and T008 (US2, also modifies tail_input.py + tail_textual.py) share files and must be serialized: T002→T003→T008. Test tasks T004/T005/T009 can run in parallel (different test files).
- **After US1 + US2 complete**: US3, US4, US5 can all start in parallel
- **Within US3**: T011 (test file), T012 (tail_suggester.py), T013 (tail_textual.py) can all run in parallel after T010 completes
- **Within US4**: T017 (tail_suggester.py) and T018 (test file) can run in parallel after T016 completes
- **Phase 8**: T028 (coverage) and T029 (linting) can run in parallel after T027 completes

---

## Parallel Example: US1 + US2 (Both P1)

```bash
# Phase A — Core modules in parallel (different files, no interdependencies):
Task T001: "Implement TailCommandHistory in-memory core in pgtail_py/tail_history.py"   # US1
Task T006: "Create CompletionSpec and TAIL_COMPLETION_DATA in pgtail_py/tail_completion_data.py"  # US2
Task T007: "Implement TailCommandSuggester in pgtail_py/tail_suggester.py"              # US2

# Phase B — US1 wiring (must be serialized, modifies tail_input.py + tail_textual.py):
Task T002: "Add history parameter and Up/Down bindings to TailInput in pgtail_py/tail_input.py"
Task T003: "Wire history in TailApp in pgtail_py/tail_textual.py"

# Phase C — US2 wiring (must follow Phase B, modifies same files):
Task T008: "Add suggester to TailInput and TailApp wiring"

# Phase D — Tests in parallel (different test files):
Task T004: "Write TailCommandHistory in-memory unit tests in tests/test_tail_history.py"
Task T005: "Write TailInput history integration tests in tests/test_tail_input_history.py"
Task T009: "Write command name completion tests in tests/test_tail_suggester.py"
```

## Parallel Example: Post-US1+US2

```bash
# Launch US3, US4, US5 in parallel after US1+US2 complete:

# US3 Agent: Argument Autocomplete
Task T010-T015

# US4 Agent: History Suggestions
Task T016-T019

# US5 Agent: Persistent History
Task T020-T025
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 3: US1 — Command History Recall
2. **STOP and VALIDATE**: Enter commands, Up/Down cycle works, typing resets
3. Users can immediately benefit from command recall even without autocomplete
4. Deploy/demo if ready

### Incremental Delivery

1. US1 → History recall works → Validate ✓
2. US2 → Command name ghost text works → Validate ✓
3. US3 → Argument ghost text works → Validate ✓
4. US4 → History fallback suggestions work → Validate ✓
5. US5 → History persists across sessions → Validate ✓
6. Polish → Constitution compliance, coverage, cleanup → Final ✓

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With two agents:

1. **Agent A**: US1 (history) → US5 (persistence) → US4 (history suggestions) → share of Polish
2. **Agent B**: US2 (command autocomplete) → US3 (argument autocomplete) → share of Polish
3. Both paths converge at Phase 8 for final validation

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable per acceptance scenarios in spec.md
- TailInput modifications span US1 (history param in T002) and US2 (suggester param in T008) — each story adds its own param
- TailApp wiring spans US1 (T003), US2 (T008), US3 (T013), US5 (T024) — each story adds its own wiring
- test_tail_history.py spans US1 (T004 — navigation/add), US4 (T018 — search_prefix), US5 (T025 — file I/O)
- test_tail_suggester.py spans US2 (T009 — command names), US3 (T015 — arguments), US4 (T019 — history fallback)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `theme` command is handled directly in tail_textual.py _handle_command (not in cli_tail.py TAIL_MODE_COMMANDS), but still needs a completion spec entry
- `unset` is not a tail mode command (REPL-only), so no completion spec needed
