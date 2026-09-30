---
title: Export and pipe
description: Write the filtered entries to a file as text, JSON Lines, or CSV, or pipe them to a shell command.
---

Export the filtered entries of your last tail to a file, or pipe them to another command.

## Export to a file

### Basic export

```pgtail
pgtail> export /tmp/errors.log
Exported 42 entries to /tmp/errors.log
```

Exports the entries of the last tail that match the current filters. If the file exists, pgtail asks before
replacing it: `File /tmp/errors.log exists. Overwrite? [y/N]`.

### Formats

```pgtail
export --format text /tmp/logs.txt    # The log lines as PostgreSQL wrote them (default)
export --format json /tmp/logs.json   # JSON Lines
export --format csv /tmp/logs.csv     # CSV with a header row
```

JSON Lines writes one object per entry, and CSV one row per entry with the same fields:

```json
{"timestamp": "2024-01-15T10:30:45.123000+00:00", "level": "ERROR", "pid": 12345, "message": "relation \"users\" does not exist"}
```

```
timestamp,level,pid,message
```

### Keeping colors

```pgtail
export --highlighted /tmp/colored.log
```

Writes each text entry as pgtail displays it, with its colors as ANSI escape sequences, for viewing with `less -R`
or `cat`.

### Append mode

```pgtail
export --append /tmp/logs.txt
```

Adds to the end of an existing file instead of replacing it.

### Time-scoped export

```pgtail
export --since 1h /tmp/recent.log
```

Exports only entries from the last hour. `--since` takes any [time format](/guide/time-filters/).

### Continuous export

```pgtail
export --follow /tmp/live.log
```

Keeps writing new entries to the file as they arrive, like `tail -f | tee`, and shows them on screen as well. Press
`Ctrl+C` to stop. `--follow` cannot be combined with `--append` or `--since`.

## Pipe to commands

### Basic pipe

```pgtail
pgtail> pipe wc -l
```

Sends the filtered entries to a command's standard input and prints what it writes. The command runs in your shell
(`sh -c`, or `cmd /c` on Windows), so pipes and quoting work as they would at a prompt.

### With a format

```pgtail
pipe --format json jq -r '.level'
```

### Examples

```pgtail
pipe grep ERROR                                   # Search within entries
pipe wc -l                                        # Count entries
pipe sort | uniq -c                               # Count identical lines
pipe --format json jq -r '.level' | sort | uniq -c   # Count entries by level
```

The command's error output is printed after `stderr:`, and a non-zero exit code is reported.

## Export in tail mode

Tail mode has its own `export`, which writes the entries the log is showing:

```pgtail
tail> export /tmp/logs.txt
tail> export /tmp/logs.json --format json
tail> export /tmp/logs.txt --highlighted
```

## The entry buffer

`export` and `pipe` in the REPL work on the entries of the most recent tail:

- The last 10,000 entries are kept
- Filters apply when you export, so you can change them and export again
- Both full screen tail mode and streaming fill the buffer, and it stays after you leave tail mode

```pgtail
pgtail> tail 0
# ... read the log, leave with 'q' ...
pgtail> export /tmp/session.log
```

If nothing has been tailed yet, `export` and `pipe` say `No log file loaded. Use 'tail <instance>' first.`
