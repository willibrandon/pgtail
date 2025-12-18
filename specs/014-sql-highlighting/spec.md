# Feature Specification: SQL Syntax Highlighting

**Feature Branch**: `014-sql-highlighting`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Apply syntax highlighting to SQL statements detected in PostgreSQL log messages. Keywords, identifiers, strings, numbers, and operators each get distinct colors. The highlighting should work both in streaming mode and full-screen TUI."

## Clarifications

### Session 2025-12-17

- Q: Should SQL highlighting be always-on or user-controllable? → A: Always-on - SQL highlighting applies automatically when colors are enabled (NO_COLOR=1 disables all colors including SQL highlighting)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quick Query Type Identification (Priority: P1)

A developer scanning PostgreSQL logs needs to quickly identify INSERT statements among many SELECT queries. With SQL syntax highlighting, the INSERT keyword stands out visually in a distinct color, allowing rapid visual scanning without reading each log line in detail.

**Why this priority**: This is the core value proposition of the feature. Without keyword highlighting, the feature provides minimal benefit over the current monochrome display.

**Independent Test**: Can be fully tested by tailing a PostgreSQL log with mixed query types and verifying that SQL keywords appear in distinct colors from surrounding text.

**Acceptance Scenarios**:

1. **Given** a PostgreSQL log with SELECT, INSERT, UPDATE, and DELETE statements, **When** the user views the log in streaming mode, **Then** each SQL keyword type (SELECT, INSERT, UPDATE, DELETE) appears in the configured keyword color (blue/bold by default)
2. **Given** a log line containing `LOG: statement: SELECT id FROM users WHERE active = true`, **When** displayed, **Then** SELECT, FROM, WHERE appear highlighted as keywords while `id`, `users`, `active`, `true` appear in their respective element colors
3. **Given** the user has disabled colors via NO_COLOR=1 environment variable, **When** viewing logs with SQL statements, **Then** no color codes are applied and output remains plain text

---

### User Story 2 - Table and Column Reference Spotting (Priority: P2)

A DBA investigating performance issues needs to find all queries touching a specific table (e.g., "users"). With table/column names highlighted in cyan, they can visually scan the log to spot table references without relying solely on text search.

**Why this priority**: After keyword highlighting, identifier highlighting provides the second-most valuable visual distinction for understanding query structure.

**Independent Test**: Can be tested by viewing logs containing queries with various table and column references and verifying identifiers appear in the configured identifier color.

**Acceptance Scenarios**:

1. **Given** a log with queries referencing multiple tables, **When** displayed, **Then** unquoted table and column names appear in cyan (or configured identifier color)
2. **Given** a query with quoted identifiers like `"MyTable"."MyColumn"`, **When** displayed, **Then** quoted identifiers are highlighted distinctly from unquoted identifiers
3. **Given** a complex JOIN query, **When** displayed, **Then** all table aliases and column references are consistently highlighted as identifiers

---

### User Story 3 - Parameter and Literal Debugging (Priority: P3)

A developer debugging parameterized queries needs to quickly distinguish between string literals (actual values) and column references in WHERE clauses. With string literals highlighted in green and columns in cyan, the distinction is immediately visible.

**Why this priority**: Distinguishing literals from identifiers helps debug data-related issues but is less frequently needed than keyword or identifier recognition.

**Independent Test**: Can be tested by viewing logs with queries containing string literals, numeric literals, and column references, then verifying each type has distinct highlighting.

**Acceptance Scenarios**:

1. **Given** a query with string literal `WHERE name = 'John Doe'`, **When** displayed, **Then** `'John Doe'` appears in green (string literal color) while `name` appears in cyan (identifier color)
2. **Given** a query with numeric literal `WHERE id = 42 AND price = 3.14`, **When** displayed, **Then** `42` and `3.14` appear in magenta (number color)
3. **Given** a query with mixed literals `WHERE status = 'active' AND count > 100`, **When** displayed, **Then** `'active'` is green, `100` is magenta, and `status`, `count` are cyan

---

### User Story 4 - Fullscreen TUI Log Browsing (Priority: P4)

A user in fullscreen TUI mode browsing through historical logs expects the same SQL highlighting as streaming mode. The highlighting should be consistent across both viewing modes.

**Why this priority**: The fullscreen TUI is a secondary viewing mode; core highlighting must work in streaming mode first.

**Independent Test**: Can be tested by entering fullscreen mode while tailing a log with SQL statements and verifying highlighting appears correctly.

**Acceptance Scenarios**:

1. **Given** the user is tailing a log and enters fullscreen mode with `fs` command, **When** scrolling through log entries containing SQL, **Then** SQL statements display with the same highlighting as streaming mode
2. **Given** the user searches for a pattern in fullscreen mode, **When** results include SQL statements, **Then** both the search highlight and SQL highlighting are applied without conflict

