# Feature: Full Screen TUI Mode

## Problem

When tailing logs, developers often want to:
- Scroll back through previous output without stopping the tail
- Search for specific patterns in the log history
- Navigate using familiar vim-style keybindings
- See more context without terminal scroll limitations

Currently, pgtail streams output directly to the terminal with no way to navigate history or search.

## Proposed Solution

Add a full-screen terminal UI mode that captures log output in a scrollable buffer. Users can switch between "follow mode" (auto-scroll to new entries) and "browse mode" (free navigation).

## User Scenarios

### Scenario 1: Scrolling Back
Developer is tailing logs and sees an error flash by. They press `Escape` or `Ctrl+S` to pause following, then use `k` or `Up` to scroll back and find the error. Press `f` or `Ctrl+F` to resume following.

### Scenario 2: Searching Logs
Developer wants to find all occurrences of a specific table name. They press `/` to open search, type the pattern, and press `Enter`. Matches are highlighted and `n`/`N` navigate between them.

### Scenario 3: Mouse Navigation
Developer clicks on a log line to select it, uses scroll wheel to navigate, can select and copy text with mouse.

## Commands & Keybindings

- `fullscreen` or `fs` - Enter full-screen mode
- `Escape` - Toggle follow/browse mode
- `j/k` or `Up/Down` - Scroll line by line
- `Ctrl+D/Ctrl+U` - Page down/up
- `g/G` - Jump to top/bottom
- `/pattern` - Search forward
- `?pattern` - Search backward
- `n/N` - Next/previous match
- `q` - Exit full-screen mode

## Success Criteria

1. User can scroll back through at least 10,000 lines of log history
2. Search finds and highlights matches within 100ms for typical patterns
3. Follow mode keeps up with high-volume log output (1000+ lines/sec)
4. Vim users feel immediately comfortable with navigation
5. Mouse works for scrolling and text selection

## Out of Scope

- Split panes (separate feature)
- Syntax highlighting (separate feature)
- Persistent log storage beyond session
