# Feature Specification: Status Bar Tail Mode

**Feature Branch**: `016-status-bar-tail`
**Created**: 2025-12-30
**Status**: Draft
**Input**: User description: "Replace the simple streaming tail with a split-screen interface featuring scrollable log output, a status bar with live stats and filter state, and an always-visible command input line."

## Clarifications

### Session 2025-12-30

- Q: When a filter is applied, should it filter existing buffer contents or only new entries? → A: Both existing buffer AND new entries (buffer display is re-filtered to show only matching lines)
- Q: When user is paused at old position and oldest lines are evicted, what happens to scroll position? → A: Adjust scroll position to keep the same content visible (scroll offset decrements as lines evict)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuous Log Streaming with Command Input (Priority: P1)

A developer tailing PostgreSQL logs needs to apply filters without interrupting the log stream. Currently, adjusting filters requires stopping the tail (Ctrl+C), typing the command, and resuming. With status bar tail mode, logs stream continuously in the top area while the user types commands in the always-visible input line at the bottom.

**Why this priority**: This is the core value proposition - eliminating the pause/resume cycle that makes the current workflow cumbersome. Without this, the feature has no purpose.

**Independent Test**: Can be fully tested by starting tail mode on an active PostgreSQL instance, typing filter commands while logs stream, and verifying both continue simultaneously.

**Acceptance Scenarios**:

1. **Given** the user has started tail mode on an active PostgreSQL instance, **When** logs are being generated and the user types a command in the input line, **Then** logs continue streaming in the output area without pause.
2. **Given** the user types `level error` and presses Enter, **When** the command executes, **Then** the level filter applies immediately and only ERROR level logs appear, while streaming continues.
3. **Given** the user is typing a command, **When** new log entries arrive, **Then** the entries appear in the output area and the user's partially-typed command remains intact in the input line.

---

### User Story 2 - Real-time Status Bar Updates (Priority: P1)

An operations engineer watching logs during a deployment needs visibility into error counts and current filter state without running separate commands. The status bar displays live statistics (error count, warning count, total lines), active filters, PostgreSQL instance info, and follow mode status.

**Why this priority**: Real-time visibility is the second core value - knowing the current state at a glance eliminates constant mental tracking and command execution.

**Independent Test**: Can be tested by tailing logs, triggering errors in PostgreSQL, and observing status bar updates in real-time.

**Acceptance Scenarios**:

1. **Given** the user is tailing logs and an ERROR level entry is received, **When** the entry is processed, **Then** the error count in the status bar increments within 100ms.
2. **Given** the user applies a filter with `level error,warning`, **When** the filter activates, **Then** the status bar displays `levels:ERROR,WARNING`.
3. **Given** the user sets a slow query threshold with `slow 100`, **When** the threshold is active, **Then** the status bar displays `slow:>100ms`.
4. **Given** the user is connected to a PostgreSQL 17 instance on port 5432, **When** viewing the status bar, **Then** it displays `PG17` and `:5432`.

---

### User Story 3 - Scrollback Navigation (Priority: P2)

A DBA sees an error flash by in the log stream and needs to scroll back to examine it without losing their place in the live stream. The user can scroll through a 10,000-line buffer using keyboard navigation, then press End to resume following live logs.

**Why this priority**: Scrollback is essential for investigating issues but builds on the core streaming capability. Users can work without it initially.

**Independent Test**: Can be tested by generating enough logs to fill the buffer, scrolling back, examining historical entries, then pressing End to resume live tailing.

**Acceptance Scenarios**:

1. **Given** the user is following live logs, **When** they press Page Up or Up arrow, **Then** the view scrolls back and the status bar shows `PAUSED`.
2. **Given** the user has scrolled back and new logs arrive, **When** viewing the status bar, **Then** it shows `PAUSED +N new` where N is the count of new entries since scrolling.
3. **Given** the user has scrolled back in the buffer, **When** they press End, **Then** the view jumps to the latest log entry and status changes to `FOLLOW`.
4. **Given** the buffer contains 10,000 lines and new lines arrive, **When** the oldest lines are evicted, **Then** the buffer maintains exactly 10,000 lines maximum.

---

### User Story 4 - Inline Command Output (Priority: P2)

A developer wants to check error statistics while continuing to watch logs. Running the `errors` command displays the summary inline in the log output area with visual separators, then log streaming resumes below it.

