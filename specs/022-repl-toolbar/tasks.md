# Tasks: REPL Bottom Toolbar

**Input**: Design documents from `/specs/022-repl-toolbar/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Unit tests for toolbar formatting included as specified in quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/unit/` at repository root
- **Themes**: `pgtail_py/themes/` for built-in themes

---

## Phase 1: Setup (Theme Infrastructure)

**Purpose**: Add toolbar style definitions to all built-in themes

- [ ] T001 [P] Add toolbar styles to dark theme in pgtail_py/themes/dark.py
- [ ] T002 [P] Add toolbar styles to light theme in pgtail_py/themes/light.py
- [ ] T003 [P] Add toolbar styles to high-contrast theme in pgtail_py/themes/high_contrast.py
- [ ] T004 [P] Add toolbar styles to monokai theme in pgtail_py/themes/monokai.py
- [ ] T005 [P] Add toolbar styles to solarized-dark theme in pgtail_py/themes/solarized_dark.py
- [ ] T006 [P] Add toolbar styles to solarized-light theme in pgtail_py/themes/solarized_light.py

**Style keys to add to each theme's `ui` dictionary:**
- `toolbar` - Default toolbar text (normal foreground on dark background)
- `toolbar.dim` - Separators and hints (subdued foreground)
- `toolbar.filter` - Filter values / accent color (cyan/highlight color)
- `toolbar.warning` - "No instances" warning (yellow/warning color)
- `toolbar.shell` - Shell mode indicator (white, bold)

**Checkpoint**: All 6 built-in themes have toolbar style definitions

---

## Phase 2: Foundational (Toolbar Module)

**Purpose**: Create core toolbar rendering infrastructure that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create repl_toolbar.py module with create_toolbar_func() in pgtail_py/repl_toolbar.py
- [ ] T008 Implement _format_filters() helper function in pgtail_py/repl_toolbar.py
- [ ] T009 Integrate toolbar with PromptSession in pgtail_py/cli.py

**Implementation details for T007-T008:**
- `create_toolbar_func(state: AppState)` returns a callable that returns `list[tuple[str, str]]`
- Callable is invoked by prompt_toolkit on each render cycle
- Uses `is_color_disabled()` from `pgtail_py.utils` for NO_COLOR support
- Returns FormattedText-compatible style tuples

**Implementation details for T009:**
```python
from pgtail_py.repl_toolbar import create_toolbar_func

toolbar_func = create_toolbar_func(state)
session: PromptSession[str] = PromptSession(
    history=FileHistory(str(history_path)),
    key_bindings=bindings,
    completer=completer,
    bottom_toolbar=toolbar_func,  # ADD
    style=get_style(state.theme_manager),  # ADD (may need to add)
)
```

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View Instance Status at a Glance (Priority: P1) 🎯 MVP

**Goal**: Users see PostgreSQL instance count immediately upon launching pgtail without running commands

**Independent Test**: Launch pgtail with various instance configurations and verify toolbar displays correct count

### Tests for User Story 1

- [ ] T010 [P] [US1] Unit test for instance count display (0, 1, N) in tests/unit/test_repl_toolbar.py
- [ ] T011 [P] [US1] Unit test for singular/plural grammar ("1 instance" vs "2 instances") in tests/unit/test_repl_toolbar.py
- [ ] T012 [P] [US1] Unit test for "No instances" warning with refresh hint in tests/unit/test_repl_toolbar.py

### Implementation for User Story 1

- [ ] T013 [US1] Implement instance count display (0, 1, N cases) in get_toolbar() in pgtail_py/repl_toolbar.py
- [ ] T014 [US1] Implement "No instances" warning state with "(run 'refresh')" hint in pgtail_py/repl_toolbar.py
- [ ] T015 [US1] Verify toolbar updates after `refresh` command completes

**Acceptance Scenarios (from spec.md):**
1. Given 3 PostgreSQL instances detected → toolbar displays "3 instances"
2. Given 1 PostgreSQL instance detected → toolbar displays "1 instance" (singular)
3. Given 0 instances → toolbar displays "No instances" in warning color with "(run 'refresh')" hint
4. Given user runs `refresh` and instances increase → toolbar updates on next prompt

