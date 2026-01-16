# Tasks: Semantic Log Highlighting

**Input**: Design documents from `/specs/023-semantic-highlighting/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/highlighter.md

**Tests**: Tests are included as this is a core infrastructure feature requiring comprehensive coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` package directory
- **Tests**: `tests/` at repository root
- **Highlighters**: `pgtail_py/highlighters/` subdirectory

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and directory structure

- [X] T001 Add pyahocorasick dependency to pyproject.toml (BSD-3-Clause, cross-platform wheels)
- [X] T002 Create highlighters/ package directory with pgtail_py/highlighters/__init__.py
- [X] T003 [P] Create test file stubs for new modules in tests/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Core Entities (from data-model.md)

- [X] T004 Implement Match dataclass in pgtail_py/highlighter.py (frozen, slots: start, end, style, text)
- [X] T005 Implement OccupancyTracker class in pgtail_py/highlighter.py (is_available, mark_occupied, available_ranges)
- [X] T006 Implement Highlighter protocol in pgtail_py/highlighter.py (name, priority, description, find_matches, apply, apply_rich)
- [X] T007 Implement RegexHighlighter base class in pgtail_py/highlighter.py (pre-compiled patterns, find_matches)
- [X] T008 Implement GroupedRegexHighlighter base class in pgtail_py/highlighter.py (named groups → styles mapping)
- [X] T009 Implement KeywordHighlighter base class in pgtail_py/highlighter.py (Aho-Corasick via pyahocorasick)
- [X] T010 Implement HighlighterChain compositor in pgtail_py/highlighter.py (priority ordering, overlap prevention)
- [X] T011 Implement escape_brackets utility in pgtail_py/highlighter.py (Rich markup escaping)
- [X] T012 Implement depth limiting (max_length) in HighlighterChain.apply_rich() per FR-006

### Registry

- [X] T013 Implement HighlighterRegistry singleton in pgtail_py/highlighter_registry.py (register, get, get_by_category, all_names, all_categories)
- [X] T014 Implement create_chain method in HighlighterRegistry (builds HighlighterChain from HighlightingConfig)

### Configuration

- [X] T015 Add HighlightingSection dataclass to pgtail_py/config.py (enabled: bool, max_length: int)
- [X] T016 Add HighlightingDurationSection dataclass to pgtail_py/config.py (slow, very_slow, critical thresholds)
- [X] T017 Add HighlightingEnabledHighlightersSection dataclass to pgtail_py/config.py (29 highlighter toggles)
- [X] T018 Add CustomHighlighter dataclass to pgtail_py/config.py (name, pattern, style, priority)
- [X] T019 Implement HighlightingConfig class in pgtail_py/highlighting_config.py (runtime state, enable/disable, thresholds)
- [X] T020 Add highlighting.* section parsing to pgtail_py/config.py TOML loader

### Theme Integration (FR-110, FR-111)

- [X] T021 Add get_style(key, fallback) method to Theme class in pgtail_py/theme.py (FR-110)
- [X] T022 [P] Add hl_* style keys to pgtail_py/themes/dark.py (~35 keys per research.md)
- [X] T023 [P] Add hl_* style keys to pgtail_py/themes/light.py
- [X] T024 [P] Add hl_* style keys to pgtail_py/themes/high_contrast.py
- [X] T025 [P] Add hl_* style keys to pgtail_py/themes/monokai.py
- [X] T026 [P] Add hl_* style keys to pgtail_py/themes/solarized_dark.py
- [X] T027 [P] Add hl_* style keys to pgtail_py/themes/solarized_light.py

### Foundational Tests

- [X] T028 Write tests for Match dataclass validation in tests/test_highlighter.py
- [X] T029 Write tests for OccupancyTracker in tests/test_highlighter.py (is_available, mark_occupied, edge cases)
- [X] T030 Write tests for HighlighterChain overlap prevention in tests/test_highlighter.py
- [X] T031 Write tests for escape_brackets in tests/test_highlighter.py
- [X] T032 Write tests for HighlighterRegistry in tests/test_highlighter_registry.py
- [X] T033 Write tests for HighlightingConfig in tests/test_highlighting_config.py
- [X] T034 Write tests for Theme.get_style() in existing tests/test_theme.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Stories 1-3 - Core Highlighting (Priority: P1) 🎯 MVP

