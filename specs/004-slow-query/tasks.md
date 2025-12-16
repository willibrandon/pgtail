# Tasks: Slow Query Detection and Highlighting

**Input**: Design documents from `/specs/004-slow-query/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as the project uses pytest (per pyproject.toml and CLAUDE.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `pgtail_py/` for source, `tests/` for tests at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new module and shared entities used by all user stories

- [x] T001 Create slow_query.py module with SlowQueryLevel enum in pgtail_py/slow_query.py
- [x] T002 [P] Add SlowQueryConfig dataclass with default thresholds (100/500/1000ms) in pgtail_py/slow_query.py
- [x] T003 [P] Add DurationStats dataclass with samples list and running counters in pgtail_py/slow_query.py
- [x] T004 [P] Implement extract_duration() function with regex parsing in pgtail_py/slow_query.py
- [x] T005 Add slow query styles (warning/slow/critical) to LEVEL_STYLES in pgtail_py/colors.py
- [x] T006 [P] Add 'slow' and 'stats' commands to COMMANDS dict in pgtail_py/commands.py
- [x] T007 Add slow_query_config and duration_stats fields to AppState in pgtail_py/cli.py

**Checkpoint**: Foundation ready - all user stories share these components

---

## Phase 2: User Story 1 - Visual Slow Query Detection (Priority: P1) MVP

**Goal**: Parse query duration from log entries and apply visual highlighting based on configurable thresholds (yellow/bold yellow/red bold)

**Independent Test**: Tail a log file containing queries with varying durations and observe that queries exceeding thresholds are visually highlighted with appropriate colors

### Tests for User Story 1

- [x] T008 [P] [US1] Unit test for extract_duration() with ms format in tests/test_slow_query.py
- [x] T009 [P] [US1] Unit test for extract_duration() with seconds format in tests/test_slow_query.py
- [x] T010 [P] [US1] Unit test for extract_duration() with malformed input in tests/test_slow_query.py
- [x] T011 [P] [US1] Unit test for SlowQueryConfig.get_level() threshold logic in tests/test_slow_query.py

### Implementation for User Story 1

- [x] T012 [US1] Implement SlowQueryConfig.get_level(duration_ms) method in pgtail_py/slow_query.py
- [x] T013 [US1] Add format_slow_query_entry() function for styled output in pgtail_py/colors.py
- [x] T014 [US1] Modify tailer display loop to check slow query config and apply styling in pgtail_py/cli.py
- [x] T015 [US1] Implement slow query precedence over regex highlighting in pgtail_py/cli.py
- [x] T016 [US1] Add duration collection to DurationStats when log entry has duration in pgtail_py/cli.py

**Checkpoint**: User Story 1 complete - slow queries are visually highlighted during log tailing

---

## Phase 3: User Story 2 - Custom Threshold Configuration (Priority: P2)

**Goal**: Provide `slow` command to configure thresholds with three numeric arguments, display current config, and disable highlighting

**Independent Test**: Configure custom thresholds via `slow` command and verify subsequent log entries are highlighted according to new thresholds

### Tests for User Story 2

- [x] T017 [P] [US2] Unit test for threshold validation (positive numbers, ascending order) in tests/test_slow_query.py
- [x] T018 [P] [US2] Unit test for SlowQueryConfig.format_thresholds() output in tests/test_slow_query.py

### Implementation for User Story 2

- [x] T019 [US2] Implement validate_thresholds() function in pgtail_py/slow_query.py
- [x] T020 [US2] Implement SlowQueryConfig.format_thresholds() method in pgtail_py/slow_query.py
- [x] T021 [US2] Implement slow_command() handler in pgtail_py/cli.py
- [x] T022 [US2] Handle slow command with three numeric args (enable with thresholds) in pgtail_py/cli.py
- [x] T023 [US2] Handle slow command with no args (display current config) in pgtail_py/cli.py
- [x] T024 [US2] Handle slow off command (disable highlighting) in pgtail_py/cli.py
- [x] T025 [US2] Add error handling for invalid threshold input in pgtail_py/cli.py
- [x] T026 [US2] Add slow command completion for 'off' argument in pgtail_py/commands.py

**Checkpoint**: User Story 2 complete - users can configure, view, and disable slow query thresholds

---

## Phase 4: User Story 3 - Query Duration Statistics (Priority: P3)

**Goal**: Provide `stats` command showing count, average, and percentile breakdown (p50, p95, p99, max) of observed query durations

**Independent Test**: Tail a log with various query durations, then run `stats` command to verify accurate statistical calculations

### Tests for User Story 3

- [x] T027 [P] [US3] Unit test for DurationStats.add() and basic stats (count, avg, min, max) in tests/test_slow_query.py
- [x] T028 [P] [US3] Unit test for DurationStats percentile calculations (p50, p95, p99) in tests/test_slow_query.py
- [x] T029 [P] [US3] Unit test for DurationStats.is_empty() and edge cases in tests/test_slow_query.py

### Implementation for User Story 3

- [x] T030 [US3] Implement DurationStats.add() method with running counters in pgtail_py/slow_query.py
- [x] T031 [US3] Implement DurationStats percentile properties (p50, p95, p99) using statistics.quantiles in pgtail_py/slow_query.py
- [x] T032 [US3] Implement DurationStats.format_summary() method in pgtail_py/slow_query.py
- [x] T033 [US3] Implement stats_command() handler in pgtail_py/cli.py
- [x] T034 [US3] Handle stats command with no data (display helpful message) in pgtail_py/cli.py

**Checkpoint**: User Story 3 complete - users can view query duration statistics

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, integration verification, and documentation

- [ ] T035 [P] Handle edge case: multiple "duration:" patterns in single line in pgtail_py/slow_query.py
- [ ] T036 [P] Handle edge case: negative duration values in pgtail_py/slow_query.py
- [ ] T037 [P] Unit test for edge cases (multiple patterns, negative values) in tests/test_slow_query.py
- [ ] T038 Run make lint and fix any issues
- [ ] T039 Run make test and ensure all tests pass
- [ ] T040 Validate quickstart.md scenarios work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup completion - uses SlowQueryConfig, extract_duration(), styles
- **User Story 2 (Phase 3)**: Depends on Setup completion - uses SlowQueryConfig, validate_thresholds()
- **User Story 3 (Phase 4)**: Depends on Setup completion - uses DurationStats
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) - Core highlighting functionality
- **User Story 2 (P2)**: Can start after Setup (Phase 1) - Configuration commands (independent of US1 display)
- **User Story 3 (P3)**: Can start after Setup (Phase 1) - Statistics (independent of US1/US2)

**Note**: US1, US2, and US3 can be implemented in parallel after Setup completes, but US1 should be prioritized as it's the core MVP.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core logic before CLI handlers
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different functions in same file)
- All tests for a user story marked [P] can run in parallel
- T035, T036, T037 can run in parallel (different edge cases)

---

## Parallel Example: Setup Phase

```bash
# Launch foundation tasks in parallel (different concerns):
Task: "Add SlowQueryConfig dataclass in pgtail_py/slow_query.py"
Task: "Add DurationStats dataclass in pgtail_py/slow_query.py"
Task: "Implement extract_duration() function in pgtail_py/slow_query.py"
Task: "Add 'slow' and 'stats' commands to COMMANDS in pgtail_py/commands.py"
```

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together:
Task: "Unit test for extract_duration() with ms format in tests/test_slow_query.py"
Task: "Unit test for extract_duration() with seconds format in tests/test_slow_query.py"
Task: "Unit test for extract_duration() with malformed input in tests/test_slow_query.py"
Task: "Unit test for SlowQueryConfig.get_level() threshold logic in tests/test_slow_query.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: User Story 1 (T008-T016)
3. **STOP and VALIDATE**: Test slow query highlighting works
4. Demo with `slow 100 500 1000` then `tail 1`

### Incremental Delivery

1. Setup → Foundation ready
2. Add User Story 1 → Test independently → MVP ready!
3. Add User Story 2 → `slow` command fully functional
4. Add User Story 3 → `stats` command available
5. Each story adds value without breaking previous stories

### Single Developer Flow

1. Complete Setup (T001-T007) in order
2. Complete US1 tests (T008-T011), verify they fail
3. Complete US1 implementation (T012-T016), verify tests pass
4. Repeat for US2, then US3
5. Polish phase (T035-T040)

---

## Notes

- [P] tasks = different files or different functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests use pytest per pyproject.toml
- New module slow_query.py follows pattern of existing regex_filter.py
- Colors use prompt_toolkit styles per research.md decisions
- Statistics use Python stdlib statistics.quantiles() - no new dependencies
