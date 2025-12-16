# Tasks: Configuration File Support

**Input**: Design documents from `/specs/005-config-file/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification. Test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `pgtail_py/` package, `tests/` at repository root
- Paths follow existing project structure from plan.md

---

## Phase 1: Setup

**Purpose**: Add tomlkit dependency and prepare project for configuration support

- [x] T001 Add tomlkit>=0.12.0 to dependencies in pyproject.toml
- [x] T002 Run `uv sync` or `pip install -e .` to install new dependency

---

## Phase 2: Foundational (Core Config Module)

**Purpose**: Core configuration infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Define ConfigSchema dataclass with all sections and defaults in pgtail_py/config.py
- [x] T004 Implement get_config_path() for platform-specific config locations in pgtail_py/config.py
- [x] T005 Implement load_config() with graceful degradation (warn and continue) in pgtail_py/config.py
- [x] T006 Implement save_config() with comment preservation using tomlkit in pgtail_py/config.py
- [x] T007 Implement per-key validation with helpful error messages in pgtail_py/config.py
- [x] T008 Add SETTINGS_SCHEMA dict with validators for all config keys in pgtail_py/config.py
- [x] T009 Implement get_nested() and set_nested() helpers for dotted key paths in pgtail_py/config.py
- [x] T010 Define DEFAULT_CONFIG_TEMPLATE string with commented sections in pgtail_py/config.py
- [x] T011 Load config in AppState.__init__() and store in self.config in pgtail_py/cli.py
- [x] T012 Apply config.slow.* thresholds to SlowQueryTracker on startup in pgtail_py/cli.py
- [x] T013 Apply config.default.levels to level_filter on startup in pgtail_py/cli.py

**Checkpoint**: Foundation ready - config loads on startup and applies settings

---

## Phase 3: User Story 1 - Set and Persist Configuration Values (Priority: P1) 🎯 MVP

**Goal**: Users can save settings with `set` command that persist across sessions

**Independent Test**: Run `set slow.warn 50`, exit pgtail, restart, verify threshold is 50ms

### Implementation for User Story 1

- [ ] T014 [US1] Register `set` command in COMMANDS dict in pgtail_py/commands.py
- [ ] T015 [US1] Add SETTING_KEYS list for autocomplete in pgtail_py/commands.py
- [ ] T016 [US1] Update PgtailCompleter to complete setting keys after `set` in pgtail_py/commands.py
- [ ] T017 [US1] Implement cmd_set() handler in pgtail_py/cli.py
- [ ] T018 [US1] Implement parse_value() for type conversion (bool, int, list, str) in pgtail_py/config.py
- [ ] T019 [US1] Handle `set <key>` (no value) to display current value in pgtail_py/cli.py
- [ ] T020 [US1] Handle `set <key> <value>` to validate, save, and apply setting in pgtail_py/cli.py
- [ ] T021 [US1] Create config file and parent dirs on first set if needed in pgtail_py/config.py
- [ ] T022 [US1] Update in-memory state immediately after set (slow thresholds, level filter) in pgtail_py/cli.py

**Checkpoint**: User Story 1 complete - settings persist across sessions

---

## Phase 4: User Story 2 - View Current Configuration (Priority: P2)

**Goal**: Users can view all settings with `config` command

**Independent Test**: Run `config` command, verify it shows file path and all current settings

### Implementation for User Story 2

- [ ] T023 [US2] Register `config` command with subcommands in COMMANDS dict in pgtail_py/commands.py
- [ ] T024 [US2] Update PgtailCompleter to complete `edit`, `reset`, `path` after `config` in pgtail_py/commands.py
- [ ] T025 [US2] Implement cmd_config() handler to display current config in pgtail_py/cli.py
- [ ] T026 [US2] Format output as TOML with config file path header in pgtail_py/cli.py
- [ ] T027 [US2] Show default values when config file doesn't exist in pgtail_py/cli.py
- [ ] T028 [US2] Implement cmd_config_path() to show config file location in pgtail_py/cli.py

**Checkpoint**: User Story 2 complete - users can view configuration

---

## Phase 5: User Story 3 - Edit Configuration Directly (Priority: P3)

**Goal**: Power users can edit config file in $EDITOR

**Independent Test**: Run `config edit`, verify editor opens with config file

### Implementation for User Story 3

- [ ] T029 [US3] Implement cmd_config_edit() handler in pgtail_py/cli.py
- [ ] T030 [US3] Check $EDITOR environment variable and show helpful error if not set in pgtail_py/cli.py
- [ ] T031 [US3] Create config file with DEFAULT_CONFIG_TEMPLATE if it doesn't exist in pgtail_py/cli.py
- [ ] T032 [US3] Open editor using subprocess and wait for exit in pgtail_py/cli.py
- [ ] T033 [US3] Reload config after editor closes and apply changes in pgtail_py/cli.py

**Checkpoint**: User Story 3 complete - users can edit config in $EDITOR

---

## Phase 6: User Story 4 - Reset Configuration (Priority: P3)

**Goal**: Users can reset to defaults with backup preserved

**Independent Test**: Run `config reset`, verify backup created and defaults restored

### Implementation for User Story 4

- [ ] T034 [US4] Implement cmd_config_reset() handler in pgtail_py/cli.py
- [ ] T035 [US4] Check if config file exists, show message if not in pgtail_py/cli.py
- [ ] T036 [US4] Create timestamped backup file (.bak.YYYYMMDD-HHMMSS) in pgtail_py/cli.py
- [ ] T037 [US4] Delete original config file after backup in pgtail_py/cli.py
- [ ] T038 [US4] Reset in-memory config to defaults in pgtail_py/cli.py
- [ ] T039 [US4] Display confirmation with backup file path in pgtail_py/cli.py

**Checkpoint**: User Story 4 complete - users can reset with backup

---

## Phase 7: User Story 5 - Remove Individual Settings (Priority: P3)

**Goal**: Users can remove specific settings to revert to defaults

**Independent Test**: Run `unset slow.warn`, verify setting removed and default used

### Implementation for User Story 5

- [ ] T040 [US5] Register `unset` command in COMMANDS dict in pgtail_py/commands.py
- [ ] T041 [US5] Update PgtailCompleter to complete setting keys after `unset` in pgtail_py/commands.py
- [ ] T042 [US5] Implement cmd_unset() handler in pgtail_py/cli.py
- [ ] T043 [US5] Validate key exists in schema in pgtail_py/cli.py
- [ ] T044 [US5] Remove key from config file using tomlkit in pgtail_py/config.py
- [ ] T045 [US5] Revert in-memory value to default and apply in pgtail_py/cli.py
- [ ] T046 [US5] Show confirmation with default value in pgtail_py/cli.py

**Checkpoint**: User Story 5 complete - users can unset individual settings

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration and documentation

- [ ] T047 Verify all edge cases from spec (invalid TOML, invalid values, permissions) in pgtail_py/config.py
- [ ] T048 Add config-related entries to help command output in pgtail_py/commands.py
- [ ] T049 Update CLAUDE.md with new commands documentation
- [ ] T050 Run `make lint` and fix any issues
- [ ] T051 Run `make test` and verify existing tests pass
- [ ] T052 Manual testing: run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3)
  - US3, US4, US5 are all P3 and can be done in any order
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2/US3
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2/US3/US4

### Within Each User Story

- Commands registered before handlers implemented
- Autocomplete before handlers
- Core functionality before edge cases
- Story complete before moving to next priority

### Parallel Opportunities

- T001 and T002 are sequential (dependency first, then install)
- T003-T010 in Phase 2 modify same file (config.py) - must be sequential
- T011-T013 in Phase 2 modify cli.py - must be sequential with each other but can follow config.py work
- Within each user story, command registration can happen in parallel with autocomplete updates
- All P3 user stories (US3, US4, US5) can be worked on in parallel by different developers

---

## Parallel Example: Foundational Phase

```bash
# These must be sequential (same file):
Task T003: Define ConfigSchema dataclass in pgtail_py/config.py
Task T004: Implement get_config_path() in pgtail_py/config.py
Task T005: Implement load_config() in pgtail_py/config.py
# ... continue sequentially through T010

