# Tasks: SQL Syntax Highlighting

**Input**: Design documents from `/specs/014-sql-highlighting/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Unit tests included as specified in plan.md (pytest for tokenizer and integration tests)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- **Source**: `pgtail_py/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Create new module files and establish basic structure

- [x] T001 [P] Create SQL tokenizer module skeleton in pgtail_py/sql_tokenizer.py with SQLTokenType enum and SQLToken dataclass
- [x] T002 [P] Create SQL highlighter module skeleton in pgtail_py/sql_highlighter.py with SQLHighlighter class stub
- [x] T003 [P] Create SQL detector module skeleton in pgtail_py/sql_detector.py with detect_sql_content() stub

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add SQL color style keys (sql_keyword, sql_identifier, sql_string, sql_number, sql_operator, sql_comment, sql_function) to Theme.ui validation in pgtail_py/theme.py
- [x] T005 [P] Add SQL colors to dark theme in pgtail_py/themes/dark.py
- [x] T006 [P] Add SQL colors to light theme in pgtail_py/themes/light.py
- [x] T007 [P] Add SQL colors to high-contrast theme in pgtail_py/themes/high_contrast.py
- [x] T008 [P] Add SQL colors to monokai theme in pgtail_py/themes/monokai.py
- [x] T009 [P] Add SQL colors to solarized-dark theme in pgtail_py/themes/solarized_dark.py
- [x] T010 [P] Add SQL colors to solarized-light theme in pgtail_py/themes/solarized_light.py
- [x] T011 Implement SQLDetector.detect_sql_content() with PostgreSQL log prefix patterns (LOG: statement:, LOG: execute, DETAIL:, ERROR:) in pgtail_py/sql_detector.py
- [x] T012 Update THEME_TEMPLATE in pgtail_py/theme.py to include SQL color placeholders for custom themes

**Checkpoint**: Foundation ready - theme integration and SQL detection complete, user story implementation can begin

---

## Phase 3: User Story 1 - Quick Query Type Identification (Priority: P1) 🎯 MVP

**Goal**: Highlight SQL keywords (SELECT, INSERT, UPDATE, DELETE, etc.) so developers can quickly identify query types in logs

**Independent Test**: Tail a PostgreSQL log with mixed query types and verify SQL keywords appear in blue/bold color distinct from surrounding text

### Tests for User Story 1

- [x] T013 [P] [US1] Create unit tests for keyword tokenization in tests/test_sql_tokenizer.py (test SELECT, INSERT, UPDATE, DELETE, FROM, WHERE, JOIN, etc.)
- [x] T014 [P] [US1] Create unit tests for keyword highlighting in tests/test_sql_highlighter.py (test FormattedText output has sql_keyword class)

### Implementation for User Story 1

- [x] T015 [US1] Implement keyword regex pattern (case-insensitive, word boundaries) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T016 [US1] Add all 45+ SQL keywords from FR-002 to keyword set in pgtail_py/sql_tokenizer.py
- [x] T017 [US1] Implement SQLTokenizer.tokenize() method with keyword matching in pgtail_py/sql_tokenizer.py
- [x] T018 [US1] Implement SQLHighlighter.highlight() to convert KEYWORD tokens to FormattedText with sql_keyword style in pgtail_py/sql_highlighter.py
- [x] T019 [US1] Integrate SQL highlighting into format_entry_compact() in pgtail_py/display.py (detect SQL, highlight keywords in message)
- [x] T020 [US1] Add NO_COLOR check to skip highlighting when colors disabled in pgtail_py/sql_highlighter.py

**Checkpoint**: Keywords highlighted in streaming mode - MVP complete, independently testable

---

## Phase 4: User Story 2 - Table and Column Reference Spotting (Priority: P2)

**Goal**: Highlight table and column identifiers in cyan so DBAs can spot table references while scanning logs

**Independent Test**: View logs with queries referencing multiple tables and verify identifiers appear in cyan color

### Tests for User Story 2

- [x] T021 [P] [US2] Add unit tests for identifier tokenization (unquoted and quoted) in tests/test_sql_tokenizer.py
- [x] T022 [P] [US2] Add unit tests for identifier highlighting in tests/test_sql_highlighter.py

### Implementation for User Story 2

- [x] T023 [US2] Implement unquoted identifier regex pattern ([a-zA-Z_][a-zA-Z0-9_]*) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T024 [US2] Implement quoted identifier regex pattern ("...") in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T025 [US2] Add IDENTIFIER and QUOTED_IDENTIFIER token types to tokenize() in pgtail_py/sql_tokenizer.py
- [x] T026 [US2] Add identifier style mapping (sql_identifier) to SQLHighlighter in pgtail_py/sql_highlighter.py

**Checkpoint**: Identifiers highlighted - User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 - Parameter and Literal Debugging (Priority: P3)

**Goal**: Highlight string literals in green and numbers in magenta so developers can distinguish values from column references

**Independent Test**: View logs with queries containing string literals and numeric values, verify each has distinct color

### Tests for User Story 3

