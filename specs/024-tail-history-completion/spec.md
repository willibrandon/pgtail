# Feature Specification: Tail Mode Command History & Autocomplete

**Feature Branch**: `024-tail-history-completion`
**Created**: 2026-03-01
**Revised**: 2026-03-01 (post-review, round 3)
**Status**: Draft
**Input**: User description: "Add command history with Up/Down arrow recall and context-aware ghost text autocomplete to the tail mode command input (TailInput)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Command History Recall (Priority: P1)

A user is tailing PostgreSQL logs and has entered several filter commands (`level error+`, `since 5m`, `filter /deadlock/`). They want to re-apply a previous filter without retyping it. They press the Up arrow key to cycle through previously entered commands, find the one they want, and press Enter to re-execute it.

**Why this priority**: Command history is the most frequently needed input enhancement. Users currently must retype every command from memory, which is slow and error-prone. History recall eliminates this friction for the most common interaction pattern: adjusting filters during active log tailing.

**Independent Test**: Can be fully tested by entering commands, pressing Up/Down arrows, and verifying the input field cycles through previous entries. Delivers immediate productivity improvement even without autocomplete.

**Acceptance Scenarios**:

1. **Given** a user has entered commands `level error+`, `since 5m`, and `filter /deadlock/` in tail mode, **When** they press the Up arrow key three times, **Then** the input field shows `filter /deadlock/` (most recent) on the first press, `since 5m` on the second press, and `level error+` (oldest) on the third press.
2. **Given** a user has navigated backward in history to `since 5m`, **When** they press the Down arrow key, **Then** the input field shows the next newer command (`filter /deadlock/`).
3. **Given** a user was typing `lev` before navigating history, **When** they press Down past the newest history entry, **Then** the input field restores their original partial text `lev`.
4. **Given** a user is navigating history and starts typing a new character, **When** they type any character, **Then** history navigation resets and subsequent Up/Down starts fresh from the end of history.
5. **Given** a user presses Up at the oldest history entry, **When** they press Up again, **Then** nothing happens (the input stays at the oldest entry).
6. **Given** a user presses Down with no active history navigation, **When** they press Down, **Then** nothing happens (no-op).
7. **Given** the user enters the same command twice consecutively (`level error+` then `level error+`), **When** they press Up, **Then** only one entry appears (consecutive duplicates are deduplicated).

---

### User Story 2 - Ghost Text Autocomplete for Commands (Priority: P1)

A user is in tail mode and wants to enter a command but doesn't remember the exact name. As they type the first few letters, a dimmed ghost text suggestion appears inline showing the completed command name. They press the Right arrow key to accept the suggestion.

**Why this priority**: Equal to history because autocomplete directly addresses command discoverability. New users and infrequent users cannot remember all commands. Ghost text suggestions eliminate the need to consult help before every command.

**Independent Test**: Can be fully tested by typing partial command names and verifying ghost text suggestions appear with correct completions. Delivers immediate discoverability improvement even without history.

**Acceptance Scenarios**:

1. **Given** the user types `le` in the input, **When** the input value changes, **Then** ghost text `vel` appears after the cursor (suggesting `level`).
2. **Given** the user types `hi`, **When** the input value changes, **Then** ghost text `ghlight` appears (suggesting `highlight`).
3. **Given** the user types `le` and sees the ghost text `vel`, **When** they press the Right arrow key at the end of the input, **Then** the input becomes `level` (suggestion accepted).
4. **Given** the user types `s`, **When** the input value changes, **Then** the first alphabetical match is suggested (`set` before `since` before `slow` before `stop`).
5. **Given** the user types `p` (a complete command alias for `pause`), **When** the input value changes, **Then** no ghost text appears because `p` exactly matches a command name and the suffix is empty.
6. **Given** the user types `xyz` (no matching command), **When** the input value changes, **Then** no ghost text appears.
7. **Given** the user types `LEVEL` (uppercase), **When** the input value changes, **Then** command matching is case-insensitive and ghost text still suggests `level` completions.
8. **Given** the user types `pa`, **When** the input value changes, **Then** ghost text `use` appears (suggesting `pause`), because `pa` prefix-matches `pause` but does not exactly match any command name — even though the alias `p` is a separate command entry.

---

### User Story 3 - Context-Aware Argument Autocomplete (Priority: P2)

After entering a command name and a space, the user gets ghost text suggestions for valid arguments specific to that command. For example, after `level ` they see log level names, after `highlight ` they see subcommand names, and after `errors --code ` they see SQLSTATE codes.

