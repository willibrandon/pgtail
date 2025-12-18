# Feature Specification: Full Screen TUI Mode

**Feature Branch**: `012-fullscreen-tui`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Full Screen TUI Mode - Add a full-screen terminal UI for log viewing with vim-style navigation, search, and mouse support"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scroll Back to Review Error (Priority: P1)

Developer is tailing logs in real-time when they notice an error flash by in the output. They need to pause the live stream and scroll back through the log history to find and examine the error in detail.

**Why this priority**: This is the primary use case that differentiates full-screen mode from standard streaming output. Without the ability to scroll back, users would need to restart the tail with different filters or search through raw log files manually.

**Independent Test**: Can be fully tested by entering fullscreen mode, generating log output, pressing Escape to switch to browse mode, and using j/k or arrow keys to scroll. Delivers immediate value by letting users review missed log entries.

**Acceptance Scenarios**:

1. **Given** user is in fullscreen mode with follow mode active, **When** they press `Escape`, **Then** system switches to browse mode and user can freely scroll through the buffer without new entries moving the view
2. **Given** user is in browse mode, **When** they press `k` or `Up`, **Then** the view scrolls up by one line
3. **Given** user is in browse mode, **When** they press `j` or `Down`, **Then** the view scrolls down by one line
4. **Given** user is in browse mode, **When** they press `f` or `Escape` again, **Then** follow mode resumes and the view jumps to the latest entries

---

### User Story 2 - Search for Pattern in Logs (Priority: P1)

Developer wants to find all occurrences of a specific pattern (table name, error code, user ID) in the log history. They use vim-style search to locate matches and navigate between them.

**Why this priority**: Search is fundamental to log analysis. Combined with scrolling, it enables users to efficiently locate specific events without leaving the TUI.

**Independent Test**: Can be fully tested by pressing `/`, typing a pattern, pressing Enter, and using `n`/`N` to navigate matches. Delivers value by highlighting relevant log entries instantly.

**Acceptance Scenarios**:

1. **Given** user is in fullscreen mode, **When** they press `/`, **Then** a search prompt appears at the bottom of the screen
2. **Given** search prompt is active, **When** they type a pattern and press `Enter`, **Then** the view jumps to the first match and the match is highlighted
3. **Given** search results exist, **When** they press `n`, **Then** the view jumps to the next match
4. **Given** search results exist, **When** they press `N`, **Then** the view jumps to the previous match
5. **Given** user presses `?` instead of `/`, **When** they enter a pattern, **Then** search proceeds backward from current position
6. **Given** no matches are found, **When** search completes, **Then** user sees "Pattern not found" message
7. **Given** search prompt is active, **When** user presses `Escape`, **Then** search is cancelled and prompt closes without executing search

---

### User Story 3 - Navigate with Keyboard Shortcuts (Priority: P2)

Experienced vim user wants efficient keyboard navigation through large log buffers. They use page navigation and jump-to-end shortcuts to quickly move through thousands of lines.

**Why this priority**: Power users need efficient navigation for large logs. Once basic scrolling works, these shortcuts significantly improve productivity.

**Independent Test**: Can be tested by loading a buffer with many entries and verifying Ctrl+D/U move by half-page, g/G jump to top/bottom.

**Acceptance Scenarios**:

1. **Given** user is in fullscreen mode with a large buffer, **When** they press `Ctrl+D`, **Then** the view scrolls down by half a page
2. **Given** user is in fullscreen mode, **When** they press `Ctrl+U`, **Then** the view scrolls up by half a page
3. **Given** user is anywhere in the buffer, **When** they press `g`, **Then** the view jumps to the first line (top)
4. **Given** user is anywhere in the buffer, **When** they press `G`, **Then** the view jumps to the last line (bottom)

---

### User Story 4 - Mouse Navigation and Selection (Priority: P2)

Developer prefers using mouse for navigation. They use scroll wheel to browse logs, click to position, and select text for copying.

**Why this priority**: Mouse support broadens accessibility and matches user expectations for modern terminal applications. Important for users less familiar with vim keybindings.

**Independent Test**: Can be tested by using scroll wheel to navigate and selecting text with click-and-drag.

**Acceptance Scenarios**:

1. **Given** user is in fullscreen mode, **When** they scroll the mouse wheel down, **Then** the view scrolls down
2. **Given** user is in fullscreen mode, **When** they scroll the mouse wheel up, **Then** the view scrolls up
3. **Given** user wants to copy text, **When** they click and drag to select log content, **Then** the text is selected and can be copied to clipboard

---

### User Story 5 - Enter and Exit Fullscreen Mode (Priority: P1)

User wants to switch between the standard REPL mode and fullscreen TUI mode while maintaining their current tailing session and filters.

**Why this priority**: This is the entry/exit point for the feature. Users must be able to easily toggle between modes.

**Independent Test**: Can be tested by running `fullscreen` command while tailing, verifying TUI appears, then pressing `q` to return to REPL.

**Acceptance Scenarios**:

1. **Given** user is in standard REPL mode with an active tail, **When** they type `fullscreen` or `fs`, **Then** the screen clears and fullscreen TUI mode activates with existing log buffer
2. **Given** user is in fullscreen mode, **When** they press `q`, **Then** fullscreen mode exits and user returns to the standard REPL (buffer is preserved)
3. **Given** user is in fullscreen mode with follow mode active, **When** new log entries arrive, **Then** entries appear at the bottom and view auto-scrolls to show them
4. **Given** user previously exited fullscreen mode, **When** they re-enter with `fullscreen` or `fs`, **Then** the previous buffer history is shown plus any new entries that arrived while in REPL mode

---

### Edge Cases

- What happens when buffer reaches 10,000 line limit? Oldest entries are discarded (FIFO) while maintaining scroll position relative to content
- What happens when user searches for a pattern with no matches? Display "Pattern not found" message briefly, return to previous view
- What happens when terminal is resized during fullscreen mode? Layout redraws to fit new dimensions, maintaining relative scroll position
- How does system handle rapid log output (1000+ lines/sec)? Batch updates to maintain responsiveness, potentially skipping intermediate renders
- What happens if user tries to scroll past the buffer boundaries? View stops at first/last line, does not wrap or error
- What happens when follow mode is active but user scrolls manually? Follow mode automatically pauses when user initiates manual scroll

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `fullscreen` (alias `fs`) command to enter full-screen TUI mode
- **FR-002**: System MUST maintain a scrollable buffer of at least 10,000 log lines in memory
- **FR-003**: System MUST support two modes: "follow mode" (auto-scroll to new entries) and "browse mode" (free navigation)
- **FR-004**: System MUST toggle between follow/browse mode when user presses `Escape` (when no prompt is active)
- **FR-004a**: System MUST cancel and close the search prompt when user presses `Escape` while search prompt is active (Escape in search context takes priority over mode toggle)
- **FR-005**: System MUST support line-by-line scrolling with `j`/`k` and `Up`/`Down` arrow keys
- **FR-006**: System MUST support page scrolling with `Ctrl+D` (down) and `Ctrl+U` (up)
- **FR-007**: System MUST support jump-to-boundary navigation with `g` (top) and `G` (bottom)
- **FR-008**: System MUST provide forward search with `/pattern` syntax
- **FR-009**: System MUST provide backward search with `?pattern` syntax
- **FR-010**: System MUST navigate between search matches with `n` (next) and `N` (previous)
- **FR-011**: System MUST visually highlight search matches in the buffer
- **FR-012**: System MUST exit fullscreen mode and return to REPL when user presses `q`
- **FR-013**: System MUST support mouse wheel scrolling
- **FR-014**: System MUST support text selection with mouse for clipboard copying
- **FR-015**: System MUST preserve existing filters (level, regex, field, time) when entering fullscreen mode
- **FR-016**: System MUST display a status bar showing current mode (follow/browse), line count, and search status
- **FR-017**: System MUST handle terminal resize events gracefully, redrawing the layout

### Key Entities

- **LogBuffer**: Circular buffer storing formatted log entries with a configurable maximum size (default 10,000 lines). Supports random access for scrolling and search operations. Persists across fullscreen mode transitions (preserved when exiting to REPL, continues accumulating entries).
- **ViewState**: Current view position within the buffer, including scroll offset, selected line, and search state (pattern, matches, current match index).
- **DisplayMode**: Enum distinguishing follow mode (auto-scroll) from browse mode (manual navigation).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can scroll back through at least 10,000 lines of log history without noticeable delay
- **SC-002**: Search finds and highlights first match within 100ms for typical patterns on a full 10,000 line buffer
- **SC-003**: Follow mode maintains real-time display for log output up to 1,000 lines per second without dropping entries
- **SC-004**: Vim users can navigate without consulting documentation (keybindings match vim conventions exactly)
- **SC-005**: Mouse scroll wheel and text selection work identically to standard terminal behavior
- **SC-006**: Transition between REPL and fullscreen mode completes in under 200ms with no visible flicker
- **SC-007**: 90% of users who enable fullscreen mode continue using it in subsequent sessions (adoption metric)

## Clarifications

### Session 2025-12-17

- Q: Should there be a maximum memory limit for the log buffer? → A: No memory cap - rely on fixed 10,000 line limit only
- Q: How should users cancel an active search prompt? → A: Escape cancels search prompt (takes priority over follow/browse toggle)
- Q: What happens to the log buffer when exiting fullscreen mode? → A: Buffer preserved - re-entering fullscreen shows same history plus any new entries

## Assumptions

- Memory consumption is bounded by the fixed 10,000 line limit; no additional memory cap is enforced (typical worst-case ~5MB for long log lines)
- The existing prompt_toolkit dependency supports full-screen application mode (verified: yes, via `Application` class)
- Terminal emulators support the required ANSI escape sequences for full-screen mode
- Mouse support depends on terminal emulator capabilities; graceful degradation when unavailable
- Buffer size of 10,000 lines provides sufficient history for typical debugging sessions
- Half-page scroll distance follows vim convention (half of visible terminal height)
- Search uses regex patterns consistent with existing `filter` command syntax

## Out of Scope

- Split panes or multiple buffer views (separate feature)
- Syntax highlighting for SQL or other log content (separate feature)
- Persistent log storage beyond session (logs are memory-only during session)
- Custom keybinding configuration (use standard vim keybindings only)
- Recording or replay of log sessions
