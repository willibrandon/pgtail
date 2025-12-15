# Tasks: pgtail CLI Tool

**Input**: Design documents from `/specs/001-pgtail-cli/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested in the specification. Unit tests included for core detection and parsing logic per constitution Quality Standards.

**REPL Requirement**: Per constitution v1.2.0, the REPL MUST use `github.com/c-bata/go-prompt` for autocomplete and history. NO simplified implementations (e.g., bufio.Scanner) are permitted. Reference: `../go-prompt/`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This project uses Go conventions:
- **Entry point**: `cmd/pgtail/`
- **Internal packages**: `internal/`
- **Tests**: Colocated with source (`*_test.go`) or in `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create directory structure: `cmd/pgtail/`, `internal/detector/`, `internal/instance/`, `internal/tailer/`, `internal/repl/`
- [X] T002 Initialize Go module with `go mod init github.com/willibrandon/pgtail` in go.mod
- [X] T003 [P] Add dependencies to go.mod: go-prompt (REQUIRED for REPL), lipgloss, fsnotify, gopsutil/v3
- [X] T004 [P] Create .gitignore for Go project (binaries, vendor/, .idea/, etc.)
- [X] T005 [P] Configure golangci-lint with .golangci.yml (default configuration per constitution)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and shared infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create Instance type with all fields in internal/instance/instance.go
- [X] T007 [P] Create DetectionSource enum with String() method in internal/instance/instance.go
- [X] T008 [P] Create LogLevel enum with all PostgreSQL levels in internal/tailer/filter.go
- [X] T009 [P] Create LogEntry struct for parsed log lines in internal/tailer/parser.go
- [X] T010 Create AppState struct with Instances, CurrentIndex, Filter, Tailing fields in internal/repl/executor.go
- [X] T011 [P] Create entry point skeleton with --help, --version flags and go-prompt REPL loop in cmd/pgtail/main.go (MUST use go-prompt, not bufio)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Discover PostgreSQL Instances (Priority: P1) 🎯 MVP

**Goal**: Auto-detect all PostgreSQL instances on the local machine and display them via `list` command

**Independent Test**: Launch pgtail, run `list`, see all detected instances in a formatted table

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement postgresql.conf parser for log_directory, log_filename, port in internal/detector/config.go
- [X] T013 [P] [US1] Implement PG_VERSION file reader to extract PostgreSQL version in internal/detector/config.go
- [X] T014 [P] [US1] Implement postmaster.pid parser for port and PID in internal/detector/config.go
- [X] T015 [P] [US1] Implement running process detection with gopsutil in internal/detector/process.go
- [X] T016 [P] [US1] Implement Unix-specific process detection (build tag: !windows) in internal/detector/process_unix.go
- [X] T017 [P] [US1] Implement Windows-specific process detection (build tag: windows) in internal/detector/process_windows.go
- [X] T018 [US1] Implement pgrx path scanner for ~/.pgrx/data-*/ directories in internal/detector/paths.go
- [X] T019 [US1] Implement platform-specific known paths (Homebrew, apt, yum, Windows) in internal/detector/paths.go
- [X] T020 [US1] Implement PGDATA environment variable check in internal/detector/paths.go
- [X] T021 [US1] Implement main detector orchestration with priority ordering in internal/detector/detector.go
- [X] T022 [US1] Implement instance deduplication by normalized DataDir in internal/detector/detector.go
- [X] T023 [US1] Implement `list` command with tabular output formatting in internal/repl/executor.go
- [X] T024 [US1] Implement helpful "no instances found" message with suggestions in internal/repl/executor.go
- [X] T025 [US1] Add graceful error handling: continue on detection failures, report skipped sources in internal/detector/detector.go
- [X] T026 [P] [US1] Add unit tests for config parsing in internal/detector/config_test.go
- [X] T027 [P] [US1] Add unit tests for detector with mock filesystem in internal/detector/detector_test.go

**Checkpoint**: User Story 1 complete - `pgtail` launches and `list` shows all detected PostgreSQL instances

---

## Phase 4: User Story 2 - Tail Instance Logs (Priority: P2)

**Goal**: Stream log file contents in real-time for a selected instance

**Independent Test**: Run `tail 0` after `list`, see new log entries appear within 1 second of being written

### Implementation for User Story 2

