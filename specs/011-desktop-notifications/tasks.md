# Tasks: Desktop Notifications for Alerts

**Input**: Design documents from `/specs/011-desktop-notifications/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested - tests omitted per specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Single CLI application
- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root (optional)

---

## Phase 1: Setup

**Purpose**: Create module files and basic structure

- [X] T001 [P] Create NotificationRuleType enum and NotificationRule dataclass in pgtail_py/notify.py
- [X] T002 [P] Create Notifier abstract interface in pgtail_py/notifier.py
- [X] T003 [P] Create MacOSNotifier and LinuxNotifier in pgtail_py/notifier_unix.py
- [X] T004 [P] Create WindowsNotifier in pgtail_py/notifier_windows.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core notification infrastructure that MUST be complete before user story commands

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement platform detection and notifier factory in pgtail_py/notifier.py (depends on T002-T004)
- [X] T006 Implement RateLimiter class in pgtail_py/notify.py
- [X] T007 Implement QuietHours class with overnight span handling in pgtail_py/notify.py
- [X] T008 Implement NotificationConfig dataclass in pgtail_py/notify.py (depends on T001, T006, T007)
- [X] T009 Implement NotificationManager with check(entry) method in pgtail_py/notify.py (depends on T005, T008)
- [X] T010 Extend NotificationsSection in pgtail_py/config.py with patterns, error_rate, slow_query_ms fields
- [X] T011 Add NotificationManager to AppState in pgtail_py/cli.py and wire to tailer.on_entry callback (depends on T009)

**Checkpoint**: Foundation ready - notify command implementation can now begin

---

## Phase 3: User Story 1 - Level-Based Notifications (Priority: P1) 🎯 MVP

**Goal**: Enable notifications for specific log levels (FATAL, PANIC, etc.)

**Independent Test**: Run `notify on FATAL PANIC`, trigger a FATAL error in PostgreSQL, verify desktop notification appears

### Implementation for User Story 1

- [X] T012 [US1] Implement LEVEL rule matching in NotificationManager.check() in pgtail_py/notify.py
- [X] T013 [US1] Create cli_notify.py with notify_command handler skeleton in pgtail_py/cli_notify.py
- [X] T014 [US1] Implement `notify on <levels>` parsing and validation in pgtail_py/cli_notify.py
- [X] T015 [US1] Implement `notify off` command handler in pgtail_py/cli_notify.py
- [X] T016 [US1] Add notify command routing in handle_command() in pgtail_py/cli.py (depends on T013)
- [X] T017 [US1] Implement config persistence for level rules in pgtail_py/cli_notify.py
- [X] T018 [US1] Add 'notify' to PgtailCompleter in pgtail_py/commands.py

**Checkpoint**: User Story 1 complete - level-based notifications working independently

---

## Phase 4: User Story 2 - Notification Rate Limiting (Priority: P1)

**Goal**: Prevent notification spam during incidents (max 1 per 5 seconds)

**Independent Test**: Enable ERROR notifications, trigger 50 errors rapidly, verify at most 1 notification per 5 seconds

### Implementation for User Story 2

- [X] T019 [US2] Integrate RateLimiter into NotificationManager.check() flow in pgtail_py/notify.py
- [X] T020 [US2] Add rate limiting before notification send in NotificationManager in pgtail_py/notify.py
- [X] T021 [US2] Update RateLimiter timestamp on successful send in pgtail_py/notify.py

**Checkpoint**: User Story 2 complete - rate limiting prevents spam

---

## Phase 5: User Story 3 - Pattern-Based Notifications (Priority: P2)

**Goal**: Enable notifications for regex pattern matches in log messages

**Independent Test**: Run `notify on /deadlock detected/`, generate log with "deadlock detected", verify notification

### Implementation for User Story 3

- [X] T022 [US3] Implement PATTERN rule type matching in NotificationManager.check() in pgtail_py/notify.py
- [X] T023 [US3] Implement `notify on /<pattern>/[i]` parsing with regex compilation in pgtail_py/cli_notify.py
- [X] T024 [US3] Add regex validation and error handling for invalid patterns in pgtail_py/cli_notify.py
- [X] T025 [US3] Implement config persistence for pattern rules (as list of strings) in pgtail_py/cli_notify.py
- [X] T026 [US3] Add pattern completions to PgtailCompleter in pgtail_py/commands.py

**Checkpoint**: User Story 3 complete - pattern-based notifications working

---

## Phase 6: User Story 4 - Rate-Based Threshold Notifications (Priority: P2)

**Goal**: Alert when error rate exceeds N errors per minute

**Independent Test**: Run `notify on errors > 10/min`, generate 11 errors in 1 minute, verify threshold notification

### Implementation for User Story 4

- [X] T027 [US4] Implement ERROR_RATE rule type in NotificationRule in pgtail_py/notify.py
- [X] T028 [US4] Add error rate checking against ErrorStats in NotificationManager.check() in pgtail_py/notify.py
- [X] T029 [US4] Implement `notify on errors > N/min` parsing in pgtail_py/cli_notify.py
- [X] T030 [US4] Implement config persistence for error_rate threshold in pgtail_py/cli_notify.py

**Checkpoint**: User Story 4 complete - error rate threshold notifications working

---

## Phase 7: User Story 5 - Slow Query Notifications (Priority: P2)

**Goal**: Alert when query duration exceeds threshold

**Independent Test**: Run `notify on slow > 500ms`, run query taking 600ms, verify notification

### Implementation for User Story 5

- [X] T031 [US5] Implement SLOW_QUERY rule type in NotificationRule in pgtail_py/notify.py
- [X] T032 [US5] Add slow query checking (extract duration from entry) in NotificationManager.check() in pgtail_py/notify.py
- [X] T033 [US5] Implement `notify on slow > Nms` parsing with duration conversion in pgtail_py/cli_notify.py
- [X] T034 [US5] Implement config persistence for slow_query_ms threshold in pgtail_py/cli_notify.py

**Checkpoint**: User Story 5 complete - slow query notifications working

---

## Phase 8: User Story 6 - Quiet Hours (Priority: P3)

**Goal**: Suppress notifications during configured time ranges

**Independent Test**: Set quiet hours to current time range, trigger alert, verify no notification appears

### Implementation for User Story 6

- [X] T035 [US6] Integrate QuietHours checking in NotificationManager.check() flow in pgtail_py/notify.py
- [X] T036 [US6] Implement `notify quiet HH:MM-HH:MM` parsing and validation in pgtail_py/cli_notify.py
- [X] T037 [US6] Implement `notify quiet off` handler in pgtail_py/cli_notify.py
- [X] T038 [US6] Add "(active)" indicator to status display when in quiet period in pgtail_py/cli_notify.py

**Checkpoint**: User Story 6 complete - quiet hours suppress notifications

---

## Phase 9: User Story 7 - Test and Status Commands (Priority: P3)

**Goal**: Enable users to verify notification setup and view configuration

**Independent Test**: Run `notify test`, verify notification appears; run `notify`, verify status displayed

### Implementation for User Story 7

- [X] T039 [US7] Implement `notify test` command that bypasses rate limiting and quiet hours in pgtail_py/cli_notify.py
- [X] T040 [US7] Implement `notify` (status) command showing all settings in pgtail_py/cli_notify.py
- [X] T041 [US7] Implement `notify clear` command to remove all rules in pgtail_py/cli_notify.py
- [X] T042 [US7] Add platform info and availability hints to status output in pgtail_py/cli_notify.py
- [X] T043 [US7] Handle notification unavailability with helpful error messages in pgtail_py/cli_notify.py

**Checkpoint**: User Story 7 complete - test and status commands working

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T044 [P] Add docstrings to all public functions in pgtail_py/notify.py
- [X] T045 [P] Add docstrings to all public functions in pgtail_py/notifier.py
- [X] T046 [P] Add docstrings to all public functions in pgtail_py/cli_notify.py
- [X] T047 [P] Add type hints to all functions across notification modules
- [X] T048 Update CLAUDE.md with new notification modules and commands
- [X] T049 Run quickstart.md validation (manual verification of setup guide)
- [X] T050 Verify graceful degradation when notification system unavailable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (P1) and US2 (P1) are both high priority, but US2 depends on US1 foundation
  - US3, US4, US5 (all P2) can proceed after US1/US2
  - US6, US7 (both P3) can proceed after foundational
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Level-Based)**: Can start after Foundational - Core MVP
- **US2 (Rate Limiting)**: Builds on US1 notification sending
- **US3 (Pattern-Based)**: Independent of US1/US2, can parallel
- **US4 (Error Rate)**: Independent, needs ErrorStats reference
- **US5 (Slow Query)**: Independent, needs duration extraction
- **US6 (Quiet Hours)**: Independent of rule types
- **US7 (Test/Status)**: Depends on all command implementations

### Within Each User Story

- Core logic before CLI parsing
- CLI parsing before command routing
- Command routing before config persistence
- All parts complete before checkpoint

### Parallel Opportunities

**Phase 1 (all parallel)**:
- T001, T002, T003, T004 can all run simultaneously

**Phase 2 (sequential)**:
- T005-T011 have dependencies, run sequentially

**User Stories (after foundational)**:
- US3, US4, US5, US6 can run in parallel (different rule types)
- US7 should run last (needs all commands)

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all setup tasks together:
Task: "Create NotificationRuleType enum and NotificationRule dataclass in pgtail_py/notify.py"
Task: "Create Notifier abstract interface in pgtail_py/notifier.py"
Task: "Create MacOSNotifier and LinuxNotifier in pgtail_py/notifier_unix.py"
Task: "Create WindowsNotifier in pgtail_py/notifier_windows.py"
```

