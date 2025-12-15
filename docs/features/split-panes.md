# Feature: Split Panes for Multiple Instances

## Problem

Developers often run multiple PostgreSQL instances:
- Primary and replica
- Multiple pgrx test instances (pg14, pg15, pg16)
- Dev and test databases

Currently, users must run multiple terminal windows to tail different instances. There's no way to see correlated activity across instances.

## Proposed Solution

Add split pane support within the full-screen TUI. Users can create horizontal or vertical splits, each tailing a different instance. Log entries can be color-coded by instance for easy identification.

## User Scenarios

### Scenario 1: Primary/Replica Comparison
DBA is debugging replication lag. They split the screen vertically, tail primary on left and replica on right. They can see the same queries appearing on both with timing differences.

### Scenario 2: Multi-Version pgrx Testing
Extension developer is testing across PostgreSQL versions. They create three horizontal splits for pg14, pg15, pg16 instances. They run tests and watch for version-specific errors.

### Scenario 3: Focused Debugging
Developer starts with all instances visible, spots an issue in instance 2, maximizes that pane to focus, then restores splits when done.

## Commands

- `split h` or `sp` - Horizontal split
- `split v` or `vsp` - Vertical split
- `Ctrl+W h/j/k/l` - Navigate between panes
- `Ctrl+W =` - Equalize pane sizes
- `Ctrl+W _` - Maximize current pane
- `Ctrl+W c` or `close` - Close current pane
- `tail <id>` - In current pane, tail specified instance

## Visual Design

```
┌─────────────────────┬─────────────────────┐
│ [0] pg16 - primary  │ [1] pg16 - replica  │
│ LOG: SELECT ...     │ LOG: SELECT ...     │
│ LOG: INSERT ...     │ LOG: INSERT ...     │
│                     │                     │
├─────────────────────┴─────────────────────┤
│ [2] pg15 - test                           │
│ ERROR: relation "foo" does not exist      │
│                                           │
└───────────────────────────────────────────┘
```

## Success Criteria

1. Support at least 4 simultaneous panes without performance degradation
2. Each pane independently scrollable and filterable
3. Color coding makes instance identification instant
4. Pane navigation feels natural to vim/tmux users
5. Works correctly when terminal is resized

## Out of Scope

- Synchronized scrolling across panes
- Pane layouts saved to config file
- Floating/overlay panes