- [X] T028 [US2] Implement log file path resolution from Instance.LogDir and LogPattern in internal/tailer/tailer.go
- [X] T029 [US2] Implement most-recent log file finder when multiple files match pattern in internal/tailer/tailer.go
- [X] T030 [US2] Implement file tailing with fsnotify (cross-platform: inotify/kqueue/ReadDirectoryChangesW) in internal/tailer/tailer.go
- [X] T031 [US2] Implement polling-based file tailing fallback for edge cases (network fs, permission issues) in internal/tailer/tailer.go
- [X] T032 [US2] Implement PostgreSQL log line parser (timestamp, PID, level extraction) in internal/tailer/parser.go
- [X] T033 [US2] Implement multi-line log entry handling (continuation detection) in internal/tailer/parser.go
- [X] T034 [US2] Implement `tail` command with numeric index argument in cmd/pgtail/main.go
- [X] T035 [US2] Implement `tail` command with path substring fuzzy matching in cmd/pgtail/main.go
- [X] T036 [US2] Implement `follow` as alias for `tail` in cmd/pgtail/main.go
- [X] T037 [US2] Implement Ctrl+C handling to stop tail and return to prompt in cmd/pgtail/main.go
- [X] T038 [US2] Implement `stop` command to halt active tail in cmd/pgtail/main.go
- [X] T039 [US2] Add actionable error messages for: invalid index, no log file, permission denied in cmd/pgtail/main.go
- [X] T040 [P] [US2] Add unit tests for log line parser in internal/tailer/parser_test.go

**Checkpoint**: User Stories 1 AND 2 complete - can discover instances and tail their logs

---

## Phase 5: User Story 3 - Filter Logs by Level (Priority: P3)

**Goal**: Filter displayed log entries by severity level during tail operations

**Independent Test**: Run `levels ERROR WARNING`, then `tail 0`, see only ERROR and WARNING entries

### Implementation for User Story 3

- [X] T041 [US3] Implement Filter struct with Allow(), Set(), Clear(), String() methods in internal/tailer/filter.go
- [X] T042 [US3] Implement LogLevel parsing from string (case-insensitive) in internal/tailer/filter.go
- [X] T043 [US3] Implement `levels` command with multiple level arguments in internal/repl/executor.go
- [X] T044 [US3] Implement `levels` with no arguments to clear filter in internal/repl/executor.go
- [X] T045 [US3] Integrate filter with tailer to suppress non-matching entries in internal/tailer/tailer.go
- [X] T046 [US3] Add filter state display in prompt (e.g., "ERR,WARN") in internal/repl/repl.go
- [X] T047 [US3] Add error message for invalid level names in internal/repl/executor.go
- [X] T048 [P] [US3] Add unit tests for filter logic in internal/tailer/filter_test.go

**Checkpoint**: User Stories 1-3 complete - can discover, tail, and filter logs

---

## Phase 6: User Story 4 - Interactive REPL Experience (Priority: P4)

**Goal**: Provide autocomplete, command history, and dynamic prompt via go-prompt

**Independent Test**: Type `ta` + Tab → autocompletes to `tail`; Up arrow recalls previous command

### Implementation for User Story 4

- [X] T049 [US4] Implement REPL initialization with go-prompt (REQUIRED - see ../go-prompt/) in internal/repl/repl.go
- [X] T050 [US4] Implement command completer for all commands in internal/repl/completer.go
- [X] T051 [US4] Implement instance index/path suggestions after `tail ` in internal/repl/completer.go
- [X] T052 [US4] Implement log level suggestions after `levels ` in internal/repl/completer.go
- [X] T053 [US4] Implement dynamic live prefix showing current state (instance, filter) in internal/repl/repl.go
- [X] T054 [US4] Implement Ctrl+L keybinding for clear screen in internal/repl/repl.go
- [X] T055 [US4] Implement Ctrl+D handling for exit (when input empty) in internal/repl/repl.go
- [X] T056 [US4] Implement `refresh` command to re-scan instances in internal/repl/executor.go
- [X] T057 [US4] Implement `help` command with full command reference in internal/repl/executor.go
- [X] T058 [US4] Implement `clear` command in internal/repl/executor.go
- [X] T059 [US4] Implement `quit` and `exit` commands in internal/repl/executor.go

**Checkpoint**: User Stories 1-4 complete - full interactive REPL with autocomplete and history

---

## Phase 7: User Story 5 - Color-Coded Log Output (Priority: P5)

**Goal**: Display log entries with severity-appropriate colors for quick visual scanning

