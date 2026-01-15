# Feature Specification: Semantic Log Highlighting

**Feature Branch**: `023-semantic-highlighting`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: Add composable, extensible semantic highlighting system for PostgreSQL log output with 29 pattern-based highlighters

## Clarifications

### Session 2026-01-14

- Q: How should new SQL highlighters (FR-071 through FR-073) relate to existing sql_highlighter.py/sql_tokenizer.py? → A: Migrate existing SQL highlighting into new system (replace sql_highlighter.py/sql_tokenizer.py with new highlighters)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Pattern Recognition During Log Tailing (Priority: P1)

As a DBA or developer tailing PostgreSQL logs, I want meaningful patterns (timestamps, PIDs, error codes, durations, table names, LSNs) to be automatically colorized so I can quickly scan and understand log output without mental parsing.

**Why this priority**: This is the core value proposition. Without automatic highlighting during tailing, the feature has no purpose. Every other capability builds on this foundation.

**Independent Test**: Can be fully tested by running `pgtail tail` on a PostgreSQL log file and observing that patterns are colorized according to theme settings. Delivers immediate visual distinction of semantic elements.

**Acceptance Scenarios**:

1. **Given** highlighting is enabled (default), **When** a log line containing a timestamp appears, **Then** the date, time, milliseconds, and timezone are each styled with distinct colors defined by the current theme.

2. **Given** highlighting is enabled, **When** a log line contains a SQLSTATE code (e.g., 23505), **Then** the code is highlighted with a color indicating its error class (integrity constraint = red).

3. **Given** highlighting is enabled, **When** a log line shows "duration: 5234.567 ms", **Then** the duration value is highlighted with a critical color (red) because it exceeds the critical threshold (5000ms default).

4. **Given** highlighting is enabled, **When** a log line contains "[12345]" (PID), **Then** the brackets and number are distinctly styled.

5. **Given** highlighting is enabled, **When** a log line contains a quoted identifier like `"users_email_key"`, **Then** the identifier is highlighted to stand out from surrounding text.

6. **Given** highlighting is enabled, **When** a log line contains an LSN like "0/1234ABCD", **Then** the segment and offset portions are distinctly colored.

7. **Given** highlighting is enabled, **When** the log line exceeds the configured max_length (default 10KB), **Then** only the first max_length characters are processed for highlighting to maintain performance.

---

### User Story 2 - Theme-Consistent Highlighting (Priority: P1)

As a user who has configured a preferred color theme, I want semantic highlighting to use colors from my theme so the highlighting integrates visually with my existing setup.

**Why this priority**: Equal to P1 because highlighting without theme integration would produce inconsistent, jarring visuals. Theme integration is mandatory for the feature to be usable.

**Independent Test**: Can be tested by switching themes (e.g., `theme dark`, `theme solarized-light`) and observing that highlighted patterns change colors accordingly.

**Acceptance Scenarios**:

1. **Given** the dark theme is active, **When** log output is displayed, **Then** all highlight colors match the dark theme's highlight style definitions.

2. **Given** a user switches from dark theme to light theme, **When** they continue tailing, **Then** all highlighted patterns immediately use light theme colors.

3. **Given** a custom theme is loaded, **When** the theme includes highlight style keys, **Then** those custom styles are applied to highlighted patterns.

4. **Given** NO_COLOR environment variable is set, **When** log output is displayed, **Then** no highlighting colors are applied (plain text output).

---

### User Story 3 - Non-Overlapping Composable Highlighting (Priority: P1)

As a user viewing complex log lines with multiple patterns, I want highlighters to work together without conflicts so that already-highlighted text isn't re-highlighted and patterns remain readable.

**Why this priority**: Without overlap prevention, the highlighting system would produce garbled, unreadable output when multiple patterns exist on the same line. This is architecturally essential.

**Independent Test**: Can be tested by viewing a log line containing multiple patterns (timestamp, PID, SQLSTATE, identifier) and verifying each is distinctly highlighted without overlap artifacts.

**Acceptance Scenarios**:

1. **Given** a log line contains both a timestamp and an LSN, **When** highlighting is applied, **Then** each pattern is highlighted with its own style without interfering with the other.

2. **Given** a highlighter has already colorized a portion of text, **When** subsequent highlighters run, **Then** they skip the already-highlighted regions and only process unhighlighted text.

