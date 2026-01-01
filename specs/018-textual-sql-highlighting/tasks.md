# Tasks: SQL Syntax Highlighting in Textual Tail Mode

**Input**: Design documents from `/specs/018-textual-sql-highlighting/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Unit and integration tests are included (referenced in quickstart.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source code**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root
- Paths based on existing project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify prerequisites and project readiness

- [x] T001 Verify on branch `018-textual-sql-highlighting` or create it from main
- [x] T002 Verify existing modules exist and are functional: `pgtail_py/sql_tokenizer.py`, `pgtail_py/sql_detector.py`, `pgtail_py/theme.py`
- [x] T003 [P] Verify all 6 built-in themes have SQL color definitions in `pgtail_py/themes/` (dark.py, light.py, high_contrast.py, monokai.py, solarized_dark.py, solarized_light.py)
- [x] T004 [P] Run existing tests to confirm baseline: `make test`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Add `TOKEN_TYPE_TO_THEME_KEY` mapping constant in `pgtail_py/sql_highlighter.py` mapping SQLTokenType enum values to theme UI keys (sql_keyword, sql_identifier, sql_string, sql_number, sql_operator, sql_comment, sql_function)
- [x] T006 Add `_get_theme_manager()` helper function in `pgtail_py/sql_highlighter.py` for module-level ThemeManager singleton access
- [x] T007 Add `_color_style_to_rich_markup()` helper function in `pgtail_py/sql_highlighter.py` converting ColorStyle to Rich markup tag content (handles bold, dim, italic, underline, fg, bg, ANSI prefix stripping)
- [x] T008 Add `highlight_sql_rich()` function in `pgtail_py/sql_highlighter.py` that tokenizes SQL and returns Rich markup string with theme colors

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View SQL with Keyword Highlighting (Priority: P1) 🎯 MVP

**Goal**: SQL keywords (SELECT, FROM, WHERE, JOIN) are visually distinct from table names and values in tail mode log entries.

**Independent Test**: Tail a PostgreSQL instance with `log_statement = 'all'` and verify keywords appear in distinct blue/bold color while identifiers appear in cyan.

### Tests for User Story 1

- [x] T009 [P] [US1] Add unit tests for `_color_style_to_rich_markup()` in `tests/test_sql_highlighter.py` covering: empty style, fg only, fg+bold, ANSI color stripping, ansibright conversion, hex colors, background colors, dim modifier
- [x] T010 [P] [US1] Add unit tests for `highlight_sql_rich()` in `tests/test_sql_highlighter.py` covering: keywords highlighted, brackets escaped, empty SQL returns empty, string literals styled, numbers styled, comments styled
- [x] T051 [P] [US1] Add unit test in `tests/test_sql_highlighter.py` verifying function detection: `COUNT(*)`, `NOW()`, `COALESCE()` styled as sql_function
- [x] T052 [P] [US1] Add unit test in `tests/test_sql_highlighter.py` verifying keyword coverage with samples from each category: DDL (CREATE, ALTER), DML (SELECT, INSERT), clauses (WHERE, JOIN), operators (AND, OR, NOT)

### Implementation for User Story 1

- [x] T011 [US1] Import `detect_sql_content` from `pgtail_py.sql_detector` and `highlight_sql_rich` from `pgtail_py.sql_highlighter` in `pgtail_py/tail_rich.py`
- [x] T012 [US1] Modify `format_entry_compact()` in `pgtail_py/tail_rich.py` to call `detect_sql_content()` on `entry.message`
- [x] T013 [US1] Add SQL highlighting branch in `format_entry_compact()` in `pgtail_py/tail_rich.py`: when SQL detected, escape prefix, call `highlight_sql_rich()` on SQL portion, escape suffix, join parts
- [x] T014 [US1] Add integration tests for SQL detection in `format_entry_compact()` in `tests/test_tail_rich.py` covering: SQL statement highlighted, no-SQL message escaped, SQL with brackets escaped, execute statement detected
- [x] T053 [US1] Add test in `tests/test_tail_textual.py` verifying SQL highlighting works identically in PAUSED mode as in FOLLOW mode (FR-012)
- [x] T056 [P] [US1] Add async widget tests for SQL highlighting in `tests/test_tail_textual.py` per plan.md: verify TailLog renders SQL with Rich markup correctly

**Checkpoint**: User Story 1 complete - SQL keywords and identifiers visually distinguished in tail mode

---

## Phase 4: User Story 2 - Distinguish Literals from Identifiers (Priority: P1)

**Goal**: String literals appear in green, numeric literals in magenta, making parameter values immediately identifiable.

**Independent Test**: Log queries with string and numeric literals, verify each appears in distinct color matching theme definitions.

### Tests for User Story 2

- [x] T015 [P] [US2] Add unit test in `tests/test_sql_highlighter.py` verifying string literals `'John'` are styled distinctly from identifiers
- [x] T016 [P] [US2] Add unit test in `tests/test_sql_highlighter.py` verifying numeric literals like `42` are styled distinctly
- [x] T017 [P] [US2] Add unit test in `tests/test_sql_highlighter.py` verifying dollar-quoted strings `$$body$$` are styled as strings

### Implementation for User Story 2

- [x] T018 [US2] Verify `SQLTokenizer` in `pgtail_py/sql_tokenizer.py` correctly produces STRING tokens for single-quoted literals (should already work)
- [x] T019 [US2] Verify `SQLTokenizer` in `pgtail_py/sql_tokenizer.py` correctly produces STRING tokens for dollar-quoted strings (should already work)
- [x] T020 [US2] Verify `SQLTokenizer` in `pgtail_py/sql_tokenizer.py` correctly produces NUMBER tokens for numeric literals (should already work)
- [x] T021 [US2] Verify theme mapping in `highlight_sql_rich()` applies sql_string style to STRING tokens and sql_number style to NUMBER tokens

**Checkpoint**: User Story 2 complete - literals visually distinguished from identifiers

---

## Phase 5: User Story 3 - Copy SQL Without Markup (Priority: P2)

**Goal**: When copying SQL via visual mode (v/V) or mouse selection, clipboard contains plain SQL without Rich markup tags.

**Independent Test**: Select highlighted SQL with visual mode, yank (y), paste in text editor - verify no markup tags like `[bold blue]` present.

### Tests for User Story 3

- [x] T022 [P] [US3] Add test in `tests/test_tail_log.py` verifying `_strip_markup()` removes Rich opening tags like `[bold blue]`
- [x] T023 [P] [US3] Add test in `tests/test_tail_log.py` verifying `_strip_markup()` removes Rich closing tags like `[/]`
- [x] T024 [P] [US3] Add test in `tests/test_tail_log.py` verifying `_strip_markup()` unescapes brackets: `\\[` becomes `[`

### Implementation for User Story 3

- [x] T025 [US3] Verify existing `_strip_markup()` method in `pgtail_py/tail_log.py` removes Rich markup tags (regex: `\[/?[^\]]*\]`)
- [x] T026 [US3] Verify existing `_strip_markup()` method in `pgtail_py/tail_log.py` unescapes brackets (`\\[` → `[`)
- [x] T027 [US3] Add integration test in `tests/test_tail_log.py` for full SQL yank flow: Rich markup input → `_strip_markup()` → plain SQL output with proper brackets

**Checkpoint**: User Story 3 complete - copied SQL is clean and executable

---

## Phase 6: User Story 4 - Respect NO_COLOR Environment Variable (Priority: P3)

**Goal**: When NO_COLOR=1 is set, SQL highlighting is completely disabled and all text displays in default terminal color.

**Independent Test**: Set `NO_COLOR=1`, run pgtail tail mode, verify SQL statements have no color styling.

### Tests for User Story 4

- [x] T028 [P] [US4] Add unit test in `tests/test_sql_highlighter.py` verifying `highlight_sql_rich()` returns SQL with only bracket escaping when NO_COLOR=1 is set
- [x] T029 [P] [US4] Add unit test in `tests/test_sql_highlighter.py` verifying no Rich markup tags (no `[/`) in output when NO_COLOR=1

### Implementation for User Story 4

- [x] T030 [US4] Import `is_color_disabled` from `pgtail_py.utils` in `pgtail_py/sql_highlighter.py`
- [x] T031 [US4] Add NO_COLOR check at start of `highlight_sql_rich()` in `pgtail_py/sql_highlighter.py`: if `is_color_disabled()` returns True, return `sql.replace("[", "\\[")`
- [x] T032 [US4] Add integration test in `tests/test_tail_rich.py` verifying `format_entry_compact()` produces no Rich markup when NO_COLOR=1

**Checkpoint**: User Story 4 complete - NO_COLOR compliance verified

---

## Phase 7: User Story 5 - Theme-Customizable SQL Colors (Priority: P2)

**Goal**: SQL token colors are defined in the theme system and change immediately when user switches themes.

**Independent Test**: Run `theme monokai`, verify SQL colors change. Run `theme dark`, verify colors revert.

### Tests for User Story 5

- [x] T033 [P] [US5] Add unit test in `tests/test_sql_highlighter.py` verifying `highlight_sql_rich()` uses passed theme for color lookup
- [x] T034 [P] [US5] Add unit test in `tests/test_sql_highlighter.py` verifying `highlight_sql_rich()` uses global ThemeManager when theme=None
- [x] T035 [P] [US5] Add unit test in `tests/test_sql_highlighter.py` verifying graceful fallback when theme is missing SQL color keys (returns unstyled text)

### Implementation for User Story 5

- [x] T036 [US5] Verify `highlight_sql_rich()` in `pgtail_py/sql_highlighter.py` accepts optional `theme: Theme | None` parameter
- [x] T037 [US5] Verify `highlight_sql_rich()` in `pgtail_py/sql_highlighter.py` uses `_get_theme_manager().current_theme` when theme is None
- [x] T038 [US5] Verify `highlight_sql_rich()` in `pgtail_py/sql_highlighter.py` calls `theme.get_ui_style(theme_key)` for each token
- [x] T039 [US5] Verify all 6 themes in `pgtail_py/themes/` define: sql_keyword, sql_identifier, sql_string, sql_number, sql_operator, sql_comment, sql_function
- [x] T040 [US5] Add integration test in `tests/test_tail_rich.py` simulating theme switch and verifying SQL colors update

**Checkpoint**: User Story 5 complete - theme integration fully functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, performance validation, and final quality checks

- [x] T041 [P] Add edge case test in `tests/test_sql_highlighter.py` for SQL with nested brackets `SELECT arr[1][2]` - verify all brackets escaped
- [x] T042 [P] Add edge case test in `tests/test_sql_highlighter.py` for malformed SQL with unrecognized tokens - verify recognized tokens highlighted, unknown displayed plain
- [x] T043 [P] Add edge case test in `tests/test_sql_highlighter.py` for extremely long SQL (50KB) - verify no performance degradation
- [x] T044 [P] Add edge case test in `tests/test_sql_highlighter.py` for nested quotes and dollar-quoted strings `$tag$body$tag$`
- [x] T045 [P] Add edge case test in `tests/test_sql_highlighter.py` for SQL comments `-- comment` and `/* block */` - verify styled as dim
- [x] T054 [P] Add performance test in `tests/test_tail_rich.py` verifying `format_entry_compact()` completes within 100ms for typical SQL entries (SC-001)
- [x] T055 [P] Add throughput test in `tests/test_tail_rich.py` verifying 100+ entries/sec can be formatted without visible delay (SC-004)
- [x] T046 Run full test suite: `make test` - verify all tests pass
- [x] T047 Run linter: `make lint` - verify no lint errors
- [x] T048 Manual validation per quickstart.md: verify keywords blue/bold, identifiers cyan, strings green, numbers magenta
- [x] T049 Manual validation per quickstart.md: verify theme switching updates SQL colors immediately
- [x] T050 Manual validation per quickstart.md: verify visual mode copy produces clean SQL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 are both P1, can run in parallel
  - US3 and US5 are both P2, can run in parallel
  - US4 is P3, can run last or in parallel with P2 stories
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - requires T005-T008 complete
- **User Story 2 (P1)**: Can start after Foundational - verifies existing tokenizer behavior
- **User Story 3 (P2)**: Can start after US1 - verifies existing strip_markup works with new highlighting
- **User Story 4 (P3)**: Can start after Foundational - independent NO_COLOR handling
- **User Story 5 (P2)**: Can start after US1 - extends theme integration

### Within Each User Story

- Tests MUST be written first
- Verification/implementation tasks follow tests
- Story complete before final checkpoint

### Parallel Opportunities

- T003, T004 can run in parallel (different verification tasks)
- T009, T010, T051, T052 can run in parallel (different test cases in same file)
- T015, T016, T017 can run in parallel (same file but independent tests)
- T022, T023, T024 can run in parallel (independent test cases)
- T028, T029 can run in parallel (independent test cases)
- T033, T034, T035 can run in parallel (independent test cases)
- T041-T045, T054, T055 can run in parallel (independent edge case and performance tests)
- T053, T056 can run in parallel (different async tests in same file)
- US1 and US2 can run in parallel after Foundational (both P1)
- US3, US4, US5 can run in parallel after US1 (independent of each other)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add unit tests for _color_style_to_rich_markup() in tests/test_sql_highlighter.py"
Task: "Add unit tests for highlight_sql_rich() in tests/test_sql_highlighter.py"
Task: "Add function detection test in tests/test_sql_highlighter.py"
Task: "Add keyword coverage test in tests/test_sql_highlighter.py"
Task: "Add async widget tests in tests/test_tail_textual.py"

# After tests written, implementation is sequential (same file):
Task: "Import detect_sql_content and highlight_sql_rich in pgtail_py/tail_rich.py"
Task: "Modify format_entry_compact() to call detect_sql_content()"
Task: "Add SQL highlighting branch in format_entry_compact()"
Task: "Add integration tests in tests/test_tail_rich.py"
Task: "Add PAUSED mode test in tests/test_tail_textual.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test keywords/identifiers distinguished in tail mode
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP: keyword highlighting)
3. Add User Story 2 → Test → Deploy (literals distinguished)
4. Add User Story 3 + 5 in parallel → Test → Deploy (copy + themes)
5. Add User Story 4 → Test → Deploy (NO_COLOR compliance)
6. Polish phase → Final validation

### Single Developer Strategy

1. Complete Setup + Foundational sequentially
2. Work through stories in priority order: US1 → US2 → US3 → US5 → US4
3. Run tests after each story checkpoint
4. Polish phase last

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests pass before moving to next story
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Existing modules (sql_tokenizer.py, sql_detector.py) require NO modifications
- All 6 built-in themes already have SQL color definitions (verified in research.md)
