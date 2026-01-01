# Tasks: Log Entry Selection and Copy

**Input**: Design documents from `/specs/017-log-selection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Branch**: `017-log-selection`
**Generated**: 2025-12-31

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency configuration

- [X] T001 Add textual>=0.89.0 and pyperclip>=1.8.0 to dependencies in pyproject.toml
- [X] T002 Run `uv sync` to install new dependencies and verify installation
- [X] T003 [P] Create empty module file pgtail_py/tail_textual.py with module docstring
- [X] T004 [P] Create empty module file pgtail_py/tail_log.py with module docstring
- [X] T005 [P] Create empty module file pgtail_py/tail_rich.py with module docstring
- [X] T006 Verify Textual installation with `python -c "from textual import __version__; print(__version__)"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement Rich text formatting for LogEntry in pgtail_py/tail_rich.py (LEVEL_STYLES dict, format_entry_as_rich function)
- [X] T008 Implement format_entry_compact function returning plain string in pgtail_py/tail_rich.py
- [X] T009 Create TailLog base class extending Log with ALLOW_SELECT=True in pgtail_py/tail_log.py
- [X] T010 Create TailApp shell class extending App in pgtail_py/tail_textual.py with compose() yielding TailLog, Static, Input
- [X] T011 Implement TailApp CSS for layout (TailLog height:1fr, status height:1, Input dock:bottom) in pgtail_py/tail_textual.py
- [X] T012 Implement TailApp __init__ accepting state, instance, log_path, max_lines in pgtail_py/tail_textual.py
- [X] T013 Implement TailApp.run_tail_mode() class method entry point in pgtail_py/tail_textual.py
- [X] T014 Implement TailApp.on_mount() to start LogTailer and background consumer in pgtail_py/tail_textual.py
- [X] T015 Implement TailApp.on_unmount() to stop tailer and set _running=False in pgtail_py/tail_textual.py
- [X] T016 Implement background worker _start_consumer() using @work decorator in pgtail_py/tail_textual.py
- [X] T017 Implement _add_entry() method to add formatted entries to TailLog in pgtail_py/tail_textual.py
- [X] T018 Implement _update_status() method to update Static status bar in pgtail_py/tail_textual.py
- [X] T019 Add format_plain() method to TailStatus class in pgtail_py/tail_status.py for plain text status output
- [X] T020 Implement action_quit() bound to 'q' key in pgtail_py/tail_textual.py
- [X] T021 Implement _handle_command() method to dispatch commands to cli_tail handlers in pgtail_py/tail_textual.py
- [X] T022 Implement on_input_submitted() event handler to process command input in pgtail_py/tail_textual.py
- [X] T023 Add log_widget parameter to handle_tail_command() function signature in pgtail_py/cli_tail.py
- [X] T024 Update handle_tail_command() to use log_widget for clear command in pgtail_py/cli_tail.py
- [X] T025 Update cli.py to import TailApp from tail_textual and call TailApp.run_tail_mode() in pgtail_py/cli.py
- [X] T026 Add deprecation warning to tail_app.py module docstring in pgtail_py/tail_app.py
- [X] T027 Add deprecation warning to tail_layout.py module docstring in pgtail_py/tail_layout.py
- [X] T028 Run `make test` to verify no regressions from foundational changes
- [X] T029 Run `make lint` to verify code style compliance

**Checkpoint**: Foundation ready - TailApp can launch, display log entries, accept commands, and quit. User story implementation can now begin.

---

## Phase 3: User Story 1 - Mouse Selection and Copy (Priority: P1)

**Goal**: Users can select text with mouse drag and copy to clipboard

**Independent Test**: Launch tail mode, generate log entries, select text with mouse drag, verify selected text appears in system clipboard (Cmd+V in another app)

### Implementation for User Story 1

