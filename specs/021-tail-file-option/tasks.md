# Tasks: Tail Arbitrary Log Files

**Input**: Design documents from `/specs/021-tail-file-option/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included in Phase 7 (Polish) as the spec does not explicitly request TDD.

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

**Purpose**: Create path validation utilities that all user stories depend on

- [X] T001 Create validate_file_path() function in pgtail_py/cli_utils.py
- [X] T002 [P] Add validate_tail_args() mutual exclusivity check in pgtail_py/cli_utils.py
- [X] T003 [P] Add current_file_path field to AppState dataclass in pgtail_py/cli.py
- [X] T085 [P] Implement tilde (~) expansion in validate_file_path() in pgtail_py/cli_utils.py

---

## Phase 2: Foundational (Status Bar & TailApp Changes)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add filename field to TailStatus dataclass in pgtail_py/tail_status.py
- [X] T005 [P] Add file_unavailable field to TailStatus in pgtail_py/tail_status.py
- [X] T006 [P] Add detected_from_content field to TailStatus in pgtail_py/tail_status.py
- [X] T007 Implement set_file_source() method in pgtail_py/tail_status.py
- [X] T008 Implement set_file_unavailable() method in pgtail_py/tail_status.py
- [X] T009 Update format_rich() to show filename when no instance in pgtail_py/tail_status.py
- [X] T010 [P] Update format_plain() to show filename when no instance in pgtail_py/tail_status.py
- [X] T011 Make instance parameter optional (Instance | None) in TailApp.__init__ in pgtail_py/tail_textual.py
- [X] T012 Add _instance_detected flag to TailApp in pgtail_py/tail_textual.py
- [X] T013 Update TailApp.on_mount() to handle instance=None case in pgtail_py/tail_textual.py
- [X] T014 Add DetectedInstanceInfo dataclass in pgtail_py/tail_textual.py
- [X] T015 Implement VERSION_PATTERN and PORT_PATTERN regex constants in pgtail_py/tail_textual.py
- [X] T016 Implement _detect_instance_info() method to scan log content in pgtail_py/tail_textual.py
- [X] T083 [P] Implement file_only factory method or adjust Instance for file-only use in pgtail_py/instance.py
- [X] T087 [P] Implement PORT_SOCKET_PATTERN for Unix socket port detection in pgtail_py/tail_textual.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 3 - CLI-Level File Tailing (Priority: P0 - MANDATORY)

**Goal**: Users can run `pgtail tail --file <path>` from the shell with full flag support

**Independent Test**: Run `pgtail tail --file ./test.log --since 5m` from command line

### Implementation for User Story 3

- [X] T017 [US3] Add --file/-f option to tail command in pgtail_py/cli_main.py
- [X] T018 [US3] Make instance_id argument optional (default=None) in pgtail_py/cli_main.py
- [X] T019 [US3] Add mutual exclusivity check (--file vs instance_id) in pgtail_py/cli_main.py
- [X] T020 [US3] Add path validation (exists, is_file, readable) in pgtail_py/cli_main.py
- [X] T021 [US3] Implement file-only tail mode entry (skip instance lookup) in pgtail_py/cli_main.py
- [X] T022 [US3] Call TailApp.run_tail_mode with instance=None when using --file in pgtail_py/cli_main.py
- [X] T023 [US3] Set status bar filename from log_path.name in pgtail_py/cli_main.py
- [X] T024 [US3] Update help text to document --file option in pgtail_py/cli_main.py

**Checkpoint**: At this point, `pgtail tail --file <path>` works from command line

---

## Phase 4: User Story 4 - REPL-Level File Tailing (Priority: P0 - MANDATORY)

**Goal**: Users can run `tail --file <path>` from the pgtail REPL

**Independent Test**: Enter REPL, run `tail --file ./test.log`

### Implementation for User Story 4

- [X] T025 [US4] Add --file argument parsing in tail_command() in pgtail_py/cli_core.py
- [X] T026 [US4] Add mutual exclusivity check (--file vs instance ID) in pgtail_py/cli_core.py
- [X] T027 [US4] Add path resolution (relative → absolute) using Path.resolve() in pgtail_py/cli_core.py
- [X] T028 [US4] Add path validation with error messages in pgtail_py/cli_core.py
- [X] T029 [US4] Implement tail_file_mode() function for file-only tailing in pgtail_py/cli_core.py
- [X] T030 [US4] Call TailApp.run_tail_mode with instance=None in tail_file_mode() in pgtail_py/cli_core.py
- [X] T031 [US4] Set state.current_file_path when tailing a file in pgtail_py/cli_core.py
- [X] T032 [US4] Clear state.current_file_path when stopping in pgtail_py/cli_core.py
- [X] T033 [US4] Handle `tail --file` without path argument (usage error) in pgtail_py/cli_core.py
- [X] T034 [US4] Update help_command() to document --file option in pgtail_py/cli_core.py

**Checkpoint**: At this point, `tail --file <path>` works from REPL

---

## Phase 5: User Story 1 - Tail pg_regress Test Logs (Priority: P0 - MANDATORY)

**Goal**: All filters work identically for file-based tailing (level, regex, time, slow, field)

**Independent Test**: Create pg_regress-style log, tail with `--file`, apply filters

**Note**: Core file tailing already works from US3/US4. This phase ensures filter parity.

### Implementation for User Story 1

- [X] T035 [US1] Verify LogTailer works with arbitrary paths (no changes needed) in pgtail_py/tailer.py
- [X] T036 [US1] Verify format auto-detection works for file-based tailing in pgtail_py/format_detector.py
- [X] T037 [US1] Verify level filter applies to file-based entries in pgtail_py/tail_textual.py
- [X] T038 [US1] Verify regex filter applies to file-based entries in pgtail_py/tail_textual.py
- [X] T039 [US1] Verify time filter applies to file-based entries in pgtail_py/tail_textual.py
- [X] T040 [US1] Verify field filter applies to file-based entries in pgtail_py/tail_textual.py
- [X] T041 [US1] Verify slow query highlighting applies to file-based entries in pgtail_py/tail_textual.py
- [X] T042 [US1] Ensure error/warning counts work for file-based tailing in pgtail_py/tail_textual.py
- [X] T043 [US1] Ensure notifications work for file-based tailing in pgtail_py/tail_textual.py
- [X] T084 [US1] Verify/test UTF-8 encoding fallback for malformed input in pgtail_py/parser.py
- [X] T088 [US1] Verify ErrorStats and ConnectionStats work with file-based tailing in pgtail_py/tail_textual.py

**Checkpoint**: All filters work identically for file-based tailing

---

## Phase 6: User Story 2 - Tail Archived/Downloaded Logs (Priority: P0 - MANDATORY)

**Goal**: CSV and JSON format logs are auto-detected and parsed correctly when tailing files

**Independent Test**: Create CSV and JSON format logs, tail with `--file`, verify field access

### Implementation for User Story 2

- [X] T044 [US2] Verify CSV format auto-detection from file content in pgtail_py/format_detector.py
- [X] T045 [US2] Verify JSON format auto-detection from file content in pgtail_py/format_detector.py
- [X] T046 [US2] Verify field filtering (app=, db=, user=) works for CSV files in pgtail_py/field_filter.py
- [X] T047 [US2] Verify field filtering works for JSON files in pgtail_py/field_filter.py
- [X] T048 [US2] Handle static files that are not actively written to (existing behavior) in pgtail_py/tailer.py
- [X] T049 [US2] Verify display mode (compact, full, custom) works for file-based CSV/JSON in pgtail_py/display.py

**Checkpoint**: Archived CSV/JSON logs can be analyzed with full filtering

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Completions, edge cases, tests, and documentation

### Tab Completion

- [X] T050 [P] Add --file to tail command completions in pgtail_py/commands.py
- [X] T051 [P] Add PathCompleter for --file argument in pgtail_py/commands.py

### Edge Cases

- [X] T052 Handle file deletion during tailing (wait indefinitely) in pgtail_py/tail_textual.py
- [X] T053 [P] Handle symlinks (Path.resolve() follows them) in pgtail_py/cli_utils.py
- [X] T054 [P] Handle paths with spaces and special characters in pgtail_py/cli_utils.py
- [X] T055 [P] Handle empty files (enter tail mode, wait for content) in pgtail_py/tailer.py
- [X] T056 Handle files with no valid PostgreSQL entries (text fallback) in pgtail_py/parser.py

### Instance Detection from Log Content

- [X] T057 Implement async instance info detection during first 50 entries in pgtail_py/tail_textual.py
- [X] T058 Update status bar when version/port detected from content in pgtail_py/tail_textual.py

### Tests

- [X] T059 [P] Create unit tests for validate_file_path() in tests/unit/test_tail_file.py
- [X] T060 [P] Create unit tests for validate_tail_args() in tests/unit/test_tail_file.py
- [X] T061 [P] Create unit tests for TailStatus.set_file_source() in tests/unit/test_tail_file.py
- [X] T062 [P] Create unit tests for TailStatus filename display in tests/unit/test_tail_file.py
- [X] T063 [P] Create unit tests for instance detection patterns in tests/unit/test_tail_file.py
- [X] T064 [P] Create integration test: tail --file with relative path in tests/integration/test_tail_file_e2e.py
- [X] T065 [P] Create integration test: tail --file with absolute path in tests/integration/test_tail_file_e2e.py
- [X] T066 [P] Create integration test: tail --file --since combined in tests/integration/test_tail_file_e2e.py
- [X] T067 [P] Create integration test: tail --file error cases in tests/integration/test_tail_file_e2e.py
- [X] T068 [P] Create integration test: file-based CSV format detection in tests/integration/test_tail_file_e2e.py
- [X] T069 [P] Create integration test: file-based JSON format detection in tests/integration/test_tail_file_e2e.py
- [X] T086 [P] Create integration test: tail --file without path argument (usage error) in tests/integration/test_tail_file_e2e.py
- [X] T090 [P] Create integration test: glob pattern expansion in tests/integration/test_tail_file_e2e.py (placeholder - Phase 8)
- [X] T091 [P] Create integration test: glob pattern with no matches (error) in tests/integration/test_tail_file_e2e.py (placeholder - Phase 8)
- [X] T092 [P] Create integration test: multiple --file arguments in tests/integration/test_tail_file_e2e.py (placeholder - Phase 9)
- [X] T093 [P] Create integration test: multi-file timestamp interleaving in tests/integration/test_tail_file_e2e.py (placeholder - Phase 9)
- [X] T094 [P] Create integration test: stdin pipe input in tests/integration/test_tail_file_e2e.py (placeholder - Phase 10)
- [X] T095 [P] Create integration test: stdin EOF handling in tests/integration/test_tail_file_e2e.py (placeholder - Phase 10)
- [X] T096 [P] Create unit tests for glob pattern matching in tests/unit/test_tail_file.py (placeholder - Phase 8)
- [X] T097 [P] Create unit tests for multi-file tailer in tests/unit/test_tail_file.py (placeholder - Phase 9)
- [X] T098 [P] Create unit tests for stdin reader in tests/unit/test_tail_file.py (placeholder - Phase 10)

### Documentation

- [X] T070 Run make lint and fix any issues
- [X] T071 Run make test and ensure all tests pass
- [X] T072 Validate quickstart.md scenarios work correctly

---

## Phase 8: User Story 5 - Glob Pattern Tailing (Priority: P0 - MANDATORY)

**Goal**: Users can tail multiple log files matching a glob pattern

**Independent Test**: Create multiple log files matching `*.log`, run `tail --file "*.log"`

### Implementation for User Story 5

- [X] T073 [US5] Implement glob pattern expansion for --file in pgtail_py/cli_main.py
- [X] T074 [US5] Handle "No files match pattern" error in pgtail_py/cli_main.py
- [X] T075 [US5] Implement multi-file interleaving by timestamp in pgtail_py/tailer.py
- [X] T076 [US5] Add source file indicator to log entries in pgtail_py/tail_rich.py
- [X] T089 [US5] Add dynamic file watching to include newly created files matching glob pattern in pgtail_py/tailer.py

---

## Phase 9: User Story 6 - Multiple Explicit Files (Priority: P0 - MANDATORY)

**Goal**: Users can tail multiple specific files simultaneously

**Independent Test**: Run `tail --file a.log --file b.log` with two log files

### Implementation for User Story 6

- [X] T077 [US6] Support multiple --file arguments in pgtail_py/cli_main.py
- [X] T078 [US6] Independent format detection per file in pgtail_py/tailer.py
- [X] T079 [US6] Source file indicator in display in pgtail_py/tail_rich.py

---

## Phase 10: User Story 7 - Stdin Pipe Support (Priority: P0 - MANDATORY)

**Goal**: Users can pipe log data into pgtail from stdin

**Independent Test**: Run `cat log.gz | gunzip | pgtail tail --stdin`

### Implementation for User Story 7

- [X] T080 [US7] Add --stdin flag to tail command in pgtail_py/cli_main.py
- [X] T081 [US7] Implement stdin reader in pgtail_py/stdin_reader.py
- [X] T082 [US7] Handle EOF gracefully (exit tail mode) in pgtail_py/tail_textual.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US3 (CLI) and US4 (REPL) can proceed in parallel
  - US1 (Filters) depends on US3 or US4 being complete
  - US2 (Archived) depends on US1 being complete
- **Polish (Phase 7)**: Depends on US1-US4 being complete
- **Phase 8-10 (US5-US7)**: MANDATORY - depend on Phase 7 completion

### User Story Dependencies

- **User Story 3 (CLI)**: Can start after Foundational (Phase 2)
- **User Story 4 (REPL)**: Can start after Foundational (Phase 2) - parallel with US3
- **User Story 1 (Filters)**: Depends on US3 or US4 (basic file tailing must work first)
- **User Story 2 (Archived)**: Depends on US1 (filters must work for CSV/JSON)
- **User Story 5 (Glob Patterns)**: Depends on US2 completion (multi-file needs single-file working)
- **User Story 6 (Multiple Files)**: Can proceed in parallel with US5 after US2
- **User Story 7 (Stdin)**: Can proceed in parallel with US5/US6 after US2

### Within Each User Story

- Path validation before tailing
- Status bar setup before display
- Core implementation before integration

### Parallel Opportunities

- T002 and T003 can run in parallel in Phase 1
- T005 and T006 can run in parallel in Phase 2
- T009 and T010 can run in parallel in Phase 2
- US3 and US4 can run in parallel (different files: cli_main.py vs cli_core.py)
- All test tasks (T059-T069) can run in parallel
- All tab completion tasks (T050-T051) can run in parallel

---

## Parallel Example: User Story 3 (CLI)

```bash
# After Phase 2 completion, launch CLI implementation:
# These modify different sections of cli_main.py and can be done sequentially quickly