# Then these can follow (different file):
Task T011: Load config in AppState.__init__() in pgtail_py/cli.py
Task T012: Apply slow thresholds in pgtail_py/cli.py
Task T013: Apply level filter in pgtail_py/cli.py
```

---

## Parallel Example: Multiple P3 Stories

```bash
# After Foundational complete, these can run in parallel with different developers:

# Developer A - User Story 3:
Task T029-T033: config edit implementation

# Developer B - User Story 4:
Task T034-T039: config reset implementation

# Developer C - User Story 5:
Task T040-T046: unset implementation
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (2 tasks)
2. Complete Phase 2: Foundational (11 tasks) - CRITICAL
3. Complete Phase 3: User Story 1 (9 tasks)
4. **STOP and VALIDATE**: Test `set` command and persistence
5. Deploy/demo if ready - users can now save settings!

### Incremental Delivery

1. Setup + Foundational → Foundation ready (13 tasks)
2. Add User Story 1 → Settings persist (MVP!) (+9 tasks = 22 total)
3. Add User Story 2 → Can view config (+6 tasks = 28 total)
4. Add User Story 3 → Can edit in $EDITOR (+5 tasks = 33 total)
5. Add User Story 4 → Can reset with backup (+6 tasks = 39 total)
6. Add User Story 5 → Can unset individual (+7 tasks = 46 total)
7. Polish → Production ready (+6 tasks = 52 total)

---

## Notes

- [P] tasks = different files, no dependencies (limited in this feature due to shared files)
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Most config.py and cli.py changes are sequential within phases
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