### User Story 1 - Automatic Pattern Recognition During Log Tailing (P1)

**Goal**: Automatically colorize timestamps, PIDs, SQLSTATE codes, durations, table names, LSNs during tailing

**Independent Test**: Run `pgtail tail` and observe patterns are colorized according to theme

#### Built-in Highlighters - Structural (FR-010, FR-011, FR-012)

- [X] T035 [P] [US1] Implement TimestampHighlighter in pgtail_py/highlighters/structural.py (date, time, ms, tz)
- [X] T036 [P] [US1] Implement PIDHighlighter in pgtail_py/highlighters/structural.py ([12345], [12345-1])
- [X] T037 [P] [US1] Implement ContextLabelHighlighter in pgtail_py/highlighters/structural.py (DETAIL:, HINT:, CONTEXT:)
- [X] T038 [US1] Register structural highlighters in pgtail_py/highlighters/__init__.py (priorities 100-199)
- [X] T039 [US1] Write tests for structural highlighters in tests/test_highlighters_structural.py

#### Built-in Highlighters - Diagnostic (FR-020, FR-021)

- [X] T040 [P] [US1] Implement SQLStateHighlighter in pgtail_py/highlighters/diagnostic.py (error class coloring)
- [X] T041 [P] [US1] Implement ErrorNameHighlighter in pgtail_py/highlighters/diagnostic.py (unique_violation, deadlock_detected, etc. via Aho-Corasick)
- [X] T042 [US1] Register diagnostic highlighters in pgtail_py/highlighters/__init__.py (priorities 200-299)
- [X] T043 [US1] Write tests for diagnostic highlighters in tests/test_highlighters_diagnostic.py

#### Built-in Highlighters - Performance (FR-030, FR-031, FR-032)

- [X] T044 [P] [US1] Implement DurationHighlighter in pgtail_py/highlighters/performance.py (threshold-based fast/slow/very_slow/critical)
- [X] T045 [P] [US1] Implement MemoryHighlighter in pgtail_py/highlighters/performance.py (bytes, kB, MB, GB, TB)
- [X] T046 [P] [US1] Implement StatisticsHighlighter in pgtail_py/highlighters/performance.py (checkpoint/vacuum counts, percentages)
- [X] T047 [US1] Register performance highlighters in pgtail_py/highlighters/__init__.py (priorities 300-399)
- [X] T048 [US1] Write tests for performance highlighters in tests/test_highlighters_performance.py

#### Built-in Highlighters - Objects (FR-040, FR-041, FR-042)

- [X] T049 [P] [US1] Implement IdentifierHighlighter in pgtail_py/highlighters/objects.py (double-quoted identifiers)
- [X] T050 [P] [US1] Implement RelationHighlighter in pgtail_py/highlighters/objects.py (relation "users", table "orders")
- [X] T051 [P] [US1] Implement SchemaHighlighter in pgtail_py/highlighters/objects.py (schema-qualified names)
- [X] T052 [US1] Register object highlighters in pgtail_py/highlighters/__init__.py (priorities 400-499)
- [X] T053 [US1] Write tests for object highlighters in tests/test_highlighters_objects.py

#### Built-in Highlighters - WAL (FR-050, FR-051, FR-052)

- [X] T054 [P] [US1] Implement LSNHighlighter in pgtail_py/highlighters/wal.py (segment/offset format)
- [X] T055 [P] [US1] Implement WALSegmentHighlighter in pgtail_py/highlighters/wal.py (24-char hex filenames)
- [X] T056 [P] [US1] Implement TxidHighlighter in pgtail_py/highlighters/wal.py (xid, transaction, xmin, xmax)
- [X] T057 [US1] Register WAL highlighters in pgtail_py/highlighters/__init__.py (priorities 500-599)
- [X] T058 [US1] Write tests for WAL highlighters in tests/test_highlighters_wal.py

#### Built-in Highlighters - Connection (FR-060, FR-061, FR-062)

- [X] T059 [P] [US1] Implement ConnectionHighlighter in pgtail_py/highlighters/connection.py (host, port, user, database)
- [X] T060 [P] [US1] Implement IPHighlighter in pgtail_py/highlighters/connection.py (IPv4, IPv6, CIDR)
- [X] T061 [P] [US1] Implement BackendHighlighter in pgtail_py/highlighters/connection.py (autovacuum, checkpointer, etc. via Aho-Corasick)
- [X] T062 [US1] Register connection highlighters in pgtail_py/highlighters/__init__.py (priorities 600-699)
- [X] T063 [US1] Write tests for connection highlighters in tests/test_highlighters_connection.py

