# Feature Specification: Log Entry Selection and Copy

**Feature Branch**: `017-log-selection`
**Created**: 2025-12-31
**Status**: Draft
**Input**: User description: Replace prompt_toolkit tail mode with Textual for built-in text selection and clipboard support

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mouse Selection and Copy (Priority: P1)

A DBA is monitoring PostgreSQL logs in pgtail's tail mode when an error occurs. They need to copy the exact error message, including DETAIL and STATEMENT fields, to share with a developer via Slack or email.

**Why this priority**: This is the core functionality that addresses the primary pain point. Without mouse selection and clipboard copy, users cannot accomplish the fundamental task that motivated this feature.

**Independent Test**: Can be fully tested by launching tail mode, generating log entries, selecting text with mouse drag, and verifying the selected text appears in system clipboard.

**Acceptance Scenarios**:

1. **Given** tail mode is running with log entries visible, **When** user clicks and drags mouse across log text, **Then** the dragged text is visually highlighted as selected
2. **Given** text is selected in the log area, **When** user releases mouse button, **Then** selected text is automatically copied to system clipboard
3. **Given** text is selected in the log area, **When** user presses Ctrl+C, **Then** selected text is explicitly copied to system clipboard
4. **Given** a multi-line log entry (ERROR with DETAIL and STATEMENT), **When** user drags mouse from first line to last line, **Then** all lines including secondary fields are selected and copyable

---

### User Story 2 - Vim-Style Navigation (Priority: P2)

A power user wants to navigate through log history efficiently without using the mouse. They want to use familiar vim keybindings to scroll through logs and find specific entries.

**Why this priority**: Navigation is essential for reviewing log history, but the feature delivers value even without vim bindings (arrow keys work). Vim bindings enhance usability for power users.

**Independent Test**: Can be fully tested by launching tail mode, populating buffer with entries, and verifying each vim navigation key moves the viewport correctly.

**Acceptance Scenarios**:

1. **Given** tail mode is running with 100+ log entries, **When** user presses `j`, **Then** log view scrolls down one line
2. **Given** tail mode is running with scroll position not at top, **When** user presses `k`, **Then** log view scrolls up one line
3. **Given** tail mode is running, **When** user presses `Ctrl+D`, **Then** log view scrolls down by half the viewport height
4. **Given** tail mode is running, **When** user presses `Ctrl+U`, **Then** log view scrolls up by half the viewport height
5. **Given** tail mode is running with scroll position not at top, **When** user presses `g`, **Then** log view jumps to the first entry (top)
6. **Given** tail mode is scrolled up from bottom, **When** user presses `G`, **Then** log view jumps to the last entry and resumes FOLLOW mode

---

### User Story 3 - Vim Visual Mode Selection (Priority: P3)

A user wants to select text without using the mouse. They want to use vim's visual mode to select lines using keyboard navigation.

**Why this priority**: Keyboard-only selection is valuable for users who prefer not to use mouse or work in environments where mouse interaction is limited. However, mouse selection (P1) covers the majority of use cases.

**Independent Test**: Can be fully tested by launching tail mode, pressing `v` to enter visual mode, navigating with j/k, pressing `y` to yank, and verifying text is in clipboard.

**Acceptance Scenarios**:

1. **Given** tail mode is running with focus on log area, **When** user presses `v`, **Then** visual mode is activated and current line is marked as selection start
2. **Given** visual mode is active, **When** user presses `j` or `k`, **Then** selection extends to include navigated lines
3. **Given** visual mode is active with text selected, **When** user presses `y`, **Then** selected text is copied to clipboard and visual mode exits
4. **Given** visual mode is active, **When** user presses `V` (shift+v), **Then** visual line mode is activated selecting full lines
5. **Given** visual mode is active, **When** user presses `Escape`, **Then** selection is cleared and visual mode exits

---

### User Story 4 - Standard Selection Shortcuts (Priority: P2)

A user expects standard keyboard shortcuts to work for selection operations, including Ctrl+A to select all and Ctrl+C to copy.

**Why this priority**: Standard shortcuts are expected behavior for any text-capable interface. They complement mouse selection (P1) and provide consistency with other applications.

**Independent Test**: Can be fully tested by launching tail mode, pressing Ctrl+A to select all, then Ctrl+C to copy, and verifying clipboard contents.

