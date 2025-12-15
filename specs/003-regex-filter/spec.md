# Feature Specification: Regex Pattern Filtering

**Feature Branch**: `003-regex-filter`
**Created**: 2025-12-14
**Status**: Draft
**Input**: User description: "Add regex-based filtering that works alongside level filtering. Users can include or exclude lines matching patterns. Multiple patterns can be combined with AND/OR logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Include Filter by Pattern (Priority: P1)

A developer debugging an issue needs to see only log lines related to a specific table, query pattern, or application identifier. They enter a filter command with a regex pattern to focus on relevant entries.

**Why this priority**: This is the core functionality - filtering to include only matching lines. Without this, the feature has no value. Most users will use include filters as their primary interaction.

**Independent Test**: Can be fully tested by running `filter /pattern/` command and verifying only matching log lines appear in output.

**Acceptance Scenarios**:

1. **Given** pgtail is displaying log output, **When** user enters `filter /orders/`, **Then** only log lines containing "orders" are displayed
2. **Given** an include filter is active, **When** a log line arrives that does not match, **Then** the line is not displayed
3. **Given** an include filter is active, **When** a log line arrives that matches, **Then** the line is displayed with normal formatting
4. **Given** no filter is active, **When** user enters `filter`, **Then** system displays "No filters active"

---

### User Story 2 - Exclude Filter by Pattern (Priority: P2)

A DBA wants to see error-level logs but needs to exclude routine "connection authorized" messages that create noise. They add an exclusion filter to hide matching lines while keeping all others visible.

**Why this priority**: Exclusion filters complement include filters and are essential for reducing noise. Many users need to filter out known patterns rather than filter for specific ones.

**Independent Test**: Can be fully tested by running `filter -/pattern/` command and verifying matching lines are hidden while non-matching lines appear.

**Acceptance Scenarios**:

1. **Given** pgtail is displaying log output, **When** user enters `filter -/connection authorized/`, **Then** lines containing "connection authorized" are hidden
2. **Given** an exclude filter is active, **When** a non-matching log line arrives, **Then** the line is displayed normally
3. **Given** both level filter (ERROR) and exclude filter are active, **When** an ERROR line matching the exclude pattern arrives, **Then** the line is not displayed

---

### User Story 3 - Combine Multiple Filters (Priority: P2)

A developer needs complex filtering logic - for example, showing lines that match pattern A OR pattern B, or lines that must match BOTH pattern A AND pattern B. They add additional patterns with appropriate logic operators.

**Why this priority**: Real-world debugging often requires multiple patterns. This is essential for power users but secondary to basic single-pattern filtering.

**Independent Test**: Can be fully tested by adding multiple filters with `+` (OR) and `&` (AND) prefixes and verifying correct logical combination.

**Acceptance Scenarios**:

1. **Given** filter `/orders/` is active, **When** user enters `filter +/products/`, **Then** lines matching "orders" OR "products" are displayed
2. **Given** filter `/SELECT/` is active, **When** user enters `filter &/users/`, **Then** only lines matching BOTH "SELECT" AND "users" are displayed
3. **Given** multiple filters are active, **When** user enters `filter`, **Then** all active filters and their logic are displayed
4. **Given** multiple filters are active, **When** user enters `filter clear`, **Then** all filters are removed and all lines are displayed (subject to level filters)

---

### User Story 4 - Highlight Without Filtering (Priority: P3)

A developer wants to see all log output but have specific patterns visually highlighted so they stand out. They use the highlight command to mark patterns without hiding any lines.

**Why this priority**: Highlighting is a convenience feature that adds visual emphasis without changing which lines are shown. Useful but not essential for core filtering functionality.

**Independent Test**: Can be fully tested by running `highlight /pattern/` and verifying matching text is visually emphasized while all lines remain visible.

**Acceptance Scenarios**:

1. **Given** pgtail is displaying log output, **When** user enters `highlight /SELECT/`, **Then** all lines continue to display but "SELECT" text is visually emphasized
2. **Given** a highlight is active, **When** user enters `highlight clear`, **Then** highlighting is removed and display returns to normal
3. **Given** both a filter and highlight are active, **When** a line matches the highlight but not the filter, **Then** the line is not displayed (filter takes precedence)

