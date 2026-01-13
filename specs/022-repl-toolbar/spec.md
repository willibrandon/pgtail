# Feature Specification: REPL Bottom Toolbar

**Feature Branch**: `022-repl-toolbar`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "Add bottom toolbar to REPL showing instance count, pre-configured filters, and theme settings"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Instance Status at a Glance (Priority: P1)

Users launching pgtail want to immediately see how many PostgreSQL instances are available without running additional commands. The toolbar provides persistent visibility of instance count, eliminating the need to remember startup messages or run `list` repeatedly.

**Why this priority**: Core value proposition - users need basic orientation about what they can tail. Without instances, other toolbar features are less relevant.

**Independent Test**: Launch pgtail with various instance configurations and verify the toolbar displays correct count. Delivers immediate value by removing guesswork about available instances.

**Acceptance Scenarios**:

1. **Given** 3 PostgreSQL instances are detected, **When** pgtail starts and the user sees the prompt, **Then** the toolbar displays "3 instances" on a dark background below the prompt line
2. **Given** 1 PostgreSQL instance is detected, **When** pgtail starts, **Then** the toolbar displays "1 instance" (singular grammar)
3. **Given** no PostgreSQL instances are detected, **When** pgtail starts, **Then** the toolbar displays "No instances" in a warning color with "(run 'refresh')" hint in dim text
4. **Given** user runs `refresh` and instances increase from 0 to 2, **When** the refresh completes, **Then** the toolbar updates to show "2 instances" on the next prompt

---

### User Story 2 - See Pre-configured Filters Before Tailing (Priority: P2)

Users configure filters (levels, regex patterns, time constraints, slow query thresholds) before launching tail mode. Currently, they have no visibility into what's configured. The toolbar shows active filters so users know exactly how their next `tail` command will behave.

**Why this priority**: Prevents user confusion and errors when tailing. Configured filters become invisible immediately after setting, leading to unexpected results when tailing.

**Independent Test**: Configure multiple filter types and verify they appear in the toolbar. Delivers value by making configuration state visible.

**Acceptance Scenarios**:

1. **Given** no filters are configured, **When** viewing the toolbar, **Then** no filter section appears (only instances and theme)
2. **Given** user runs `levels error+`, **When** viewing the toolbar, **Then** it shows "levels:ERROR,FATAL,PANIC" in an accent color
3. **Given** user runs `filter /deadlock/i`, **When** viewing the toolbar, **Then** it shows "filter:/deadlock/i" in an accent color
4. **Given** user runs `since 1h`, **When** viewing the toolbar, **Then** it shows the time filter description (e.g., "since:1h ago") in an accent color
5. **Given** user runs `slow 200`, **When** viewing the toolbar, **Then** it shows "slow:>200ms" in an accent color
6. **Given** multiple filters are set (level + regex + time), **When** viewing the toolbar, **Then** all filters appear space-separated in the filter section
7. **Given** user runs `clear` to reset filters, **When** viewing the toolbar, **Then** the filter section disappears

---

### User Story 3 - View Current Theme (Priority: P3)

Users switch themes to customize their visual experience. The toolbar shows which theme is active, providing confirmation after `theme` commands and persistent visibility of the current styling.

**Why this priority**: Nice-to-have visibility feature. Theme affects appearance but users typically set it once and forget.

**Independent Test**: Switch themes and verify the toolbar updates to show the new theme name. Delivers value by confirming theme changes.

**Acceptance Scenarios**:

1. **Given** default dark theme is active, **When** viewing the toolbar, **Then** it shows "Theme: dark" at the right side
2. **Given** user runs `theme monokai`, **When** viewing the toolbar, **Then** it immediately shows "Theme: monokai"
3. **Given** user runs `theme list`, **When** viewing the toolbar, **Then** the theme display remains unchanged (only actual theme switches update it)

---

### User Story 4 - Shell Mode Indicator (Priority: P4)

Users enter shell mode by pressing `!` with an empty prompt. The toolbar provides a clear indicator that shell mode is active, along with instructions for exiting.

**Why this priority**: Secondary feature - shell mode is used less frequently and already has a prompt indicator (`! `), but the toolbar provides additional clarity.

**Independent Test**: Enter shell mode and verify the toolbar changes to show shell mode indicator. Exit and verify it returns to normal display.

**Acceptance Scenarios**:

1. **Given** user is in idle mode, **When** user presses `!` with empty buffer, **Then** the toolbar changes to display "SHELL" in bold white text with "Press Escape to exit" hint in dim text
2. **Given** shell mode is active, **When** user presses Escape, **Then** the toolbar returns to normal idle display showing instances, filters, and theme
3. **Given** shell mode is active, **When** user runs a shell command and it completes, **Then** the toolbar returns to normal idle display

---

### Edge Cases

- What happens when terminal width is very narrow (< 40 columns)? Toolbar content gracefully truncates, prioritizing instance count over filters over theme.
- What happens when there are many filters configured? Show first filter pattern with count indicator if multiple exist (e.g., "filter:/deadlock/i +2 more").
- What happens when regex pattern contains special characters? Display pattern as-is without interpretation.
- What happens during tail mode (Textual TUI)? The REPL toolbar is not visible - Textual's TailApp takes over the terminal completely. Toolbar only applies to idle REPL.
- What happens when theme name is very long (custom themes)? Truncate theme name to reasonable length (15 characters) with ellipsis.
- What happens with NO_COLOR environment variable set? Toolbar still appears but without styling (plain text).
- What happens when user types in the prompt? The toolbar remains static and does not flicker or redraw while typing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a bottom toolbar in the REPL using prompt_toolkit's `bottom_toolbar` parameter
- **FR-002**: System MUST show the number of detected PostgreSQL instances in the toolbar with correct singular/plural grammar
- **FR-003**: System MUST show a warning indicator when no instances are detected, with a hint to run 'refresh'
- **FR-004**: System MUST display active level filters when configured (not matching all levels)
- **FR-005**: System MUST display active regex filters (first pattern with flags)
- **FR-006**: System MUST display active time filters using existing `format_description()` output
- **FR-007**: System MUST display slow query threshold when customized from default (100ms)
- **FR-008**: System MUST display the current theme name
- **FR-009**: System MUST use distinct visual styling for different toolbar elements (normal, dim, accent/filter, warning, bold/shell)
- **FR-010**: System MUST update the toolbar dynamically when state changes (filters added/removed, theme switched, instances refreshed)
- **FR-011**: System MUST display a distinct shell mode indicator when shell mode is active
- **FR-012**: System MUST apply theme-aware styling to the toolbar background and text colors
- **FR-013**: System MUST use bullet separators (•) between toolbar sections for visual clarity
- **FR-014**: System MUST respect the NO_COLOR environment variable by displaying plain text without styling

### Key Entities

- **Toolbar State**: Dynamic content derived from AppState (instances, filters, theme, shell_mode)
- **Toolbar Styles**: Style classes for different content types (normal, dim, filter/accent, warning, shell/bold)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can see instance count without running any command after launching pgtail
- **SC-002**: Users can see all active filters at a glance without running status commands
- **SC-003**: Users can confirm their current theme without running `theme` command
- **SC-004**: Users can clearly distinguish shell mode from idle mode via toolbar indicator
- **SC-005**: Toolbar updates within 100ms of state changes (filter/theme/refresh commands)
- **SC-006**: Toolbar remains readable on terminals 80 columns wide or greater
- **SC-007**: 95% of users correctly identify their current configuration state from the toolbar on first view
