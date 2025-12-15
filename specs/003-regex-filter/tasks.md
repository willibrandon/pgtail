# Tasks: Regex Pattern Filtering

**Input**: Design documents from `/specs/003-regex-filter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included as unit tests are part of project quality standards.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Create new module and basic structure

- [x] T001 Create pgtail_py/regex_filter.py with module docstring and imports
- [x] T002 [P] Create tests/test_regex_filter.py with test file structure

---

## Phase 2: Foundational (Core Data Structures)

**Purpose**: Core entities that ALL user stories depend on - MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement FilterType enum in pgtail_py/regex_filter.py
- [x] T004 Implement RegexFilter dataclass with create() and matches() methods in pgtail_py/regex_filter.py
- [x] T005 Implement Highlight dataclass with create() and find_spans() methods in pgtail_py/regex_filter.py
- [x] T006 Implement FilterState dataclass with empty(), has_filters(), should_show() methods in pgtail_py/regex_filter.py
- [x] T007 Implement parse_filter_arg() to parse /pattern/ and /pattern/c syntax in pgtail_py/regex_filter.py
- [x] T008 [P] Write unit tests for FilterType, RegexFilter.create(), RegexFilter.matches() in tests/test_regex_filter.py
- [x] T009 [P] Write unit tests for Highlight.create(), Highlight.find_spans() in tests/test_regex_filter.py
- [x] T010 [P] Write unit tests for FilterState.should_show() with include/exclude/AND logic in tests/test_regex_filter.py
- [x] T011 [P] Write unit tests for parse_filter_arg() including edge cases in tests/test_regex_filter.py
- [x] T012 Run pytest tests/test_regex_filter.py to verify foundation

**Checkpoint**: Foundation ready - FilterState can evaluate any combination of filters

---

## Phase 3: User Story 1 - Include Filter by Pattern (Priority: P1) 🎯 MVP

**Goal**: Users can filter logs to show only lines matching a regex pattern

**Independent Test**: Run `filter /pattern/` and verify only matching lines appear

### Implementation for User Story 1

- [x] T013 [US1] Add regex_state: FilterState field to AppState dataclass in pgtail_py/cli.py
- [x] T014 [US1] Add "filter" to COMMANDS dict with description in pgtail_py/commands.py
- [x] T015 [US1] Implement filter_command() handler for `filter /pattern/` syntax in pgtail_py/cli.py
- [x] T016 [US1] Implement filter status display when `filter` called with no args in pgtail_py/cli.py
- [x] T017 [US1] Add filter command dispatch to handle_command() in pgtail_py/cli.py
- [x] T018 [US1] Integrate FilterState.should_show() into log line processing in pgtail_py/tailer.py
- [x] T019 [US1] Add error handling for invalid regex patterns with helpful messages in pgtail_py/cli.py
- [x] T020 [US1] Update help_command() to include filter command documentation in pgtail_py/cli.py

**Checkpoint**: `filter /pattern/` works - shows only matching lines, `filter` shows status

---

## Phase 4: User Story 2 - Exclude Filter by Pattern (Priority: P2)

**Goal**: Users can exclude lines matching a pattern using `filter -/pattern/`

**Independent Test**: Run `filter -/pattern/` and verify matching lines are hidden

### Implementation for User Story 2

- [x] T021 [US2] Extend filter_command() to handle `-/pattern/` exclude syntax in pgtail_py/cli.py
- [x] T022 [US2] Update filter status display to show exclude filters in pgtail_py/cli.py
- [x] T023 [US2] Test exclude filter precedence (exclude wins over include for same line)

**Checkpoint**: `filter -/pattern/` hides matching lines, works with include filters

---

## Phase 5: User Story 3 - Combine Multiple Filters (Priority: P2)

**Goal**: Users can combine filters with OR (`+/pattern/`) and AND (`&/pattern/`) logic

**Independent Test**: Add multiple filters and verify logical combination works correctly

### Implementation for User Story 3

- [x] T024 [US3] Extend filter_command() to handle `+/pattern/` OR syntax in pgtail_py/cli.py
- [x] T025 [US3] Extend filter_command() to handle `&/pattern/` AND syntax in pgtail_py/cli.py
- [x] T026 [US3] Update filter status display to show all filter types with logic indicators in pgtail_py/cli.py
- [x] T027 [US3] Implement `filter clear` to remove all filters in pgtail_py/cli.py
- [x] T028 [US3] Add completion for filter subcommands (clear) in pgtail_py/commands.py

**Checkpoint**: Multiple filters combine correctly, `filter clear` works, status shows all filters

---

## Phase 6: User Story 4 - Highlight Without Filtering (Priority: P3)

**Goal**: Users can highlight matching text without hiding any lines

**Independent Test**: Run `highlight /pattern/` and verify matched text has yellow background

### Implementation for User Story 4

- [x] T029 [US4] Add HIGHLIGHT_STYLE for yellow background in pgtail_py/colors.py
- [x] T030 [US4] Implement format_log_entry_with_highlights() to apply highlight spans in pgtail_py/colors.py
- [x] T031 [US4] Add "highlight" to COMMANDS dict with description in pgtail_py/commands.py
- [x] T032 [US4] Implement highlight_command() handler for `highlight /pattern/` syntax in pgtail_py/cli.py
- [x] T033 [US4] Implement highlight status display when `highlight` called with no args in pgtail_py/cli.py
- [x] T034 [US4] Implement `highlight clear` to remove highlights in pgtail_py/cli.py
- [x] T035 [US4] Add highlight command dispatch to handle_command() in pgtail_py/cli.py
- [x] T036 [US4] Integrate highlight rendering into log output in pgtail_py/cli.py
- [x] T037 [US4] Update help_command() to include highlight command documentation in pgtail_py/cli.py

**Checkpoint**: `highlight /pattern/` shows yellow background on matches, all lines still visible

---

## Phase 7: User Story 5 - View and Manage Active Filters (Priority: P3)

**Goal**: Users can view and clear all active filters and highlights

**Independent Test**: Add filters/highlights, run `filter`/`highlight` to view, `filter clear`/`highlight clear` to remove

### Implementation for User Story 5

- [x] T038 [US5] Enhance filter status display to show pattern, type, and case sensitivity in pgtail_py/cli.py
- [x] T039 [US5] Enhance highlight status display to show pattern and case sensitivity in pgtail_py/cli.py
- [x] T040 [US5] Add completion for highlight subcommands (clear) in pgtail_py/commands.py

**Checkpoint**: Status commands show complete filter/highlight information

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation

- [x] T041 [P] Run ruff check pgtail_py/ and fix any lint issues
- [x] T042 [P] Verify all new functions have type hints
- [x] T043 Run full test suite: pytest tests/ -v
- [x] T044 Manual test: filter /pattern/, filter -/pattern/, filter +/pattern/, filter &/pattern/
- [x] T045 Manual test: highlight /pattern/, filter and highlight interaction
- [x] T046 Manual test: filter clear, highlight clear, status display
- [x] T047 Manual test: Invalid regex patterns show helpful error messages
- [x] T048 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1): Can proceed after Foundational
  - US2 (P2): Can proceed after Foundational (builds on US1 code paths)
  - US3 (P2): Can proceed after US2 (extends filter command)
  - US4 (P3): Can proceed after Foundational (independent highlight feature)
  - US5 (P3): Can proceed after US3 and US4 (enhances status displays)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational - Core filter functionality
- **User Story 2 (P2)**: After US1 - Extends filter command with exclude
- **User Story 3 (P2)**: After US2 - Extends filter command with OR/AND
- **User Story 4 (P3)**: After Foundational - Independent highlight feature
- **User Story 5 (P3)**: After US3 and US4 - Enhances status displays

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
```
T008, T009, T010, T011 can run in parallel (different test functions)
```

**User Story Parallelism**:
- US1 and US4 could proceed in parallel (filter vs highlight are separate commands)
- US5 must wait for US3 and US4

---

## Parallel Example: Foundational Tests

```bash
# Launch all test tasks in parallel:
Task: "Write unit tests for FilterType, RegexFilter in tests/test_regex_filter.py"
Task: "Write unit tests for Highlight in tests/test_regex_filter.py"
Task: "Write unit tests for FilterState.should_show() in tests/test_regex_filter.py"
Task: "Write unit tests for parse_filter_arg() in tests/test_regex_filter.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test `filter /pattern/` independently
5. Deploy/demo if ready - basic regex filtering works!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → `filter /pattern/` works → MVP!
3. Add User Story 2 → `filter -/pattern/` works
4. Add User Story 3 → OR/AND/clear works
5. Add User Story 4 → `highlight /pattern/` works
6. Add User Story 5 → Enhanced status displays
7. Polish → Production ready

### Recommended Order

Given the dependencies, implement in this order:
1. Phase 1-2: Foundation (T001-T012)
2. Phase 3: US1 Include Filter (T013-T020) - **MVP**
3. Phase 4: US2 Exclude Filter (T021-T023)
4. Phase 5: US3 Multiple Filters (T024-T028)
5. Phase 6: US4 Highlight (T029-T037)
6. Phase 7: US5 Management (T038-T040)
7. Phase 8: Polish (T041-T048)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