**Acceptance Scenarios**:

1. **Given** tail mode is running with log entries, **When** user presses `Ctrl+A`, **Then** all visible log content is selected
2. **Given** text is selected (via mouse or keyboard), **When** user presses `Ctrl+C`, **Then** selected text is copied to system clipboard
3. **Given** text is selected, **When** user presses `Escape`, **Then** selection is cleared

---

### User Story 5 - Auto-Scroll Behavior (Priority: P2)

A user is monitoring live logs. When new entries arrive, the view should auto-scroll to show them. But when the user scrolls up to review history, auto-scroll should pause until they return to the bottom.

**Why this priority**: Proper auto-scroll behavior is critical for usability. Without it, either users miss new entries or can't review history. This is a usability requirement, not a new feature.

**Independent Test**: Can be fully tested by launching tail mode, verifying new entries auto-scroll, scrolling up, verifying auto-scroll pauses, then scrolling to bottom to verify it resumes.

**Acceptance Scenarios**:

1. **Given** tail mode is at bottom of log (FOLLOW mode), **When** new log entries arrive, **Then** view auto-scrolls to show new entries
2. **Given** tail mode is in FOLLOW mode, **When** user scrolls up (via k, Page Up, or mouse), **Then** auto-scroll is paused
3. **Given** auto-scroll is paused, **When** user scrolls to bottom (via G, End, or mouse drag scrollbar to bottom), **Then** FOLLOW mode resumes and auto-scroll is re-enabled
4. **Given** auto-scroll is paused, **When** new entries arrive, **Then** view stays at current scroll position (no jump)

---

### User Story 6 - Clipboard Fallback for Terminal.app (Priority: P3)