Task T017: Add --file/-f option
Task T018: Make instance_id optional
Task T019: Add mutual exclusivity check
Task T020: Add path validation
Task T021: Implement file-only tail mode entry
Task T022: Call TailApp with instance=None
Task T023: Set status bar filename
Task T024: Update help text
```

---

## Parallel Example: Tests (Phase 7)

```bash
# Launch all unit tests in parallel (different test functions):
Task T059: "Unit tests for validate_file_path()"
Task T060: "Unit tests for validate_tail_args()"
Task T061: "Unit tests for TailStatus.set_file_source()"
Task T062: "Unit tests for TailStatus filename display"
Task T063: "Unit tests for instance detection patterns"

# Launch all integration tests in parallel (different test scenarios):
Task T064: "Integration test: relative path"
Task T065: "Integration test: absolute path"
Task T066: "Integration test: combined flags"
Task T067: "Integration test: error cases"
Task T068: "Integration test: CSV format"
Task T069: "Integration test: JSON format"
```

---

## Implementation Strategy

### Full Implementation (All User Stories 1-7 - MANDATORY)

1. Complete Phase 1: Setup (T001-T003, T085)
2. Complete Phase 2: Foundational (T004-T016, T083, T087)
3. Complete Phase 3: User Story 3 - CLI (T017-T024)
4. **CHECKPOINT**: Test `pgtail tail --file <path>` from command line
5. Complete Phase 4: User Story 4 - REPL (T025-T034)
6. **CHECKPOINT**: Test `tail --file <path>` from REPL
7. Complete Phase 5: User Story 1 - Filters (T035-T043, T084, T088)
8. **CHECKPOINT**: All filters work identically for file-based tailing
9. Complete Phase 6: User Story 2 - Archived (T044-T049)
10. **CHECKPOINT**: CSV/JSON format logs work correctly
11. Complete Phase 7: Polish (T050-T072, T086)
12. **CHECKPOINT**: All tests pass, docs validated
13. Complete Phase 8: User Story 5 - Glob Patterns (T073-T076, T089)
14. **CHECKPOINT**: Glob patterns tail multiple files correctly
15. Complete Phase 9: User Story 6 - Multiple Files (T077-T079)
16. **CHECKPOINT**: Multiple explicit files work correctly
17. Complete Phase 10: User Story 7 - Stdin (T080-T082)
18. **FINAL VALIDATION**: All features complete, all tests pass

### Incremental Delivery (ALL PHASES MANDATORY)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 3 (CLI) → Test independently → `pgtail tail --file` works
3. Add User Story 4 (REPL) → Test independently → REPL `tail --file` works
4. Add User Story 1 (Filters) → Test independently → All filters work
5. Add User Story 2 (Archived) → Test independently → CSV/JSON works
6. Add Polish → Tests pass, docs validated
7. Add User Story 5 (Glob) → Test independently → Glob patterns work
8. Add User Story 6 (Multi-file) → Test independently → Multiple files work
9. Add User Story 7 (Stdin) → Test independently → Stdin pipe works

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 3 (CLI)
   - Developer B: User Story 4 (REPL)
3. After US3/US4:
   - Developer A: User Story 1 (Filters)
   - Developer B: Tests (T059-T069)
4. Developer A: User Story 2 (Archived)
5. After US2:
   - Developer A: User Story 5 (Glob Patterns)
   - Developer B: User Story 6 (Multiple Files)
6. Developer A: User Story 7 (Stdin)
7. Both: Final polish and validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **ALL USER STORIES (US1-US7) ARE MANDATORY P0** - no deferral permitted

## Task Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Phase 1: Setup | 4 | 3 |
| Phase 2: Foundational | 15 | 6 |
| Phase 3: US3 (CLI) | 8 | 0 |
| Phase 4: US4 (REPL) | 10 | 0 |
| Phase 5: US1 (Filters) | 11 | 0 |
| Phase 6: US2 (Archived) | 6 | 0 |
| Phase 7: Polish (Tests + Docs) | 33 | 26 |
| Phase 8: US5 (Glob Patterns) | 5 | 0 |
| Phase 9: US6 (Multiple Files) | 3 | 0 |
| Phase 10: US7 (Stdin) | 3 | 0 |
| **TOTAL (ALL MANDATORY)** | **98** | **35** |