- [X] T030 [US1] Verify TailLog ALLOW_SELECT=True enables mouse selection in pgtail_py/tail_log.py
- [X] T031 [US1] Implement _copy_with_fallback() method with OSC 52 + pyperclip in pgtail_py/tail_log.py
- [X] T032 [US1] Add action_copy_selection() bound to Ctrl+C in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T033 [US1] Implement action_copy_selection() to call _copy_with_fallback with selected text in pgtail_py/tail_log.py
- [X] T034 [US1] Add SelectionCopied Message class for clipboard copy events in pgtail_py/tail_log.py
- [X] T035 [US1] Post SelectionCopied message after successful copy in pgtail_py/tail_log.py
- [X] T036 [US1] Handle empty selection in _copy_with_fallback (return early, no-op) in pgtail_py/tail_log.py
- [X] T037 [US1] Handle clipboard exceptions with graceful degradation (return False) in pgtail_py/tail_log.py
- [x] T038 [US1] Test mouse selection and Ctrl+C copy manually in iTerm2/Kitty terminal
- [x] T039 [US1] Test multi-line selection across ERROR with DETAIL and STATEMENT fields manually

**Checkpoint**: User Story 1 complete - mouse selection and copy works

---

## Phase 4: User Story 2 - Vim-Style Navigation (Priority: P2)

**Goal**: Users can navigate log history with vim keybindings (j/k/g/G/Ctrl+D/Ctrl+U)

**Independent Test**: Launch tail mode, populate buffer with 100+ entries, verify each vim navigation key moves viewport correctly

### Implementation for User Story 2

