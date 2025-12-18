# Tasks: Full Screen TUI Mode

**Input**: Design documents from `/specs/012-fullscreen-tui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per Technical Context specifying pytest unit tests for buffer, search, and keybinding logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project structure**: `pgtail_py/` package at repository root
- **Tests**: `tests/unit/fullscreen/`, `tests/integration/`
- **New module**: `pgtail_py/fullscreen/` subpackage

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create fullscreen subpackage structure and foundational types

- [X] T001 Create fullscreen package directory at pgtail_py/fullscreen/
- [X] T002 Create pgtail_py/fullscreen/__init__.py with package exports
- [X] T003 [P] Create tests/unit/fullscreen/ directory structure
- [X] T004 [P] Create DisplayMode enum in pgtail_py/fullscreen/state.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: LogBuffer and basic state management must be complete before user stories

### Tests for Foundation

- [X] T005 [P] Unit test for LogBuffer.append() and FIFO eviction in tests/unit/fullscreen/test_buffer.py
- [X] T006 [P] Unit test for LogBuffer.get_text() and get_lines() in tests/unit/fullscreen/test_buffer.py
- [X] T007 [P] Unit test for FullscreenState mode transitions in tests/unit/fullscreen/test_state.py

### Implementation for Foundation

- [X] T008 Implement LogBuffer class with deque in pgtail_py/fullscreen/buffer.py
- [X] T009 Implement FullscreenState class in pgtail_py/fullscreen/state.py
- [X] T010 Add fullscreen_buffer and fullscreen_state fields to AppState in pgtail_py/cli.py
- [X] T011 Add get_or_create_buffer() and get_or_create_fullscreen_state() methods to AppState in pgtail_py/cli.py
- [X] T012 Extend tailer on_entry callback to feed LogBuffer in pgtail_py/cli_core.py (in tail_command)

**Checkpoint**: Foundation ready - LogBuffer accumulates entries, state management in place

---

## Phase 3: User Story 5 - Enter and Exit Fullscreen Mode (Priority: P1) 🎯 MVP

**Goal**: User can type `fullscreen` or `fs` to enter fullscreen TUI mode and press `q` to exit back to REPL

**Independent Test**: Run `tail <id>`, then `fullscreen`, verify TUI appears, press `q`, verify return to REPL

**Why first**: This is the entry/exit point - without it, no other stories can be tested

### Tests for User Story 5

- [X] T013 [P] [US5] Unit test for fullscreen_command error when no active tail in tests/unit/fullscreen/test_cli_fullscreen.py
- [X] T014 [P] [US5] Integration test for fullscreen enter/exit cycle in tests/integration/test_fullscreen.py

### Implementation for User Story 5

- [X] T015 [P] [US5] Create basic layout with TextArea and status bar in pgtail_py/fullscreen/layout.py
- [X] T016 [P] [US5] Create exit keybinding (q) in pgtail_py/fullscreen/keybindings.py
- [X] T017 [US5] Create create_fullscreen_app() function in pgtail_py/fullscreen/app.py
- [X] T018 [US5] Create run_fullscreen() function in pgtail_py/fullscreen/app.py
- [X] T019 [US5] Implement fullscreen_command handler in pgtail_py/cli_fullscreen.py
- [X] T020 [US5] Register fullscreen/fs command in pgtail_py/commands.py
- [X] T021 [US5] Wire fullscreen_command to command dispatch in pgtail_py/cli.py
- [X] T022 [US5] Add status bar showing mode and line count in pgtail_py/fullscreen/layout.py
- [X] T023 [US5] Implement live buffer updates with app.invalidate() in pgtail_py/fullscreen/app.py

**Checkpoint**: User can enter fullscreen mode, see log content, and exit with `q`

---

## Phase 4: User Story 1 - Scroll Back to Review Error (Priority: P1)

**Goal**: User can pause follow mode with Escape, scroll with j/k/arrows, and resume with f/Escape

**Independent Test**: Enter fullscreen, press Escape to pause, use j/k to scroll, press f to resume

### Tests for User Story 1

- [X] T024 [P] [US1] Unit test for toggle_follow() state transitions in tests/unit/fullscreen/test_state.py
- [X] T025 [P] [US1] Unit test for scroll keybindings in tests/unit/fullscreen/test_keybindings.py

### Implementation for User Story 1

- [X] T026 [US1] Add Escape keybinding to toggle follow/browse in pgtail_py/fullscreen/keybindings.py
- [X] T027 [US1] Add j/k keybindings for line scroll in pgtail_py/fullscreen/keybindings.py
- [X] T028 [US1] Add Up/Down arrow keybindings for line scroll in pgtail_py/fullscreen/keybindings.py
- [X] T029 [US1] Add f keybinding to enter follow mode in pgtail_py/fullscreen/keybindings.py
- [X] T030 [US1] Implement auto-scroll to bottom in follow mode in pgtail_py/fullscreen/app.py
- [X] T031 [US1] Update status bar to show FOLLOW/BROWSE mode in pgtail_py/fullscreen/layout.py
- [X] T032 [US1] Auto-pause follow mode on manual scroll in pgtail_py/fullscreen/keybindings.py

**Checkpoint**: User can browse history and resume live tailing

---

## Phase 5: User Story 2 - Search for Pattern in Logs (Priority: P1)

**Goal**: User can search with `/pattern`, navigate matches with n/N, cancel search with Escape

**Independent Test**: Press `/`, type pattern, press Enter, verify highlight, use n/N to navigate

### Tests for User Story 2

- [ ] T033 [P] [US2] Unit test for search keybindings in tests/unit/fullscreen/test_keybindings.py
- [ ] T034 [P] [US2] Unit test for search state management in tests/unit/fullscreen/test_state.py

### Implementation for User Story 2

- [ ] T035 [US2] Add SearchToolbar widget to layout in pgtail_py/fullscreen/layout.py
- [ ] T036 [US2] Connect SearchToolbar to TextArea for highlighting in pgtail_py/fullscreen/layout.py
- [ ] T037 [US2] Add / keybinding for forward search in pgtail_py/fullscreen/keybindings.py
- [ ] T038 [US2] Add ? keybinding for backward search in pgtail_py/fullscreen/keybindings.py
- [ ] T039 [US2] Add n/N keybindings for next/prev match in pgtail_py/fullscreen/keybindings.py
- [ ] T040 [US2] Add Escape handling in search context (cancel search) in pgtail_py/fullscreen/keybindings.py
- [ ] T041 [US2] Update status bar to show search status in pgtail_py/fullscreen/layout.py
- [ ] T042 [US2] Handle "Pattern not found" message display in pgtail_py/fullscreen/layout.py

**Checkpoint**: User can search logs with vim-style commands

---

## Phase 6: User Story 3 - Navigate with Keyboard Shortcuts (Priority: P2)

**Goal**: User can use Ctrl+D/U for half-page scroll, g/G to jump to top/bottom

**Independent Test**: Load buffer with many lines, test Ctrl+D/U scroll half page, g/G jump to ends

### Tests for User Story 3

- [ ] T043 [P] [US3] Unit test for page navigation keybindings in tests/unit/fullscreen/test_keybindings.py

### Implementation for User Story 3

- [ ] T044 [US3] Add Ctrl+D keybinding for half-page down in pgtail_py/fullscreen/keybindings.py
- [ ] T045 [US3] Add Ctrl+U keybinding for half-page up in pgtail_py/fullscreen/keybindings.py
- [ ] T046 [US3] Add g keybinding to jump to top in pgtail_py/fullscreen/keybindings.py
- [ ] T047 [US3] Add G keybinding to jump to bottom in pgtail_py/fullscreen/keybindings.py
- [ ] T048 [US3] Enable enable_page_navigation_bindings in Application in pgtail_py/fullscreen/app.py

**Checkpoint**: Power users have full vim-style navigation

---

## Phase 7: User Story 4 - Mouse Navigation and Selection (Priority: P2)

**Goal**: User can scroll with mouse wheel and select text for copying

**Independent Test**: Use scroll wheel to navigate, select text with click-drag, copy to clipboard

### Implementation for User Story 4

- [ ] T049 [US4] Enable mouse_support=True in Application in pgtail_py/fullscreen/app.py
- [ ] T050 [US4] Enable scrollbar=True in TextArea in pgtail_py/fullscreen/layout.py
- [ ] T051 [US4] Test mouse wheel scroll triggers browse mode in pgtail_py/fullscreen/keybindings.py
- [ ] T052 [US4] Verify text selection works via terminal native handling (no code needed, just test)

**Checkpoint**: Mouse users can navigate comfortably

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, documentation, and cleanup

- [ ] T053 [P] Handle terminal resize events gracefully in pgtail_py/fullscreen/app.py
- [ ] T054 [P] Add buffer boundary clamping (prevent scroll past first/last line) in pgtail_py/fullscreen/keybindings.py
- [ ] T055 [P] Add error handling for invalid search regex in pgtail_py/fullscreen/keybindings.py
- [ ] T056 Update CLAUDE.md with fullscreen module documentation
- [X] T057 Add fullscreen command to help output in pgtail_py/cli_core.py (completed in Phase 3)
- [ ] T058 Run make lint and fix any issues
- [ ] T059 Run make test and ensure all tests pass
- [ ] T060 Manual validation per quickstart.md scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 5 (Phase 3)**: Depends on Foundational - MUST be first user story (entry point)
- **User Stories 1-4 (Phases 4-7)**: Depend on US5 completion (need working fullscreen to test)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 2 (Foundation)
       │
       ▼
Phase 3 (US5: Enter/Exit) ────────────── MVP checkpoint
       │
       ├──────────┬──────────┐
       ▼          ▼          ▼
Phase 4 (US1)  Phase 5 (US2)  Phase 6 (US3)  ← Can parallelize
       │          │          │
       └──────────┴──────────┴──────────┐
                                        ▼
                               Phase 7 (US4)
                                        │
                                        ▼
                               Phase 8 (Polish)
```