3. **Given** a log line contains nested patterns (e.g., schema-qualified name within a relation message), **When** highlighting is applied, **Then** the more specific pattern takes precedence and is not double-highlighted.

---

### User Story 4 - Enable/Disable Specific Highlighters (Priority: P2)

As a user who finds certain highlights distracting or unnecessary, I want to enable or disable individual highlighters so I can customize the highlighting to my preferences.

**Why this priority**: Personalization is important but secondary to core functionality. Users can get value without customization.

**Independent Test**: Can be tested by running `highlight disable timestamp` and verifying timestamps are no longer highlighted while other patterns still are.

**Acceptance Scenarios**:

1. **Given** all highlighters are enabled (default), **When** I run `highlight disable sqlstate`, **Then** SQLSTATE codes are no longer highlighted but all other patterns remain highlighted.

2. **Given** a highlighter is disabled, **When** I run `highlight enable <name>`, **Then** that highlighter begins applying its patterns again.

3. **Given** I have disabled several highlighters, **When** I run `highlight list`, **Then** I see all highlighters with their enabled/disabled status.

4. **Given** I disable a highlighter, **When** I restart pgtail, **Then** my preference persists (stored in config.toml).

---

### User Story 5 - Add Custom Regex Highlighters (Priority: P2)

As a user with application-specific patterns in my logs (e.g., custom transaction IDs, request IDs), I want to add custom highlighters using regex patterns so those patterns are also colorized.

**Why this priority**: Custom patterns extend the value but require the core system to exist first. This enables power users to tailor the feature.

**Independent Test**: Can be tested by running `highlight add myapp "APP-[A-Z]{3}-\\d{6}" --style "bold cyan"` and verifying matching patterns in logs are highlighted.

**Acceptance Scenarios**:

1. **Given** I run `highlight add request_id "REQ-[0-9]{10}" --style "yellow"`, **When** log output contains "REQ-1234567890", **Then** it is highlighted in yellow.

2. **Given** I have added a custom highlighter, **When** I run `highlight list`, **Then** my custom highlighter appears alongside built-in highlighters.

3. **Given** I have a custom highlighter, **When** I run `highlight remove request_id`, **Then** that custom pattern is no longer highlighted.

4. **Given** an invalid regex pattern is provided, **When** I try to add it, **Then** I receive a clear error message explaining the problem.

---

### User Story 6 - Global Highlighting Toggle (Priority: P2)

As a user who sometimes wants raw uncolored output, I want to quickly toggle all highlighting on or off so I can switch between enhanced and plain views.

**Why this priority**: A convenience feature that enhances usability but isn't essential for core functionality.

**Independent Test**: Can be tested by running `highlight off` and verifying no patterns are highlighted, then `highlight on` to restore highlighting.

**Acceptance Scenarios**:

1. **Given** highlighting is enabled, **When** I run `highlight off`, **Then** all pattern highlighting is disabled and output shows plain text (except log level colors).

2. **Given** highlighting is disabled, **When** I run `highlight on`, **Then** all enabled highlighters resume applying patterns.

3. **Given** I run `highlight`, **When** highlighting is enabled, **Then** I see status information showing "enabled" and listing active highlighters.

---

### User Story 7 - Configure Duration Thresholds (Priority: P2)

As a DBA monitoring query performance, I want to configure what durations count as "slow", "very slow", or "critical" so highlighting reflects my environment's performance expectations.

**Why this priority**: Threshold customization provides meaningful personalization for duration highlighting, which is one of the most actionable patterns.

**Independent Test**: Can be tested by configuring `highlighting.duration.slow = 50` and verifying 75ms durations are highlighted as slow.

**Acceptance Scenarios**:

1. **Given** slow threshold is 100ms (default), **When** a log shows "duration: 150.000 ms", **Then** it is highlighted with the slow color (yellow).

2. **Given** I configure slow threshold to 50ms, **When** a log shows "duration: 75.000 ms", **Then** it is highlighted as slow (previously would be fast).

3. **Given** critical threshold is 5000ms (default), **When** a log shows "duration: 6000.000 ms", **Then** it is highlighted with critical color (red, bold).

---

### User Story 8 - Export/Import Highlighting Configuration (Priority: P3)

As a user who configures highlighting on one machine, I want to export and import my configuration so I can share it across machines or with team members.

**Why this priority**: Configuration portability is a convenience feature for advanced users.