A user running macOS Terminal.app (which doesn't support OSC 52 clipboard) needs clipboard functionality to work via system clipboard tools.

**Why this priority**: OSC 52 covers most modern terminals. macOS Terminal.app is legacy but still used. Fallback ensures broad compatibility without degrading the primary experience.

**Independent Test**: Can be fully tested by running tail mode in Terminal.app, selecting text, and verifying it appears in macOS clipboard (testable via Cmd+V in another app).

**Acceptance Scenarios**:

1. **Given** tail mode is running in a terminal supporting OSC 52 (iTerm2, Kitty, etc.), **When** text is copied, **Then** OSC 52 escape sequence is sent and text is in system clipboard
2. **Given** tail mode is running in Terminal.app (no OSC 52), **When** text is copied, **Then** pyperclip fallback copies text via pbcopy and text is in system clipboard
3. **Given** no clipboard mechanism is available, **When** text is copied, **Then** copy fails silently without error (graceful degradation)

---

### User Story 7 - Focus Management (Priority: P2)

A user needs to switch between the log viewing area and the command input area to enter filter commands while tailing.

**Why this priority**: Tail mode already has command input. Focus switching is required for the new layout to be usable.

**Independent Test**: Can be fully tested by launching tail mode, pressing Tab to switch focus, verifying cursor moves to input, pressing Tab again to return to log.

**Acceptance Scenarios**:

1. **Given** tail mode is running with focus on log area, **When** user presses `Tab`, **Then** focus moves to command input area
2. **Given** focus is on command input, **When** user presses `Tab`, **Then** focus moves back to log area
3. **Given** focus is on log area, **When** user presses `/`, **Then** focus moves to command input area
4. **Given** focus is on command input, **When** user presses `Enter` to submit command, **Then** command executes and focus returns to log area

---

### Edge Cases

- **Live updates during selection**: When user is actively selecting text with mouse, new log entries should NOT disrupt the selection. Selection should remain stable until user releases mouse.
- **Large selection**: OSC 52 has payload limits (approximately 100KB base64-encoded). For very large selections, pyperclip fallback handles the full text. If both fail, silent degradation.
- **Filter changes during selection**: When user applies a new filter (level, regex, time) while text is selected, selection should be cleared as buffer content changes.
- **Double-click on word**: Selects the entire word (built-in Textual behavior)
- **Triple-click on line**: Selects the entire line (built-in Textual behavior)
- **Scrollbar grab**: While user drags scrollbar with mouse, auto-scroll should be paused
- **Empty log buffer**: Selection operations should gracefully handle empty state (no-op)
- **Visual mode at buffer boundaries**: When in visual mode and navigating past top/bottom, selection should stop at buffer boundary (clamp to valid range)
- **Ctrl+C with no selection**: When user presses Ctrl+C with no active selection, the operation should be a no-op (no clipboard modification, no error)
- **Yank (y) with no selection**: When user presses y outside visual mode with no selection, the operation should be a no-op

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to select text in the log viewing area using mouse click-and-drag
- **FR-002**: System MUST copy selected text to system clipboard when selection completes (mouse release)
- **FR-003**: System MUST copy selected text to clipboard when user presses Ctrl+C
- **FR-004**: System MUST support Ctrl+A to select all visible log content
- **FR-005**: System MUST support Escape key to clear current selection
- **FR-006**: System MUST support vim-style navigation keys: j (down), k (up), g (top), G (bottom)
- **FR-007**: System MUST support half-page scroll: Ctrl+D (down), Ctrl+U (up)
- **FR-008**: System MUST support full-page scroll: Ctrl+F/PageDown, Ctrl+B/PageUp
- **FR-009**: System MUST support visual mode (v) for keyboard-based selection
- **FR-010**: System MUST support visual line mode (V) for selecting full lines
- **FR-011**: System MUST support yank (y) to copy selection in visual mode
- **FR-012**: System MUST auto-scroll when at bottom (FOLLOW mode) and new entries arrive
- **FR-013**: System MUST pause auto-scroll when user scrolls up from bottom
- **FR-014**: System MUST resume FOLLOW mode when user navigates to bottom
- **FR-015**: System MUST support Tab key to switch focus between log area and command input
- **FR-016**: System MUST support / key to focus command input
- **FR-017**: System MUST support q key to quit tail mode
- **FR-018**: System MUST use OSC 52 escape sequence for clipboard when terminal supports it
- **FR-019**: System MUST fall back to pyperclip (pbcopy/xclip) when OSC 52 is unavailable
- **FR-020**: System MUST preserve existing log entry formatting including timestamps, PIDs, levels, and SQL highlighting
- **FR-021**: System MUST maintain 10,000 line buffer limit for log entries
- **FR-022**: System MUST display status bar showing FOLLOW/SCROLL mode, error/warning counts, and line count
- **FR-023**: System MUST preserve all existing tail mode commands (level, filter, since, clear, errors, etc.)

### Key Entities

- **TailLog**: Custom Log widget subclass with vim bindings and visual mode support. Contains log lines, manages selection state, handles navigation key bindings.
- **TailApp**: Main Textual Application coordinating log display, command input, status bar, and log entry consumption from tailer.
- **Selection**: Text region defined by start and end positions. Managed by Textual's built-in selection system (three-level hierarchy: App, Screen, Widget).
- **LogEntry**: Existing dataclass representing parsed log entry with timestamp, pid, level, message, and secondary fields.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select and copy log text within 2 seconds (mouse drag to clipboard)
- **SC-002**: All 10 vim navigation keys respond within 50ms (no perceptible lag)
- **SC-003**: Auto-scroll maintains smooth follow at 100+ entries per second
- **SC-004**: Visual mode selection updates in real-time as user navigates
- **SC-005**: Clipboard operations succeed in iTerm2, Kitty, WezTerm, Windows Terminal, and macOS Terminal.app
- **SC-006**: 100% of existing tail mode commands continue to function identically
- **SC-007**: Log entry colors and SQL syntax highlighting render correctly
- **SC-008**: Buffer memory usage stays within 10% of current implementation for 10,000 entries
- **SC-009**: Tail mode startup time remains under 500ms
- **SC-010**: Focus switching between log and input is instant (under 50ms)

## Assumptions

1. **Textual version**: Using Textual >= 0.89.0 which has stable Log widget with ALLOW_SELECT support
2. **Rich compatibility**: Textual's Rich integration handles all existing color/style requirements
3. **Async compatibility**: Textual's event loop integrates cleanly with existing asyncio log consumer
4. **pyperclip availability**: pyperclip is installable and functional on all supported platforms
5. **Existing command handlers**: Current cli_tail.py command handlers can be adapted to new Textual app structure
6. **NO_COLOR respected**: Textual respects NO_COLOR environment variable for accessibility