## Parallel Example: P2 User Stories

```bash
# After US1 and US2 complete, launch P2 stories together:
Task: "US3 - Pattern-Based Notifications"
Task: "US4 - Rate-Based Threshold Notifications"
Task: "US5 - Slow Query Notifications"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Level-Based)
4. Complete Phase 4: User Story 2 (Rate Limiting)
5. **STOP and VALIDATE**: Test `notify on FATAL PANIC` + spam prevention
6. Deploy/demo if ready - core functionality complete

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 + US2 → MVP - basic notifications with spam prevention
3. US3 → Pattern matching for targeted alerts
4. US4 + US5 → Threshold-based alerts
5. US6 + US7 → Quality of life features
6. Polish → Documentation and cleanup

---

## Summary

| Phase | Tasks | Parallel | Description |
|-------|-------|----------|-------------|
| Setup | T001-T004 | 4 | Module scaffolding |
| Foundational | T005-T011 | 0 | Core infrastructure |
| US1 (P1) | T012-T018 | 0 | Level-based notifications |
| US2 (P1) | T019-T021 | 0 | Rate limiting |
| US3 (P2) | T022-T026 | 0 | Pattern-based |
| US4 (P2) | T027-T030 | 0 | Error rate threshold |
| US5 (P2) | T031-T034 | 0 | Slow query threshold |
| US6 (P3) | T035-T038 | 0 | Quiet hours |
| US7 (P3) | T039-T043 | 0 | Test and status |
| Polish | T044-T050 | 4 | Documentation |

**Total Tasks**: 50
**MVP Tasks**: 25 (through US2)
**Suggested MVP**: User Stories 1 + 2 (level-based notifications with rate limiting)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Config already has NotificationsSection - extend rather than replace