**Independent Test**: Can be tested by running `highlight export --file /tmp/highlight.toml`, transferring the file, and importing with `highlight import /tmp/highlight.toml`.

**Acceptance Scenarios**:

1. **Given** I have customized highlighters, **When** I run `highlight export`, **Then** my configuration is output as valid TOML.

2. **Given** I have a TOML configuration file, **When** I run `highlight import <path>`, **Then** the configuration is loaded and applied.

3. **Given** an imported configuration disables certain highlighters, **When** import completes, **Then** those highlighters are disabled.

---

### User Story 9 - Preview Highlighting (Priority: P3)

As a user configuring highlighting, I want to preview how patterns will be highlighted so I can see the effect of my settings before applying them permanently.

**Why this priority**: Preview is helpful for configuration but not essential for using the feature.

**Independent Test**: Can be tested by running `highlight preview` and seeing sample log output with current highlighting settings applied.

**Acceptance Scenarios**:

1. **Given** I run `highlight preview`, **When** the preview displays, **Then** I see sample log lines demonstrating each enabled highlighter's patterns.

2. **Given** I have disabled the timestamp highlighter, **When** I run `highlight preview`, **Then** sample timestamps appear unhighlighted.

---

### User Story 10 - REPL Mode Integration (Priority: P1)

As a user in REPL mode viewing individual log entries, I want semantic highlighting applied to output so the REPL experience matches tail mode.

**Why this priority**: The REPL is a primary interaction mode, so highlighting must work there too for consistency.

**Independent Test**: Can be tested by querying logs in REPL mode and verifying patterns are highlighted.

**Acceptance Scenarios**:

1. **Given** highlighting is enabled, **When** I view log entries in REPL mode, **Then** patterns are highlighted just as in tail mode.

2. **Given** I disable highlighting, **When** I view log entries in REPL mode, **Then** patterns are not highlighted.

---

### User Story 11 - Export Without Highlighting Markup (Priority: P2)

As a user exporting logs for external tools or sharing, I want highlighting markup stripped from plain text exports so the output is clean.

**Why this priority**: Clean exports are important for interoperability but secondary to viewing functionality.

**Independent Test**: Can be tested by exporting to a file and verifying no Rich markup tags appear in the output.

**Acceptance Scenarios**:

1. **Given** I export to text format, **When** export completes, **Then** the output contains no Rich markup tags (plain text only).

2. **Given** I export with `--highlighted` flag, **When** export completes, **Then** markup tags are preserved in the output.

3. **Given** I export to JSON format, **When** export completes, **Then** no highlighting markup appears in any field.

---

### Edge Cases

- What happens when a log line is extremely long (>10KB)? Only the first configurable number of characters are highlighted; the rest remains plain.
- What happens when a regex pattern matches zero-length strings? Such patterns are rejected during validation.
- What happens when multiple patterns match the same text position? The first pattern (by priority) wins due to overlap prevention.
- What happens when theme is missing highlight style keys? Fallback to default colors or theme-defined fallbacks.
- What happens when custom pattern regex is invalid? Clear error message shown; pattern not added.
- What happens when config file has invalid highlighting settings? Settings are ignored with warning; defaults used.
- What happens when a log contains Rich markup-like text (e.g., `[bold]`)? Escaped brackets in actual log content are preserved.
- What happens when NO_COLOR is set? All highlighting disabled; plain text output.
- What happens when highlighting a log format (CSV/JSON) with different field structures? Highlighting applies to the formatted display output regardless of underlying format.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Infrastructure

- **FR-001**: System MUST implement a Highlighter protocol with `name`, `priority`, `apply()`, and `apply_rich()` methods that all highlighters conform to.
- **FR-002**: System MUST implement a HighlighterChain compositor that applies multiple highlighters in priority order.
- **FR-003**: System MUST implement overlap prevention using chunk iteration that identifies already-highlighted regions and skips them.
- **FR-004**: System MUST compile regex patterns once at highlighter instantiation, not per-line processed.
- **FR-005**: System MUST return input unchanged (zero allocation) when no patterns match.
- **FR-006**: System MUST support configurable highlighting depth limit (default 10KB, configurable via `highlighting.max_length`).

#### Built-in Highlighters (29 total)