**Why this priority**: Argument completion builds on command completion and provides deeper assistance. It reduces errors from typos in level names, flag names, and setting keys, and helps users discover command options they didn't know existed.

**Independent Test**: Can be fully tested by typing command names followed by a space and verifying appropriate argument suggestions appear for each command.

**Acceptance Scenarios**:

1. **Given** the user types `level `, **When** the space triggers suggestion, **Then** ghost text suggests the first alphabetical level value from the completion data.
2. **Given** the user types `level e`, **When** the partial argument triggers suggestion, **Then** ghost text suggests the remaining characters of the first case-insensitive prefix match among level values (e.g., if the canonical form is `error`, ghost text is `rror`).
3. **Given** the user types `highlight `, **When** the space triggers suggestion, **Then** ghost text suggests the first alphabetical subcommand (e.g., `add`).
4. **Given** the user types `highlight enable `, **When** the space triggers suggestion, **Then** ghost text suggests a highlighter name from the current configuration (dynamic source).
5. **Given** the user types `errors --code `, **When** the space triggers suggestion, **Then** ghost text suggests a SQLSTATE code (e.g., `23503`).
6. **Given** the user types `errors --since 5m --code `, **When** the last unconsumed flag is `--code` (because `--since` is consumed by `5m`), **Then** ghost text suggests SQLSTATE codes (not time values).
7. **Given** the user types `set `, **When** the space triggers suggestion, **Then** ghost text suggests setting keys from the configuration schema (dynamic source).
8. **Given** the user types `between 5m `, **When** the second positional argument is expected, **Then** ghost text suggests end-time completions.
9. **Given** the user types `pause `, **When** a no-argument command has a trailing space, **Then** no ghost text appears (command takes no arguments).
10. **Given** the user types `filter /`, **When** the partial argument starts with `/` (regex pattern), **Then** no ghost text appears (free-form input, not completable).
11. **Given** the user types `help `, **When** the space triggers suggestion, **Then** ghost text suggests the first alphabetical entry from the help topic list (which includes `keys` and all COMMAND_HELP entries).
12. **Given** the user types `between `, **When** the first positional argument is expected, **Then** ghost text suggests start-time completions (same values as `since`).
13. **Given** the user types `export `, **When** the first argument is a free-form file path, **Then** no ghost text appears (free-form position per FR-022).
14. **Given** the user types `between 5m 15:00 `, **When** all positional argument slots are filled, **Then** no ghost text appears (no further arguments expected).
15. **Given** the user types `errors c`, **When** the partial `c` is matched against the positional values for `errors`, **Then** ghost text suggests `lear` (completing to `clear`), because the partial does not start with `--` so the positional sequence is checked before flags.
16. **Given** the user types `errors --trend --code `, **When** the boolean flag `--trend` (takes no value) precedes the value-taking flag `--code`, **Then** ghost text suggests SQLSTATE codes, because `--trend` is boolean and never consumes the following token, leaving `--code` as the last unconsumed value-taking flag.
17. **Given** the user types `export /tmp/out.csv --`, **When** the free-form first positional is filled and the partial starts with `--`, **Then** ghost text suggests the first alphabetical flag name for `export` (e.g., `format` completing to `--format`).
18. **Given** the user types `connections --db=`, **When** the partial token is `--db=` (a flag with `=` and empty value), **Then** no structural suggestion appears for the value portion (database names are not a defined dynamic source), and the system falls back to history prefix matching per FR-016.

---

### User Story 4 - History-Aware Suggestions (Priority: P2)

When no structural completion matches the current input (or the structural match yields an empty suffix), the autocomplete falls back to suggesting previously entered command lines from history. This allows users to recall exact previous commands including arguments and modifiers.

**Why this priority**: History-aware suggestions bridge the gap between structural completions (which only know valid values) and user-specific patterns (like `level error+` with the `+` suffix, which is free-form). This creates a complete suggestion experience.

**Independent Test**: Can be fully tested by entering commands, then typing partial prefixes and verifying history-based suggestions appear when structural completions don't match or produce no additional text.

**Acceptance Scenarios**:

