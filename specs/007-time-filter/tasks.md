# Tasks: Time-Based Filtering

**Input**: Design documents from `/specs/007-time-filter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No test tasks generated (tests not explicitly requested in specification).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Source: `pgtail_py/`
- Tests: `tests/`

---

## Phase 1: Setup

**Purpose**: Create new time_filter module with core parsing and filtering logic

- [x] T001 [P] Create time_filter.py module skeleton with imports in pgtail_py/time_filter.py
- [x] T002 [P] Add `since`, `until`, `between` to COMMANDS dict in pgtail_py/commands.py

---

## Phase 2: Foundational (Core Time Filter Module)

**Purpose**: Implement TimeFilter dataclass and parse_time function - BLOCKS all user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `parse_time()` function supporting relative times (5m, 2h, 1d, 30s) in pgtail_py/time_filter.py
- [x] T004 Extend `parse_time()` to support HH:MM and HH:MM:SS formats (today at time) in pgtail_py/time_filter.py
- [x] T005 Extend `parse_time()` to support ISO 8601 with T separator and Z suffix in pgtail_py/time_filter.py
- [x] T006 Implement TimeFilter dataclass with since/until/original_input fields in pgtail_py/time_filter.py
- [x] T007 Implement `TimeFilter.matches(entry)` method for entry filtering in pgtail_py/time_filter.py
- [x] T008 Implement `TimeFilter.is_active()` and `TimeFilter.empty()` methods in pgtail_py/time_filter.py
- [x] T009 Implement `is_future_time()` helper function in pgtail_py/time_filter.py
- [x] T010 Implement `format_time_range()` for human-readable display in pgtail_py/time_filter.py
- [x] T011 Add `time_filter: TimeFilter` field to AppState dataclass in pgtail_py/cli.py
- [x] T012 Add `_time_filter` parameter to LogTailer.__init__() in pgtail_py/tailer.py
- [x] T013 Implement `LogTailer.update_time_filter()` method in pgtail_py/tailer.py
- [x] T014 Integrate time filter into LogTailer._should_show() method (first in filter chain) in pgtail_py/tailer.py

**Checkpoint**: Foundation ready - TimeFilter module complete, LogTailer integration done

---

## Phase 3: User Story 1 - Recent History Investigation (Priority: P1) MVP

**Goal**: Enable `since <relative>` command for filtering logs by relative time (5m, 2h, 1d)

**Independent Test**: Run `since 5m` and verify only entries from the last 5 minutes are displayed

### Implementation for User Story 1

- [ ] T015 [US1] Implement `handle_since()` command handler in pgtail_py/cli.py
- [ ] T016 [US1] Add `since clear` subcommand handling to clear time filter in pgtail_py/cli.py
- [ ] T017 [US1] Display time range feedback when filter is set ("Showing logs from last 5 minutes") in pgtail_py/cli.py
- [ ] T018 [US1] Handle "no entries in range" case with informative message in pgtail_py/cli.py
- [ ] T019 [US1] Add time filter to status display in existing status output in pgtail_py/cli.py
- [ ] T020 [US1] Add completions for `since` command (clear, time examples) in pgtail_py/commands.py

**Checkpoint**: User Story 1 complete - `since 5m`, `since 2h`, `since 1d`, `since clear` all work

---

## Phase 4: User Story 2 - Specific Time Window Investigation (Priority: P1)

**Goal**: Enable absolute time formats (HH:MM, HH:MM:SS, ISO 8601) with `since` command

**Independent Test**: Run `since 14:30` and verify logs from today at 14:30 onward are displayed

### Implementation for User Story 2

- [ ] T021 [US2] Ensure handle_since() works with HH:MM format in pgtail_py/cli.py
- [ ] T022 [US2] Ensure handle_since() works with HH:MM:SS format in pgtail_py/cli.py
- [ ] T023 [US2] Ensure handle_since() works with YYYY-MM-DDTHH:MM format in pgtail_py/cli.py
- [ ] T024 [US2] Add future time warning (show warning but allow command) in pgtail_py/cli.py
- [ ] T025 [US2] Format display to show resolved time ("since 14:30:00 today") in pgtail_py/cli.py

**Checkpoint**: User Story 2 complete - All absolute time formats work with `since`

---

## Phase 5: User Story 3 - Time Range Investigation (Priority: P2)

**Goal**: Enable `between <start> <end>` command for bounded time ranges

**Independent Test**: Run `between 14:30 15:00` and verify only entries in that range are displayed

### Implementation for User Story 3

- [ ] T026 [US3] Implement `handle_between()` command handler in pgtail_py/cli.py
- [ ] T027 [US3] Validate start time < end time with error message in pgtail_py/cli.py
- [ ] T028 [US3] Display range feedback ("Showing logs between 14:30 and 15:00") in pgtail_py/cli.py
- [ ] T029 [US3] Add completions for `between` command in pgtail_py/commands.py

**Checkpoint**: User Story 3 complete - `between` command works for time ranges

---

## Phase 6: User Story 4 - Upper Bound Filtering (Priority: P2)

**Goal**: Enable `until <time>` command for filtering logs up to a specific time

**Independent Test**: Run `until 15:00` and verify only entries before that time are shown

### Implementation for User Story 4

- [ ] T030 [US4] Implement `handle_until()` command handler in pgtail_py/cli.py
- [ ] T031 [US4] Ensure `until` disables follow mode (no tailing) in pgtail_py/cli.py
- [ ] T032 [US4] Display feedback ("Showing logs until 15:00:00") in pgtail_py/cli.py
- [ ] T033 [US4] Add completions for `until` command in pgtail_py/commands.py

**Checkpoint**: User Story 4 complete - `until` command works

---

## Phase 7: User Story 5 - Time Filter with Live Tail (Priority: P2)

**Goal**: Support `--since` flag on tail command for starting tail from a specific time

**Independent Test**: Run `tail 0 --since 10m` and verify historical entries shown first, then tailing continues

### Implementation for User Story 5

- [ ] T034 [US5] Parse `--since <time>` flag in tail command arguments in pgtail_py/cli.py
- [ ] T035 [US5] When --since provided, read historical entries from that time before starting live tail in pgtail_py/cli.py
- [ ] T036 [US5] Ensure new entries during tail are displayed (since filter allows future entries) in pgtail_py/cli.py
- [ ] T037 [US5] Add completions for `tail --since` in pgtail_py/commands.py

**Checkpoint**: User Story 5 complete - `tail --since` works for historical + live tail

---

## Phase 8: User Story 6 - Clear Time Filter (Priority: P3)

**Goal**: Enable `since clear` to remove active time filters

**Independent Test**: Set time filter, run `since clear`, verify all logs are shown again

### Implementation for User Story 6

Already implemented in T016 (part of US1). This phase is for verification only.

- [ ] T038 [US6] Verify `since clear` properly resets time_filter to TimeFilter.empty() in pgtail_py/cli.py
- [ ] T039 [US6] Verify feedback message confirms filter was removed in pgtail_py/cli.py

**Checkpoint**: User Story 6 complete - `since clear` works

---

## Phase 9: User Story 7 - Combined Filtering (Priority: P3)

**Goal**: Time filter works correctly with level and regex filters simultaneously

**Independent Test**: Set level=ERROR, regex=/connection/, since=1h, verify all filters combine correctly

### Implementation for User Story 7

Mostly implemented via LogTailer._should_show() integration (T014). This phase is for verification and status display.

- [ ] T040 [US7] Verify time filter combines with level filter in LogTailer._should_show() in pgtail_py/tailer.py
- [ ] T041 [US7] Verify time filter combines with regex filter in LogTailer._should_show() in pgtail_py/tailer.py
- [ ] T042 [US7] Ensure status display shows all active filters (levels + regex + time) in pgtail_py/cli.py

**Checkpoint**: User Story 7 complete - All filter types combine correctly

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and documentation

- [ ] T043 [P] Add comprehensive error messages for invalid time formats in pgtail_py/time_filter.py
- [ ] T044 [P] Handle entries without timestamps gracefully (skip silently when filter active) in pgtail_py/time_filter.py
- [ ] T045 [P] Update export.py to use new parse_time from time_filter.py (replace duplicate parse_since) in pgtail_py/export.py
- [ ] T046 Run manual validation using quickstart.md scenarios
- [ ] T047 Run `make lint` and fix any issues
- [ ] T048 Run `make test` and verify all existing tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Foundational
  - US2 (P1): Can start after Foundational (parallelize with US1 if desired)
  - US3-US7: Can start after Foundational, benefit from US1/US2 patterns
- **Polish (Phase 10)**: Can start after US1 is complete, best after all stories done

### User Story Dependencies

- **User Story 1 (P1)**: Foundation only - No dependencies on other stories
- **User Story 2 (P1)**: Foundation only - Extends parse_time formats from Foundation
- **User Story 3 (P2)**: Foundation only - Independent `between` command
- **User Story 4 (P2)**: Foundation only - Independent `until` command
- **User Story 5 (P2)**: Foundation only - Extends tail command
- **User Story 6 (P3)**: Depends on US1 (`since clear` is part of `since` command)
- **User Story 7 (P3)**: Foundation only - Verifies filter composition

### Parallel Opportunities

Within Foundational Phase:
```
T003, T004, T005 must be sequential (building parse_time incrementally)
T006, T007, T008, T009, T010 can be parallel after parse_time done
T011, T012, T013, T014 can be parallel (different files: cli.py, tailer.py)
```

Across User Stories:
- US1 and US2 can run in parallel (both use `since`, different format handling)
- US3, US4, US5 can run in parallel (independent commands: between, until, tail --since)
- US6 and US7 are verification-focused, can run after core implementation

---

## Parallel Example: Foundational Phase

```bash
# After parse_time is complete, launch these in parallel:
Task: "Implement TimeFilter dataclass in pgtail_py/time_filter.py"
Task: "Add time_filter field to AppState in pgtail_py/cli.py"
Task: "Add _time_filter to LogTailer in pgtail_py/tailer.py"
```

## Parallel Example: User Story Commands

```bash
# After Foundational is complete, launch US1-US5 command handlers:
Task: "Implement handle_since() in pgtail_py/cli.py"      # US1
Task: "Implement handle_between() in pgtail_py/cli.py"    # US3
Task: "Implement handle_until() in pgtail_py/cli.py"      # US4
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T014)
3. Complete Phase 3: User Story 1 (T015-T020)
4. **STOP and VALIDATE**: Test `since 5m`, `since 2h`, `since clear`
5. MVP delivers: Relative time filtering for recent investigation

### Incremental Delivery

1. Setup + Foundational → Core time filter ready
2. Add US1 → `since <relative>` works → Test independently
3. Add US2 → `since <absolute>` works → Test independently
4. Add US3 → `between` works → Test independently
5. Add US4 → `until` works → Test independently
6. Add US5 → `tail --since` works → Test independently
7. Polish → Error handling, edge cases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The parse_time function is built incrementally (T003→T004→T005) to ensure each format works before adding next