**Structural (3):**
- **FR-010**: System MUST highlight timestamps with distinct styles for date, time, milliseconds, timezone, and separators.
- **FR-011**: System MUST highlight PIDs in bracket format `[12345]` and optional virtual transaction suffix `[12345-1]`.
- **FR-012**: System MUST highlight PostgreSQL context labels (DETAIL:, HINT:, CONTEXT:, STATEMENT:, QUERY:).

**Diagnostic (2):**
- **FR-020**: System MUST highlight 5-character SQLSTATE codes with colors based on error class (00=success, 23=integrity, 42=syntax, XX=internal, etc.).
- **FR-021**: System MUST highlight PostgreSQL error names (unique_violation, deadlock_detected, query_canceled, etc.).

**Performance (3):**
- **FR-030**: System MUST highlight query durations with threshold-based coloring (fast/slow/very_slow/critical).
- **FR-031**: System MUST highlight memory/size values with units (bytes, kB, MB, GB, TB).
- **FR-032**: System MUST highlight numeric statistics in checkpoint/vacuum messages (counts, percentages).

**Database Objects (3):**
- **FR-040**: System MUST highlight double-quoted identifiers (table names, column names, constraint names).
- **FR-041**: System MUST highlight relation names in patterns like `relation "users"`, `table "orders"`.
- **FR-042**: System MUST highlight schema-qualified names (e.g., `pg_catalog.pg_class`, `public.users`).

**WAL & Replication (3):**
- **FR-050**: System MUST highlight Log Sequence Number (LSN) values in format `segment/offset`.
- **FR-051**: System MUST highlight WAL segment filenames (24-character hex with timeline and segment).
- **FR-052**: System MUST highlight transaction IDs (xid, transaction, xmin, xmax patterns).

**Connection & Session (3):**
- **FR-060**: System MUST highlight connection information (host, port, user, database, action).
- **FR-061**: System MUST highlight IPv4 and IPv6 addresses including CIDR notation.
- **FR-062**: System MUST highlight PostgreSQL backend type names (autovacuum, checkpointer, walwriter, etc.).

**SQL Elements (5):**
- **FR-070**: System MUST highlight query parameters ($1, $2, etc.).
- **FR-071**: System MUST highlight SQL keywords with category distinction (DML, DDL, DCL, TCL).
- **FR-072**: System MUST highlight SQL string literals including dollar-quoted and escape strings.
- **FR-073**: System MUST highlight SQL numeric literals including scientific notation and hex.
- **FR-074**: System MUST migrate existing SQL highlighting (sql_highlighter.py, sql_tokenizer.py) into the new semantic highlighting system, replacing the legacy modules entirely.

**Lock & Concurrency (2):**
- **FR-080**: System MUST highlight lock type names with severity-based coloring (share vs exclusive).
- **FR-081**: System MUST highlight lock wait information (waiting for, acquired, duration).

**Checkpoint & Recovery (2):**
- **FR-090**: System MUST highlight checkpoint statistics (starting, complete, trigger, stats).
- **FR-091**: System MUST highlight recovery progress messages (redo starts/done, ready to accept connections).

**Miscellaneous (4):**
- **FR-100**: System MUST highlight boolean values (on/off, true/false, yes/no).
- **FR-101**: System MUST highlight NULL keyword.
- **FR-102**: System MUST highlight object IDs (OID patterns).
- **FR-103**: System MUST highlight Unix file system paths.

#### Theme Integration

- **FR-110**: System MUST add `get_style(key, fallback=None)` method to Theme class for style lookups.
- **FR-111**: System MUST add all highlight style keys to all six built-in themes (dark, light, high-contrast, monokai, solarized-dark, solarized-light).
- **FR-112**: System MUST respect NO_COLOR environment variable and disable all highlighting when set.

#### Configuration

- **FR-120**: System MUST support `highlighting.enabled` setting for global enable/disable.
- **FR-121**: System MUST support `highlighting.max_length` setting for depth limiting.
- **FR-122**: System MUST support `highlighting.enabled_highlighters.<name>` settings for each of the 29 highlighters.
- **FR-123**: System MUST support `highlighting.duration.slow`, `highlighting.duration.very_slow`, `highlighting.duration.critical` threshold settings.
- **FR-124**: System MUST support `highlighting.custom` array for user-defined regex patterns with name, pattern, style, and priority.

#### Commands

