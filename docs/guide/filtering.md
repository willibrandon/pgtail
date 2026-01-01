# Filtering

pgtail provides multiple filter types that can be combined for precise log analysis.

## Level Filtering

Filter logs by severity level.

### Basic Level Filter

```
level error      # Exact match - ERROR only
level warning    # WARNING only
level log        # LOG only
```

### Severity Ranges

```
level error+     # ERROR and more severe (FATAL, PANIC)
level warning+   # WARNING, ERROR, FATAL, PANIC
level warning-   # WARNING and less severe (NOTICE, LOG, INFO, DEBUG)
```

### Level Abbreviations

| Abbrev | Level |
|--------|-------|
| `e` | ERROR |
| `w` | WARNING |
| `f` | FATAL |
| `p` | PANIC |
| `n` | NOTICE |
| `l` | LOG |
| `i` | INFO |
| `d` | DEBUG |

Examples:

```
level e+    # ERROR and above
level w     # WARNING only
```

## Regex Filtering

Filter by pattern matching on log messages.

### Basic Pattern

```
filter /deadlock/        # Case-sensitive
filter /deadlock/i       # Case-insensitive
```

### Multiple Patterns

Patterns are combined with AND logic:

```
filter /SELECT/
filter /users/           # Must match both SELECT and users
```

### Remove Filter

```
unfilter /deadlock/      # Remove specific pattern
clear                    # Clear all filters
```

## Field Filtering

Filter by structured fields (CSV/JSON log formats only).

### Available Fields

| Field | Description |
|-------|-------------|
| `app` / `application` | Application name |
| `db` / `database` | Database name |
| `user` | Username |
| `pid` | Process ID |
| `host` / `ip` | Connection source |

### Examples

```
filter app=myapp         # Application name
filter db=production     # Database name
filter user=postgres     # Username
```

!!! warning "Format Requirement"
    Field filtering requires CSV or JSON log format. With TEXT format,
    pgtail will warn that field filtering is not effective.

## Time Filtering

See [Time Filters](time-filters.md) for detailed time filtering options.

```
since 5m                 # Last 5 minutes
until 14:00              # Before 2 PM today
between 14:00 16:00      # Between 2-4 PM
```

## Filter Order

Filters are applied in order of cost (cheapest first):

1. **Time filter** - O(1) datetime comparison
2. **Level filter** - O(1) set membership
3. **Field filter** - O(1) string equality
4. **Regex filter** - O(n) pattern matching

## Combining Filters

All filters combine with AND logic:

```
level error+
filter /timeout/
since 1h
```

This shows only ERROR+ entries containing "timeout" from the last hour.

## Filter Anchor

When you enter tail mode with filters (e.g., `tail 0 --since 1h`), those become the **anchor**.

- `clear` - Resets to anchor state
- `clear force` - Clears everything including anchor