#### Built-in Highlighters - SQL (FR-070, FR-071, FR-072, FR-073, FR-074)

- [X] T064 [P] [US1] Implement SQLParamHighlighter in pgtail_py/highlighters/sql.py ($1, $2, etc.)
- [X] T065 [P] [US1] Migrate SQLTokenizer from sql_tokenizer.py to pgtail_py/highlighters/sql.py
- [X] T066 [P] [US1] Implement SQLKeywordHighlighter in pgtail_py/highlighters/sql.py (120+ keywords via Aho-Corasick with category-based styling: DML=select/insert/update/delete, DDL=create/alter/drop, DCL=grant/revoke, TCL=commit/rollback per FR-071)
- [X] T067 [P] [US1] Implement SQLStringHighlighter in pgtail_py/highlighters/sql.py (single/double/dollar-quoted)
- [X] T068 [P] [US1] Implement SQLNumberHighlighter in pgtail_py/highlighters/sql.py (integers, decimals, hex, scientific)
- [X] T069 [P] [US1] Implement SQLOperatorHighlighter in pgtail_py/highlighters/sql.py (=, <>, !=, <=, >=, ||, :: operators per existing sql_tokenizer.py migration)
- [X] T070 [US1] Implement SQL context detection in pgtail_py/highlighters/sql.py (statement:, execute:, parse:, bind: prefixes)
- [X] T071 [US1] Register SQL highlighters in pgtail_py/highlighters/__init__.py (priorities 700-799)
- [X] T072 [US1] Migrate tests from tests/test_sql_highlighter.py to tests/test_highlighters_sql.py

#### Built-in Highlighters - Lock (FR-080, FR-081)

- [X] T073 [P] [US1] Implement LockTypeHighlighter in pgtail_py/highlighters/lock.py (share vs exclusive via Aho-Corasick)
- [X] T074 [P] [US1] Implement LockWaitHighlighter in pgtail_py/highlighters/lock.py (waiting for, acquired, duration)
- [X] T075 [US1] Register lock highlighters in pgtail_py/highlighters/__init__.py (priorities 800-899)
- [X] T076 [US1] Write tests for lock highlighters in tests/test_highlighters_lock.py

#### Built-in Highlighters - Checkpoint (FR-090, FR-091)

- [X] T077 [P] [US1] Implement CheckpointHighlighter in pgtail_py/highlighters/checkpoint.py (starting, complete, trigger, stats)
- [X] T078 [P] [US1] Implement RecoveryHighlighter in pgtail_py/highlighters/checkpoint.py (redo starts/done, ready to accept)
- [X] T079 [US1] Register checkpoint highlighters in pgtail_py/highlighters/__init__.py (priorities 900-999)
- [X] T080 [US1] Write tests for checkpoint highlighters in tests/test_highlighters_checkpoint.py

#### Built-in Highlighters - Misc (FR-100, FR-101, FR-102, FR-103)

- [X] T081 [P] [US1] Implement BooleanHighlighter in pgtail_py/highlighters/misc.py (on/off, true/false, yes/no)
- [X] T082 [P] [US1] Implement NullHighlighter in pgtail_py/highlighters/misc.py (NULL keyword)
- [X] T083 [P] [US1] Implement OIDHighlighter in pgtail_py/highlighters/misc.py (OID patterns)
- [X] T084 [P] [US1] Implement PathHighlighter in pgtail_py/highlighters/misc.py (Unix file paths)
- [X] T085 [US1] Register misc highlighters in pgtail_py/highlighters/__init__.py (priorities 1000+)
- [X] T086 [US1] Write tests for misc highlighters in tests/test_highlighters_misc.py

#### Tail Mode Integration (FR-150)

- [X] T087 [US1] Integrate HighlighterChain into pgtail_py/tail_rich.py format_entry_compact()
- [X] T088 [US1] Remove direct sql_highlighter.py calls from pgtail_py/tail_rich.py
- [X] T089 [US1] Add highlighting state to TailApp in pgtail_py/tail_textual.py
- [X] T090 [US1] Write integration tests for tail mode highlighting in tests/test_highlighting_integration.py