**Why this priority**: Inline output prevents context-switching but is an enhancement to the core streaming capability.

**Independent Test**: Can be tested by running `errors` during tailing and verifying output appears inline with separators, followed by continued log streaming.

**Acceptance Scenarios**:

1. **Given** the user is tailing logs, **When** they run the `errors` command, **Then** the error summary appears inline in the log output area with dotted-line separators above and below.
2. **Given** command output has been displayed inline, **When** new log entries arrive, **Then** they appear below the command output and streaming continues normally.
3. **Given** the user runs `connections`, **When** the command completes, **Then** the connection summary appears inline with separators.

---

### User Story 5 - Quick Filter Commands (Priority: P2)

A developer wants to quickly toggle filters to focus on specific log types. Short commands like `level error`, `filter /deadlock/`, `since 5m`, and `slow 100` apply immediately without interrupting the log stream.

**Why this priority**: Quick filters enhance usability but the core streaming and status visibility work without them.

**Independent Test**: Can be tested by running each filter command and verifying the filter applies immediately with status bar update.

**Acceptance Scenarios**:

1. **Given** the user types `filter /deadlock/` and presses Enter, **When** the filter is applied, **Then** only log lines matching "deadlock" appear and the status bar shows `filter:/deadlock/`.
2. **Given** the user types `since 5m` and presses Enter, **When** the filter is applied, **Then** only logs from the last 5 minutes appear and the status bar shows `since:5m`.
3. **Given** the user types `clear` and presses Enter, **When** the command executes, **Then** all filters are removed and the status bar shows `levels:ALL` with no filter indicators.

---

### User Story 6 - Mouse Scroll Navigation (Priority: P3)

A user prefers using the mouse scroll wheel to navigate through the log buffer instead of keyboard shortcuts.

**Why this priority**: Mouse support is a usability enhancement but keyboard navigation covers the core need.

**Independent Test**: Can be tested by using the scroll wheel to navigate the buffer and verifying smooth scrolling behavior.

**Acceptance Scenarios**:

1. **Given** the user is in follow mode, **When** they scroll up with the mouse wheel, **Then** the view scrolls back through the buffer and status changes to `PAUSED`.
2. **Given** the user has scrolled up, **When** they scroll down past the latest entry, **Then** the view resumes following and status changes to `FOLLOW`.

---

### User Story 7 - Exit to REPL (Priority: P3)

A user needs to run complex multi-command workflows that are easier in the standard REPL. They can exit tail mode with `stop`, `exit`, `q`, or Ctrl+C to return to the pgtail prompt.

**Why this priority**: Exit capability is necessary but simple to implement once the core is working.

**Independent Test**: Can be tested by entering tail mode and using each exit method to verify return to REPL.

**Acceptance Scenarios**:

1. **Given** the user is in tail mode, **When** they type `stop` and press Enter, **Then** tailing stops and they return to the `pgtail>` prompt.
2. **Given** the user is in tail mode, **When** they press Ctrl+C, **Then** tailing stops gracefully and they return to the `pgtail>` prompt.
3. **Given** the user has returned to the REPL, **When** they run `tail 0`, **Then** they re-enter tail mode for the same instance.

---

### User Story 8 - Terminal Resize Handling (Priority: P3)

The user resizes their terminal window while tailing. The layout reflows to the new dimensions, preserving scroll position relative to content.

**Why this priority**: Resize handling is important for usability but the feature works at a fixed size initially.

**Independent Test**: Can be tested by resizing the terminal during tailing and verifying the layout adapts correctly.

**Acceptance Scenarios**:

1. **Given** the user is viewing logs in a 120x40 terminal, **When** they resize to 80x24, **Then** the layout reflows with log lines wrapping appropriately and status bar remaining visible.
2. **Given** the user has scrolled to a specific log entry, **When** they resize the terminal, **Then** that entry remains visible in the view.
3. **Given** the terminal is resized below 40 columns or 10 rows, **When** the layout renders, **Then** a warning message indicates the terminal is too small for proper display.

---

### Edge Cases