- **FR-130**: System MUST implement `highlight` command to show current highlighting status.
- **FR-131**: System MUST implement `highlight on` to enable semantic highlighting globally.
- **FR-132**: System MUST implement `highlight off` to disable semantic highlighting globally.
- **FR-133**: System MUST implement `highlight list` to show all highlighters with enabled/disabled status.
- **FR-134**: System MUST implement `highlight enable <name>` to enable a specific highlighter.
- **FR-135**: System MUST implement `highlight disable <name>` to disable a specific highlighter.
- **FR-136**: System MUST implement `highlight preview` to show sample output with current settings.
- **FR-137**: System MUST implement `highlight reset` to restore default configuration.
- **FR-138**: System MUST implement `highlight add <name> <pattern> [--style <style>]` to add custom regex highlighter.
- **FR-139**: System MUST implement `highlight remove <name>` to remove custom highlighter.
- **FR-140**: System MUST implement `highlight export [--file <path>]` to export configuration as TOML.
- **FR-141**: System MUST implement `highlight import <path>` to import configuration from TOML file.

#### Integration

- **FR-150**: System MUST integrate highlighting into tail mode (tail_rich.py).
- **FR-151**: System MUST integrate highlighting into REPL mode (display.py).
- **FR-152**: System MUST strip highlighting markup when exporting to plain text format.
- **FR-153**: System MUST support `--highlighted` flag to preserve markup in text exports.
- **FR-154**: System MUST never include highlighting markup in JSON exports.

#### Performance

- **FR-160**: System MUST use Aho-Corasick algorithm for multi-keyword matching (lock types, backend names, error names).
- **FR-161**: System MUST cache highlighted output for static content (help screens, etc.).
- **FR-162**: System MUST achieve highlighting throughput of at least 10,000 lines per second.

### Key Entities

- **Highlighter**: A pattern matcher that applies styling to specific text patterns. Has name, priority, and regex/keyword patterns.
- **HighlighterChain**: An ordered collection of highlighters that processes text sequentially while preventing overlap.
- **Chunk**: A segment of text identified as either already-highlighted or available for highlighting.
- **CustomHighlighter**: A user-defined highlighter with regex pattern and style created via configuration or command.
- **HighlightingConfig**: Configuration state including enabled status, thresholds, enabled highlighters, and custom patterns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify error-class SQLSTATE codes at a glance without reading the numeric value (color indicates class).
- **SC-002**: Users can spot slow queries instantly by color intensity without reading duration values.
- **SC-003**: Users can visually distinguish 10+ different pattern types on a single log line without confusion.
- **SC-004**: System processes 10,000 log lines per second with highlighting enabled (no noticeable lag during high-volume tailing).
- **SC-005**: 100% of the 29 documented pattern types are highlighted correctly with appropriate theme colors.
- **SC-006**: Theme switching immediately updates all highlighting colors with no restart required.
- **SC-007**: Configuration changes (enable/disable highlighters) take effect immediately without restart.
- **SC-008**: Custom regex patterns added by users highlight matching text within the same session.
- **SC-009**: Exported plain text files contain zero Rich markup tags.
- **SC-010**: Highlighting applies consistently across tail mode, REPL mode, and export preview.
- **SC-011**: Long log lines (>10KB) are processed without performance degradation due to configurable depth limiting.
- **SC-012**: Zero highlighting overlap artifacts occur when multiple patterns exist on the same line.

## Assumptions

- Users have terminals that support ANSI colors (highlighting degrades gracefully without colors).
- The existing theme system (theme.py, ThemeManager) is in place and functional.
- The existing configuration system (config.py) supports nested TOML settings.
- Performance testing infrastructure exists or can be created for throughput benchmarks.
- Rich library is available and used for text formatting in both tail mode and REPL mode.
- PostgreSQL log formats (stderr, CSV, JSON) are already parsed by existing infrastructure.

## Dependencies

- Existing theme system for style lookups and color definitions.
- Existing configuration system for settings persistence.
- Existing display infrastructure for tail mode (tail_rich.py) and REPL mode (display.py).
- Existing export infrastructure (export.py) for integration.
- pyahocorasick library (or alternative) for Aho-Corasick keyword matching.

## Out of Scope

- Binary plugins or external code loading for highlighters (only regex patterns in configuration).
- Highlighting in web or GUI interfaces (terminal output only).
- Machine learning or AI-based pattern detection (only explicit regex/keyword matching).
- Real-time pattern suggestion or auto-learning from log content.