**Checkpoint**: User Story 1 complete - patterns are automatically colorized during tailing

---

### User Story 2 - Theme-Consistent Highlighting (P1)

**Goal**: Highlighting uses colors from current theme; theme switching updates colors immediately

**Independent Test**: Switch themes with `theme dark` / `theme solarized-light` and observe color changes

- [X] T091 [US2] Pass theme parameter through HighlighterChain.apply_rich() call chain in pgtail_py/tail_rich.py
- [X] T092 [US2] Trigger _rebuild_log() on theme switch in pgtail_py/tail_textual.py to re-render with new colors
- [X] T093 [US2] Implement NO_COLOR environment variable check in HighlighterChain (FR-112) in pgtail_py/highlighter.py
- [X] T094 [US2] Write tests for theme switching in tests/test_highlighting_integration.py
- [X] T095 [US2] Write tests for NO_COLOR handling in tests/test_highlighting_integration.py

**Checkpoint**: User Story 2 complete - theme changes immediately update highlight colors

---

### User Story 3 - Non-Overlapping Composable Highlighting (P1)

**Goal**: Multiple highlighters work together without conflicts or double-highlighting

**Independent Test**: View log line with timestamp + PID + SQLSTATE + identifier and verify each is distinctly styled

- [X] T096 [US3] Verify OccupancyTracker prevents overlapping matches in pgtail_py/highlighter.py
- [X] T097 [US3] Implement priority-based conflict resolution (lower priority wins) in HighlighterChain
- [X] T098 [US3] Write tests for multi-pattern overlap scenarios in tests/test_highlighter.py
- [X] T099 [US3] Write tests for nested pattern handling (schema-qualified within relation) in tests/test_highlighter.py

**Checkpoint**: User Story 3 complete - zero overlap artifacts occur

---

### User Story 10 - REPL Mode Integration (P1)

**Goal**: REPL mode displays highlighted log entries matching tail mode

**Independent Test**: Query logs in REPL and verify patterns are highlighted

- [X] T100 [US10] Integrate HighlighterChain into pgtail_py/display.py format functions (FR-151)
- [X] T101 [US10] Remove direct sql_highlighter.py calls from pgtail_py/display.py
- [X] T102 [US10] Implement apply() method returning FormattedText in all highlighters
- [X] T103 [US10] Write tests for REPL highlighting in tests/test_display.py

**Checkpoint**: P1 User Stories complete - MVP ready for validation

---

## Phase 4: User Story 4 - Enable/Disable Highlighters (Priority: P2)

**Goal**: Users can enable/disable individual highlighters to customize their view

**Independent Test**: Run `highlight disable timestamp`, verify timestamps no longer highlighted

### Commands (FR-133, FR-134, FR-135)

- [X] T104 [US4] Implement `highlight list` command in pgtail_py/cli_highlight.py (show all with status)
- [X] T105 [US4] Implement `highlight enable <name>` command in pgtail_py/cli_highlight.py
- [X] T106 [US4] Implement `highlight disable <name>` command in pgtail_py/cli_highlight.py
- [X] T107 [US4] Add highlighter name validation with suggestions for typos in pgtail_py/cli_highlight.py
- [X] T108 [US4] Persist enable/disable state to config.toml via pgtail_py/highlighting_config.py
- [X] T109 [US4] Reload enable/disable state on pgtail restart in pgtail_py/highlighting_config.py
- [X] T110 [US4] Update HighlighterChain to skip disabled highlighters in pgtail_py/highlighter.py
- [X] T111 [US4] Add highlight commands to pgtail_py/commands.py completer with highlighter names
- [X] T112 [US4] Write tests for highlight list/enable/disable in tests/test_cli_highlight.py

**Checkpoint**: User Story 4 complete - individual highlighters can be toggled

---

## Phase 5: User Story 5 - Custom Regex Highlighters (Priority: P2)

**Goal**: Users can add custom regex patterns to highlight application-specific text

**Independent Test**: Run `highlight add request_id "REQ-[0-9]{10}" --style "yellow"`, verify pattern highlighted

### Commands (FR-138, FR-139)