1. **Given** the user previously entered `level error+`, **When** they type `level error` (structural completion matches `error` exactly but yields an empty suffix), **Then** ghost text suggests `+` from the history entry `level error+`.
2. **Given** the user previously entered `since 5m` and `since 30m`, **When** they type `since 5`, **Then** the structural suggestion for `5m` takes priority over history.
3. **Given** the user previously entered `filter /deadlock/i`, **When** they type `filter /dead`, **Then** ghost text suggests `lock/i` from history (structural completions don't cover regex patterns).
4. **Given** no history entries match the current input and no structural completions match, **When** the user types novel text, **Then** no ghost text appears.

---

### User Story 5 - Persistent History Across Sessions (Priority: P3)

When a user exits tail mode and starts a new pgtail session later, their previous tail mode command history is available via Up/Down arrow navigation. History is stored in a platform-specific file separate from the REPL history.

**Why this priority**: Persistence is a quality-of-life enhancement that builds on the in-memory history (P1). Without persistence, users lose their history when they restart pgtail. With persistence, power users who run pgtail daily benefit from accumulated command patterns.

**Independent Test**: Can be fully tested by entering commands, exiting pgtail, restarting, entering tail mode, and pressing Up to verify previous commands are available.

**Acceptance Scenarios**:

1. **Given** a user enters `level error+` and `since 5m` in tail mode, then exits pgtail, **When** they restart pgtail and enter tail mode, **Then** pressing Up shows `since 5m` followed by `level error+`.
2. **Given** the history file does not exist (first run), **When** the user enters tail mode, **Then** history starts empty with no errors.
3. **Given** the history file contains 1500 entries, **When** the user enters tail mode, **Then** only the most recent 500 entries are loaded and the file is compacted.
4. **Given** the history file contains malformed data (binary content, non-UTF-8 bytes, very long lines), **When** the user enters tail mode, **Then** malformed entries are silently skipped and valid entries are loaded.
5. **Given** multiple pgtail instances are running simultaneously, **When** both write to the history file, **Then** entries are appended without corrupting the file format (one entry per line, valid UTF-8); however, compaction may lose entries from concurrent appenders (accepted trade-off per Edge Cases).

---

### Edge Cases *(informative — these supplement the normative FRs but do not override them)*

- **Empty input**: Up arrow with empty history does nothing. Submitting empty input does not add to history. Ghost text returns nothing for empty/whitespace-only input.
- **Whitespace-only input**: Treated identically to empty input for both history storage and suggestions.
- **Single history entry**: Up returns the entry, second Up does nothing. Down restores saved input, second Down does nothing.
- **Very long commands**: Stored verbatim with no truncation on save. However, lines exceeding 4096 bytes in the history file are skipped on load (FR-009 safety measure), meaning extraordinarily long commands (>4KB) will not survive session restarts.
- **Special characters**: Commands with quotes, backslashes, and regex patterns (`/error\d+/`) are stored verbatim in history.
- **Rapid key presses**: Each Up/Down press synchronously updates the input; no async race conditions possible.
- **Focus transitions**: History navigation only works when the input has focus. Escape clears input and resets navigation. Typing after navigating resets navigation.
- **Ghost suggestion acceptance**: Accepting a ghost text suggestion via Right arrow changes the input value, which resets history navigation (same as typing per FR-004 and FR-026).
- **Concurrent sessions**: Multiple instances may write to the same history file. Append writes minimize interleaving risk but don't guarantee atomicity. Compaction can lose concurrent entries (accepted trade-off for a convenience feature). See FR-006.
- **NO_COLOR**: History and completion are unaffected. Ghost text styling uses built-in component classes that respect the app's color mode.
- **Alias commands**: Single-letter aliases (`p`, `f`, `q`) are included as separate entries in the command list. Typing `p` matches the command `p` exactly (empty suffix), so no ghost text appears; `pause` is not suggested as a prefix completion.
- **Free-form arguments**: Arguments that accept arbitrary user input (regex patterns starting with `/`, file paths for `export`) receive no structural suggestions. History-based suggestions still apply.
- **Removed commands in history**: History entries for commands removed in a future version remain in the history file and can be recalled via Up/Down, but will produce an error when submitted. This is accepted behavior.
- **Double spaces**: Multiple consecutive spaces in input are treated as a single separator for argument parsing. The partial word is everything after the last space character.
- **Equals-suffix flags**: Flags using `=` to attach values (e.g., `--db=mydb`) are self-contained single tokens under whitespace splitting. The completion engine splits on the first `=` to extract the flag name and partial value.

## Requirements *(mandatory)*

### Functional Requirements

**Command History:**

- **FR-001**: System MUST record each non-empty, non-whitespace command entered via the tail mode input, deduplicate consecutive repeats, and store them in an ordered list (newest at end).
- **FR-002**: Users MUST be able to navigate backward through command history by pressing the Up arrow key, with each press showing the next older entry.
- **FR-003**: Users MUST be able to navigate forward through command history by pressing the Down arrow key, with each press showing the next newer entry. On the first backward navigation from at-rest state, the current input text MUST be saved. Pressing Down past the newest entry MUST restore the saved text and return to at-rest state.
- **FR-004**: System MUST reset history navigation to at-rest state when the user types new characters, deletes characters, or submits a command, so that subsequent Up/Down starts fresh from the end of history.
- **FR-005**: System MUST persist command history to a platform-specific UTF-8 encoded file (macOS: `~/Library/Application Support/pgtail/tail_history`, Linux: `~/.local/share/pgtail/tail_history`, Windows: `%APPDATA%/pgtail/tail_history`), with one entry per line.
- **FR-006**: System MUST load persisted history on tail mode startup and compact the file when it exceeds twice the maximum entry count. Compaction is not atomic with respect to concurrent appenders (see Edge Cases).
- **FR-007**: System MUST limit history to 500 entries in memory, dropping oldest entries when the limit is exceeded.
- **FR-008**: System MUST silently handle file I/O errors during history load, save, and compact operations without crashing or disrupting the user experience.
- **FR-009**: System MUST skip lines exceeding 4096 bytes and gracefully handle non-UTF-8 content when loading history files. This is a safety measure against corrupted or externally-modified files; normal user commands are not expected to approach this limit.

**Ghost Text Autocomplete:**

- **FR-010**: System MUST provide ghost text (dimmed inline text after cursor) suggestions as the user types, updating on every input value change.
- **FR-011**: System MUST suggest command names when the user is typing the first word, using case-insensitive prefix matching against all tail mode commands including aliases (sorted alphabetically, first match shown). Command aliases (e.g., `p` for `pause`, `f` for `follow`, `q` for `stop`) are included as separate entries in the command list.
- **FR-012**: System MUST suggest context-aware arguments after a command name is entered (detected by trailing space), including: log level values for `level`, subcommands for `highlight`, time presets for `since`/`until`/`between`, threshold presets for `slow`, flags for `errors`/`connections`/`export`, setting keys for `set`, and help topics for `help`.
- **FR-013**: System MUST support multi-level completion: subcommand arguments (e.g., `highlight enable <name>`), flag-value arguments (e.g., `errors --code <sqlstate>`), and positional arguments (e.g., `between <start> <end>`).
- **FR-014**: System MUST use last-flag-before-cursor scanning for flag-value completions. The completion data distinguishes boolean flags (take no value, e.g., `--trend`, `--live`) from value-taking flags (e.g., `--code`, `--since`). A value-taking flag is "consumed" if it is immediately followed by a non-flag token (its value argument). Boolean flags are never considered to consume the following token. The last unconsumed value-taking flag determines the completion context. For example, in `errors --since 5m --code `, `--since` is consumed by `5m` and `--code` is unconsumed, so SQLSTATE completions are suggested. In `errors --trend --code `, `--trend` is boolean (never consumes), so `--code` is the last unconsumed value-taking flag. Tokens matching the `--flag=value` pattern (see FR-021) are always treated as consumed regardless of flag type.
- **FR-015**: System MUST resolve dynamic completion sources at suggestion time: highlighter names from current configuration, setting keys from config schema, and help topics from the COMMAND_HELP dictionary merged with static entries (e.g., `keys`).
- **FR-016**: System MUST fall back to history prefix matching when structural completion produces no non-empty suggestion text (either no match found, or the matched value equals the input token, yielding an empty suffix).
- **FR-017**: System MUST return the entire input line (not just the completed word) from the suggestion function, as required by the Textual Suggester API.
- **FR-018**: System MUST use case-insensitive matching for command names and static argument completions. History prefix search and dynamic sources (highlighter names, setting keys) MUST use case-sensitive matching. Rationale: history entries may contain case-sensitive content (regex patterns like `/Deadlock/`, usernames like `Admin`) where case-insensitive matching would silently corrupt the user's intent by suggesting a differently-cased variant. Note: this means case-sensitive matching applies to the entire history line including the command prefix — a history entry `Level error+` will not match a search for `level error`. This is the intended trade-off; protecting case-sensitive argument content is prioritized over cross-case command prefix matching, and users typically type commands in consistent casing.
- **FR-019**: System MUST NOT suggest arguments for commands that take no arguments (`pause`, `p`, `follow`, `f`, `stop`, `exit`, `q`).
- **FR-020**: System MUST NOT cache suggestions, because history changes on every command submission and dynamic sources change during a session.
- **FR-021**: System MUST parse input text for suggestion by splitting on whitespace using `str.split()` semantics (any whitespace character, consecutive runs collapsed into a single separator), where the last token is the partial word being typed (empty string if the input ends with whitespace) and all preceding tokens are completed parts. The first completed part identifies the command; subsequent parts identify arguments, subcommands, or flags. Tokens matching the pattern `--flag=value` (containing `=` after a `--` prefix) are split on the first `=` to extract the flag name and attached value; such tokens are treated as a consumed flag-value pair during scanning (FR-014). When the partial token itself matches `--flag=` (flag with `=` and partial or empty value), the engine suggests values for that flag using the text after `=` as the prefix.
- **FR-022**: System MUST NOT suggest structural completions for free-form argument positions: regex patterns (arguments starting with `/`), file paths (first argument of `export`), and other arguments that accept arbitrary user input. History-based suggestions (FR-016) still apply to these positions.

**Integration:**

- **FR-023**: System MUST accept optional `suggester` and `history` parameters in the TailInput constructor, maintaining backward compatibility when these are not provided.
- **FR-024**: System MUST wire history and suggester in the TailApp coordinator: create both in initialization, pass to TailInput in composition, add commands to history on submission, load/compact history on mount.
- **FR-025**: System MUST distinguish between value changes from history navigation and value changes from user typing. The implementation MUST use a synchronous guard (a boolean flag set before programmatic value changes and cleared after) so that the value-change handler skips navigation reset when the guard is set. The guard MUST be set around any programmatic assignment to the input widget's value during navigation state transitions (navigate_back setting the input to a history entry, navigate_forward setting the input to a history entry or restored saved input). The guard is NOT set during reset operations that only clear internal state (cursor, saved input) without changing the input value.
- **FR-026**: System MUST treat acceptance of a ghost text suggestion (via Right arrow) as a value change that resets history navigation, identical to the typing behavior defined in FR-004.

### Key Entities

- **TailCommandHistory**: An ordered collection of previously entered commands with a three-state cursor model:
  - **At-rest** (`cursor == len(entries)`, no saved input): Not navigating. Up triggers backward navigation. Down is a no-op.
  - **At-history-entry** (`0 <= cursor < len(entries)`, saved input preserved): Showing a history entry. Up moves to the next older entry (clamped at index 0). Down moves to the next newer entry.
  - **Past-newest** (cursor returns to `len(entries)`, saved input is restored to the input field — this restoration is a programmatic value change requiring the synchronous guard per FR-025 — then the saved input variable is cleared): Transitional state when the user presses Down past the newest entry. Immediately transitions to at-rest after restoration.

  On first backward navigation from at-rest, the current input text is saved for later restoration. Typing, deletion, command submission, or ghost suggestion acceptance resets to at-rest, clearing cursor position and saved input.

  Manages in-memory entries (capped at 500), file persistence (load, save, compact), and prefix search for suggestion integration. Exposes a `search_prefix(prefix: str) -> str | None` method that returns the most recent history entry matching the given prefix (case-sensitive per FR-018, to preserve case-sensitive content like regex patterns), or `None` if no match is found.

- **TailCommandSuggester**: A custom Textual `Suggester` subclass that combines structural completions with history-based fallback. Given the current input value, it:
  1. Parses input into command, completed parts, and partial word (per FR-021)
  2. Resolves structural completions from the completion data
  3. Falls back to `TailCommandHistory.search_prefix()` when structural produces no non-empty suggestion (per FR-016)
  4. Returns the full input line with the suggested completion appended (per FR-017), or `None` for no suggestion

- **Completion Data**: A per-command mapping defining valid completions. Each command entry specifies one or more of:
  - **Static values**: A list of valid string arguments (e.g., level names, subcommand names), matched by case-insensitive prefix
  - **Dynamic source reference**: A callable returning a list of strings at suggestion time (e.g., highlighter names from current config), matched by case-sensitive prefix
  - **Subcommand tree**: A nested mapping from subcommand name to its own completion spec (e.g., `highlight` -> `enable` -> dynamic highlighter names)
  - **Flag-value map**: A mapping from flag names to either a completion spec (value-taking flag, e.g., `--code` -> SQLSTATE codes) or `None` (boolean flag, e.g., `--trend`). Boolean flags take no value argument and never consume the following token during last-flag scanning (FR-014). Flags may be specified by the user as either `--flag value` (space-separated) or `--flag=value` (equals-attached); the engine handles both forms (FR-021).
  - **Positional sequence**: An ordered list of completion specs for sequential positional arguments (e.g., `between` -> [time values, time values]). Individual slots may be marked as **free-form** to indicate the argument accepts arbitrary input and should not receive structural suggestions (FR-022). After all positional slots are filled, only flag suggestions are offered.
  - **No-argument marker**: An explicit indicator that the command takes no arguments (FR-019)

  **Composition rules**: A command's spec may combine multiple structural types (e.g., `errors` has both a positional value `clear` and flags `--code`, `--trend`). The suggestion engine resolves them in this order:
  1. If the partial word starts with `--`, match against the command's flag names only
  2. Otherwise, check the positional sequence for the current argument index
  3. If the current positional slot is free-form, skip structural suggestions
  4. After all positional slots are exhausted, suggest flag names (for a `--` partial) or offer no structural suggestion (for a non-`--` partial)
  5. When a positional slot and subcommand tree both apply at the same argument index (e.g., `errors` where `clear` could be positional or a subcommand), the completion data MUST model this as a positional slot containing `clear` as a static value — not as a separate subcommand tree — to avoid ambiguity in the resolution order

  Note: step 1 ensures `errors --` suggests flag names, while step 2 ensures `errors c` suggests `lear` (from the positional value `clear`). The `--` prefix is the explicit signal that the user intends a flag.

  Commands absent from the mapping receive only history-based suggestions for their arguments.

### Non-Goals

The following are explicitly out of scope for this feature:

- **Dropdown completion menus**: All suggestions use inline ghost text only; no popup or overlay UI.
- **Fuzzy matching**: Completion uses strict prefix matching only; no subsequence or edit-distance matching.
- **Shared history with REPL**: Tail mode maintains its own history file, separate from the prompt_toolkit REPL history.
- **Multi-line input**: The TailInput remains a single-line widget; no multi-line command entry.
- **Shell-style history expansion**: No `!` or `!!` expansion syntax; only Up/Down arrow navigation.
- **Tab completion**: All completion is via ghost text and Right arrow acceptance; Tab retains its focus-toggle behavior.

### Traceability

| User Story | Implementing Requirements |
|---|---|
| Story 1 — Command History Recall | FR-001, FR-002, FR-003, FR-004, FR-007, FR-025, FR-026 |
| Story 2 — Ghost Text Command Autocomplete | FR-010, FR-011, FR-017, FR-018, FR-019, FR-020, FR-021 |
| Story 3 — Context-Aware Argument Autocomplete | FR-012, FR-013, FR-014, FR-015, FR-021, FR-022 |
| Story 4 — History-Aware Suggestions | FR-016 |
| Story 5 — Persistent History Across Sessions | FR-005, FR-006, FR-007, FR-008, FR-009 |
| All Stories — Integration | FR-023, FR-024 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can recall their most recent command in 1 key press (Up then Enter) and the Nth most recent command in N Up presses, for any N up to 500.
- **SC-002**: Suggestion computation (the `get_suggestion` call) completes in under 1 millisecond, ensuring ghost text appears with no perceptible delay after accounting for framework overhead.
- **SC-003**: All tail mode commands (including aliases) are discoverable via prefix typing, with correct suggestions appearing for every valid command prefix.
- **SC-004**: All command arguments defined in the completion data produce correct ghost text suggestions, covering level values, highlight subcommands, time presets, threshold presets, SQLSTATE codes, setting keys, and help topics.
- **SC-005**: History persists across sessions: commands entered in one session are available via Up arrow in the next session, with no data loss under normal single-instance usage.
- **SC-006**: The input aesthetic remains unchanged: single-line minimal-chrome input with no dropdown menus, no visible chrome additions, and ghost text matching the existing Textual input styling.
- **SC-007**: All existing tail mode keybindings continue to work identically: `q` (quit when empty), Escape (clear and blur), Tab (toggle focus), Enter (submit), `/` (focus from log).
- **SC-008**: All acceptance scenarios have corresponding automated tests. Branch coverage exceeds 95% for history navigation state transitions (at-rest, at-history-entry, past-newest), the structural-to-history fallback path, and the completion data composition rules (flag vs positional vs subcommand resolution). Overall branch coverage for all new code in this feature exceeds 90%.
