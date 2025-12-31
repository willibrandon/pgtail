# Feature Specification: Remove Fullscreen TUI

**Feature Branch**: `015-remove-fullscreen`
**Created**: 2025-12-30
**Status**: Draft
**Input**: User description: "Remove the full screen TUI it makes no sense since the log tailer is already full screen. We will no longer support this feature. Do not maintain any backwards compatibility and I do not care how complex it is remove all code related to the full screen tui"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Codebase Without Fullscreen TUI (Priority: P1)

A developer maintaining pgtail wants a simpler codebase without the redundant fullscreen TUI feature. The log tailer already provides a full-screen experience, making the separate fullscreen mode unnecessary and confusing.

**Why this priority**: This is the core purpose of the feature - removing unnecessary code complexity and eliminating user confusion about redundant functionality.

**Independent Test**: Can be fully tested by verifying that all fullscreen-related code, commands, and documentation are removed, and the application still functions correctly without them.

**Acceptance Scenarios**:

1. **Given** pgtail is installed, **When** a user runs `fullscreen` or `fs` command, **Then** the command is not recognized and an appropriate error message is shown
2. **Given** pgtail is installed, **When** a user views available commands, **Then** `fullscreen` and `fs` are not listed
3. **Given** the pgtail codebase, **When** a developer inspects the source, **Then** no fullscreen-related modules or code exist

---

### User Story 2 - Documentation Reflects Removal (Priority: P2)

A user reading pgtail documentation should not see any references to the fullscreen TUI feature, avoiding confusion about non-existent functionality.

**Why this priority**: Documentation accuracy is important but secondary to the actual code removal.

**Independent Test**: Can be tested by searching all documentation files for fullscreen-related references.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md file, **When** searched for fullscreen references, **Then** no fullscreen TUI documentation sections exist
2. **Given** any help text or command documentation, **When** reviewed, **Then** no references to fullscreen mode exist

---

### User Story 3 - Existing Functionality Unaffected (Priority: P1)

A user using pgtail for log tailing should experience no change in existing functionality - all non-fullscreen features continue to work exactly as before.

**Why this priority**: Ensuring the removal doesn't break existing functionality is equally critical to the removal itself.

**Independent Test**: Can be tested by running the existing test suite and manually testing core log tailing, filtering, and display features.

**Acceptance Scenarios**:

1. **Given** pgtail with fullscreen removed, **When** user runs log tailing commands, **Then** logs are displayed correctly
2. **Given** pgtail with fullscreen removed, **When** user applies filters (level, regex, time, field), **Then** filtering works correctly
3. **Given** pgtail with fullscreen removed, **When** user uses display modes and themes, **Then** styling and formatting work correctly
4. **Given** pgtail with fullscreen removed, **When** all tests are executed, **Then** no test failures occur (except fullscreen-specific tests which should be removed)

---

### Edge Cases

- What happens when a user has `fullscreen` in their command history and tries to use it? The command should fail gracefully with "unknown command" error.
- What happens if any code has imports from the fullscreen module? All such imports must be removed or the application will fail to start.
- What happens to the LogBuffer class if it was shared with non-fullscreen code? Any shared components must be evaluated - if only used by fullscreen, remove; if used elsewhere, preserve.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove the `fullscreen` command from the CLI
- **FR-002**: System MUST remove the `fs` command alias from the CLI
- **FR-003**: System MUST remove all files in the `pgtail_py/fullscreen/` directory
- **FR-004**: System MUST remove the `pgtail_py/cli_fullscreen.py` module
- **FR-005**: System MUST remove all imports referencing fullscreen modules
- **FR-006**: System MUST remove fullscreen-related entries from command completion/autocomplete
- **FR-007**: System MUST remove all fullscreen references from all documentation (CLAUDE.md, README, docstrings, help text)
- **FR-008**: System MUST remove any fullscreen-specific tests
- **FR-009**: System MUST preserve all non-fullscreen functionality without modification
- **FR-010**: System MUST NOT maintain any backwards compatibility shims, deprecation warnings, or transitional code

### Key Entities

- **Fullscreen Package** (`pgtail_py/fullscreen/`): Contains LogBuffer, FullscreenState, DisplayMode, keybindings, layout, lexer, and app modules - all to be deleted
- **CLI Fullscreen Handler** (`pgtail_py/cli_fullscreen.py`): Command handler for fullscreen mode - to be deleted
- **Commands Module** (`pgtail_py/commands.py`): Contains command definitions including fullscreen - to be modified to remove fullscreen commands

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero files exist in the `pgtail_py/fullscreen/` directory (directory itself removed)
- **SC-002**: Zero references to "fullscreen" exist in the codebase (excluding git history and this spec)
- **SC-003**: All existing tests pass after removal (excluding removed fullscreen-specific tests)
- **SC-004**: Application starts and runs without import errors
- **SC-005**: Users attempting to run `fullscreen` or `fs` commands receive a clear "unknown command" error
- **SC-006**: Codebase line count is reduced by the removal (net negative lines changed)

## Clarifications

### Session 2025-12-30

- Q: Documentation scope? → A: All docs (CLAUDE.md, README, docstrings, help text)

## Assumptions

- The LogBuffer class in fullscreen is only used by fullscreen code and can be safely removed
- No external tools or scripts depend on the fullscreen command
- The pygments dependency may still be needed for SQL syntax highlighting outside of fullscreen mode
- The fullscreen-specific Pygments lexer (LogLineLexer) is only used by fullscreen and can be removed