---

### User Story 5 - View and Manage Active Filters (Priority: P3)

A user has been adding filters during a session and wants to see what's currently active, then selectively clear them.

**Why this priority**: Filter management is secondary to filter functionality but necessary for usability when multiple filters accumulate.

**Independent Test**: Can be fully tested by adding filters, running `filter` to view them, and running `filter clear` to remove all.

**Acceptance Scenarios**:

1. **Given** multiple filters are active, **When** user enters `filter`, **Then** system displays all active include and exclude filters with their patterns
2. **Given** filters are active, **When** user enters `filter clear`, **Then** all filters are removed
3. **Given** highlights are active, **When** user enters `highlight`, **Then** system displays all active highlight patterns

---

### Edge Cases

- What happens when user enters an invalid regex pattern? System displays a helpful error message explaining the syntax error and does not apply the filter.
- What happens when filter pattern matches nothing for extended time? Filter remains active; no special notification (user can check with `filter` command).
- What happens when user enters empty pattern `/`? System displays error "Empty pattern not allowed".
- How does system handle very long regex patterns? Standard regex length limits apply; excessively complex patterns may be rejected with timeout/complexity error.
- What happens when include and exclude filters conflict (same pattern)? Exclude takes precedence - if a line matches both include and exclude, it is hidden.
- How do regex filters interact with level filters? Both must pass - a line must match level filter AND regex filter logic to be displayed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support include filters via `filter /pattern/` command syntax
- **FR-002**: System MUST support exclude filters via `filter -/pattern/` command syntax
- **FR-003**: System MUST support adding OR patterns via `filter +/pattern/` command syntax
- **FR-004**: System MUST support adding AND patterns via `filter &/pattern/` command syntax
- **FR-005**: System MUST support clearing all filters via `filter clear` command
- **FR-006**: System MUST display active filters when user enters `filter` with no arguments
- **FR-007**: System MUST support highlighting without filtering via `highlight /pattern/` command
- **FR-008**: System MUST support clearing highlights via `highlight clear` command
- **FR-009**: System MUST display active highlights when user enters `highlight` with no arguments
- **FR-010**: System MUST apply regex matching to the full raw log line (timestamp, PID, level, message)
- **FR-011**: System MUST use case-insensitive matching by default
- **FR-012**: System MUST support case-sensitive matching via `/pattern/c` suffix (`c` = case-sensitive)
- **FR-013**: System MUST display helpful error messages for invalid regex syntax
- **FR-014**: System MUST compile regex patterns once and reuse for performance
- **FR-015**: System MUST persist filters during the session (until cleared or pgtail exits)
- **FR-016**: System MUST apply both level filters and regex filters together (line must pass both)
- **FR-017**: System MUST give exclude filters precedence over include filters for the same line

### Key Entities

- **RegexFilter**: A compiled regex pattern with a filter type (include, exclude, and-include, and-exclude) and case sensitivity setting
- **Highlight**: A compiled regex pattern used for visual emphasis without affecting which lines are displayed
- **FilterState**: Collection of active filters and highlights maintained during session

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a regex filter and see filtered output within 1 second of entering the command
- **SC-002**: Invalid regex patterns display a clear error message that helps users correct the syntax
- **SC-003**: Filtering 10,000+ log lines per minute introduces no visible delay in output (matches native level filtering performance)
- **SC-004**: Users can combine at least 5 filters (mix of include/exclude/AND/OR) without performance degradation
- **SC-005**: The `filter` command accurately displays all active filters and their types
- **SC-006**: Highlight patterns visually distinguish matched text using background color (e.g., yellow)

## Clarifications

### Session 2025-12-14

- Q: What visual style should highlights use? → A: Background color (e.g., yellow background on matched text)
- Q: What suffix should indicate case-sensitive matching? → A: `/pattern/c` (`c` = case-sensitive, avoids confusion with standard regex `/i` convention)

## Assumptions

- Standard Python `re` module regex syntax is sufficient for user needs
- Case-insensitive is the better default since log messages have inconsistent casing
- Users understand basic regex syntax or will learn from error messages
- Session persistence is sufficient; cross-session persistence will be handled by config-file feature
