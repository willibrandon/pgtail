# Feature Specification: Configuration File Support

**Feature Branch**: `005-config-file`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Configuration File Support - Persist user preferences using TOML config file with commands to view and modify settings"

## Clarifications

### Session 2025-12-15

- Q: How should pgtail behave when config file contains invalid TOML or invalid values? → A: Warn and continue with defaults (show error, use default for invalid keys)
- Q: Should keybindings configuration be included given pgtail is REPL-based without TUI mode? → A: Defer keybindings section until TUI mode exists

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set and Persist Configuration Values (Priority: P1)

A user wants to configure pgtail settings once and have them persist across sessions. They use the `set` command to save preferences like default log level filters or slow query thresholds. When they restart pgtail, their settings are automatically applied.

**Why this priority**: This is the core value proposition - without persistent settings, the feature has no utility. Users must be able to save and automatically load their preferences.

**Independent Test**: Can be fully tested by running `set slow.warn 50`, exiting pgtail, restarting, and verifying the slow query warning threshold is automatically set to 50ms.

**Acceptance Scenarios**:

1. **Given** pgtail is running with no config file, **When** user runs `set slow.warn 50`, **Then** the config file is created and the setting is saved
2. **Given** a config file exists with `slow.warn = 50`, **When** user starts pgtail, **Then** slow query warning threshold is automatically set to 50ms
3. **Given** pgtail is running, **When** user runs `set default.levels ERROR WARNING`, **Then** the setting is saved and confirmed to user
4. **Given** a config file exists with `default.levels = ["ERROR", "WARNING"]`, **When** user starts pgtail, **Then** the level filter is automatically applied

---

### User Story 2 - View Current Configuration (Priority: P2)

A user wants to see all their current settings in one place. They use the `config` command to display the configuration file location and all current settings, formatted in a readable TOML structure.

**Why this priority**: Users need visibility into what settings are active. Without this, they cannot verify their configuration or troubleshoot issues.

**Independent Test**: Can be fully tested by running `config` command and verifying it displays the config file path and all current settings.

**Acceptance Scenarios**:

1. **Given** a config file exists with settings, **When** user runs `config`, **Then** the config file path and all settings are displayed in TOML format
2. **Given** no config file exists, **When** user runs `config`, **Then** the expected config file path is shown with default values
3. **Given** user runs `set slow.warn`, **When** executed without a value, **Then** the current value of `slow.warn` is displayed

---

### User Story 3 - Edit Configuration Directly (Priority: P3)

A power user prefers to edit the configuration file directly in their text editor. They use `config edit` to open the file in their default editor ($EDITOR).

**Why this priority**: This is a convenience feature for advanced users who want bulk edits or prefer manual file editing. The feature works without it.

**Independent Test**: Can be fully tested by running `config edit` and verifying the text editor opens with the config file.

**Acceptance Scenarios**:

1. **Given** $EDITOR is set to "vim", **When** user runs `config edit`, **Then** vim opens with the config file
2. **Given** $EDITOR is not set, **When** user runs `config edit`, **Then** a helpful error message explains how to set $EDITOR
3. **Given** config file does not exist, **When** user runs `config edit`, **Then** the file is created with commented defaults before opening

---

### User Story 4 - Reset Configuration (Priority: P3)

A user wants to restore default settings. They use `config reset` to reset all settings to defaults while preserving a backup of their previous configuration.

**Why this priority**: This is a safety and recovery feature. Users can use the feature without it, but it provides peace of mind.

**Independent Test**: Can be fully tested by running `config reset` and verifying defaults are restored and a backup file is created.

**Acceptance Scenarios**:

1. **Given** a config file exists with custom settings, **When** user runs `config reset`, **Then** the config is reset to defaults and a backup file is created
2. **Given** user runs `config reset`, **When** reset completes, **Then** a confirmation message shows the backup file location
3. **Given** no config file exists, **When** user runs `config reset`, **Then** a message indicates there is nothing to reset

---

### User Story 5 - Remove Individual Settings (Priority: P3)

A user wants to remove a specific setting and revert to its default. They use `unset` to remove just that setting without affecting others.

**Why this priority**: Provides fine-grained control over configuration. The feature works without it, but improves usability.

**Independent Test**: Can be fully tested by running `unset slow.warn` and verifying the setting is removed from config file.

**Acceptance Scenarios**:

1. **Given** config has `slow.warn = 50`, **When** user runs `unset slow.warn`, **Then** the setting is removed and default is used
2. **Given** user runs `unset nonexistent.key`, **When** executed, **Then** a message indicates the key was not found

---

### Edge Cases

- **Invalid TOML syntax**: System displays warning message with parse error details, then continues with all defaults
- **Invalid values** (e.g., `slow.warn = "abc"`): System displays warning identifying the invalid key, uses default for that key, loads valid settings normally
- **No write permissions**: System displays error when attempting `set`/`unset`/`config reset`, continues operating with current in-memory settings
- **$EDITOR fails**: System displays error message with exit code, returns to pgtail prompt
- **Config deleted while running**: Next `set` command recreates the file; in-memory settings remain until exit

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store configuration in a TOML file at platform-specific locations:
  - macOS: `~/Library/Application Support/pgtail/config.toml`
  - Linux: `~/.config/pgtail/config.toml`
  - Windows: `%APPDATA%/pgtail/config.toml`
- **FR-002**: System MUST create the config file and parent directories on first `set` command if they don't exist
- **FR-003**: System MUST support these configuration sections: `[default]`, `[slow]`, `[display]`, `[theme]`, `[notifications]`
- **FR-004**: System MUST load configuration on startup and apply settings before user interaction
- **FR-005**: System MUST validate configuration values on load and report errors for invalid values
- **FR-006**: System MUST provide `config` command to display current configuration
- **FR-007**: System MUST provide `config edit` command to open config file in $EDITOR
- **FR-008**: System MUST provide `config reset` command to restore defaults with backup
- **FR-009**: System MUST provide `config path` command to show config file location
- **FR-010**: System MUST provide `set <key> <value>` command to update settings
- **FR-011**: System MUST provide `set <key>` command (without value) to display current value
- **FR-012**: System MUST provide `unset <key>` command to remove a setting
- **FR-013**: System MUST use reasonable defaults when config file doesn't exist or setting is absent
- **FR-014**: System MUST preserve comments and formatting in config file when updating via `set`
- **FR-015**: System MUST show helpful error messages for invalid setting names or values
- **FR-016**: System MUST warn and continue with defaults when config file contains invalid TOML or invalid values (graceful degradation)

### Configuration Schema

- **default.levels**: Array of log levels to filter by default (default: all levels shown)
- **default.follow**: Boolean to auto-follow new entries (default: true)
- **slow.warn**: Warning threshold in milliseconds (default: 100)
- **slow.error**: Error threshold in milliseconds (default: 500)
- **slow.critical**: Critical threshold in milliseconds (default: 1000)
- **display.timestamp_format**: strftime format for timestamps (default: "%H:%M:%S.%f")
- **display.show_pid**: Boolean to show process ID (default: true)
- **display.show_level**: Boolean to show log level (default: true)
- **theme.name**: Theme name - "dark" or "light" (default: "dark")
- **notifications.enabled**: Boolean to enable notifications (default: false)
- **notifications.levels**: Array of levels that trigger notifications (default: ["FATAL", "PANIC"])
- **notifications.quiet_hours**: Time range for quiet hours (default: none)

### Key Entities

- **Configuration**: The complete set of user preferences, stored as a TOML file. Contains multiple sections each with related settings.
- **Setting**: A single configuration value identified by a dotted key path (e.g., `slow.warn`). Has a name, value, and default value.
- **ConfigSection**: A logical grouping of related settings (default, slow, display, theme, notifications).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can save a setting and have it persist across pgtail sessions
- **SC-002**: Users can view all current settings with a single command
- **SC-003**: Invalid configuration values are detected and reported with helpful error messages
- **SC-004**: Configuration reset preserves a backup of the previous configuration
- **SC-005**: Configuration file is human-readable and editable with any text editor
- **SC-006**: All documented configuration options are supported and validated
- **SC-007**: Settings apply within 1 second of pgtail startup

## Assumptions

- Users have write access to their platform's standard config directory
- The TOML format is acceptable for configuration (human-readable, well-supported)
- Platform-specific config paths follow established conventions (XDG on Linux, Application Support on macOS, AppData on Windows)
- $EDITOR environment variable is the standard way to specify preferred text editor
- Backup files use `.bak` extension with timestamp for uniqueness

## Out of Scope

- Multiple configuration profiles
- Configuration sync across machines
- GUI configuration editor
- Environment variable overrides for all settings
- Real-time config file watching (reload when file changes externally)
- Import/export configuration
- Configuration migration between versions
