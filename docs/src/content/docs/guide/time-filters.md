---
title: Time filters
description: Show entries from, until, or between times, written as relative durations, times of day, or ISO 8601.
---

Filter log entries by time.

## Time formats

### Relative time

A duration back from now:

| Example | Meaning |
|---------|---------|
| `30s` | 30 seconds ago |
| `5m` | 5 minutes ago |
| `2h` | 2 hours ago |
| `1d` | 1 day ago |

### Time of day

A time today, in local time:

| Example | Meaning |
|---------|---------|
| `14:30` | 2:30 PM today |
| `14:30:45` | 2:30:45 PM today |

### ISO 8601

A date, or a date and time:

| Example | Meaning |
|---------|---------|
| `2024-01-15` | Midnight at the start of January 15, 2024, local time |
| `2024-01-15T14:30` | January 15, 2024 at 2:30 PM, local time |
| `2024-01-15T14:30:00Z` | The same time in UTC |
| `2024-01-15T14:30:00+05:00` | With an offset |

## Commands

### since

Show entries from a time onward:

```
since 5m           # The last 5 minutes
since 14:30        # From 2:30 PM today
since 2024-01-15   # From January 15
```

### until

Show entries up to a time:

```
until 15:00        # Up to 3 PM today
until 1h           # Up to one hour ago
```

With an upper bound, entries written after it never match, so live tailing shows nothing new; the REPL notes this.

### between

Show entries within a range:

```
between 14:00 16:00              # 2 to 4 PM today
between 2024-01-15 2024-01-16    # The whole of January 15
between 1h 30m                   # From an hour ago to 30 minutes ago
```

The start must come before the end.

`since` and `until` each replace the whole time filter; use `between` for both bounds. A time in the future is
accepted with a warning, since nothing matches it yet.

## Starting tail mode with a time filter

```
pgtail> tail 0 --since 1h
```

```sh
pgtail tail --file ./postgresql.log --since 1h
```

The log first shows the entries already written since that time, then follows new ones. The time filter becomes
part of the [filter anchor](/guide/filtering/#filter-anchor): `clear` returns to it.

## Clearing time filters

```
since clear        # Remove the time filter
until clear        # The same
clear              # In tail mode: back to the filters tail mode started with
clear force        # In tail mode: remove every filter
```

## Time zones

pgtail compares times as UTC:

- Timestamps with a zone abbreviation PostgreSQL writes (`UTC`, `GMT`, `EST`, `PDT`, `CET`, `JST`, and others) or an
  offset (`+00`, `-05:00`) are converted to UTC, in every log format. In csvlog and jsonlog an unknown abbreviation is
  read as UTC; in TEXT logs it is read as the local time it was written in.
- Timestamps without a zone, and the times you type without an offset, are local time.

Entries show their time as it was written in the log, in every format, and JSON and CSV export keep the offset it was
written with (for example `2024-01-15T10:30:45.123000-07:00`).
