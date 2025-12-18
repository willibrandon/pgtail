# Feature Specification: Color Themes

**Feature Branch**: `013-color-themes`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Support multiple built-in themes and custom theme definitions for terminal color customization"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Switch Active Theme (Priority: P1)

Users with different terminal backgrounds need to quickly switch between built-in themes to find colors that work well for their setup.

**Why this priority**: Core functionality - without theme switching, the feature has no value. This is the minimum viable product that delivers immediate user benefit.

**Independent Test**: Can be fully tested by running `theme light` and verifying all log output uses the light theme colors.

**Acceptance Scenarios**:

1. **Given** pgtail is running with dark theme (default), **When** user enters `theme light`, **Then** a confirmation message "Theme set to: light" is displayed and all subsequent log output uses light theme colors.
2. **Given** pgtail is running, **When** user enters `theme nonexistent`, **Then** an error message lists available themes.
3. **Given** user has set theme to "high-contrast", **When** pgtail is restarted, **Then** the high-contrast theme is automatically applied from saved configuration.

---

### User Story 2 - List and Preview Themes (Priority: P2)

Users want to explore available themes before committing to one, seeing how their logs will look with different color schemes.

**Why this priority**: Discovery feature - users need to know what's available before they can make informed choices. Builds on P1 by adding theme exploration.

**Independent Test**: Can be fully tested by running `theme list` to see available themes and `theme preview monokai` to see sample output.

**Acceptance Scenarios**:

1. **Given** pgtail is running, **When** user enters `theme list`, **Then** all available themes are displayed with the current theme marked.
2. **Given** pgtail is running, **When** user enters `theme preview monokai`, **Then** sample log entries (one for each log level) are displayed using monokai colors.
3. **Given** custom themes exist in config directory, **When** user enters `theme list`, **Then** both built-in and custom themes are listed.

---

### User Story 3 - Create Custom Theme (Priority: P3)

Power users want to define their own color schemes to match their terminal aesthetic or accessibility needs.

**Why this priority**: Advanced feature for power users - extends value beyond built-in options but requires P1/P2 to be useful.

**Independent Test**: Can be fully tested by creating a custom theme file, running `theme reload`, and verifying custom colors are applied.

**Acceptance Scenarios**:

1. **Given** pgtail is running, **When** user enters `theme edit custom`, **Then** the system opens the theme file in $EDITOR (or creates a template if it doesn't exist).
2. **Given** a valid custom theme file exists at the config themes directory, **When** user enters `theme custom`, **Then** the custom theme colors are applied.
3. **Given** a custom theme file has syntax errors, **When** user enters `theme custom`, **Then** an error message describes the problem and the previous theme remains active.

---

### User Story 4 - Reload Theme Without Restart (Priority: P4)

Users editing custom themes want to see changes immediately without restarting pgtail.

**Why this priority**: Quality-of-life improvement for theme editors - makes the customization workflow smoother.

**Independent Test**: Can be fully tested by modifying a theme file while pgtail is running and executing `theme reload`.

**Acceptance Scenarios**:

1. **Given** user has modified the current theme file externally, **When** user enters `theme reload`, **Then** the updated colors are applied immediately with confirmation message.
2. **Given** theme file was deleted after being loaded, **When** user enters `theme reload`, **Then** an appropriate error is shown and fallback to default theme occurs.

---

### Edge Cases

- What happens when NO_COLOR=1 is set? → All themes are bypassed, plain text output only.
- What happens when theme file contains invalid hex color codes? → Error message identifies the invalid value, theme not applied.
- What happens when config directory doesn't exist? → Directory is created when first custom theme is saved.
- What happens when switching themes during active tailing? → New theme applies to subsequent log entries immediately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide at least 6 built-in themes: dark (default), light, high-contrast, monokai, solarized-dark, and solarized-light.
- **FR-002**: System MUST persist theme selection in the configuration file so it survives restarts.
- **FR-003**: System MUST apply theme changes immediately without requiring restart.
- **FR-004**: System MUST respect the NO_COLOR environment variable by disabling all theme colors when set.
- **FR-005**: System MUST display helpful error messages when theme files contain invalid syntax or values.
- **FR-006**: System MUST allow users to create custom themes in TOML format at the platform-specific config directory.
- **FR-007**: System MUST define colors for all log levels (PANIC, FATAL, ERROR, WARNING, NOTICE, LOG, INFO, DEBUG1-5).
- **FR-008**: System MUST define colors for UI elements (prompt, timestamp, pid, highlight, selection).
- **FR-009**: System MUST support both named colors (red, yellow, cyan) and hex color codes (#ff6b6b).
- **FR-010**: System MUST support style modifiers (bold, dim, italic, underline) in theme definitions.
- **FR-011**: System MUST provide sample output for theme preview showing all log levels.
- **FR-012**: System MUST validate theme files before applying and report specific validation errors.
- **FR-013**: System MUST fall back to the default theme when the configured theme cannot be loaded.

### Key Entities

- **Theme**: A named collection of color definitions with metadata (name, description) and style rules for levels and UI elements.
- **ColorStyle**: A style specification with foreground color, optional background color, and optional modifiers (bold, dim, italic, underline).
- **ThemeManager**: Responsible for loading, validating, switching, and persisting theme state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can switch themes in under 2 seconds with immediate visual feedback.
- **SC-002**: All 6 built-in themes render correctly across dark and light terminal backgrounds.
- **SC-003**: 100% of log levels have distinct, visually differentiable colors in each built-in theme.
- **SC-004**: Custom theme files with syntax errors produce actionable error messages identifying the problem location.
- **SC-005**: Theme preference persists across sessions with 100% reliability.
- **SC-006**: Preview command displays sample output for all 8 distinct log levels (PANIC through DEBUG).
- **SC-007**: High-contrast theme provides WCAG AA contrast ratios for users with visual impairments.

## Assumptions

- Users are familiar with TOML format for custom themes (standard for this project's configuration).
- Terminal emulators support basic ANSI colors and 256-color mode for hex codes.
- The existing config file mechanism (TOML at platform-specific path) will be extended for theme storage.
- Custom themes are stored in a `themes/` subdirectory of the config directory.
- One theme is active at a time (no per-element theme mixing).

## Out of Scope

- Theme marketplace or sharing mechanism
- Automatic theme detection based on terminal background
- Per-instance themes (all instances use the same theme)
- Animation or transition effects when switching themes
- Exporting themes to other formats