- [x] T027 [P] [US3] Add unit tests for string literal tokenization (single-quoted, dollar-quoted) in tests/test_sql_tokenizer.py
- [x] T028 [P] [US3] Add unit tests for numeric literal tokenization in tests/test_sql_tokenizer.py
- [x] T029 [P] [US3] Add unit tests for operator tokenization in tests/test_sql_tokenizer.py
- [x] T030 [P] [US3] Add unit tests for comment tokenization (-- and /* */) in tests/test_sql_tokenizer.py

### Implementation for User Story 3

- [x] T031 [US3] Implement single-quoted string regex pattern ('...') with escape handling in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T032 [US3] Implement dollar-quoted string regex pattern ($$...$$ and $tag$...$tag$) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T033 [US3] Implement numeric literal regex pattern ([0-9]+(\.[0-9]+)?) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T034 [US3] Implement operator regex patterns (multi-char then single-char) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T035 [US3] Implement comment regex patterns (-- and /* */) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T036 [US3] Implement function name detection (identifier followed by open paren) in SQLTokenizer in pgtail_py/sql_tokenizer.py
- [x] T037 [US3] Add STRING, NUMBER, OPERATOR, COMMENT, FUNCTION style mappings to SQLHighlighter in pgtail_py/sql_highlighter.py
- [x] T038 [US3] Ensure token matching order follows research.md (comments first, then strings, then keywords, etc.) in pgtail_py/sql_tokenizer.py

**Checkpoint**: All token types highlighted - full SQL highlighting in streaming mode

---

## Phase 6: User Story 4 - Fullscreen TUI Log Browsing (Priority: P4)

**Goal**: Ensure SQL highlighting works identically in fullscreen TUI mode as in streaming mode

**Independent Test**: Enter fullscreen mode while tailing logs with SQL statements, verify highlighting appears correctly and search highlighting layers properly

### Tests for User Story 4

- [x] T039 [P] [US4] Add integration test for SQL highlighting in fullscreen display in tests/test_display_sql.py

### Implementation for User Story 4

- [x] T040 [US4] Integrate SQL highlighting into format_entry_full() in pgtail_py/display.py
- [x] T041 [US4] Integrate SQL highlighting into format_entry_custom() in pgtail_py/display.py
- [x] T042 [US4] Verify FormattedText with SQL highlighting renders correctly in fullscreen buffer (pgtail_py/fullscreen/buffer.py)
- [x] T043 [US4] Test SQL highlighting with search highlighting overlay in fullscreen mode

**Checkpoint**: SQL highlighting works in both streaming and fullscreen modes

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance optimization, edge cases, and documentation

- [ ] T044 [P] Add unit tests for malformed SQL handling (graceful degradation) in tests/test_sql_tokenizer.py
- [ ] T045 [P] Add unit tests for SQL detection edge cases in tests/test_sql_detector.py
- [ ] T046 Add performance test for 10,000-character SQL (verify <100ms) in tests/test_sql_highlighter.py
- [ ] T047 Compile regex patterns at module level for performance in pgtail_py/sql_tokenizer.py
- [ ] T048 Add type annotations to all public functions in SQL modules
- [ ] T049 Add module docstrings to pgtail_py/sql_tokenizer.py, pgtail_py/sql_highlighter.py, pgtail_py/sql_detector.py
- [ ] T050 Run quickstart.md validation - verify SQL highlighting works as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed sequentially in priority order (P1 → P2 → P3 → P4)
  - Each story builds on tokenization infrastructure from previous stories
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Establishes tokenizer foundation
- **User Story 2 (P2)**: Builds on US1 tokenizer - adds identifier patterns
- **User Story 3 (P3)**: Builds on US1+US2 tokenizer - adds literal/operator patterns
- **User Story 4 (P4)**: Builds on US1+US2+US3 - extends to fullscreen display

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Token patterns before highlighting
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All theme update tasks (T005-T010) can run in parallel
- Tests within a story marked [P] can run in parallel
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create unit tests for keyword tokenization in tests/test_sql_tokenizer.py"
Task: "Create unit tests for keyword highlighting in tests/test_sql_highlighter.py"
```

## Parallel Example: Theme Updates

```bash
# Launch all theme updates together:
Task: "Add SQL colors to dark theme in pgtail_py/themes/dark.py"
Task: "Add SQL colors to light theme in pgtail_py/themes/light.py"
Task: "Add SQL colors to high-contrast theme in pgtail_py/themes/high_contrast.py"
Task: "Add SQL colors to monokai theme in pgtail_py/themes/monokai.py"
Task: "Add SQL colors to solarized-dark theme in pgtail_py/themes/solarized_dark.py"
Task: "Add SQL colors to solarized-light theme in pgtail_py/themes/solarized_light.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (skeleton files)
2. Complete Phase 2: Foundational (theme integration, SQL detection)
3. Complete Phase 3: User Story 1 (keyword highlighting)
4. **STOP and VALIDATE**: Test keyword highlighting independently
5. Deploy/demo if ready - keywords highlighted is already valuable

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Keywords highlighted → MVP!
3. Add User Story 2 → Identifiers highlighted → Enhanced!
4. Add User Story 3 → All literals highlighted → Complete!
5. Add User Story 4 → Fullscreen support → Full feature!
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story builds on previous tokenization but can be tested independently
- Tests use pytest as specified in plan.md
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
