# Quickstart: Time-Based Filtering

**Feature**: 007-time-filter

## Usage Examples

### Recent History (Relative Time)

```
pgtail> since 5m
Showing logs from last 5 minutes (since 14:25:30)

pgtail> since 2h
Showing logs from last 2 hours (since 12:30:30)

pgtail> since 1d
Showing logs from last 24 hours (since yesterday 14:30:30)
```

### Specific Time Today

```
pgtail> since 14:30
Showing logs since 14:30:00 today

pgtail> since 14:30:45
Showing logs since 14:30:45 today
```

### Specific Date and Time

```
pgtail> since 2024-01-15T14:30
Showing logs since 2024-01-15 14:30:00

pgtail> since 2024-01-15T14:30:00Z
Showing logs since 2024-01-15 14:30:00 UTC
```

### Time Range

```
pgtail> between 14:30 15:00
Showing logs between 14:30:00 and 15:00:00

pgtail> between 2024-01-15T09:00 2024-01-15T10:00
Showing logs between 2024-01-15 09:00 and 2024-01-15 10:00
```

### Upper Bound Only

```
pgtail> until 15:00
Showing logs until 15:00:00

pgtail> until 30m
Showing logs until 30 minutes ago
```

### Clearing Time Filter

```
pgtail> since clear
Time filter cleared
```

### Combined with Other Filters

```
pgtail> levels ERROR WARNING
pgtail> since 1h
# Shows only ERROR and WARNING entries from last hour

pgtail> filter /connection/
pgtail> between 14:00 15:00
# Shows entries matching "connection" within the hour
```

### Starting Tail from a Specific Time

```
pgtail> tail 0 --since 10m
Starting tail from 10 minutes ago
[Shows historical entries first, then continues tailing]
```

## Time Format Reference

| Format | Example | Meaning |
|--------|---------|---------|
| `Nm` | `5m` | Last N minutes |
| `Ns` | `30s` | Last N seconds |
| `Nh` | `2h` | Last N hours |
| `Nd` | `1d` | Last N days |
| `HH:MM` | `14:30` | Today at 14:30:00 |
| `HH:MM:SS` | `14:30:45` | Today at 14:30:45 |
| `YYYY-MM-DDTHH:MM` | `2024-01-15T14:30` | Specific datetime |
| `YYYY-MM-DDTHH:MM:SSZ` | `2024-01-15T14:30:00Z` | Datetime in UTC |

## Behavior Notes

- Times without timezone are interpreted as local time
- Times with `Z` suffix are interpreted as UTC
- When time filter is active, entries without timestamps are skipped
- Future times generate a warning but are allowed (useful for waiting)
- `until` command disables follow mode (shows only historical entries)
