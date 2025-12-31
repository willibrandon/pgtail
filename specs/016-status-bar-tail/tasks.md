# Tasks: Status Bar Tail Mode

**Input**: Design documents from `/specs/016-status-bar-tail/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in spec.md. Tests can be added later if needed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure for tail mode components

- [ ] T001 Create empty `pgtail_py/tail_buffer.py` with module docstring
- [ ] T002 [P] Create empty `pgtail_py/tail_status.py` with module docstring
- [ ] T003 [P] Create empty `pgtail_py/tail_layout.py` with module docstring
- [ ] T004 [P] Create empty `pgtail_py/tail_app.py` with module docstring
- [ ] T005 [P] Create empty `pgtail_py/cli_tail.py` with module docstring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement `FormattedLogEntry` dataclass in `pgtail_py/tail_buffer.py` per contracts/tail_buffer.py
- [ ] T007 Implement `TailBuffer` class in `pgtail_py/tail_buffer.py` with:
  - deque with maxlen=10000
  - append(), clear(), total_entries property
  - Basic follow_mode property (always True for now)
- [ ] T008 [P] Implement `TailStatus` class in `pgtail_py/tail_status.py` with:
  - error_count, warning_count, total_lines properties
  - update_from_entry(), set_total_lines(), reset_counts() methods
  - format() returning basic FormattedText
- [ ] T009 [P] Implement `TailLayout` builder in `pgtail_py/tail_layout.py` with:
  - HSplit with 3 sections (log, status, input)
  - LAYOUT_CONFIG and LAYOUT_STYLES constants
  - Basic key bindings structure (Enter for command submit)
- [ ] T010 Implement core `TailApp` coordinator in `pgtail_py/tail_app.py` with:
  - start() method that blocks until exit
  - Basic Application setup with layout
  - Integration with LogTailer for background streaming
- [ ] T011 Add `tail` command dispatch to `pgtail_py/cli.py` to launch TailApp
- [ ] T012 Implement background entry consumer in `TailApp` using asyncio with thread-safe invalidate()
- [ ] T013 Validate thread-safe queue handoff between LogTailer thread and UI event loop
- [ ] T014 Add Ctrl+L key binding for manual screen redraw in `pgtail_py/tail_layout.py`

**Checkpoint**: Foundation ready - basic tail mode launches and displays streaming logs

---

## Phase 3: User Story 1 - Continuous Log Streaming with Command Input (Priority: P1)

**Goal**: Logs stream continuously while user types commands in the input line

**Independent Test**: Start tail mode, type filter commands while logs stream, verify both continue simultaneously

### Implementation for User Story 1

- [ ] T015 [US1] Add BufferControl for command input line in `pgtail_py/tail_layout.py`
- [ ] T016 [US1] Implement command parsing in `pgtail_py/cli_tail.py` for tail mode commands
- [ ] T017 [US1] Wire command submission (Enter key) to TailApp._on_command in `pgtail_py/tail_app.py`
- [ ] T018 [US1] Implement `level` command handler in `pgtail_py/cli_tail.py` (reuses existing filter.py)
- [ ] T019 [US1] Add filter predicate to TailBuffer and wire level filter updates
- [ ] T020 [US1] Implement refilter() in TailBuffer to re-evaluate existing entries when filter changes
- [ ] T021 [US1] Add tab completion for tail mode commands using existing PgtailCompleter

**Checkpoint**: User can type `level error` while logs stream, filter applies to both existing and new entries

---

## Phase 4: User Story 2 - Real-time Status Bar Updates (Priority: P1)

**Goal**: Status bar displays live statistics and active filter state

**Independent Test**: Tail logs, trigger errors in PostgreSQL, observe status bar updates in real-time

### Implementation for User Story 2

- [ ] T022 [US2] Enhance TailStatus.format() to show mode, counts, and filters per status bar format
- [ ] T023 [US2] Add set_level_filter(), set_regex_filter(), set_time_filter(), set_slow_threshold() to TailStatus
- [ ] T024 [US2] Wire TailStatus updates to filter command execution in TailApp
- [ ] T025 [US2] Add set_instance_info() and display PG version/port in status bar
- [ ] T026 [US2] Style status bar sections using LAYOUT_STYLES classes in `pgtail_py/tail_layout.py`
- [ ] T027 [US2] Add status bar invalidation on new entries (<100ms latency requirement)

**Checkpoint**: Status bar shows `FOLLOW | E:N W:N | N lines | levels:... | PG17:5432`

---

## Phase 5: User Story 3 - Scrollback Navigation (Priority: P2)

**Goal**: User can scroll through 10,000-line buffer and resume following live logs

**Independent Test**: Generate enough logs to fill buffer, scroll back, examine history, press End to resume

### Implementation for User Story 3

- [ ] T028 [US3] Implement scroll_offset and PAUSED mode tracking in TailBuffer
- [ ] T029 [US3] Implement scroll_up(lines), scroll_down(lines), scroll_to_top() in TailBuffer
- [ ] T030 [US3] Implement resume_follow() to jump to end and enter FOLLOW mode
- [ ] T031 [US3] Add new_since_pause counter and increment on new entries when paused
- [ ] T032 [US3] Update TailStatus.set_follow_mode() to display PAUSED +N new
- [ ] T033 [US3] Add keyboard handlers for Up/Down/PageUp/PageDown/Home/End in `pgtail_py/tail_layout.py`
- [ ] T034 [US3] Implement get_visible_lines(height) to return filtered entries based on scroll position
- [ ] T035 [US3] Handle scroll position adjustment when oldest entries evicted (FR-008a)

**Checkpoint**: User can scroll with keyboard, status shows PAUSED +N, End resumes following

---

## Phase 6: User Story 4 - Inline Command Output (Priority: P2)

**Goal**: Command output displays inline in log area with visual separators

**Independent Test**: Run `errors` during tailing, verify output appears inline with separators

### Implementation for User Story 4

- [ ] T036 [US4] Implement insert_command_output() in TailBuffer to add separator + output + separator
- [ ] T037 [US4] Add SEPARATOR_STYLE constant in `pgtail_py/tail_layout.py` for dotted line separators
- [ ] T038 [US4] Implement `errors` command handler in `pgtail_py/cli_tail.py` using existing ErrorStats
- [ ] T039 [US4] Implement `connections` command handler in `pgtail_py/cli_tail.py` using existing ConnectionStats
- [ ] T040 [US4] Ensure command output entries have matches_filter=True (always shown)

**Checkpoint**: Running `errors` or `connections` shows output inline with separators

---

## Phase 7: User Story 5 - Quick Filter Commands (Priority: P2)

**Goal**: Short filter commands apply immediately without interrupting stream

**Independent Test**: Run each filter command and verify immediate application with status bar update

### Implementation for User Story 5

- [ ] T041 [US5] Implement `filter /pattern/` command handler in `pgtail_py/cli_tail.py` (regex filter)
- [ ] T042 [US5] Implement `since <time>` command handler in `pgtail_py/cli_tail.py` (time filter)
- [ ] T043 [US5] Implement `until <time>` command handler in `pgtail_py/cli_tail.py`
- [ ] T044 [US5] Implement `between <start> <end>` command handler in `pgtail_py/cli_tail.py`
- [ ] T045 [US5] Implement `slow <ms>` command handler in `pgtail_py/cli_tail.py` (slow query threshold)
- [ ] T046 [US5] Implement `clear` command handler to remove all filters
- [ ] T047 [US5] Add update_filters() to TailBuffer that accepts list of filter predicates and triggers refilter()

**Checkpoint**: All filter commands work: level, filter, since, until, between, slow, clear

---

## Phase 8: User Story 6 - Mouse Scroll Navigation (Priority: P3)

**Goal**: Mouse scroll wheel navigates through log buffer

**Independent Test**: Use scroll wheel to navigate buffer, verify smooth scrolling and mode transitions

### Implementation for User Story 6

- [ ] T048 [US6] Enable mouse_support=True on Application in `pgtail_py/tail_app.py`
- [ ] T049 [US6] Implement mouse handler for SCROLL_UP/SCROLL_DOWN events in log window
- [ ] T050 [US6] Wire mouse scroll events to TailBuffer.scroll_up/scroll_down (3 lines per tick)

**Checkpoint**: Mouse wheel scrolls log area, enters PAUSED mode on scroll up

---

## Phase 9: User Story 7 - Exit to REPL (Priority: P3)

**Goal**: User can exit tail mode and return to pgtail REPL

**Independent Test**: Enter tail mode, use each exit method, verify return to REPL

### Implementation for User Story 7

- [ ] T051 [US7] Implement `stop`, `exit`, `q` command handlers that call TailApp.stop()
- [ ] T052 [US7] Add Ctrl+C key binding that triggers TailApp.stop()
- [ ] T053 [US7] Implement TailApp.stop() cleanup: set running=False, stop tailer, exit Application
- [ ] T054 [US7] Ensure clean return to REPL without orphan threads (SC-011)

**Checkpoint**: All exit methods work: stop, exit, q, Ctrl+C

---

## Phase 10: User Story 8 - Terminal Resize Handling (Priority: P3)

**Goal**: Layout reflows on terminal resize, preserving scroll context

**Independent Test**: Resize terminal during tailing, verify layout adapts and scroll position preserved

### Implementation for User Story 8

- [ ] T055 [US8] Verify prompt_toolkit automatic resize handling works with HSplit layout
- [ ] T056 [US8] Add minimum terminal size check (40x10) in TailLayout
- [ ] T057 [US8] Display warning message when terminal too small using class:warning style
- [ ] T058 [US8] Ensure scroll position remains valid after resize (clamp if needed)

**Checkpoint**: Terminal resize reflows layout, small terminal shows warning

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T059 [P] Validate all keyboard shortcuts work per TAIL_MODE_KEYS in contracts/tail_app.py
- [ ] T060 [P] Add `pause` command to explicitly enter PAUSED mode
- [ ] T061 [P] Add `follow` command to explicitly resume FOLLOW mode
- [ ] T062 Ensure UI latency <50ms under 1000 lines/sec log volume (SC-006)
- [ ] T063 Verify memory usage <50MB for 10,000 line buffer (SC-007)
- [ ] T064 Validate tab completion appears within 100ms (SC-008)
- [ ] T065 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
  - US1 and US2 are both P1, can be done in priority order
  - US3, US4, US5 are P2, can proceed after P1 stories
  - US6, US7, US8 are P3, can proceed after P2 stories
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Streaming + Commands)**: Requires Foundational - Core value proposition
- **US2 (Status Bar)**: Requires Foundational, benefits from US1 filter commands
- **US3 (Scrollback)**: Requires Foundational, independent of US1/US2
- **US4 (Inline Output)**: Requires Foundational, uses commands from US1
- **US5 (Filter Commands)**: Requires Foundational, extends US1 command handling
- **US6 (Mouse Scroll)**: Requires US3 scrollback infrastructure
- **US7 (Exit)**: Requires Foundational, simple addition
- **US8 (Resize)**: Requires Foundational, mostly automatic

### Within Each User Story

- Core functionality before edge cases
- Integration with existing modules before new features
- Commit after each task or logical group

### Parallel Opportunities

- All Setup tasks (T002-T005) can run in parallel
- Foundational T008-T009 can run in parallel
- Once Foundational phase completes, US1 and US2 can begin
- Polish tasks T059-T061 can run in parallel

---

## Parallel Example: Setup Phase

```bash
# Launch all module creation tasks together:
Task: "Create empty pgtail_py/tail_status.py with module docstring"
Task: "Create empty pgtail_py/tail_layout.py with module docstring"
Task: "Create empty pgtail_py/tail_app.py with module docstring"
Task: "Create empty pgtail_py/cli_tail.py with module docstring"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (streaming + commands)
4. Complete Phase 4: User Story 2 (status bar)
5. **STOP and VALIDATE**: Test MVP - logs stream while typing commands, status bar updates
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational -> Foundation ready
2. Add US1 + US2 -> Test independently -> MVP ready!
3. Add US3 (scrollback) -> Navigation complete
4. Add US4 + US5 (inline output + filters) -> Full command support
5. Add US6-US8 (polish) -> Production ready
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Existing modules reused: tailer.py, filter.py, regex_filter.py, time_filter.py, slow_query.py, error_stats.py, connection_stats.py, display.py, colors.py
- No new dependencies required (uses existing prompt_toolkit >=3.0.0)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
