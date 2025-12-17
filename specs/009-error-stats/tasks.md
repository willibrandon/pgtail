# Tasks: Error Statistics Dashboard

**Input**: Design documents from `/specs/009-error-stats/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as unit tests are mentioned in the Quality Standards of plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module files and register the command

- [x] T001 Create error_stats.py module skeleton in pgtail_py/error_stats.py
- [x] T002 [P] Create error_trend.py module skeleton in pgtail_py/error_trend.py
- [x] T003 [P] Create cli_errors.py module skeleton in pgtail_py/cli_errors.py
- [x] T004 Register `errors` command in pgtail_py/commands.py COMMANDS dict

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and integration hooks that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement SQLSTATE_CATEGORIES dict with class codes (23, 42, 53, 57, 58) in pgtail_py/error_stats.py
- [x] T006 [P] Implement SQLSTATE_NAMES dict with ~15 common error codes in pgtail_py/error_stats.py
- [x] T007 Implement ErrorEvent frozen dataclass with from_entry() classmethod in pgtail_py/error_stats.py
- [x] T008 Implement ERROR_LEVELS, WARNING_LEVELS, TRACKED_LEVELS constants in pgtail_py/error_stats.py
- [x] T009 Implement ErrorStats dataclass with deque, add(), clear(), is_empty() in pgtail_py/error_stats.py
- [x] T010 Add error_stats field to AppState dataclass in pgtail_py/cli.py
- [x] T011 Add on_entry callback parameter to LogTailer.__init__() in pgtail_py/tailer.py
- [x] T012 Call on_entry callback in LogTailer._read_new_lines() for ALL entries (before filtering) in pgtail_py/tailer.py
- [x] T013 Wire up ErrorStats.add as on_entry callback when creating LogTailer in pgtail_py/cli.py

**Checkpoint**: Foundation ready - error events are now being tracked during tailing

---

## Phase 3: User Story 1 - Error Summary View (Priority: P1) MVP

**Goal**: Display error summary with counts by type (SQLSTATE) and by level

**Independent Test**: Run `errors` command after tailing logs with errors, verify counts and breakdowns display correctly

### Tests for User Story 1

- [x] T014 [P] [US1] Create test file tests/test_error_stats.py with test fixtures
- [x] T015 [P] [US1] Test ErrorEvent.from_entry() creates correct fields in tests/test_error_stats.py
- [x] T016 [P] [US1] Test ErrorStats.add() increments counters correctly in tests/test_error_stats.py
- [x] T017 [P] [US1] Test ErrorStats.get_by_level() returns correct counts in tests/test_error_stats.py
- [x] T018 [P] [US1] Test ErrorStats.get_by_code() returns counts sorted by frequency in tests/test_error_stats.py
- [x] T019 [P] [US1] Test get_sqlstate_name() and get_sqlstate_category() lookups in tests/test_error_stats.py

### Implementation for User Story 1

- [x] T020 [US1] Implement get_sqlstate_name() helper function in pgtail_py/error_stats.py
- [x] T021 [US1] Implement get_sqlstate_category() helper function in pgtail_py/error_stats.py
- [x] T022 [US1] Implement ErrorStats.get_by_level() method in pgtail_py/error_stats.py
- [x] T023 [US1] Implement ErrorStats.get_by_code() method in pgtail_py/error_stats.py
- [x] T024 [US1] Implement errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T025 [US1] Implement _show_summary() with formatted output in pgtail_py/cli_errors.py
- [x] T026 [US1] Add "no errors recorded" message when stats.is_empty() in pgtail_py/cli_errors.py
- [x] T027 [US1] Add "not tailing" error message when no active tail in pgtail_py/cli_errors.py
- [x] T028 [US1] Wire errors_command into REPL command dispatcher in pgtail_py/cli.py
- [x] T029 [US1] Add _complete_errors() method to PgtailCompleter in pgtail_py/commands.py

**Checkpoint**: User Story 1 complete - `errors` command shows summary with type/level breakdowns

---

## Phase 4: User Story 2 - Error Trend Visualization (Priority: P2)

**Goal**: Display sparkline visualization of error rate over time with `errors --trend`

**Independent Test**: Generate errors at varying rates, run `errors --trend`, verify sparklines reflect rate changes

### Tests for User Story 2

- [x] T030 [P] [US2] Create test file tests/test_error_trend.py with test fixtures
- [x] T031 [P] [US2] Test sparkline() generates correct characters for values in tests/test_error_trend.py
- [x] T032 [P] [US2] Test bucket_events() correctly groups events by minute in tests/test_error_trend.py
- [x] T033 [P] [US2] Test sparkline() handles empty list in tests/test_error_trend.py
- [x] T034 [P] [US2] Test sparkline() handles all-same values in tests/test_error_trend.py

### Implementation for User Story 2

- [x] T035 [US2] Implement SPARK_CHARS constant in pgtail_py/error_trend.py
- [x] T036 [US2] Implement sparkline() function in pgtail_py/error_trend.py
- [x] T037 [US2] Implement bucket_events() function in pgtail_py/error_trend.py
- [x] T038 [US2] Implement ErrorStats.get_trend_buckets() method in pgtail_py/error_stats.py
- [x] T039 [US2] Implement _show_trend() handler in pgtail_py/cli_errors.py
- [x] T040 [US2] Add spike detection and annotation (>2x average) in pgtail_py/cli_errors.py
- [x] T041 [US2] Handle --trend flag in errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T042 [US2] Add --trend to completion in _complete_errors() in pgtail_py/commands.py

**Checkpoint**: User Story 2 complete - `errors --trend` shows sparkline visualization

---

## Phase 5: User Story 3 - Live Error Counter (Priority: P2)

**Goal**: Display real-time updating error counter with `errors --live`

**Independent Test**: Start live mode, generate errors, verify counter updates in place without scrolling

### Implementation for User Story 3

- [x] T043 [US3] Implement _show_live() handler with ANSI cursor control in pgtail_py/cli_errors.py
- [x] T044 [US3] Implement live loop with 500ms update interval in pgtail_py/cli_errors.py
- [x] T045 [US3] Add Ctrl+C handler to exit live mode cleanly in pgtail_py/cli_errors.py
- [x] T046 [US3] Display "time since last error" that updates in pgtail_py/cli_errors.py
- [x] T047 [US3] Handle --live flag in errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T048 [US3] Add --live to completion in _complete_errors() in pgtail_py/commands.py

**Checkpoint**: User Story 3 complete - `errors --live` shows updating counter

---

## Phase 6: User Story 4 - Filter by Error Code (Priority: P3)

**Goal**: Filter statistics by SQLSTATE code with `errors --code CODE`

**Independent Test**: Generate multiple error types, run `errors --code 23505`, verify only matching errors shown

### Implementation for User Story 4

- [x] T049 [US4] Implement ErrorStats.get_events_by_code() method in pgtail_py/error_stats.py
- [x] T050 [US4] Implement _show_by_code() handler in pgtail_py/cli_errors.py
- [x] T051 [US4] Display recent examples with timestamp and message excerpt in pgtail_py/cli_errors.py
- [x] T052 [US4] Add validation for 5-character SQLSTATE format in pgtail_py/cli_errors.py
- [x] T053 [US4] Add "no errors with code" message when no matches in pgtail_py/cli_errors.py
- [x] T054 [US4] Handle --code flag in errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T055 [US4] Add --code to completion with common SQLSTATE codes in pgtail_py/commands.py

**Checkpoint**: User Story 4 complete - `errors --code CODE` filters by SQLSTATE

---

## Phase 7: User Story 5 - Time-Scoped Statistics (Priority: P3)

**Goal**: Scope statistics to a time window with `errors --since TIME`

**Independent Test**: Generate errors across time periods, run `errors --since 30m`, verify only recent errors counted

### Implementation for User Story 5

- [x] T056 [US5] Implement ErrorStats.get_events_since() method in pgtail_py/error_stats.py
- [x] T057 [US5] Integrate with existing time_filter.parse_time() in pgtail_py/cli_errors.py
- [x] T058 [US5] Update _show_summary() to accept time filter in pgtail_py/cli_errors.py
- [x] T059 [US5] Display time window in output header in pgtail_py/cli_errors.py
- [x] T060 [US5] Handle --since flag in errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T061 [US5] Allow --since to combine with --code and --trend in pgtail_py/cli_errors.py
- [x] T062 [US5] Add --since to completion with time examples in pgtail_py/commands.py

**Checkpoint**: User Story 5 complete - `errors --since TIME` filters by time window

---

## Phase 8: User Story 6 - Reset Counters (Priority: P3)

**Goal**: Reset all error statistics with `errors clear`

**Independent Test**: Accumulate errors, run `errors clear`, verify subsequent `errors` shows zero counts

### Implementation for User Story 6

- [x] T063 [US6] Implement _clear_stats() handler in pgtail_py/cli_errors.py
- [x] T064 [US6] Call ErrorStats.clear() and display confirmation in pgtail_py/cli_errors.py
- [x] T065 [US6] Handle `clear` subcommand in errors_command() dispatcher in pgtail_py/cli_errors.py
- [x] T066 [US6] Add `clear` to completion in _complete_errors() in pgtail_py/commands.py

**Checkpoint**: User Story 6 complete - `errors clear` resets statistics

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validation, edge cases, and documentation

- [x] T067 [P] Add invalid option combination error messages in pgtail_py/cli_errors.py
- [x] T068 [P] Add module docstrings to error_stats.py, error_trend.py, cli_errors.py
- [x] T069 [P] Add type hints to all public functions in new modules
- [x] T070 Run `make lint` and fix any issues
- [x] T071 Run `make test` and ensure all tests pass
- [x] T072 Manual testing: verify all scenarios from contracts/errors-command.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-8)**: All depend on Foundational phase completion
  - US1 (Phase 3): Required first - provides core display infrastructure
  - US2-US6 (Phases 4-8): Can proceed after US1, mostly independent
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on ErrorStats from US1 for trend data
- **User Story 3 (P2)**: Depends on ErrorStats from US1 for live counts
- **User Story 4 (P3)**: Can start after Foundational - independent of display logic
- **User Story 5 (P3)**: Can start after Foundational - adds filtering to existing output
- **User Story 6 (P3)**: Can start after Foundational - simple clear operation

### Within Each User Story

- Tests should be written first and verified to fail
- Core logic before display formatting
- Handler implementation before dispatcher integration
- Integration before completion support

### Parallel Opportunities

- All Setup tasks T001-T003 marked [P] can run in parallel
- T005-T006 (SQLSTATE dicts) can run in parallel
- All test tasks for each story marked [P] can run in parallel
- Different user stories can be worked on in parallel after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "T014 Create test file tests/test_error_stats.py"
Task: "T015 Test ErrorEvent.from_entry()"
Task: "T016 Test ErrorStats.add()"
Task: "T017 Test ErrorStats.get_by_level()"
Task: "T018 Test ErrorStats.get_by_code()"
Task: "T019 Test SQLSTATE lookup functions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test `errors` command independently
5. Demo basic error summary functionality

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test `errors` → Demo (MVP!)
3. Add User Story 2 → Test `errors --trend` → Demo
4. Add User Story 3 → Test `errors --live` → Demo
5. Add User Stories 4-6 → Test filters and clear → Demo
6. Each story adds value without breaking previous stories

### Recommended Order

Given the dependencies:
1. **Phase 1-2**: Setup and Foundational (required)
2. **Phase 3 (US1)**: Core summary - MVP milestone
3. **Phase 4 (US2)**: Trend visualization
4. **Phase 5 (US3)**: Live counter
5. **Phases 6-8 (US4-6)**: Filters and clear (can be parallelized)
6. **Phase 9**: Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 72 tasks across 9 phases