**Checkpoint**: User Story 1 fully functional - instance count visible at a glance

---

## Phase 4: User Story 2 - See Pre-configured Filters Before Tailing (Priority: P2)

**Goal**: Users see active filters (levels, regex, time, slow query) so they know how `tail` will behave

**Independent Test**: Configure multiple filter types and verify they appear in toolbar

### Tests for User Story 2

- [ ] T016 [P] [US2] Unit test for level filter display in tests/unit/test_repl_toolbar.py
- [ ] T017 [P] [US2] Unit test for regex filter display with flags in tests/unit/test_repl_toolbar.py
- [ ] T018 [P] [US2] Unit test for time filter display in tests/unit/test_repl_toolbar.py
- [ ] T019 [P] [US2] Unit test for slow query threshold display in tests/unit/test_repl_toolbar.py
- [ ] T020 [P] [US2] Unit test for multiple filters combined in tests/unit/test_repl_toolbar.py
- [ ] T021 [P] [US2] Unit test for filter section hidden when no filters configured in tests/unit/test_repl_toolbar.py

### Implementation for User Story 2

- [ ] T022 [US2] Implement level filter formatting (only when not ALL levels) in _format_filters() in pgtail_py/repl_toolbar.py
- [ ] T023 [US2] Implement regex filter formatting (first pattern with flags, +N more indicator) in pgtail_py/repl_toolbar.py
- [ ] T024 [US2] Implement time filter formatting using format_description() in pgtail_py/repl_toolbar.py
- [ ] T025 [US2] Implement slow query threshold formatting (only when != 100ms default) in pgtail_py/repl_toolbar.py
- [ ] T026 [US2] Implement filter section visibility logic (hide when no filters) in pgtail_py/repl_toolbar.py
- [ ] T027 [US2] Verify toolbar updates after filter commands (levels, filter, since, slow)
- [ ] T028 [US2] Verify toolbar updates after `clear` command removes filters

**Acceptance Scenarios (from spec.md):**
1. No filters configured → no filter section appears
2. `levels error+` → shows "levels:ERROR,FATAL,PANIC" in accent color
3. `filter /deadlock/i` → shows "filter:/deadlock/i" in accent color
4. `since 1h` → shows time filter description in accent color
5. `slow 200` → shows "slow:>200ms" in accent color
6. Multiple filters set → all appear space-separated
7. `clear` run → filter section disappears

**Checkpoint**: User Story 2 fully functional - all filter types visible

---

## Phase 5: User Story 3 - View Current Theme (Priority: P3)

**Goal**: Users see which theme is active for visual confirmation after theme commands

**Independent Test**: Switch themes and verify toolbar updates to show new theme name

### Tests for User Story 3

- [ ] T029 [P] [US3] Unit test for theme name display in tests/unit/test_repl_toolbar.py
- [ ] T030 [P] [US3] Unit test for theme display unchanged on `theme list` in tests/unit/test_repl_toolbar.py

### Implementation for User Story 3

- [ ] T031 [US3] Implement theme name display at right side of toolbar in pgtail_py/repl_toolbar.py
- [ ] T032 [US3] Verify toolbar updates after `theme <name>` command

**Acceptance Scenarios (from spec.md):**
1. Default dark theme active → shows "Theme: dark" at right side
2. `theme monokai` → immediately shows "Theme: monokai"
3. `theme list` → theme display remains unchanged

**Checkpoint**: User Story 3 fully functional - theme visibility confirmed

---

## Phase 6: User Story 4 - Shell Mode Indicator (Priority: P4)

**Goal**: Users clearly see when shell mode is active with exit instructions

**Independent Test**: Enter shell mode and verify toolbar changes to show shell indicator

### Tests for User Story 4

- [ ] T033 [P] [US4] Unit test for shell mode indicator display in tests/unit/test_repl_toolbar.py
- [ ] T034 [P] [US4] Unit test for return to normal display after shell mode exit in tests/unit/test_repl_toolbar.py

### Implementation for User Story 4

