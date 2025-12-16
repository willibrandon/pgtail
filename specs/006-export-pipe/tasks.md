# Tasks: Export Logs and Pipe to External Commands

**Input**: Design documents from `/specs/006-export-pipe/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in feature specification. Implementation-only tasks below.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Project structure**: `pgtail_py/` for source, `tests/` for tests
- Uses existing single-project structure from plan.md

---

## Phase 1: Setup

**Purpose**: Create the new export module and foundational types

- [x] T001 Create export module with ExportFormat enum in pgtail_py/export.py
- [x] T002 Add ExportOptions dataclass with path, format, follow, append, since fields in pgtail_py/export.py
- [x] T003 [P] Add PipeOptions dataclass with command and format fields in pgtail_py/export.py
- [x] T004 [P] Add parse_since() function for relative time parsing (1h, 30m, 2d) in pgtail_py/export.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core formatting functions that ALL user stories depend on

**⚠️ CRITICAL**: User story implementation cannot begin until these formatting functions exist

- [x] T005 Implement format_text_entry() returning raw log line in pgtail_py/export.py
- [x] T006 [P] Implement format_json_entry() returning JSONL with ISO 8601 timestamps in pgtail_py/export.py
- [x] T007 [P] Implement format_csv_row() using csv module with QUOTE_MINIMAL in pgtail_py/export.py
- [x] T008 Implement format_entry() dispatcher that routes to format-specific functions in pgtail_py/export.py
- [x] T009 Implement get_filtered_entries() generator applying level/regex filters in pgtail_py/export.py
- [x] T010 Add ensure_parent_dirs() using Path.mkdir(parents=True) in pgtail_py/export.py

**Checkpoint**: Foundation ready - export formatting and filtering infrastructure complete

---

## Phase 3: User Story 1 - Export Filtered Logs to File (Priority: P1) 🎯 MVP

**Goal**: Basic export command that writes filtered log entries to a text file

**Independent Test**: Apply level filters (`levels ERROR`), run `export errors.log`, verify file contains only ERROR entries

### Implementation for User Story 1

- [ ] T011 [US1] Implement confirm_overwrite() prompt using prompt_toolkit in pgtail_py/export.py
- [ ] T012 [US1] Implement export_to_file() core function (opens file, streams entries, returns count) in pgtail_py/export.py
- [ ] T013 [US1] Add export_command() handler in pgtail_py/cli.py parsing filename and --append flag
- [ ] T014 [US1] Add argument parsing for export command (extract filename, detect --append) in pgtail_py/cli.py
- [ ] T015 [US1] Integrate export_command into handle_command() dispatch in pgtail_py/cli.py
- [ ] T016 [US1] Add 'export' to COMMANDS dict with description in pgtail_py/commands.py
- [ ] T017 [P] [US1] Add export command completion (--append flag) in pgtail_py/commands.py
- [ ] T018 [US1] Add export to help_command() output in pgtail_py/cli.py

**Checkpoint**: User Story 1 complete - `export file.log` works with level/regex filters and overwrite confirmation

---

## Phase 4: User Story 2 - Export in JSON/CSV Formats (Priority: P2)

**Goal**: Support --format option for JSON and CSV structured exports

**Independent Test**: Run `export --format json logs.json`, verify each line is valid JSON with timestamp/level/pid/message fields

### Implementation for User Story 2

- [ ] T019 [US2] Add --format argument parsing to export_command in pgtail_py/cli.py
- [ ] T020 [US2] Pass format parameter through to export_to_file() in pgtail_py/cli.py
- [ ] T021 [US2] Write CSV header row when format=csv and not append mode in pgtail_py/export.py
- [ ] T022 [US2] Add --format completion (text, json, csv values) to export completer in pgtail_py/commands.py
- [ ] T023 [US2] Add --since argument parsing to export_command in pgtail_py/cli.py
- [ ] T024 [US2] Filter entries by since timestamp in get_filtered_entries() in pgtail_py/export.py
- [ ] T025 [US2] Update help text with --format and --since options in pgtail_py/cli.py

**Checkpoint**: User Story 2 complete - `export --format json logs.json` and `export --format csv --since 1h data.csv` work

---

## Phase 5: User Story 3 - Pipe Logs to External Commands (Priority: P2)

**Goal**: Stream filtered entries to external processes via subprocess

**Independent Test**: Run `pipe wc -l`, verify count matches number of filtered entries

### Implementation for User Story 3

- [ ] T026 [US3] Implement pipe_to_command() using subprocess.Popen with stdin pipe in pgtail_py/export.py
- [ ] T027 [US3] Handle BrokenPipeError for commands that exit early (head, etc.) in pgtail_py/export.py
- [ ] T028 [US3] Add pipe_command() handler in pgtail_py/cli.py
- [ ] T029 [US3] Parse pipe arguments (extract --format and command string) in pgtail_py/cli.py
- [ ] T030 [US3] Display subprocess stdout and handle stderr/exit code errors in pgtail_py/cli.py
- [ ] T031 [US3] Integrate pipe_command into handle_command() dispatch in pgtail_py/cli.py
- [ ] T032 [US3] Add 'pipe' to COMMANDS dict with description in pgtail_py/commands.py
- [ ] T033 [P] [US3] Add pipe command completion (--format flag) in pgtail_py/commands.py
- [ ] T034 [US3] Add pipe to help_command() output in pgtail_py/cli.py

**Checkpoint**: User Story 3 complete - `pipe grep pattern` and `pipe --format json jq '.message'` work

---

## Phase 6: User Story 4 - Continuous Export (Priority: P3)

**Goal**: Real-time export that continues until Ctrl+C, like `tail -f | tee`

**Independent Test**: Run `export --follow test.log`, generate new log entries, stop with Ctrl+C, verify all entries captured

### Implementation for User Story 4

- [ ] T035 [US4] Add --follow argument parsing to export_command in pgtail_py/cli.py
- [ ] T036 [US4] Implement follow_export() that loops with tailer and writes entries in pgtail_py/export.py
- [ ] T037 [US4] Display "Exporting to file (Ctrl+C to stop)" message when follow mode starts in pgtail_py/cli.py
- [ ] T038 [US4] Handle KeyboardInterrupt to stop follow mode and report total count in pgtail_py/cli.py
- [ ] T039 [US4] Display entries on screen while writing to file (tee behavior) in pgtail_py/cli.py
- [ ] T040 [US4] Add --follow completion to export completer in pgtail_py/commands.py
- [ ] T041 [US4] Update help text with --follow option in pgtail_py/cli.py

**Checkpoint**: User Story 4 complete - `export --follow test.log` captures logs in real-time with screen echo

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and documentation

- [ ] T042 [P] Add error handling for permission denied (catch PermissionError) in pgtail_py/export.py
- [ ] T043 [P] Add error handling for disk full (catch OSError with ENOSPC) in pgtail_py/export.py
- [ ] T044 [P] Add error handling for command not found in pipe_to_command() in pgtail_py/export.py
- [ ] T045 Handle empty export (0 entries) with clear message in pgtail_py/cli.py
- [ ] T046 Validate --follow and --append are mutually exclusive in export_command in pgtail_py/cli.py
- [ ] T047 Run make lint and fix any linting issues
- [ ] T048 Run make test to verify existing tests still pass
- [ ] T049 Manual test: quickstart.md scenarios validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) should be completed first as MVP
  - US2-US4 can proceed after US1 or in parallel
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Builds on US1 export_to_file() but independently testable
- **User Story 3 (P2)**: Can start after Foundational - Completely independent from US1/US2
- **User Story 4 (P3)**: Can start after Foundational - Uses export_to_file() from US1 but independently testable

### Within Each User Story

- Implementation before command handlers
- Command handlers before help/completion updates
- Validate story works before moving to next

### Parallel Opportunities

- T003, T004 can run in parallel (different functions, same file but no conflicts)
- T006, T007 can run in parallel (different format functions)
- T017 can run in parallel with T018 (commands.py vs cli.py)
- T033 can run in parallel with other US3 cli.py tasks
- T042, T043, T044 can all run in parallel (different error scenarios)

---

## Parallel Example: User Story 1

```bash
# After T012 (export_to_file) is complete, these can run in parallel:
# - T017 (completion in commands.py)
# - T018 (help text in cli.py)
# Because they modify different files with no dependencies
```

---

## Parallel Example: User Story 3

```bash
# T26 and T27 must be sequential (same function)
# But T33 (commands.py) can run in parallel with T28-T34 (cli.py tasks)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010)
3. Complete Phase 3: User Story 1 (T011-T018)
4. **STOP and VALIDATE**: Test `export file.log` with filters
5. Deploy/demo if ready - basic export functionality is usable

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. Add User Story 1 → `export file.log` works → MVP!
3. Add User Story 2 → `export --format json` works
4. Add User Story 3 → `pipe grep pattern` works
5. Add User Story 4 → `export --follow` works
6. Polish → Error handling, edge cases

### Single Developer Strategy

Follow phases in order:
1. Phase 1 → Phase 2 → Phase 3 (MVP) → validate
2. Phase 4 → validate
3. Phase 5 → validate
4. Phase 6 → validate
5. Phase 7 → final validation

---

## Notes

- All export functions use generators for memory efficiency (never buffer all entries)
- Existing LogTailer already handles log rotation - reuse for --follow mode
- Use Python stdlib only (json, csv, subprocess, pathlib) - no new dependencies
- Follow existing code patterns in cli.py for command handlers
- Follow existing patterns in commands.py for completers
- Total tasks: 49
- Per-story counts: Setup=4, Foundational=6, US1=8, US2=7, US3=9, US4=7, Polish=8