### Within Each User Story

- Tests written first (TDD approach per plan.md)
- Layout/keybinding infrastructure before app integration
- Core implementation before edge case handling

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003 and T004 can run in parallel

**Phase 2 (Foundation)**:
- T005, T006, T007 (tests) can run in parallel
- T010, T011 modify same file - must be sequential

**Phase 3-7 (User Stories)**:
- Tests within each story can run in parallel
- After US5, stories US1-US3 can theoretically parallelize

**Phase 8 (Polish)**:
- T053, T054, T055 can run in parallel

---

## Parallel Example: Foundation Tests

```bash
# Launch all foundation tests together:
Task: "Unit test for LogBuffer.append() and FIFO eviction in tests/unit/fullscreen/test_buffer.py"
Task: "Unit test for LogBuffer.get_text() and get_lines() in tests/unit/fullscreen/test_buffer.py"
Task: "Unit test for FullscreenState mode transitions in tests/unit/fullscreen/test_state.py"
```

## Parallel Example: User Story 1 Tests

```bash
# Launch US1 tests together:
Task: "Unit test for toggle_follow() state transitions in tests/unit/fullscreen/test_state.py"
Task: "Unit test for scroll keybindings in tests/unit/fullscreen/test_keybindings.py"
```

---

## Implementation Strategy

### MVP First (User Story 5 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 5 (Enter/Exit)
4. **STOP and VALIDATE**: Can enter fullscreen, see logs, exit with `q`
5. Demo: Basic fullscreen viewer working

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 5 → Test independently → MVP: Basic fullscreen
3. Add User Story 1 → Test independently → Add: Scroll and follow/browse
4. Add User Story 2 → Test independently → Add: Search functionality
5. Add User Story 3 → Test independently → Add: Power user navigation
6. Add User Story 4 → Test independently → Add: Mouse support
7. Polish → Complete feature

### Recommended Order

Given that US5 is the entry point and US1/US2 are both P1 priority:

1. **US5** (Enter/Exit) - Required first
2. **US1** (Scroll/Browse) - Core value proposition
3. **US2** (Search) - Complements scrolling
4. **US3** (Page Navigation) - Power user enhancement
5. **US4** (Mouse) - Accessibility enhancement

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US5 must complete before any other story can be tested
- Buffer feeding (T012) happens during REPL tailing, not in fullscreen app
- SearchToolbar integration (T035-T036) provides most search functionality built-in
- Mouse support (T049-T052) mostly relies on prompt_toolkit defaults
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