- [ ] T035 [US4] Implement shell mode display branch in get_toolbar() in pgtail_py/repl_toolbar.py
- [ ] T036 [US4] Implement shell mode exit hint "Press Escape to exit" in pgtail_py/repl_toolbar.py
- [ ] T037 [US4] Verify toolbar returns to idle display after Escape or shell command execution

**Acceptance Scenarios (from spec.md):**
1. User in idle mode, presses `!` with empty buffer → toolbar shows "SHELL" bold white with "Press Escape to exit" dim
2. Shell mode active, user presses Escape → toolbar returns to normal idle display
3. Shell mode active, user runs command and it completes → toolbar returns to normal idle display

**Checkpoint**: User Story 4 fully functional - shell mode clearly indicated

---

## Phase 7: Edge Cases & Cross-Cutting Concerns

**Purpose**: Handle edge cases specified in spec.md

- [ ] T038 [P] Unit test for NO_COLOR environment variable support in tests/unit/test_repl_toolbar.py
- [ ] T039 [P] Unit test for long theme name truncation (>15 chars) in tests/unit/test_repl_toolbar.py
- [ ] T040 [P] Unit test for regex pattern with special characters displayed as-is in tests/unit/test_repl_toolbar.py
- [ ] T041 Implement NO_COLOR support (plain text, no styling) in pgtail_py/repl_toolbar.py
- [ ] T042 Implement theme name truncation (15 chars max with ellipsis) in pgtail_py/repl_toolbar.py
- [ ] T043 Implement bullet separator (•) between toolbar sections in pgtail_py/repl_toolbar.py
- [ ] T044 Verify toolbar does not flicker while typing in prompt

**Edge Cases (from spec.md):**
- Terminal width < 40 columns → graceful truncation (prioritize instance > filters > theme)
- Many filters configured → show first pattern with "+N more" indicator
- Regex with special chars → display as-is without interpretation
- During tail mode → toolbar not visible (Textual takes over)
- Long theme name → truncate to 15 chars with ellipsis
- NO_COLOR set → toolbar appears but without styling
- User typing → toolbar remains static (no flicker)

---

## Phase 8: Polish & Final Validation

**Purpose**: Final verification and cleanup

- [ ] T045 Run full test suite (make test) to verify no regressions
- [ ] T046 Run linting (make lint) and fix any issues
- [ ] T047 Manual verification: Launch pgtail and verify instance count displays
- [ ] T048 Manual verification: Configure filters and verify they appear in toolbar
- [ ] T049 Manual verification: Switch themes and verify toolbar updates
- [ ] T050 Manual verification: Enter shell mode and verify indicator appears
- [ ] T051 Manual verification: Set NO_COLOR=1 and verify plain text output
- [ ] T052 Run quickstart.md verification checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Edge Cases (Phase 7)**: Depends on all user stories being complete
- **Polish (Phase 8)**: Depends on Edge Cases completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests written first (where marked)
- Implementation follows tests
- Verification last

### Parallel Opportunities

**Phase 1 (all 6 tasks):**
```
T001, T002, T003, T004, T005, T006 (different theme files)
```

**Phase 3 Tests (US1):**
```
T010, T011, T012 (independent test cases)
```

**Phase 4 Tests (US2):**
```
T016, T017, T018, T019, T020, T021 (independent test cases)
```

**Phase 5 Tests (US3):**
```
T029, T030 (independent test cases)
```

**Phase 6 Tests (US4):**
```
T033, T034 (independent test cases)
```

**Phase 7 Edge Case Tests:**
```
T038, T039, T040 (independent test cases)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (theme styles)
2. Complete Phase 2: Foundational (toolbar module + CLI integration)
3. Complete Phase 3: User Story 1 (instance count)
4. **STOP and VALIDATE**: Toolbar visible, shows instance count
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Instance count visible → Deploy (MVP!)
3. Add User Story 2 → Filters visible → Deploy
4. Add User Story 3 → Theme visible → Deploy
5. Add User Story 4 → Shell mode indicator → Deploy
6. Add Edge Cases → Polish complete → Final deploy

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (all 6 theme files in parallel)
2. Complete Foundational together
3. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (for test tasks)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The toolbar is always displayed - no configuration option to disable
