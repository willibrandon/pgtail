# Tasks: pgtail Python Rewrite

**Input**: Design documents from `/specs/002-python-rewrite/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Not explicitly requested in spec. Test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Package**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create package directory structure: pgtail_py/, tests/
- [x] T002 Create pgtail_py/__init__.py with version string
- [x] T003 Create pyproject.toml with dependencies (prompt_toolkit, psutil, watchdog) and dev dependencies (pytest, ruff, pyinstaller)
- [x] T004 [P] Create .gitignore entries for Python: __pycache__/, .venv/, dist/, build/, *.egg-info/
- [x] T005 [P] Create ruff.toml with Python 3.10+ target and default rules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and utilities that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create LogLevel enum in pgtail_py/filter.py with all PostgreSQL levels (PANIC through DEBUG5)
- [x] T007 [P] Create DetectionSource enum in pgtail_py/instance.py
- [x] T008 Create Instance dataclass in pgtail_py/instance.py with id, version, data_dir, log_path, source, running, pid
- [x] T009 [P] Create LogEntry dataclass in pgtail_py/parser.py with timestamp, level, message, raw, pid
- [x] T010 Create config.py with get_history_path() returning platform-appropriate path (XDG/Library/APPDATA)
- [x] T011 [P] Create AppState dataclass in pgtail_py/cli.py with instances, current_instance, active_levels, tailing, history_path
- [x] T012 Create pgtail_py/__main__.py entry point that imports and runs main() from cli.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Launch and List Instances (Priority: P1)

**Goal**: Developer launches pgtail and sees detected PostgreSQL instances

**Independent Test**: Launch application, verify detected instances match running processes and known paths

### Implementation for User Story 1

- [x] T013 [US1] Create detector_unix.py with detect_from_processes() using psutil to find postgres processes
- [x] T014 [P] [US1] Create detector_unix.py detect_from_pgrx() scanning ~/.pgrx/data-* directories
- [x] T015 [P] [US1] Create detector_unix.py detect_from_pgdata() checking PGDATA environment variable
- [x] T016 [P] [US1] Create detector_unix.py detect_from_known_paths() for /usr/local/var/postgres, /var/lib/postgresql, etc.
- [x] T017 [US1] Create detector_windows.py with Windows-specific paths (Program Files, etc.) and process detection
- [x] T018 [US1] Create detector.py with detect_all() that calls platform-specific module and returns list[Instance]
- [x] T019 [US1] Add get_version() helper in detector.py to read PG_VERSION file from data directory
- [x] T020 [US1] Add get_log_path() helper in detector.py to find log file from postgresql.conf or log_directory
- [x] T021 [US1] Create format_instances_table() in cli.py to render instances as aligned table (ID, Version, Status, Path, Log)
- [x] T022 [US1] Create list_command() handler in cli.py that calls detect_all() and prints table
- [x] T023 [US1] Implement basic REPL loop in cli.py using PromptSession with 'pgtail> ' prompt
- [x] T024 [US1] Wire list command into REPL command dispatcher in cli.py
- [x] T025 [US1] Add startup detection: call detect_all() on launch and show instance count
- [x] T026 [US1] Add help command showing available commands in cli.py
- [x] T027 [US1] Add quit/exit commands and Ctrl+D handling in cli.py
- [x] T028 [US1] Add clear command to clear terminal screen in cli.py
- [x] T029 [US1] Add refresh command to re-run detection in cli.py
- [x] T030 [US1] Handle graceful degradation: skip unreadable directories, continue on permission errors

**Checkpoint**: User Story 1 complete - can launch, list, help, quit

---

## Phase 4: User Story 2 - Tail Logs with Color Output (Priority: P1)

**Goal**: Developer tails logs with color-coded severity levels

**Independent Test**: Tail a log file, verify colors render correctly on macOS/Linux/Windows

### Implementation for User Story 2

- [ ] T031 [US2] Create parser.py parse_log_line() function with regex for PostgreSQL default format
- [ ] T032 [US2] Handle unparseable lines in parser.py: return LogEntry with level=LOG and raw line preserved
- [ ] T033 [US2] Create colors.py with LEVEL_STYLES dict mapping LogLevel to prompt_toolkit style strings
- [ ] T034 [US2] Create colors.py print_log_entry() using print_formatted_text() with level-based styling
- [ ] T035 [US2] Add NO_COLOR environment check in colors.py to disable styling when set
- [ ] T036 [US2] Create tailer.py LogTailer class using watchdog Observer for file monitoring
- [ ] T037 [US2] Implement tailer.py on_modified() handler to read new lines from log file
- [ ] T038 [US2] Add polling fallback in tailer.py for filesystems without native watching (NFS, etc.)
- [ ] T039 [US2] Handle log rotation in tailer.py: detect file truncation/recreation and reopen
- [ ] T040 [US2] Create tail_command() handler in cli.py accepting instance ID or path
- [ ] T041 [US2] Implement tail loop in cli.py: start tailer, print entries, handle Ctrl+C to stop
- [ ] T042 [US2] Add stop command in cli.py to halt active tail and return to prompt
- [ ] T043 [US2] Update REPL to handle tailing state: different prompt or status indicator
- [ ] T044 [US2] Handle instance not found error with helpful message suggesting valid IDs

**Checkpoint**: User Story 2 complete - can tail logs with colors

---

## Phase 5: User Story 3 - Filter by Log Level (Priority: P2)

**Goal**: Developer filters log output to specific severity levels

**Independent Test**: Set filter to ERROR WARNING, verify only those levels appear

### Implementation for User Story 3

- [ ] T045 [US3] Create filter.py should_show() function checking if LogEntry.level is in active_levels set
- [ ] T046 [US3] Create levels_command() handler in cli.py parsing level arguments
- [ ] T047 [US3] Handle 'levels' with no args: display current filter settings in cli.py
- [ ] T048 [US3] Handle 'levels ALL': reset filter to show all levels in cli.py
- [ ] T049 [US3] Integrate filter into tail loop: only print entries passing should_show()
- [ ] T050 [US3] Add level name validation with helpful error for invalid level names

**Checkpoint**: User Story 3 complete - can filter by level

---

## Phase 6: User Story 4 - Interactive REPL with Autocomplete (Priority: P2)

**Goal**: Developer gets command autocomplete and persistent history

**Independent Test**: Type partial command, press Tab, verify completion; restart, verify history

### Implementation for User Story 4

- [ ] T051 [US4] Create commands.py with COMMANDS dict defining all command names and descriptions
- [ ] T052 [US4] Create PgtailCompleter class in commands.py extending Completer
- [ ] T053 [US4] Implement command name completion in PgtailCompleter.get_completions()
- [ ] T054 [US4] Add instance ID/path completion for tail command arguments
- [ ] T055 [US4] Add log level name completion for levels command arguments
- [ ] T056 [US4] Wire FileHistory into PromptSession using history_path from config.py
- [ ] T057 [US4] Ensure history directory is created if it doesn't exist
- [ ] T058 [US4] Wire PgtailCompleter into PromptSession in cli.py

**Checkpoint**: User Story 4 complete - autocomplete and history working

---

## Phase 7: User Story 5 - Enable Logging for Instance (Priority: P3)

**Goal**: Developer enables logging_collector for instances without it

**Independent Test**: Target instance with logging disabled, run enable-logging, verify postgresql.conf updated

### Implementation for User Story 5

- [ ] T059 [US5] Create enable_logging_command() handler in cli.py
- [ ] T060 [US5] Implement read_postgresql_conf() helper to parse existing config
- [ ] T061 [US5] Implement write_postgresql_conf() to update logging_collector = on
- [ ] T062 [US5] Add log_directory and log_filename defaults if not set
- [ ] T063 [US5] Handle permission errors with actionable message suggesting sudo
- [ ] T064 [US5] Print success message prompting user to restart PostgreSQL

**Checkpoint**: User Story 5 complete - can enable logging

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final quality improvements and distribution

- [ ] T065 Add module docstrings to all pgtail_py/*.py files
- [ ] T066 [P] Add type hints to all public functions
- [ ] T067 [P] Run ruff check and fix any linting issues
- [ ] T068 [P] Create tests/__init__.py
- [ ] T069 [P] Create tests/test_parser.py with tests for parse_log_line()
- [ ] T070 [P] Create tests/test_filter.py with tests for should_show()
- [ ] T071 [P] Create tests/test_detector.py with tests for get_version(), get_log_path()
- [ ] T072 Run pytest and ensure all tests pass
- [ ] T073 Create PyInstaller spec or use --onefile to build single executable
- [ ] T074 Test executable on macOS, Linux, Windows
- [ ] T075 Verify quickstart.md checklist passes
- [ ] T076 Update CLAUDE.md with Python-specific commands if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP entry point
- **User Story 2 (Phase 4)**: Depends on Foundational - Core feature, can parallel with US1
- **User Story 3 (Phase 5)**: Depends on US2 (needs tail to work)
- **User Story 4 (Phase 6)**: Depends on Foundational - Can parallel with US1/US2
- **User Story 5 (Phase 7)**: Depends on US1 (needs instance detection)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Launch/List)**: Foundation only - No dependencies on other stories
- **US2 (Tail/Colors)**: Foundation only - Can start parallel with US1
- **US3 (Filter)**: Requires US2 (filtering applies to tail output)
- **US4 (Autocomplete)**: Foundation only - Can start parallel with US1/US2
- **US5 (Enable Logging)**: Requires US1 (needs instance detection)

### Parallel Opportunities

- Setup: T004, T005 can run in parallel
- Foundational: T007, T009, T011 can run in parallel after T006
- US1: T014, T015, T016 can run in parallel (different detection sources)
- US4: T053, T054, T055 can run in parallel (different completers)
- Polish: T066, T067, T068, T069, T070, T071 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# After T013 completes, launch detection sources in parallel:
Task: "Create detector_unix.py detect_from_pgrx() scanning ~/.pgrx/data-* directories"
Task: "Create detector_unix.py detect_from_pgdata() checking PGDATA environment variable"
Task: "Create detector_unix.py detect_from_known_paths() for /usr/local/var/postgres, etc."
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Launch/List)
4. Complete Phase 4: User Story 2 (Tail/Colors)
5. **STOP and VALIDATE**: Can launch, list instances, tail with colors
6. This delivers the core value proposition (fixing Linux color issues)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Can launch and list instances (basic MVP)
3. Add US2 → Can tail with colors (primary feature)
4. Add US3 → Can filter by level (usability)
5. Add US4 → Autocomplete and history (polish)
6. Add US5 → Enable logging (convenience)
7. Polish → Tests, linting, distribution

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 are both P1 priority and can be developed in parallel
- US3 depends on US2 being complete (filtering requires tail to work)
- US4 can be added at any point after foundational
- Total tasks: 76
