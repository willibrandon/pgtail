# Tasks: Color Themes

**Input**: Design documents from `/specs/013-color-themes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification - test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `pgtail_py/` for source, `tests/` for tests
- Paths follow existing pgtail structure per plan.md

---

## Phase 1: Setup

**Purpose**: Create theme module structure and core dataclasses

- [x] T001 Create themes package directory at pgtail_py/themes/
- [x] T002 Create themes package __init__.py at pgtail_py/themes/__init__.py
- [x] T003 Create ColorStyle and Theme dataclasses in pgtail_py/theme.py
- [x] T004 Implement color validation function (ANSI, hex, named colors) in pgtail_py/theme.py
- [x] T005 Implement ColorStyle.to_style_string() conversion in pgtail_py/theme.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ThemeManager core and built-in themes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement ThemeManager class with current_theme, builtin_themes, style fields in pgtail_py/theme.py
- [x] T007 Implement ThemeManager.generate_style() to create prompt_toolkit Style from Theme in pgtail_py/theme.py
- [x] T008 [P] Create dark theme (default) in pgtail_py/themes/dark.py
- [x] T009 [P] Create light theme in pgtail_py/themes/light.py
- [x] T010 [P] Create high-contrast theme in pgtail_py/themes/high_contrast.py
- [x] T011 [P] Create monokai theme in pgtail_py/themes/monokai.py
- [x] T012 [P] Create solarized-dark theme in pgtail_py/themes/solarized_dark.py
- [x] T013 [P] Create solarized-light theme in pgtail_py/themes/solarized_light.py
- [x] T014 Update pgtail_py/themes/__init__.py to export all built-in themes
- [x] T015 Implement ThemeManager.load_builtin_themes() in pgtail_py/theme.py
- [x] T016 Implement get_themes_dir() for custom theme directory path in pgtail_py/theme.py
- [x] T017 Update validate_theme() in pgtail_py/config.py to accept all 6 built-in theme names
- [x] T018 Add ThemeManager to AppState in pgtail_py/cli.py
- [x] T019 Update pgtail_py/colors.py to use ThemeManager.get_style() instead of hardcoded LOG_STYLE

**Checkpoint**: Foundation ready - theme infrastructure complete, all 6 built-in themes defined

---

## Phase 3: User Story 1 - Switch Active Theme (Priority: P1) 🎯 MVP

**Goal**: Users can switch between built-in themes with immediate effect and persistence

**Independent Test**: Run `theme light` and verify all log output uses light theme colors

### Implementation for User Story 1

- [x] T020 [US1] Create cli_theme.py command handler module at pgtail_py/cli_theme.py
- [x] T021 [US1] Implement handle_theme_show() to display current theme in pgtail_py/cli_theme.py
- [x] T022 [US1] Implement ThemeManager.switch_theme(name) method in pgtail_py/theme.py
- [x] T023 [US1] Implement handle_theme_switch(name) command handler in pgtail_py/cli_theme.py
- [x] T024 [US1] Add theme switching to config persistence (save theme.name) in pgtail_py/cli_theme.py
- [x] T025 [US1] Implement error handling for unknown theme names with helpful message in pgtail_py/cli_theme.py
- [x] T026 [US1] Register "theme" command in pgtail_py/commands.py
- [x] T027 [US1] Load saved theme from config on startup in pgtail_py/cli.py
- [x] T028 [US1] Implement graceful fallback to dark theme when saved theme unavailable in pgtail_py/theme.py

**Checkpoint**: User Story 1 complete - users can switch themes, changes persist across restarts

---

## Phase 4: User Story 2 - List and Preview Themes (Priority: P2)

**Goal**: Users can discover available themes and preview them before switching

**Independent Test**: Run `theme list` to see themes, `theme preview monokai` for sample output

### Implementation for User Story 2

- [x] T029 [US2] Implement ThemeManager.list_themes() returning built-in and custom names in pgtail_py/theme.py
- [x] T030 [US2] Implement handle_theme_list() command handler in pgtail_py/cli_theme.py
- [x] T031 [US2] Format theme list output with current theme marker and sections in pgtail_py/cli_theme.py
- [x] T032 [US2] Create generate_sample_log_entries() for preview in pgtail_py/cli_theme.py
- [x] T033 [US2] Implement handle_theme_preview(name) command handler in pgtail_py/cli_theme.py
- [x] T034 [US2] Display all 8 log levels (PANIC through DEBUG) in preview output in pgtail_py/cli_theme.py
- [x] T035 [US2] Register "theme list" and "theme preview" commands in pgtail_py/commands.py
- [x] T036 [US2] Add theme name autocomplete for preview command in pgtail_py/commands.py

**Checkpoint**: User Story 2 complete - users can explore and preview all available themes

---

## Phase 5: User Story 3 - Create Custom Theme (Priority: P3)

**Goal**: Power users can create and use custom TOML-based themes

**Independent Test**: Create custom theme file, run `theme mytheme` to apply

### Implementation for User Story 3

- [x] T037 [US3] Implement load_custom_theme(path) TOML parser in pgtail_py/theme.py
- [x] T038 [US3] Implement ThemeManager.scan_custom_themes() to find themes in config dir in pgtail_py/theme.py
- [x] T039 [US3] Implement ThemeManager.validate_theme(theme) with error messages in pgtail_py/theme.py
- [x] T040 [US3] Create THEME_TEMPLATE constant with sample custom theme TOML in pgtail_py/theme.py
- [x] T041 [US3] Implement handle_theme_edit(name) command handler in pgtail_py/cli_theme.py
- [x] T042 [US3] Create theme template file if not exists in handle_theme_edit() in pgtail_py/cli_theme.py
- [x] T043 [US3] Open $EDITOR for theme file (or show path if no EDITOR) in pgtail_py/cli_theme.py
- [x] T044 [US3] Block editing built-in themes with helpful error message in pgtail_py/cli_theme.py
- [x] T045 [US3] Include custom themes in theme list and autocomplete in pgtail_py/cli_theme.py
- [x] T046 [US3] Register "theme edit" command in pgtail_py/commands.py
- [x] T047 [US3] Handle theme validation errors with line/field information in pgtail_py/cli_theme.py

**Checkpoint**: User Story 3 complete - users can create, validate, and apply custom themes

---

## Phase 6: User Story 4 - Reload Theme Without Restart (Priority: P4)

**Goal**: Users can reload theme after external edits without restarting pgtail

**Independent Test**: Edit theme file externally, run `theme reload` to apply changes

### Implementation for User Story 4

- [ ] T048 [US4] Implement ThemeManager.reload_current() method in pgtail_py/theme.py
- [ ] T049 [US4] Implement handle_theme_reload() command handler in pgtail_py/cli_theme.py
- [ ] T050 [US4] Handle reload errors gracefully (keep previous theme) in pgtail_py/cli_theme.py
- [ ] T051 [US4] Handle deleted theme file (fallback to dark) in pgtail_py/theme.py
- [ ] T052 [US4] Register "theme reload" command in pgtail_py/commands.py

**Checkpoint**: User Story 4 complete - live theme editing workflow fully supported

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, documentation, and cleanup

- [ ] T053 [P] Add NO_COLOR environment variable handling in theme commands in pgtail_py/cli_theme.py
- [ ] T054 [P] Show "colors disabled" note when NO_COLOR=1 and user switches themes in pgtail_py/cli_theme.py
- [ ] T055 [P] Handle missing config directory creation for custom themes in pgtail_py/theme.py
- [ ] T056 Update CLAUDE.md with theme module documentation
- [ ] T057 Verify all theme commands work during active log tailing
- [ ] T058 Validate quickstart.md scenarios work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - Can proceed sequentially in priority order (P1 → P2 → P3 → P4)
  - Or in parallel if team capacity allows
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses ThemeManager.list_themes()
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends with custom theme loading
- **User Story 4 (P4)**: Depends on US3 (reload applies to custom themes primarily)

### Within Each User Story

- ThemeManager methods before command handlers
- Command handlers before command registration
- Core implementation before error handling

### Parallel Opportunities

- T008-T013: All 6 built-in themes can be created in parallel
- T053-T055: Polish tasks can run in parallel
- User Stories 1, 2, 3 can run in parallel after Foundational phase

---

## Parallel Example: Foundational Phase

```bash
# Launch all built-in theme definitions together:
Task: "Create dark theme in pgtail_py/themes/dark.py"
Task: "Create light theme in pgtail_py/themes/light.py"
Task: "Create high-contrast theme in pgtail_py/themes/high_contrast.py"
Task: "Create monokai theme in pgtail_py/themes/monokai.py"
Task: "Create solarized-dark theme in pgtail_py/themes/solarized_dark.py"
Task: "Create solarized-light theme in pgtail_py/themes/solarized_light.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T019)
3. Complete Phase 3: User Story 1 (T020-T028)
4. **STOP and VALIDATE**: Test `theme light`, `theme dark`, restart persistence
5. Deploy/demo if ready - users can now switch themes!

### Incremental Delivery

1. Setup + Foundational → Core theme infrastructure ready
2. Add User Story 1 → Test theme switching → MVP complete
3. Add User Story 2 → Test list/preview → Discovery feature ready
4. Add User Story 3 → Test custom themes → Power user feature ready
5. Add User Story 4 → Test reload → Full feature complete
6. Polish phase → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Theme colors follow prompt_toolkit style string format: "fg:COLOR bg:COLOR bold"