---

### Edge Cases

- What happens when a SQL statement spans multiple log lines (continuation)?
  - Highlight each line independently based on content; do not attempt cross-line parsing
- How does the system handle malformed or partial SQL (e.g., truncated by log_line_prefix)?
  - Highlight recognizable tokens; unrecognized portions remain unhighlighted (no errors)
- What happens when log_statement_sample_rate causes partial statement logging?
  - Each logged portion is highlighted independently
- How are PostgreSQL dollar-quoted strings (`$$...$$` or `$tag$...$tag$`) handled?
  - Treat content between dollar quotes as string literals (green)
- How are nested parentheses in function calls handled?
  - Highlight function names in blue; parentheses/content parsed normally
- What happens with very long SQL statements (thousands of characters)?
  - Apply highlighting without performance degradation; no visible lag on high-volume output

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect SQL statements in log messages matching these patterns:
  - `LOG: statement:` prefix lines
  - `LOG: execute <name>:` prepared statement execution lines
  - `DETAIL:` lines containing query context
  - `ERROR:` messages with embedded query context
- **FR-002**: System MUST highlight SQL keywords (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, FROM, WHERE, JOIN, LEFT, RIGHT, INNER, OUTER, ON, AND, OR, NOT, IN, EXISTS, BETWEEN, LIKE, IS, NULL, AS, ORDER, BY, GROUP, HAVING, LIMIT, OFFSET, UNION, INTERSECT, EXCEPT, WITH, VALUES, SET, INTO, DISTINCT, ALL, ANY, CASE, WHEN, THEN, ELSE, END, CAST, COALESCE, NULLIF) in the configured keyword style
- **FR-003**: System MUST highlight table and column identifiers (unquoted names matching `[a-zA-Z_][a-zA-Z0-9_]*` pattern following FROM, JOIN, INTO, UPDATE, or as column references) in the configured identifier style
- **FR-004**: System MUST highlight quoted identifiers (`"identifier"`) distinctly from unquoted identifiers
- **FR-005**: System MUST highlight string literals (single-quoted `'value'` and dollar-quoted `$$value$$` or `$tag$value$tag$`) in the configured string literal style
- **FR-006**: System MUST highlight numeric literals (integers and decimals matching `[0-9]+(\.[0-9]+)?`) in the configured number style
- **FR-007**: System MUST highlight SQL operators (=, <>, !=, <, >, <=, >=, +, -, *, /, ||, ::) in the configured operator style
- **FR-008**: System MUST highlight SQL comments (single-line `--` and multi-line `/* */`) in the configured comment style
- **FR-009**: System MUST highlight SQL function names (identifiers followed by `(`) in the configured function style
- **FR-010**: System MUST apply SQL highlighting in both streaming mode and fullscreen TUI mode
- **FR-011**: System MUST apply SQL highlighting automatically whenever colors are enabled (no separate toggle required)
- **FR-012**: System MUST disable all SQL highlighting when NO_COLOR=1 environment variable is set
- **FR-013**: System MUST integrate SQL highlighting colors with the existing theme system, using theme-defined colors for each SQL element type
- **FR-014**: System MUST NOT introduce visible lag or performance degradation when highlighting high-volume log output
- **FR-015**: System MUST gracefully handle malformed or partial SQL by highlighting recognizable tokens without errors

### Key Entities

- **SQLToken**: Represents a parsed token from SQL text with type (keyword, identifier, string, number, operator, comment, function) and position/length
- **SQLHighlighter**: Component that tokenizes SQL text and produces styled output using the current theme
- **SQLDetector**: Component that identifies SQL content within log messages based on log line patterns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can visually distinguish SQL keywords from surrounding log text within 1 second of viewing a log line
- **SC-002**: All 45+ common SQL keywords listed in FR-002 are correctly highlighted
- **SC-003**: String literals, numeric literals, and identifiers are each displayed in distinct, visually distinguishable colors
- **SC-004**: Highlighting of a 10,000-character SQL statement completes without user-perceptible delay (under 100ms)
- **SC-005**: SQL highlighting remains consistent between streaming mode and fullscreen TUI mode for the same log entry
- **SC-006**: Setting NO_COLOR=1 completely disables SQL highlighting with no color escape codes in output
- **SC-007**: Malformed SQL does not cause errors, crashes, or garbled output; recognizable portions are highlighted correctly

## Assumptions

- PostgreSQL log format is one of: TEXT (stderr), CSV (csvlog), or JSON (jsonlog) - all already supported by pgtail
- SQL statements in logs follow standard PostgreSQL SQL syntax
- The existing theme system (theme.py, ThemeManager) will be extended to include SQL-specific color definitions
- Performance target of <100ms for 10,000 characters is achievable with regex-based tokenization
- Users accept that PL/pgSQL procedure highlighting and query formatting are out of scope
