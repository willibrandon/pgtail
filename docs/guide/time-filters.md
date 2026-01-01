# Time Filters

Filter log entries by time ranges.

## Format Support

Time filters support multiple formats:

### Relative Time

Duration from now:

| Example | Description |
|---------|-------------|
| `5m` | 5 minutes ago |
| `30s` | 30 seconds ago |
| `2h` | 2 hours ago |
| `1d` | 1 day ago |

### Time Only

Specific time today:

| Example | Description |
|---------|-------------|
| `14:30` | 2:30 PM today |
| `14:30:45` | 2:30:45 PM today |

### ISO 8601

Full datetime:

| Example | Description |
|---------|-------------|
| `2024-01-15T14:30` | January 15, 2024 at 2:30 PM |
| `2024-01-15T14:30:00Z` | With timezone (UTC) |
| `2024-01-15T14:30:00+05:00` | With offset |

## Commands

### Since (Start Time)

Show entries from a specific time onward:

```
since 5m           # Last 5 minutes
since 14:30        # From 2:30 PM today
since 2024-01-15   # From January 15
```

### Until (End Time)

Show entries up to a specific time:

```
until 15:00        # Before 3 PM today
until 1h           # Before 1 hour ago
```

### Between (Time Range)

Show entries within a time range:

```
between 14:00 16:00              # 2-4 PM today
between 2024-01-15 2024-01-16    # Full day
between 1h 30m                   # 1 hour ago to 30 min ago
```

## Starting Tail with Time Filter

```
pgtail> tail 0 --since 1h
```

This creates a time filter **anchor** - `clear` will reset to this state.

## Clearing Time Filters

```
since clear        # Clear start time
until clear        # Clear end time
clear              # Clear all filters (respects anchor)
clear force        # Clear everything including anchor
```

## Timezone Handling

pgtail normalizes all timestamps to UTC internally for accurate comparisons:

- PostgreSQL timestamps with timezone (e.g., `PST`, `UTC`, `+05:00`) are converted to UTC
- Timestamps without timezone are assumed to be local time
- Time filter comparisons use UTC for consistency

Supported timezone formats:

- Named: `UTC`, `GMT`, `PST`, `PDT`, `EST`, `EDT`, `CET`, `JST`, etc.
- ISO 8601 offsets: `+00:00`, `-05:00`, `Z`