- [X] T040 [US2] Add Binding for j -> action_scroll_down in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T041 [US2] Add Binding for k -> action_scroll_up in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T042 [US2] Implement action_scroll_down() calling self.scroll_down() in pgtail_py/tail_log.py
- [X] T043 [US2] Implement action_scroll_up() calling self.scroll_up() in pgtail_py/tail_log.py
- [X] T044 [US2] Add Binding for g -> action_scroll_home in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T045 [US2] Add Binding for shift+g -> action_scroll_end in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T046 [US2] Implement action_scroll_home() calling self.scroll_home() in pgtail_py/tail_log.py
- [X] T047 [US2] Implement action_scroll_end() calling self.scroll_end() in pgtail_py/tail_log.py
- [X] T048 [US2] Add Binding for ctrl+d -> action_half_page_down in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T049 [US2] Add Binding for ctrl+u -> action_half_page_up in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T050 [US2] Implement action_half_page_down() using scroll_relative(y=viewport_height//2) in pgtail_py/tail_log.py
- [X] T051 [US2] Implement action_half_page_up() using scroll_relative(y=-viewport_height//2) in pgtail_py/tail_log.py
- [X] T052 [US2] Add Binding for ctrl+f -> action_page_down in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T053 [US2] Add Binding for pagedown -> action_page_down in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T054 [US2] Add Binding for ctrl+b -> action_page_up in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T055 [US2] Add Binding for pageup -> action_page_up in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T056 [US2] Implement action_page_down() calling self.scroll_page_down() in pgtail_py/tail_log.py
- [X] T057 [US2] Implement action_page_up() calling self.scroll_page_up() in pgtail_py/tail_log.py
- [x] T058 [US2] Verify scroll boundaries clamp correctly (no scroll past top/bottom) manually
- [x] T059 [US2] Test all vim navigation keys (j, k, g, G, Ctrl+D, Ctrl+U, Ctrl+F, Ctrl+B) manually

**Checkpoint**: User Story 2 complete - vim navigation works

---

## Phase 5: User Story 3 - Vim Visual Mode Selection (Priority: P3)

**Goal**: Users can select text with keyboard using vim visual mode (v/V/y/Escape)

**Independent Test**: Launch tail mode, press v to enter visual mode, navigate with j/k, press y to yank, verify text is in clipboard

### Implementation for User Story 3

- [X] T060 [US3] Add _visual_mode: bool = False instance variable in TailLog.__init__ in pgtail_py/tail_log.py
- [X] T061 [US3] Add _visual_line_mode: bool = False instance variable in TailLog.__init__ in pgtail_py/tail_log.py
- [X] T062 [US3] Add _visual_anchor_line: int | None = None instance variable in TailLog.__init__ in pgtail_py/tail_log.py
- [X] T063 [US3] Add visual_mode read-only property returning _visual_mode in pgtail_py/tail_log.py
- [X] T064 [US3] Add visual_line_mode read-only property returning _visual_line_mode in pgtail_py/tail_log.py
- [X] T065 [US3] Add Binding for v -> action_visual_mode in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T066 [US3] Implement action_visual_mode() setting _visual_mode=True, _visual_line_mode=False, anchor to current line in pgtail_py/tail_log.py
- [X] T067 [US3] Implement _get_current_line() returning viewport center line index in pgtail_py/tail_log.py
- [X] T068 [US3] Implement _update_selection() creating Selection from anchor to current line in pgtail_py/tail_log.py
- [X] T069 [US3] Add Binding for shift+v -> action_visual_line_mode in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T070 [US3] Implement action_visual_line_mode() setting _visual_mode=True, _visual_line_mode=True, anchor to current line in pgtail_py/tail_log.py
- [X] T071 [US3] Modify action_scroll_down to call _update_selection() when _visual_mode is True in pgtail_py/tail_log.py
- [X] T072 [US3] Modify action_scroll_up to call _update_selection() when _visual_mode is True in pgtail_py/tail_log.py
- [X] T073 [US3] Add Binding for y -> action_yank in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T074 [US3] Implement action_yank() copying selection, clearing selection, exiting visual mode in pgtail_py/tail_log.py
- [X] T075 [US3] Add Binding for escape -> action_clear_selection in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T076 [US3] Implement action_clear_selection() clearing selection and exiting visual mode in pgtail_py/tail_log.py
- [X] T077 [US3] Add VisualModeChanged Message class for visual mode state changes in pgtail_py/tail_log.py
- [X] T078 [US3] Post VisualModeChanged message on visual mode enter/exit in pgtail_py/tail_log.py
- [X] T079 [US3] Handle visual mode at buffer boundaries (clamp selection to 0..line_count-1) in pgtail_py/tail_log.py
- [x] T080 [US3] Test visual mode: v, navigate j/k, y to yank, verify clipboard manually
- [x] T081 [US3] Test visual line mode: V, navigate j/k, y to yank full lines, verify clipboard manually
- [x] T082 [US3] Test Escape to exit visual mode and clear selection manually

**Checkpoint**: User Story 3 complete - vim visual mode selection works

---

## Phase 6: User Story 4 - Standard Selection Shortcuts (Priority: P2)

**Goal**: Users can use Ctrl+A to select all and Ctrl+C to copy (standard shortcuts)

**Independent Test**: Launch tail mode, press Ctrl+A to select all, then Ctrl+C to copy, verify clipboard contents

### Implementation for User Story 4

- [X] T083 [US4] Add Binding for ctrl+a -> action_select_all in TailLog BINDINGS in pgtail_py/tail_log.py
- [X] T084 [US4] Implement action_select_all() setting selection to SELECT_ALL in pgtail_py/tail_log.py
- [x] T085 [US4] Verify Ctrl+C binding from US1 (T032) works after Ctrl+A select all manually
- [x] T086 [US4] Verify Escape binding from US3 (T075) clears selection from Ctrl+A manually

**Checkpoint**: User Story 4 complete - standard Ctrl+A/Ctrl+C shortcuts work

---

## Phase 7: User Story 5 - Auto-Scroll Behavior (Priority: P2)

**Goal**: View auto-scrolls when at bottom (FOLLOW mode), pauses when user scrolls up, resumes when user returns to bottom

**Independent Test**: Launch tail mode, verify new entries auto-scroll, scroll up, verify auto-scroll pauses, scroll to bottom, verify it resumes

### Implementation for User Story 5

- [X] T087 [US5] Verify TailLog auto_scroll=True is set in compose() in pgtail_py/tail_textual.py
- [X] T088 [US5] Verify _add_entry() uses write_line() with default scroll_end behavior in pgtail_py/tail_textual.py
- [X] T089 [US5] Update _add_entry() to track was_at_end = log.is_vertical_scroll_end before write in pgtail_py/tail_textual.py
- [X] T090 [US5] Update _add_entry() to update status bar FOLLOW/SCROLL mode based on was_at_end in pgtail_py/tail_textual.py
- [X] T091 [US5] Update TailStatus to track follow_mode and new_since_pause in pgtail_py/tail_status.py
- [X] T092 [US5] Add set_follow_mode(follow: bool, new_count: int) method to TailStatus in pgtail_py/tail_status.py
- [X] T093 [US5] Update format_plain() to show FOLLOW or SCROLL+N in status bar in pgtail_py/tail_status.py
- [x] T094 [US5] Verify scrolling up (k, Page Up, mouse) pauses auto-scroll (Log widget built-in behavior) manually
- [x] T095 [US5] Verify pressing G returns to bottom and resumes FOLLOW mode (action_scroll_end sets is_vertical_scroll_end) manually
- [x] T096 [US5] Verify new entries don't jump view when user is reviewing history manually
- [x] T097 [US5] Verify scrollbar grab pauses auto-scroll (Log widget checks is_vertical_scrollbar_grabbed) manually

**Checkpoint**: User Story 5 complete - auto-scroll FOLLOW/SCROLL mode works

---

## Phase 8: User Story 6 - Clipboard Fallback for Terminal.app (Priority: P3)

**Goal**: Clipboard works in macOS Terminal.app (no OSC 52) via pyperclip fallback

**Independent Test**: Run tail mode in Terminal.app, select text, verify it appears in macOS clipboard (Cmd+V in another app)

### Implementation for User Story 6

- [X] T098 [US6] Verify _copy_with_fallback() tries OSC 52 first in pgtail_py/tail_log.py
- [X] T099 [US6] Verify _copy_with_fallback() falls back to pyperclip.copy() in pgtail_py/tail_log.py
- [X] T100 [US6] Handle pyperclip ImportError gracefully (pyperclip optional) in pgtail_py/tail_log.py
- [X] T101 [US6] Handle pyperclip.PyperclipException gracefully (no clipboard mechanism) in pgtail_py/tail_log.py
- [x] T102 [US6] Test clipboard in iTerm2 (OSC 52 works) manually
- [x] T103 [US6] Test clipboard in macOS Terminal.app (pyperclip fallback) manually
- [x] T104 [US6] Verify graceful degradation when neither mechanism works (return False, no exception) manually

**Checkpoint**: User Story 6 complete - clipboard fallback works

---

## Phase 9: User Story 7 - Focus Management (Priority: P2)

**Goal**: Users can switch focus between log area and command input with Tab and /

**Independent Test**: Launch tail mode, press Tab to switch focus to input, press Tab again to return to log, verify cursor position

### Implementation for User Story 7

- [X] T105 [US7] Add Binding for tab -> action_toggle_focus in TailApp BINDINGS in pgtail_py/tail_textual.py
- [X] T106 [US7] Implement action_toggle_focus() switching focus between log and input in pgtail_py/tail_textual.py
- [X] T107 [US7] Add Binding for slash -> action_focus_input in TailApp BINDINGS in pgtail_py/tail_textual.py
- [X] T108 [US7] Implement action_focus_input() focusing input widget in pgtail_py/tail_textual.py
- [X] T109 [US7] Verify on_input_submitted() returns focus to log after command execution in pgtail_py/tail_textual.py
- [X] T110 [US7] Test Tab toggles focus between log and input manually
- [X] T111 [US7] Test / focuses input from log manually
- [X] T112 [US7] Test Enter on command returns focus to log manually

**Checkpoint**: User Story 7 complete - focus management works

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, validation, documentation, and final verification

### Edge Case Handling

- [X] T113 Handle live updates during selection: verify selection stable when new entries arrive (Log widget behavior)
- [X] T114 Handle large selection: verify pyperclip fallback handles >100KB text in pgtail_py/tail_log.py
- [X] T115 Handle filter changes during selection: clear selection when buffer rebuilds in pgtail_py/tail_textual.py
- [X] T116 Handle double-click word selection: verify built-in Textual behavior works
- [X] T117 Handle triple-click line selection: verify built-in Textual behavior works
- [X] T118 Handle empty log buffer: verify selection operations gracefully handle empty state in pgtail_py/tail_log.py

### Existing Command Preservation (FR-023)

- [X] T119 Verify 'level' command works with new TailApp in pgtail_py/cli_tail.py
- [X] T120 Verify 'filter' command works with new TailApp in pgtail_py/cli_tail.py
- [X] T121 Verify 'since' command works with new TailApp in pgtail_py/cli_tail.py
- [X] T122 Verify 'until' command works with new TailApp in pgtail_py/cli_tail.py
- [X] T123 Verify 'clear' command clears TailLog in pgtail_py/cli_tail.py
- [X] T124 Verify 'errors' command shows error statistics in pgtail_py/cli_tail.py
- [X] T125 Verify 'connections' command shows connection stats in pgtail_py/cli_tail.py
- [X] T126 Verify 'help' command shows available commands in pgtail_py/cli_tail.py

### Formatting Preservation (FR-020)

- [X] T127 Verify timestamp formatting matches compact display mode in pgtail_py/tail_rich.py
- [X] T128 Verify PID formatting matches compact display mode in pgtail_py/tail_rich.py
- [X] T129 Verify level colors match theme configuration in pgtail_py/tail_rich.py
- [X] T130 Verify SQL syntax highlighting works in log messages in pgtail_py/tail_rich.py
- [X] T131 Verify secondary fields (DETAIL, HINT, CONTEXT, STATEMENT) are formatted correctly in pgtail_py/tail_rich.py

### Performance Validation

- [ ] T132 Verify startup time <500ms with `time python -m pgtail_py` then `tail 1` then `q`
- [ ] T133 Verify 100+ entries/sec auto-scroll performance with rapid log generation test
- [ ] T134 Verify <50ms key response with vim navigation during active tailing
- [ ] T135 Verify memory usage within 10% of baseline for 10,000 entry buffer

### Final Verification

- [X] T136 Run `make test` to verify all tests pass
- [X] T137 Run `make lint` to verify code style compliance
- [X] T138 Update CLAUDE.md if any new modules or patterns were added beyond plan.md
- [X] T139 Test full workflow: start pgtail, list instances, tail, apply filters, select text, copy, quit

### Gap Coverage (Analysis Remediation)

- [X] T140 [US1] Implement on_mouse_up handler to auto-copy selection on mouse release (FR-002) in pgtail_py/tail_log.py
- [X] T141 [US5] Implement selection stability: save selection state before write_line(), restore after, in pgtail_py/tail_log.py
- [X] T142 [US5] Clear selection when buffer content changes due to filter update in pgtail_py/tail_textual.py _handle_command()
- [X] T143 [US3] Add guard in action_visual_mode() to no-op if line_count == 0 (empty buffer) in pgtail_py/tail_log.py
- [X] T144 [US3] Add guard in action_visual_line_mode() to no-op if line_count == 0 (empty buffer) in pgtail_py/tail_log.py
- [X] T145 Add format_as_rich_text() method to FormattedLogEntry in pgtail_py/tail_buffer.py returning Rich Text object
- [X] T146 Test pyperclip fallback for selections >100KB (OSC 52 terminal limit bypass) in tests/test_tail_log.py
- [X] T147 Verify all new modules have complete module and class docstrings per constitution §Quality Standards
- [X] T148 Verify all public functions in tail_textual.py, tail_log.py, tail_rich.py have type annotations
- [X] T149 [US7] Add automated test for `/` key focuses input from log area in tests/test_tail_textual.py
- [ ] T150 [US4] Add automated test for Ctrl+A then Ctrl+C copies all content in tests/test_tail_log.py

### TailInput Module (plan.md Coverage)

- [X] T151 [P] [US7] Create empty module file pgtail_py/tail_input.py with module docstring
- [X] T152 [US7] Create TailInput class extending Input with id="input" and placeholder="tail> " in pgtail_py/tail_input.py
- [X] T153 [US7] Import and use TailInput in TailApp.compose() replacing bare Input in pgtail_py/tail_textual.py
- [X] T154 [US7] Add test for TailInput widget instantiation and placeholder in tests/test_tail_input.py

### Display Module Rich Text (plan.md Coverage)

- [X] T155 Add format_entry_as_rich() function returning Rich Text object in pgtail_py/display.py
- [X] T156 Add test for format_entry_as_rich() output in tests/test_tail_rich.py

### Performance Benchmarks (Success Criteria Coverage)

- [X] T157 Create tests/test_performance.py module with pytest-benchmark setup
- [X] T158 Create automated performance test: mouse-drag-to-clipboard latency <2s (SC-001) in tests/test_performance.py
- [X] T159 Create automated benchmark: vim key response latency <50ms (SC-002) in tests/test_performance.py
- [ ] T160 Create automated stress test: 100+ entries/sec auto-scroll (SC-003) in tests/test_performance.py
- [X] T161 Create memory baseline measurement for 10,000 entry buffer (SC-008) in tests/test_performance.py
- [X] T162 Create automated startup time benchmark <500ms (SC-009) in tests/test_performance.py
- [X] T163 Create focus switch latency benchmark <50ms (SC-010) in tests/test_performance.py

### Edge Case Automated Tests

- [ ] T164 Add automated test for double-click word selection in tests/test_tail_log.py
- [ ] T165 Add automated test for triple-click line selection in tests/test_tail_log.py
- [ ] T166 Add automated test for scrollbar grab pauses auto-scroll in tests/test_tail_textual.py
- [X] T167 Add automated test for visual mode navigation at buffer top boundary in tests/test_tail_visual.py
- [X] T168 Add automated test for visual mode navigation at buffer bottom boundary in tests/test_tail_visual.py

### Help System (Keybinding Discoverability)

- [X] T169 Add Binding for question_mark -> action_show_help in TailApp BINDINGS in pgtail_py/tail_textual.py
- [X] T170 Create TailHelp widget class extending Static with help content in pgtail_py/tail_help.py
- [X] T171 Define KEYBINDINGS constant dict mapping keys to descriptions in pgtail_py/tail_help.py
- [X] T172 Implement TailHelp.compose() rendering keybindings in two-column layout in pgtail_py/tail_help.py
- [X] T173 Add CSS for TailHelp overlay (centered modal, border, background) in pgtail_py/tail_textual.py
- [X] T174 Implement action_show_help() pushing TailHelp as modal screen in pgtail_py/tail_textual.py
- [X] T175 Add Binding for escape/q/question_mark to dismiss help overlay in TailHelp in pgtail_py/tail_help.py
- [X] T176 Add 'keys' subcommand handler to help command in pgtail_py/cli_tail.py
- [X] T177 Implement format_keybindings_text() returning plain text keybinding list in pgtail_py/tail_help.py
- [X] T178 Wire 'help keys' command to display keybindings in log area in pgtail_py/cli_tail.py
- [x] T179 Test ? key shows help overlay and escape dismisses it manually
- [x] T180 Test 'help keys' command outputs keybinding list manually
- [X] T181 Add automated test for ? key triggers help overlay in tests/test_tail_textual.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (Mouse Selection): Can start after Phase 2
  - US2 (Vim Navigation): Can start after Phase 2, independent of US1
  - US3 (Visual Mode): Depends on US2 (uses navigation actions)
  - US4 (Standard Shortcuts): Depends on US1 (uses copy action)
  - US5 (Auto-Scroll): Can start after Phase 2, independent
  - US6 (Clipboard Fallback): Depends on US1 (extends copy mechanism)
  - US7 (Focus Management): Can start after Phase 2, independent
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies Graph

```
Phase 2 (Foundation)
      │
      ├──> US1 (Mouse Selection)
      │         │
      │         ├──> US4 (Standard Shortcuts)
      │         └──> US6 (Clipboard Fallback)
      │
      ├──> US2 (Vim Navigation)
      │         │
      │         └──> US3 (Visual Mode)
      │
      ├──> US5 (Auto-Scroll)
      │
      └──> US7 (Focus Management)
              │
              v
        Phase 10 (Polish)
```

### Parallel Opportunities

**After Phase 2 completion, these can run in parallel:**
- US1, US2, US5, US7 (all independent, different files/concerns)

**Sequential dependencies:**
- US3 must wait for US2 (uses navigation actions)
- US4 must wait for US1 (uses copy action)
- US6 must wait for US1 (extends copy mechanism)

---

## Parallel Example: Foundation Phase

```bash
# These tasks can run in parallel (different files):
Task: "T003 [P] Create empty module file pgtail_py/tail_textual.py"
Task: "T004 [P] Create empty module file pgtail_py/tail_log.py"
Task: "T005 [P] Create empty module file pgtail_py/tail_rich.py"
```

## Parallel Example: After Foundation

```bash
# These user stories can be worked on in parallel by different developers:
Developer A: User Story 1 (Mouse Selection) - tasks T030-T039
Developer B: User Story 2 (Vim Navigation) - tasks T040-T059
Developer C: User Story 5 (Auto-Scroll) - tasks T087-T097
Developer D: User Story 7 (Focus Management) - tasks T105-T112
```

---

## Implementation Strategy

### MVP First (User Story 1 + Foundation Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T029) - CRITICAL
3. Complete Phase 3: User Story 1 - Mouse Selection (T030-T039)
4. **STOP and VALIDATE**: Test mouse selection independently
5. Deploy/demo if ready - users can now copy log text!

### Incremental Delivery

1. Foundation ready → TailApp launches, displays logs, accepts commands
2. Add US1 (Mouse Selection) → Users can select and copy with mouse
3. Add US2 (Vim Navigation) → Power users get vim keybindings
4. Add US5 (Auto-Scroll) → Proper FOLLOW/SCROLL mode in status bar
5. Add US7 (Focus Management) → Tab/slash navigation works
6. Add US3 (Visual Mode) → Keyboard-only selection for vim users
7. Add US4 (Standard Shortcuts) → Ctrl+A/Ctrl+C work
8. Add US6 (Clipboard Fallback) → Terminal.app users covered
9. Polish → Edge cases, performance, documentation

### Full Implementation (All Stories)

Complete all phases in order. Each checkpoint provides a working increment.

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| Phase 1: Setup | T001-T006 (6 tasks) | Dependencies and empty modules |
| Phase 2: Foundation | T007-T029 (23 tasks) | Core TailApp and TailLog infrastructure |
| Phase 3: US1 Mouse Selection | T030-T039 (10 tasks) | P1 - Core clipboard functionality |
| Phase 4: US2 Vim Navigation | T040-T059 (20 tasks) | P2 - Vim keybindings |
| Phase 5: US3 Visual Mode | T060-T082 (23 tasks) | P3 - Keyboard selection |
| Phase 6: US4 Standard Shortcuts | T083-T086 (4 tasks) | P2 - Ctrl+A/Ctrl+C |
| Phase 7: US5 Auto-Scroll | T087-T097 (11 tasks) | P2 - FOLLOW/SCROLL mode |
| Phase 8: US6 Clipboard Fallback | T098-T104 (7 tasks) | P3 - Terminal.app support |
| Phase 9: US7 Focus Management | T105-T112 (8 tasks) | P2 - Tab/slash navigation |
| Phase 10: Polish | T113-T181 (69 tasks) | Edge cases, verification, gap coverage, performance benchmarks, help system |

**Total**: 181 tasks
**User Story Task Counts**: US1=11, US2=20, US3=27, US4=6, US5=13, US6=7, US7=13
**MVP Scope**: Phases 1-3 (39 tasks) delivers mouse selection and copy
**Analysis Remediation**: +18 tasks added for plan.md coverage, performance benchmarks, and edge case automation
**Help System**: +13 tasks added for ? overlay and help keys command (T169-T181)
