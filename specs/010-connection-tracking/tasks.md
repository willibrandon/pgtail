# Tasks: Connection Tracking Dashboard

**Input**: Design documents from `/specs/010-connection-tracking/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/cli-commands.md

**Tests**: Tests are included in this task list per existing project patterns (test-driven development).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: No new project setup needed - adding to existing pgtail_py package

- [x] T001 Verify existing project structure matches plan.md in pgtail_py/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and parsing that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

- [x] T002 [P] Create test file for connection event parsing in tests/test_connection_parser.py
- [x] T003 [P] Create test file for connection event dataclass in tests/test_connection_event.py
- [x] T004 [P] Create test file for connection stats aggregator in tests/test_connection_stats.py

### Implementation for Foundational

- [x] T005 [P] Create ConnectionEventType enum in pgtail_py/connection_event.py
- [x] T006 [P] Create ConnectionEvent frozen dataclass with from_log_entry() factory in pgtail_py/connection_event.py
- [x] T007 Create connection message regex patterns (authorized, disconnection, received) in pgtail_py/connection_parser.py
- [x] T008 Implement parse_connection_message() function in pgtail_py/connection_parser.py
- [x] T009 Create ConnectionStats dataclass with _events deque and _active dict in pgtail_py/connection_stats.py
- [x] T010 Implement ConnectionStats.add() method for processing LogEntry in pgtail_py/connection_stats.py
- [x] T011 Implement ConnectionStats.clear() and is_empty() methods in pgtail_py/connection_stats.py
- [x] T012 Add connection_stats field to AppState in pgtail_py/cli.py

**Checkpoint**: Foundation ready - all connection tracking infrastructure in place

---

## Phase 3: User Story 1 - View Connection Summary (Priority: P1) 🎯 MVP

**Goal**: Display total active connections and counts grouped by database, user, and application

**Independent Test**: Run `connections` command after tailing a log with connection events; verify accurate counts

### Tests for User Story 1

- [x] T013 [P] [US1] Add test for connections command summary display in tests/test_connection_stats.py
- [x] T014 [P] [US1] Add test for get_by_database() aggregation in tests/test_connection_stats.py
- [x] T015 [P] [US1] Add test for get_by_user() aggregation in tests/test_connection_stats.py
- [x] T016 [P] [US1] Add test for get_by_application() aggregation in tests/test_connection_stats.py

### Implementation for User Story 1

- [x] T017 [US1] Implement ConnectionStats.active_count() method in pgtail_py/connection_stats.py
- [x] T018 [P] [US1] Implement ConnectionStats.get_by_database() method in pgtail_py/connection_stats.py
- [x] T019 [P] [US1] Implement ConnectionStats.get_by_user() method in pgtail_py/connection_stats.py
- [x] T020 [P] [US1] Implement ConnectionStats.get_by_application() method in pgtail_py/connection_stats.py
- [x] T021 [P] [US1] Implement ConnectionStats.get_by_host() method in pgtail_py/connection_stats.py
- [x] T022 [US1] Create cli_connections.py with connections_command() handler in pgtail_py/cli_connections.py
- [x] T023 [US1] Implement _show_summary() function for default output in pgtail_py/cli_connections.py
- [x] T024 [US1] Implement _clear_stats() function for clear subcommand in pgtail_py/cli_connections.py
- [x] T025 [US1] Register connections command in COMMANDS dict in pgtail_py/commands.py
- [x] T026 [US1] Add connections to PgtailCompleter in pgtail_py/commands.py
- [x] T027 [US1] Wire connection_stats.add() to LogTailer on_entry callback in pgtail_py/cli.py

**Checkpoint**: User Story 1 complete - `connections` and `connections clear` commands work

---

## Phase 4: User Story 2 - Connection History and Trend Analysis (Priority: P2)

**Goal**: Show connection counts over time with timeline and leak detection

**Independent Test**: Run `connections --history` after generating events over time; verify timeline shows accurate trends

### Tests for User Story 2

- [x] T028 [P] [US2] Add test for get_trend_buckets() with 15-minute intervals in tests/test_connection_stats.py
- [x] T029 [P] [US2] Add test for get_events_since() time filtering in tests/test_connection_stats.py

### Implementation for User Story 2

- [x] T030 [US2] Implement ConnectionStats.get_events_since() method in pgtail_py/connection_stats.py
- [x] T031 [US2] Implement ConnectionStats.get_trend_buckets() returning (connects, disconnects) per bucket in pgtail_py/connection_stats.py
- [x] T032 [US2] Implement _show_history() function with timeline display in pgtail_py/cli_connections.py
- [x] T033 [US2] Add sparkline visualization for connection trends in pgtail_py/cli_connections.py
- [x] T034 [US2] Add --history flag parsing in connections_command() in pgtail_py/cli_connections.py
- [x] T035 [US2] Add --history to PgtailCompleter subcompletions in pgtail_py/commands.py

**Checkpoint**: User Story 2 complete - `connections --history` shows connection trends

---

## Phase 5: User Story 3 - Watch Live Connection Events (Priority: P2)

**Goal**: Real-time stream of connection/disconnection events with color coding

**Independent Test**: Run `connections --watch`, trigger connection events, verify they appear immediately with correct indicators

### Implementation for User Story 3

- [ ] T036 [US3] Implement _show_watch() function with live event display in pgtail_py/cli_connections.py
- [ ] T037 [US3] Add color-coded event indicators ([+] green, [-] yellow, [!] red) in pgtail_py/cli_connections.py
- [ ] T038 [US3] Add Ctrl+C handling for clean exit from watch mode in pgtail_py/cli_connections.py
- [ ] T039 [US3] Add --watch flag parsing in connections_command() in pgtail_py/cli_connections.py
- [ ] T040 [US3] Add invalid combination check for --watch + --history in pgtail_py/cli_connections.py
- [ ] T041 [US3] Add --watch to PgtailCompleter subcompletions in pgtail_py/commands.py

**Checkpoint**: User Story 3 complete - `connections --watch` streams live events

---

## Phase 6: User Story 4 - Filter Connections by Criteria (Priority: P3)

**Goal**: Filter connection summary by database, user, or application

**Independent Test**: Run `connections --db=X` with mixed connections; verify only matching connections shown

### Tests for User Story 4

- [ ] T042 [P] [US4] Add test for ConnectionFilter.matches() with single criterion in tests/test_connection_stats.py
- [ ] T043 [P] [US4] Add test for ConnectionFilter.matches() with multiple criteria (AND logic) in tests/test_connection_stats.py

### Implementation for User Story 4

- [ ] T044 [US4] Create ConnectionFilter dataclass in pgtail_py/connection_stats.py
- [ ] T045 [US4] Implement ConnectionFilter.matches() method with AND logic in pgtail_py/connection_stats.py
- [ ] T046 [US4] Implement ConnectionFilter.is_empty() method in pgtail_py/connection_stats.py
- [ ] T047 [US4] Add --db, --user, --app flag parsing in connections_command() in pgtail_py/cli_connections.py
- [ ] T048 [US4] Update _show_summary() to apply ConnectionFilter in pgtail_py/cli_connections.py
- [ ] T049 [US4] Update _show_history() to apply ConnectionFilter in pgtail_py/cli_connections.py
- [ ] T050 [US4] Update _show_watch() to apply ConnectionFilter in pgtail_py/cli_connections.py
- [ ] T051 [US4] Add --db=, --user=, --app= to PgtailCompleter subcompletions in pgtail_py/commands.py

**Checkpoint**: User Story 4 complete - all filter flags work across all views

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T052 [P] Add edge case handling for malformed connection log messages in pgtail_py/connection_parser.py
- [ ] T053 [P] Add handling for CONNECTION_FAILED events (FATAL messages) in pgtail_py/connection_parser.py
- [ ] T054 Handle disconnection without matching connection (standalone event) in pgtail_py/connection_stats.py
- [ ] T055 Add "unknown" default for missing application_name in pgtail_py/connection_event.py
- [ ] T056 Run all tests and verify pass in tests/
- [ ] T057 Update CLAUDE.md Recent Changes section with 010-connection-tracking in CLAUDE.md
- [ ] T058 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify existing structure
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2 → P3)
  - US2 and US3 share same priority (P2) and can run in parallel
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Enhances US1/US2/US3 but independently testable

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Foundation entities before stats aggregator
- Stats aggregator before CLI commands
- CLI commands before command registration

### Parallel Opportunities

- All test tasks marked [P] can run in parallel within their phase
- All get_by_* methods (T018-T021) can run in parallel
- US2 (T028-T035) and US3 (T036-T041) can run in parallel (both P2)
- Filter tests (T042-T043) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all test files together:
Task: "Create test file for connection event parsing in tests/test_connection_parser.py"
Task: "Create test file for connection event dataclass in tests/test_connection_event.py"
Task: "Create test file for connection stats aggregator in tests/test_connection_stats.py"

# Launch enum and dataclass together:
Task: "Create ConnectionEventType enum in pgtail_py/connection_event.py"
Task: "Create ConnectionEvent frozen dataclass with from_log_entry() factory in pgtail_py/connection_event.py"
```

## Parallel Example: User Story 1 Aggregation Methods

```bash
# Launch all get_by_* methods together:
Task: "Implement ConnectionStats.get_by_database() method in pgtail_py/connection_stats.py"
Task: "Implement ConnectionStats.get_by_user() method in pgtail_py/connection_stats.py"
Task: "Implement ConnectionStats.get_by_application() method in pgtail_py/connection_stats.py"
Task: "Implement ConnectionStats.get_by_host() method in pgtail_py/connection_stats.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify structure)
2. Complete Phase 2: Foundational (all connection tracking infrastructure)
3. Complete Phase 3: User Story 1 (basic `connections` command)
4. **STOP and VALIDATE**: Test `connections` command independently
5. Deploy/demo - users can now see connection summaries

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test `connections` → Deploy (MVP!)
3. Add User Story 2 → Test `connections --history` → Deploy
4. Add User Story 3 → Test `connections --watch` → Deploy
5. Add User Story 4 → Test filter flags → Deploy
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files or independent methods, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Pattern follows existing error_stats/cli_errors implementation
