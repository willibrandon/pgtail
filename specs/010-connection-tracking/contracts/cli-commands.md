# CLI Commands Contract: Connection Tracking

**Date**: 2025-12-17
**Feature**: 010-connection-tracking

## Command: `connections`

Display connection statistics and real-time connection events.

### Synopsis

```
connections [--history] [--watch] [--db=NAME] [--user=NAME] [--app=NAME] [clear]
```

### Subcommands and Flags

| Flag/Subcommand | Description | Can Combine With |
|-----------------|-------------|------------------|
| (none) | Show current connection summary | --db, --user, --app |
| --history | Show connection trend over time | --db, --user, --app |
| --watch | Live stream of connection events | --db, --user, --app |
| --db=NAME | Filter by database name | All except clear |
| --user=NAME | Filter by user name | All except clear |
| --app=NAME | Filter by application name | All except clear |
| clear | Reset all connection statistics | None |

### Invalid Combinations

| Combination | Error Message |
|-------------|---------------|
| --history + --watch | "Cannot use --history and --watch together." |
| clear + any flag | "clear ignores other options" (warning, then clears) |

### Output Formats

#### Default Summary View

```
Active connections: 47

By database:
  production    32
  analytics      8
  test           7

By user:
  app_user      28
  readonly      12
  admin          7

By application:
  rails         20
  sidekiq        8
  psql           5
  unknown       14

Session totals: 234 connects, 187 disconnects
```

#### History View (`--history`)

```
Connection history (last 60 min)

Total: 234 connects, 187 disconnects (+47 net)

Timeline (15-min buckets):
10:00  40 active
10:15  45 active (+5)
10:30  52 active (+7)
10:45  61 active (+9)  ← leak detected

Trend: ████▅▆▇█  +47 net
```

#### Watch View (`--watch`)

```
Watching connections (Ctrl+C to exit)
[+] 10:23:45 rails connected from 10.0.1.5 (user: app_user, db: production)
[-] 10:23:47 psql disconnected (duration: 2.3s, user: admin, db: test)
[+] 10:23:48 sidekiq connected from 10.0.1.6 (user: app_user, db: production)
[!] 10:23:49 Connection failed: too many connections (user: app_user)
```

#### Filtered View (`--db=production`)

```
Active connections to 'production': 32

By user:
  app_user      25
  readonly       5
  admin          2

By application:
  rails         20
  sidekiq        8
  psql           4
```

#### Empty State

```
No connection data available.
Start tailing a log with `tail` to begin tracking connections.
```

#### Clear Confirmation

```
Connection statistics cleared.
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid argument/combination |

### Watch Mode Behavior

1. **Start**: Print header with log file name
2. **Event Display**: Print each connection event with timestamp and details
3. **Color Coding**:
   - `[+]` (green): New connection
   - `[-]` (yellow): Disconnection
   - `[!]` (red): Connection failure
4. **Exit**: Ctrl+C prints "Exited watch mode." and returns to prompt

### Filter Behavior

- Filters apply to display only (tracking continues for all events)
- Multiple filters use AND logic
- Partial matches not supported (exact match only)
- Case-sensitive matching

## Integration with Existing Commands

### Command Registration

Add to `COMMANDS` dict in `commands.py`:
```python
"connections": ("connections", "Show connection statistics and tracking"),
```

### Autocomplete

Add to `PgtailCompleter.get_completions()`:
- `connections` as top-level command
- `--history`, `--watch`, `--db=`, `--user=`, `--app=`, `clear` as subcompletions
