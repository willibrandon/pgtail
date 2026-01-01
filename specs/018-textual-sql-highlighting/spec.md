# Feature Specification: SQL Syntax Highlighting in Textual Tail Mode

**Feature Branch**: `018-textual-sql-highlighting`
**Created**: 2025-12-31
**Status**: Draft
**Input**: User description: "Port SQL syntax highlighting from prompt_toolkit mode to Textual-based tail mode"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View SQL with Keyword Highlighting (Priority: P1)

A developer tailing PostgreSQL logs wants to quickly scan for query structure. When log entries contain SQL statements, keywords like SELECT, FROM, WHERE, JOIN should be visually distinct from table names and values, making it easy to understand query structure at a glance.

**Why this priority**: This is the core value proposition - without keyword highlighting, users cannot quickly parse SQL structure in busy log output.

**Independent Test**: Can be fully tested by tailing a PostgreSQL instance with statement logging enabled and verifying keywords appear in a distinct color.

**Acceptance Scenarios**:

1. **Given** tail mode is active and a log entry contains `LOG: statement: SELECT id FROM users WHERE active = true`, **When** the entry is displayed, **Then** SELECT, FROM, and WHERE appear in blue/bold, while `id`, `users`, and `active` appear in cyan.
2. **Given** tail mode is active with multiple SQL statements, **When** scrolling through logs, **Then** SQL keywords are consistently highlighted across all entries.
3. **Given** tail mode is in PAUSED mode, **When** viewing buffered entries, **Then** SQL highlighting is applied identically to FOLLOW mode.

---

### User Story 2 - Distinguish Literals from Identifiers (Priority: P1)

A developer debugging a query with incorrect parameters wants to quickly spot string literals and numeric values in SQL. String literals should appear in a different color than column names, making parameter values immediately identifiable.

**Why this priority**: Equal to P1 because distinguishing literals from identifiers is essential for debugging parameterized queries and understanding data flow.

**Independent Test**: Can be tested by logging queries with various literal types and verifying each is styled distinctly.

**Acceptance Scenarios**:

1. **Given** a log entry contains `WHERE name = 'John'`, **When** displayed, **Then** the string literal `'John'` appears in green.
2. **Given** a log entry contains `WHERE count > 42`, **When** displayed, **Then** the number `42` appears in magenta.
3. **Given** a log entry contains dollar-quoted strings `$$body$$`, **When** displayed, **Then** the entire dollar-quoted string appears in green.

---

### User Story 3 - Copy SQL Without Markup (Priority: P2)

A developer wants to copy a SQL statement from the log to run it elsewhere. When using visual mode selection (v/V) or mouse selection, the copied text should be plain SQL without any Rich markup tags.

**Why this priority**: Secondary to visual highlighting but essential for practical workflow - users need to be able to reuse SQL from logs.

**Independent Test**: Can be tested by selecting SQL with visual mode, copying, and pasting into a text editor to verify no markup tags are present.

**Acceptance Scenarios**:

1. **Given** a highlighted SQL statement is visible, **When** user enters visual mode (v) and yanks (y) the SQL, **Then** clipboard contains plain SQL without Rich markup tags.
2. **Given** a highlighted SQL statement is visible, **When** user drags to select with mouse and releases, **Then** clipboard contains plain SQL without Rich markup tags.
3. **Given** a multi-line SQL statement spans multiple log lines, **When** user selects across lines, **Then** copied text maintains line breaks without markup.

---

### User Story 4 - Respect NO_COLOR Environment Variable (Priority: P3)

A user with accessibility needs or a monochrome terminal has set the NO_COLOR=1 environment variable. SQL highlighting should be completely disabled, and log entries should display without any color markup.

**Why this priority**: Important for accessibility and terminal compatibility, but affects a smaller user segment.

**Independent Test**: Can be tested by setting NO_COLOR=1 before running pgtail and verifying no colors appear.

**Acceptance Scenarios**:

1. **Given** NO_COLOR=1 is set in environment, **When** tail mode displays SQL statements, **Then** all text appears in default terminal color.
2. **Given** NO_COLOR=1 is set, **When** SQL contains brackets like `arr[1]`, **Then** brackets display correctly without Rich markup interference.

---

### User Story 5 - Theme-Customizable SQL Colors (Priority: P2)

A user who prefers the "solarized-dark" theme or has created a custom theme wants SQL highlighting colors to match their chosen color scheme. SQL token colors should be defined in the theme system, not hardcoded, allowing users to customize appearance via `theme edit`.

**Why this priority**: Equal to P2 (copy without markup) because visual consistency with the chosen theme is essential for user experience, and the theme system already exists.

**Independent Test**: Can be tested by switching themes with `theme <name>` and verifying SQL colors change accordingly.

**Acceptance Scenarios**:

1. **Given** user has selected "monokai" theme, **When** SQL statements are displayed, **Then** SQL keywords use colors defined in the monokai theme.
2. **Given** user runs `theme edit mytheme`, **When** they modify `sql_keyword` color and reload, **Then** SQL keywords display in the new custom color.
3. **Given** user switches from "dark" to "light" theme, **When** viewing the same log entries, **Then** SQL highlighting colors update to light theme values.

---

### Edge Cases

- What happens when SQL contains Rich markup-like brackets (e.g., `SELECT arr[1]`)? Brackets must be escaped to prevent Rich parsing errors.
- How does system handle malformed or partial SQL (e.g., truncated statements)? Recognized tokens are highlighted; unrecognized text displays plain.
- What happens with extremely long SQL statements (>10000 chars)? Performance must not degrade noticeably.
- What happens when SQL contains nested quotes or dollar-quoted strings? Token parser handles PostgreSQL quote escaping rules.
- How are comments in SQL handled (`--` or `/* */`)? Comments display in dim/gray to distinguish from active code.
- What happens when a custom theme is missing SQL token color definitions? System falls back to default "dark" theme colors for missing keys.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST highlight SQL keywords (SELECT, FROM, WHERE, JOIN, etc.) in a distinct color when displaying log entries in tail mode.
- **FR-002**: System MUST highlight string literals (single-quoted, dollar-quoted) in green to distinguish from identifiers.
- **FR-003**: System MUST highlight numeric literals in magenta.
- **FR-004**: System MUST highlight SQL operators (=, <>, >=, ||, ::) in yellow.
- **FR-005**: System MUST highlight SQL comments (-- and /* */) in dim/gray.
- **FR-006**: System MUST highlight function names (when followed by parenthesis) in blue.
- **FR-007**: System MUST highlight table/column identifiers in cyan.
- **FR-008**: System MUST escape brackets within SQL tokens to prevent Rich markup parsing errors.
- **FR-009**: System MUST strip all Rich markup tags when copying text via visual mode or mouse selection.
- **FR-010**: System MUST disable all SQL highlighting when NO_COLOR=1 environment variable is set.
- **FR-011**: System MUST detect SQL content in log messages matching PostgreSQL patterns: `statement:`, `execute <name>:`, `parse <name>:`, `bind <name>:`, `duration: ... statement:`, and `DETAIL:`.
- **FR-012**: System MUST apply highlighting in both FOLLOW and PAUSED modes.
- **FR-013**: System MUST gracefully handle malformed SQL by highlighting recognized tokens and displaying unrecognized text without styling.
- **FR-014**: System MUST integrate SQL token colors into the existing theme system (`theme.py`), allowing colors to be defined per-theme and customized via `theme edit`.
- **FR-015**: System MUST update all built-in themes (dark, light, high-contrast, monokai, solarized-dark, solarized-light) to include SQL token color definitions.
- **FR-016**: System MUST apply theme changes to SQL highlighting immediately when user switches themes via `theme <name>` or `theme reload`.

### Key Entities

- **SQLToken**: A parsed segment of SQL text with type (KEYWORD, IDENTIFIER, STRING, NUMBER, OPERATOR, COMMENT, FUNCTION) and text content.
- **SQLDetectionResult**: Contains prefix (text before SQL), sql (the SQL content), and suffix (text after SQL) extracted from a log message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SQL keywords are visually distinguishable from surrounding text within 100ms of log entry display.
- **SC-002**: Users can identify query structure (SELECT/FROM/WHERE clauses) without reading full statement text.
- **SC-003**: Copying SQL via visual mode produces text that can be directly executed in psql without modification.
- **SC-004**: No visible rendering delay when displaying 100+ log entries per second containing SQL.
- **SC-005**: 100% of PostgreSQL SQL keyword variants (300+ keywords) are correctly highlighted.
- **SC-006**: System handles SQL statements up to 50KB without performance degradation.
- **SC-007**: SQL highlighting colors change immediately when user switches themes, with no restart required.

## Assumptions

- The existing `sql_tokenizer.py` correctly tokenizes all PostgreSQL SQL syntax and requires no modifications.
- The existing `sql_detector.py` correctly identifies SQL content in log messages and requires no modifications.
- Rich markup strings are the appropriate output format for Textual's Log widget (confirmed by `_render_line_strip` using `Text.from_markup()`).
- The existing `_strip_markup()` method in TailLog correctly removes Rich tags for clipboard operations.
- The existing `theme.py` and `ThemeManager` infrastructure can be extended to include SQL token color definitions.
- Default color choices (blue for keywords, cyan for identifiers, green for strings, magenta for numbers, yellow for operators, dim for comments) align with user expectations from common IDE themes and will serve as the "dark" theme baseline.