- [X] T113 [US5] Implement `highlight add <name> <pattern> [--style <style>]` command in pgtail_py/cli_highlight.py
- [X] T114 [US5] Implement `highlight remove <name>` command in pgtail_py/cli_highlight.py
- [X] T115 [US5] Implement pattern validation (valid regex, non-zero-length match) in pgtail_py/cli_highlight.py
- [X] T116 [US5] Implement CustomHighlighter class in pgtail_py/highlighter.py (wraps user regex)
- [X] T117 [US5] Persist custom highlighters to config.toml [[highlighting.custom]] array
- [X] T118 [US5] Load custom highlighters on startup in pgtail_py/highlighting_config.py
- [X] T119 [US5] Register custom highlighters in HighlighterRegistry at priority 1050+
- [X] T120 [US5] Write tests for custom highlighter add/remove in tests/test_cli_highlight.py
- [X] T121 [US5] Write tests for invalid regex handling in tests/test_cli_highlight.py

**Checkpoint**: User Story 5 complete - custom patterns can be added and persist

---

## Phase 6: User Story 6 - Global Toggle (Priority: P2)

**Goal**: Users can quickly toggle all highlighting on/off

**Independent Test**: Run `highlight off`, verify plain text output, then `highlight on` to restore

### Commands (FR-130, FR-131, FR-132)

- [X] T122 [US6] Implement `highlight` command (status display) in pgtail_py/cli_highlight.py
- [X] T123 [US6] Implement `highlight on` command in pgtail_py/cli_highlight.py (FR-131)
- [X] T124 [US6] Implement `highlight off` command in pgtail_py/cli_highlight.py (FR-132)
- [X] T125 [US6] Update HighlighterChain to check global enabled state in pgtail_py/highlighter.py
- [X] T126 [US6] Persist global enabled state to config.toml in pgtail_py/highlighting_config.py (FR-120)
- [X] T127 [US6] Write tests for highlight on/off in tests/test_cli_highlight.py

**Checkpoint**: User Story 6 complete - global toggle works

---

## Phase 7: User Story 7 - Duration Thresholds (Priority: P2)

**Goal**: Users can configure what durations count as slow/very_slow/critical

**Independent Test**: Set `highlighting.duration.slow = 50`, verify 75ms is highlighted as slow

- [X] T128 [US7] Implement threshold getters in HighlightingConfig in pgtail_py/highlighting_config.py
- [X] T129 [US7] Implement get_duration_severity(ms) method in HighlightingConfig
- [X] T130 [US7] Update DurationHighlighter to use config thresholds in pgtail_py/highlighters/performance.py
- [X] T131 [US7] Add `set highlighting.duration.slow/very_slow/critical` support in pgtail_py/cli_core.py
- [X] T132 [US7] Write tests for threshold configuration in tests/test_highlighting_config.py

**Checkpoint**: User Story 7 complete - duration thresholds configurable

---

## Phase 8: User Story 11 - Export Without Markup (Priority: P2)

**Goal**: Exports strip highlighting markup by default; --highlighted preserves it

**Independent Test**: Export to file, verify no Rich markup tags present

### Export Integration (FR-152, FR-153, FR-154)

- [X] T133 [US11] Implement strip_rich_markup() function in pgtail_py/export.py
- [X] T134 [US11] Update format_text_entry() to strip markup by default in pgtail_py/export.py (FR-152)
- [X] T135 [US11] Add --highlighted flag to export command in pgtail_py/cli_core.py (FR-153)
- [X] T136 [US11] Verify JSON export never includes markup in pgtail_py/export.py (FR-154)
- [X] T137 [US11] Write tests for export markup stripping in tests/test_export.py

**Checkpoint**: User Story 11 complete - exports are clean

---

## Phase 9: User Story 8 - Export/Import Configuration (Priority: P3)

**Goal**: Users can export and import highlighting configuration as TOML

**Independent Test**: Run `highlight export --file /tmp/hl.toml`, import on another session

### Commands (FR-140, FR-141)

- [X] T138 [US8] Implement `highlight export [--file <path>]` command in pgtail_py/cli_highlight.py
- [X] T139 [US8] Implement to_dict() method in HighlightingConfig for TOML export
- [X] T140 [US8] Implement `highlight import <path>` command in pgtail_py/cli_highlight.py
- [X] T141 [US8] Implement from_dict() class method in HighlightingConfig for TOML import
- [X] T142 [US8] Validate imported configuration (highlighter names, pattern validity)
- [X] T143 [US8] Write tests for export/import in tests/test_cli_highlight.py