**Independent Test**: Tail logs with various levels; ERROR appears red, WARNING yellow, etc.

### Implementation for User Story 5

- [X] T060 [US5] Implement color functions using lipgloss for each log level in internal/tailer/color.go
- [X] T061 [US5] Implement colorize() function mapping LogLevel to colored output in internal/tailer/color.go
- [X] T062 [US5] Implement NO_COLOR environment variable detection in internal/tailer/color.go
- [X] T063 [US5] Implement terminal color capability detection fallback in internal/tailer/color.go
- [X] T064 [US5] Integrate colorized output into tailer display loop in cmd/pgtail/main.go

**Checkpoint**: All 5 user stories complete - full featured pgtail with colors

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and quality assurance

- [ ] T065 Wire all components together in main.go entry point in cmd/pgtail/main.go
- [ ] T066 [P] Ensure all error messages follow actionable format per CLI contract in internal/repl/executor.go
- [ ] T067 [P] Verify 80-column output formatting for list table in internal/repl/executor.go
- [ ] T068 Add package-level doc comments to all internal/ packages
- [ ] T069 [P] Run golangci-lint and fix any issues
- [ ] T070 [P] Build and test on macOS (ARM64)
- [ ] T071 [P] Build and test on Linux (AMD64 via Docker or VM)
- [ ] T072 [P] Build and test on Windows (AMD64 via VM or cross-compile test)
- [ ] T073 Run quickstart.md validation steps to verify all workflows
- [ ] T074 Create Makefile or build script for cross-platform builds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - delivers MVP (list command)
- **User Story 2 (Phase 4)**: Depends on US1 (needs instances to tail)
- **User Story 3 (Phase 5)**: Depends on US2 (filter applies to tail output)
- **User Story 4 (Phase 6)**: Can start after Foundational - enhances REPL
- **User Story 5 (Phase 7)**: Depends on US2 (colors apply to tail output)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup
     ↓
Phase 2: Foundational
     ↓
Phase 3: US1 (Instance Discovery) ← MVP!
     ↓
Phase 4: US2 (Log Tailing)
     ↓                   ↘
Phase 5: US3 (Filtering)  Phase 7: US5 (Colors)
     ↓
Phase 6: US4 (REPL) ← Can run parallel with US2-5 after Foundational
     ↓
Phase 8: Polish
```

### Within Each User Story

- Models/types before services
- Services before commands
- Core implementation before integration
- Unit tests can run parallel with implementation

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- All Phase 2 tasks marked [P] can run in parallel
- Within US1: T012-T017 (config/process detection) can run in parallel
- Within US1: T026-T027 (tests) can run parallel with implementation
- Within US2: T040 (parser tests) can run parallel
- Within US3: T048 (filter tests) can run parallel
- US4 (REPL) can start after Foundational, parallel with other stories
- US5 (Colors) can start after US2, parallel with US3

---

## Parallel Example: User Story 1

```bash
# After Foundational complete, launch these in parallel:
Task T012: "Implement postgresql.conf parser in internal/detector/config.go"
Task T013: "Implement PG_VERSION file reader in internal/detector/config.go"
Task T014: "Implement postmaster.pid parser in internal/detector/config.go"
Task T015: "Implement running process detection in internal/detector/process.go"
Task T016: "Implement Unix process detection in internal/detector/process_unix.go"
Task T017: "Implement Windows process detection in internal/detector/process_windows.go"

# Then sequential (depends on above):
Task T018-T025: Path scanning, orchestration, list command
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Instance Discovery)
4. **STOP and VALIDATE**: Run `pgtail`, verify `list` shows instances
5. Deploy/demo MVP if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → `list` works → **MVP!**
3. Add US2 → `tail` works → Log viewing functional
4. Add US3 → `levels` works → Filtering available
5. Add US4 → Full REPL → Autocomplete/history
6. Add US5 → Colors → Polish complete

### Single Developer Strategy

Execute phases sequentially:
1. Phase 1-2: ~30 min
2. Phase 3 (US1): ~2 hours
3. Phase 4 (US2): ~2 hours
4. Phase 5 (US3): ~1 hour
5. Phase 6 (US4): ~2 hours
6. Phase 7 (US5): ~30 min
7. Phase 8: ~1 hour

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable at its checkpoint
- Constitution requires: graceful degradation, actionable errors, cross-platform parity
- All unit tests for core detection/parsing per Quality Standards
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