- What happens when the log file rotates during tailing? The tailer detects the new file and continues streaming (existing behavior from 016-resilient-tailing).
- What happens when PostgreSQL restarts? The tailer detects the new log file via current_logfiles and resumes.
- What happens when the user types a command that doesn't exist? An error message displays inline and streaming continues.
- What happens when network I/O is slow? UI remains responsive; log processing happens in a background thread.
- What happens when log volume exceeds 1000 lines/second? Ring buffer evicts oldest entries; UI batches updates to maintain responsiveness.
- What happens when user is scrolled back and buffer evicts old lines? Scroll position adjusts to keep the same content visible; when the viewed content itself is evicted, view shifts to newest available content.
- What happens when the terminal doesn't support colors? Graceful degradation to plain text output respecting NO_COLOR environment variable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a split-screen interface with log output area (top), status bar (middle), and command input line (bottom).
- **FR-002**: System MUST stream log entries to the output area continuously while the user types commands.
- **FR-003**: System MUST maintain a ring buffer of log entries with a maximum size of 10,000 lines.
- **FR-004**: System MUST update the status bar in real-time (<100ms latency) when error/warning counts change.
- **FR-005**: System MUST display in the status bar: error count, warning count, total lines, active level filter, active regex filter, active time filter, slow query threshold, PostgreSQL version, port, and follow/paused mode.
- **FR-006**: System MUST support keyboard navigation: Up/Down for single line scroll, Page Up/Page Down for page scroll, Home for buffer start, End for resume follow.
- **FR-007**: System MUST switch from FOLLOW to PAUSED mode when the user scrolls away from the live position.
- **FR-008**: System MUST track and display "+N new" count in status bar when paused and new entries arrive.
- **FR-008a**: When buffer evicts oldest lines while user is paused, system MUST adjust scroll position to keep the same content visible until that content itself is evicted.
- **FR-009**: System MUST support mouse scroll wheel for buffer navigation.
- **FR-010**: System MUST display command output (errors, connections, stats) inline in the log area with visual separators.
- **FR-011**: System MUST support tab completion and command history in the input line.
- **FR-012**: System MUST exit to REPL on `stop`, `exit`, `q` commands, or Ctrl+C.
- **FR-013**: System MUST support screen redraw with Ctrl+L.
- **FR-014**: System MUST handle terminal resize events by reflowing the layout.
- **FR-015**: System MUST display a warning when terminal size is below minimum (40 columns x 10 rows).
- **FR-016**: System MUST support all existing filter commands: `level`, `filter`, `since`, `until`, `between`, `slow`.
- **FR-016a**: When a filter is applied, system MUST re-filter both existing buffer contents AND new incoming entries, showing only matching lines in the display.
- **FR-017**: System MUST support `clear` command to remove all active filters.
- **FR-018**: System MUST support `pause` and `follow` commands to control follow mode.
- **FR-019**: System MUST process log entries in a background thread with thread-safe handoff to the UI.
- **FR-020**: System MUST remain responsive during high log volume (1000+ lines/second).

### Key Entities

- **TailBuffer**: Ring buffer (deque) storing formatted log lines with maximum capacity of 10,000, supporting append, scroll position tracking, and visible range queries.
- **TailStatus**: State container for status bar data including error/warning counts, active filters, instance info, and follow mode.
- **TailApp**: Main application coordinating the tailer thread, buffer, status, layout, and user input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Logs stream without visible interruption while user types commands in the input line.
- **SC-002**: Status bar error/warning counts update within 100ms of log entry arrival.
- **SC-003**: Scrollback buffer preserves at least 10,000 log lines before eviction.
- **SC-004**: User can scroll from current position to buffer start in under 2 seconds using Page Up.
- **SC-005**: Resume to live tail (pressing End from any scroll position) completes in under 100ms.
- **SC-006**: UI remains responsive (input latency under 50ms) during log volumes of 1000 lines/second.
- **SC-007**: Memory usage stays bounded (buffer plus overhead under 50MB for 10,000 lines).
- **SC-008**: Tab completion suggestions appear within 100ms of Tab key press.
- **SC-009**: Terminal resize reflows layout within 200ms without losing scroll context.
- **SC-010**: 90% of filter commands (`level`, `filter`, `since`, `slow`) complete and update status bar within 50ms.
- **SC-011**: Ctrl+C exits cleanly to REPL within 200ms without leaving orphan threads.
- **SC-012**: All existing REPL commands work identically in tail mode (same syntax, same output format).