**Checkpoint**: User Story 8 complete - config portable

---

## Phase 10: User Story 9 - Preview (Priority: P3)

**Goal**: Users can preview how patterns will be highlighted

**Independent Test**: Run `highlight preview`, see sample log lines with current settings

### Commands (FR-136)

- [X] T144 [US9] Implement `highlight preview` command in pgtail_py/cli_highlight.py
- [X] T145 [US9] Create sample log lines covering all 29 highlighter patterns
- [X] T146 [US9] Apply current highlighting settings to preview output
- [X] T147 [US9] Show which highlighters are disabled in preview
- [X] T148 [US9] Write tests for preview command in tests/test_cli_highlight.py

**Checkpoint**: User Story 9 complete - preview works

---

## Phase 11: User Story 4 (continued) - Reset Command (Priority: P2)

**Goal**: Users can restore default highlighting configuration

### Command (FR-137)

- [ ] T149 [US4] Implement `highlight reset` command in pgtail_py/cli_highlight.py
- [ ] T150 [US4] Reset enabled highlighters, thresholds, and custom patterns to defaults
- [ ] T151 [US4] Write tests for reset command in tests/test_cli_highlight.py

---

## Phase 12: Migration & Cleanup

**Purpose**: Remove legacy SQL highlighting modules, update imports

- [ ] T152 Remove pgtail_py/sql_highlighter.py (migrated to highlighters/sql.py)
- [ ] T153 Remove pgtail_py/sql_tokenizer.py (migrated to highlighters/sql.py)
- [ ] T154 Remove pgtail_py/sql_detector.py (integrated into highlighters/sql.py)
- [ ] T155 Update all imports from sql_highlighter to highlighters.sql across codebase
- [ ] T156 Update all imports from sql_tokenizer to highlighters.sql across codebase
- [ ] T157 Update all imports from sql_detector to highlighters.sql across codebase
- [ ] T158 Run full test suite to verify no broken imports

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Performance optimization, edge cases, final validation

### Performance (FR-160, FR-161, FR-162)

- [ ] T159 [P] Implement lazy Aho-Corasick automaton building in KeywordHighlighter
- [ ] T160 [P] Add benchmark tests for 10,000 lines/second throughput in tests/test_highlighting_integration.py
- [ ] T161 [P] Implement help screen highlighting cache (FR-161)
- [ ] T162 Profile and optimize hot paths in HighlighterChain.apply_rich()

### Edge Cases

