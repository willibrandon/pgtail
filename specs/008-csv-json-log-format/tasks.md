# Tasks: CSV and JSON Log Format Support

**Input**: Design documents from `/specs/008-csv-json-log-format/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project root**: `pgtail_py/` for source, `tests/` for tests
- Based on existing project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module files and shared enums

- [x] T001 Create LogFormat enum in pgtail_py/format_detector.py with TEXT, CSV, JSON values
- [x] T002 [P] Create empty parser_csv.py module in pgtail_py/parser_csv.py with docstring and CSV_FIELD_ORDER constant
- [x] T003 [P] Create empty parser_json.py module in pgtail_py/parser_json.py with docstring and JSON_FIELD_MAP constant

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend LogEntry dataclass and create format detection - required before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Extend LogEntry dataclass in pgtail_py/parser.py with format field and all 26+ extended fields from data-model.md
- [x] T005 Add get_field(), available_fields(), and to_dict() methods to LogEntry in pgtail_py/parser.py
- [x] T006 Implement detect_format() function in pgtail_py/format_detector.py per contracts/format_detector.md
- [x] T007 Implement is_valid_csv_log() helper function in pgtail_py/format_detector.py
- [x] T008 Implement is_valid_json_log() helper function in pgtail_py/format_detector.py
- [x] T009 Implement detect_format_from_file() function in pgtail_py/format_detector.py

**Checkpoint**: Foundation ready - LogEntry extended and format detection working ✅

---

## Phase 3: User Story 1 - Auto-Detection of Log Format (Priority: P1) 🎯 MVP

**Goal**: Pgtail automatically detects CSV, JSON, or text format and parses accordingly without configuration

**Independent Test**: Point pgtail at log files of each format and verify correct detection and parsing

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement parse_csv_line() function in pgtail_py/parser_csv.py per contracts/parser.md
- [x] T011 [P] [US1] Implement parse_json_line() function in pgtail_py/parser_json.py per contracts/parser.md
- [x] T012 [US1] Update parse_log_line() in pgtail_py/parser.py to accept format parameter and dispatch to appropriate parser
- [x] T013 [US1] Add _detected_format attribute and _detect_format_if_needed() method to LogTailer class in pgtail_py/tailer.py
- [x] T014 [US1] Update LogTailer._read_new_lines() in pgtail_py/tailer.py to detect format on first line and pass to parser
- [x] T015 [US1] Add format property to LogTailer class in pgtail_py/tailer.py
- [x] T016 [US1] Handle format re-detection on log rotation in LogTailer._check_rotation() in pgtail_py/tailer.py
- [x] T017 [US1] Update CLI to display detected format message when tailing starts in pgtail_py/cli_core.py

**Checkpoint**: User Story 1 complete - auto-detection works for all three formats ✅

---

## Phase 4: User Story 2 - Rich Error Display (Priority: P2)

**Goal**: Display enhanced error information (SQL state, application, query) from structured logs

**Independent Test**: Generate errors in PostgreSQL with csvlog/jsonlog and verify all fields appear in output

### Implementation for User Story 2

- [x] T018 [P] [US2] Create DisplayMode enum in pgtail_py/display.py with COMPACT, FULL, CUSTOM values
- [x] T019 [P] [US2] Create OutputFormat enum in pgtail_py/display.py with TEXT, JSON values
- [x] T020 [US2] Implement DisplayState class in pgtail_py/display.py per contracts/display.md
- [x] T021 [US2] Implement format_entry_compact() in pgtail_py/display.py with SQL state code support
- [x] T022 [US2] Implement format_entry_full() in pgtail_py/display.py showing all fields with labels
- [x] T023 [US2] Implement format_entry() dispatcher in pgtail_py/display.py
- [x] T024 [US2] Add display_state attribute to AppState in pgtail_py/cli.py
- [x] T025 [US2] Update entry printing in CLI to use new display formatting in pgtail_py/cli_core.py

**Checkpoint**: User Story 2 complete - rich error display works in compact and full modes ✅

---

## Phase 5: User Story 3 - Display Mode Control (Priority: P2)

**Goal**: Users can switch between compact, full, and custom field display modes

**Independent Test**: Switch display modes during active tailing and verify output format changes

### Implementation for User Story 3

- [x] T026 [P] [US3] Implement format_entry_custom() in pgtail_py/display.py for user-selected fields
- [x] T027 [P] [US3] Add VALID_DISPLAY_FIELDS constant and get_valid_display_fields() in pgtail_py/display.py
- [x] T028 [US3] Add handle_display() command handler in pgtail_py/cli_core.py per contracts/commands.md
- [x] T029 [US3] Add "display" command to COMMANDS dict in pgtail_py/commands.py with compact/full/fields completions
- [x] T030 [US3] Add DISPLAY_FIELDS constant to pgtail_py/commands.py for field name autocomplete
- [x] T031 [US3] Update PgtailCompleter in pgtail_py/commands.py to provide field completions for display command
- [x] T032 [US3] Wire handle_display() into command dispatch in pgtail_py/cli.py

**Checkpoint**: User Story 3 complete - display command works with all three modes ✅

---

## Phase 6: User Story 4 - Field-Based Filtering (Priority: P3)

**Goal**: Filter log entries by field values (app=, db=, user=) for structured formats

**Independent Test**: Generate logs from multiple applications/databases and verify filters work

### Implementation for User Story 4

- [x] T033 [P] [US4] Create FieldFilter frozen dataclass in pgtail_py/field_filter.py per contracts/field_filter.md
- [x] T034 [P] [US4] Add FIELD_ALIASES and FIELD_ATTRIBUTES constants in pgtail_py/field_filter.py
- [x] T035 [US4] Implement resolve_field_name() function in pgtail_py/field_filter.py
- [x] T036 [US4] Implement FieldFilterState class with add/remove/clear/matches methods in pgtail_py/field_filter.py
- [x] T037 [US4] Implement format_status() method in FieldFilterState in pgtail_py/field_filter.py
- [x] T038 [US4] Add _field_filter attribute to LogTailer in pgtail_py/tailer.py
- [x] T039 [US4] Update LogTailer._should_show() in pgtail_py/tailer.py to include field filter check after level filter
- [x] T040 [US4] Add update_field_filter() method to LogTailer in pgtail_py/tailer.py
- [x] T041 [US4] Add field_filter attribute to AppState in pgtail_py/cli.py
- [x] T042 [US4] Implement handle_filter_field() function in pgtail_py/cli_filter.py for field=value syntax
- [x] T043 [US4] Update existing filter command handler in pgtail_py/cli_filter.py to detect and route field filters
- [x] T044 [US4] Add FILTER_FIELDS constant to pgtail_py/commands.py for autocomplete
- [x] T045 [US4] Show informative error when field filtering attempted on text format logs in pgtail_py/cli_filter.py

**Checkpoint**: User Story 4 complete - field filtering works for CSV/JSON logs ✅

---

## Phase 7: User Story 5 - JSON Output Mode (Priority: P3)

**Goal**: Output log entries as JSON for piping to external tools

**Independent Test**: Pipe pgtail output to jq and verify valid JSON structure

### Implementation for User Story 5

- [x] T046 [P] [US5] Implement format_entry_json() function in pgtail_py/display.py with ISO 8601 timestamps
- [x] T047 [US5] Add handle_output() command handler in pgtail_py/cli_core.py per contracts/commands.md
- [x] T048 [US5] Add "output" command to COMMANDS dict in pgtail_py/commands.py with json/text completions
- [x] T049 [US5] Wire handle_output() into command dispatch in pgtail_py/cli.py
- [x] T050 [US5] Update entry printing to handle JSON output format in pgtail_py/cli_core.py (print raw string, no colors)

**Checkpoint**: User Story 5 complete - JSON output mode works for all log formats ✅

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration, status display, and edge case handling

- [x] T051 Update status line formatting to show detected format in pgtail_py/cli.py
- [x] T052 Update status line formatting to show active field filters in pgtail_py/cli.py
- [x] T053 Update status line formatting to show display mode and output format in pgtail_py/cli.py
- [x] T054 Handle malformed CSV lines gracefully in pgtail_py/parser_csv.py (return raw entry with warning)
- [x] T055 Handle malformed JSON lines gracefully in pgtail_py/parser_json.py (return raw entry with warning)
- [x] T056 Add truncation indicator for long field values in compact mode in pgtail_py/display.py
- [x] T057 Run make lint and fix any linting issues
- [x] T058 Run make test and verify existing tests still pass
- [x] T059 Manual validation: test with sample CSV and JSON log files per quickstart.md

**Checkpoint**: Phase 8 complete - polish and cross-cutting concerns addressed ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Auto-Detection) must complete before US2-5 can be meaningfully tested
  - US2 (Rich Display) should complete before US3 (Display Mode Control)
  - US3, US4, US5 can proceed in parallel after US2
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation → Parsers → Tailer integration
- **User Story 2 (P2)**: Depends on US1 (needs parsed entries with extended fields)
- **User Story 3 (P2)**: Depends on US2 (extends display module)
- **User Story 4 (P3)**: Depends on US1 (needs extended LogEntry fields)
- **User Story 5 (P3)**: Depends on US2 (extends display module)

### Within Each User Story

- Enums/constants before classes
- Helper functions before main functions
- Core implementation before CLI integration
- CLI handler before command registration

### Parallel Opportunities

**Setup phase:**
- T002, T003 can run in parallel (separate files)

**User Story 1:**
- T010, T011 can run in parallel (CSV and JSON parsers are independent)

**User Story 2:**
- T018, T019 can run in parallel (enums in same file but independent)

**User Story 3:**
- T026, T027 can run in parallel (different functions)

**User Story 4:**
- T033, T034 can run in parallel (dataclass and constants)

---

## Parallel Example: User Story 1

```bash
# Launch parsers in parallel (different files):
Task: "Implement parse_csv_line() in pgtail_py/parser_csv.py"
Task: "Implement parse_json_line() in pgtail_py/parser_json.py"

# Then sequential integration:
Task: "Update parse_log_line() in pgtail_py/parser.py"
Task: "Add format detection to LogTailer in pgtail_py/tailer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 2: Foundational (6 tasks)
3. Complete Phase 3: User Story 1 (8 tasks)
4. **STOP and VALIDATE**: Test auto-detection with CSV, JSON, and text files
5. Total MVP: 17 tasks

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP complete! (auto-detection works)
3. Add User Story 2 → Test independently → Rich error info visible
4. Add User Story 3 → Test independently → Display modes work
5. Add User Story 4 → Test independently → Field filtering works
6. Add User Story 5 → Test independently → JSON output works
7. Complete Polish → Production ready

### Recommended Order

1. **Phases 1-3 (MVP)**: Auto-detection - delivers core value
2. **Phase 4 (US2)**: Rich display - makes structured logs useful
3. **Phase 5 (US3)**: Display control - user customization
4. **Phases 6-7 (US4, US5)**: Can be done in parallel - independent features
5. **Phase 8**: Polish - final integration

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently testable after completion
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No test tasks included (not explicitly requested in spec)