- [ ] T163 [P] Test extremely long lines (>10KB) with depth limiting
- [ ] T164 [P] Test zero-length regex pattern rejection
- [ ] T165 [P] Test Rich markup-like content escaping ([bold] in logs)
- [ ] T166 [P] Test invalid config file handling (graceful fallback)
- [ ] T167 [P] Test CSV/JSON log format highlighting (verify highlighting applies to formatted display output regardless of underlying format per Edge Case #9, including structured field values like message, detail, hint)

### Documentation

- [ ] T168 [P] Update CLAUDE.md with semantic highlighting section
- [ ] T169 [P] Add highlight command examples to help text
- [ ] T170 [P] Create docs/guide/highlighting.md with semantic highlighting user guide (patterns, commands, configuration, custom patterns)
- [ ] T171 [P] Update mkdocs.yml nav to add "Highlighting: guide/highlighting.md" under User Guide section
- [ ] T172 [P] Update docs/configuration.md with [highlighting] section (enabled, max_length, duration thresholds, per-highlighter settings)
- [ ] T173 [P] Update docs/cli-reference.md with highlight commands (list, enable, disable, add, remove, on, off, preview, reset, export, import)
- [ ] T174 Run specs/023-semantic-highlighting/quickstart.md validation

### Requirement Coverage (FR-004, FR-005)

- [ ] T175 [P] Verify regex patterns are compiled once at instantiation in RegexHighlighter/GroupedRegexHighlighter (FR-004) in tests/test_highlighter.py
- [ ] T176 [P] Implement and test zero-allocation early return when no patterns match in HighlighterChain (FR-005) in pgtail_py/highlighter.py
- [ ] T177 [P] Test missing hl_* theme key fallback behavior (Edge Case #4) in tests/test_highlighting_integration.py

### Final Validation

- [ ] T178 Run full test suite: `make test`
- [ ] T179 Run linting: `make lint`
- [ ] T180 Manual testing: tail PostgreSQL logs with all highlighters

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3 (US1-3, US10)**: All depend on Phase 2 - P1 MVP
- **Phases 4-10**: Depend on Phase 3 completion - can proceed in priority order
- **Phase 11**: Depends on Phase 4 (adds reset to US4)
- **Phase 12**: Depends on Phase 3 (SQL migration)
- **Phase 13**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Automatic Pattern Recognition)**: Foundation required - core highlighters
- **US2 (Theme-Consistent)**: Depends on US1 highlighters existing
- **US3 (Non-Overlapping)**: Depends on US1 highlighters existing
- **US10 (REPL Mode)**: Depends on US1 highlighters existing
- **US4-9, US11**: Can start after Phase 3, proceed in priority order

### Within Each User Story

- Highlighter implementations before registration
- Registration before integration
- Integration before tests
- All tests pass before checkpoint

### Parallel Opportunities

- Phase 2: T022-T027 (theme updates) can run in parallel
- US1: All highlighter implementations in same category can run in parallel (T035-T037, T040-T041, etc.)
- Different user stories can be worked on in parallel by different developers after Phase 3

---

## Parallel Examples

### Phase 2: Theme Updates (T022-T027)

```bash
# All 6 theme files can be updated in parallel:
Task: T022 - Add hl_* keys to dark.py
Task: T023 - Add hl_* keys to light.py
Task: T024 - Add hl_* keys to high_contrast.py
Task: T025 - Add hl_* keys to monokai.py
Task: T026 - Add hl_* keys to solarized_dark.py
Task: T027 - Add hl_* keys to solarized_light.py
```

### US1: Structural Highlighters (T035-T037)

```bash
# All 3 structural highlighters can be implemented in parallel:
Task: T035 - TimestampHighlighter
Task: T036 - PIDHighlighter
Task: T037 - ContextLabelHighlighter
```

### US1: All Category Highlighters

```bash
# Highlighters in different categories can be implemented in parallel:
Task: T040 - SQLStateHighlighter (diagnostic)
Task: T044 - DurationHighlighter (performance)
Task: T049 - IdentifierHighlighter (objects)
Task: T054 - LSNHighlighter (wal)
# etc.
```

---

## Implementation Strategy

### MVP First (Phase 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1-3, US10 (P1 stories)
4. **STOP and VALIDATE**: Test all 29 highlighters working in tail and REPL modes
5. Deploy/demo if ready

### Incremental Delivery

1. Phases 1-3 → P1 MVP ready (automatic highlighting in tail and REPL)
2. Add Phase 4 (US4) → Enable/disable highlighters
3. Add Phase 5 (US5) → Custom regex patterns
4. Add Phase 6 (US6) → Global toggle
5. Add Phase 7 (US7) → Duration thresholds
6. Add Phase 8 (US11) → Clean exports
7. Add Phases 9-10 (US8, US9) → Config portability and preview
8. Each phase adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers after Phase 2:

1. Developer A: US1 highlighter implementations (T035-T085)
2. Developer B: US2-US3 integration work (T090-T098)
3. Developer C: Phase 4-6 command implementations (T103-T126)

---

## Summary

| Phase | User Story | Task Count | Priority |
|-------|------------|------------|----------|
| 1 | Setup | 3 | - |
| 2 | Foundational | 31 | - |
| 3 | US1, US2, US3, US10 | 69 | P1 (MVP) |
| 4 | US4 (Enable/Disable) | 9 | P2 |
| 5 | US5 (Custom Regex) | 9 | P2 |
| 6 | US6 (Global Toggle) | 6 | P2 |
| 7 | US7 (Duration Thresholds) | 5 | P2 |
| 8 | US11 (Export) | 5 | P2 |
| 9 | US8 (Export/Import) | 6 | P3 |
| 10 | US9 (Preview) | 5 | P3 |
| 11 | US4 (Reset) | 3 | P2 |
| 12 | Migration | 7 | - |
| 13 | Polish | 22 | - |
| **Total** | | **180** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests pass after each checkpoint
- Commit after each task or logical group
- Stop at any checkpoint to validate functionality independently
