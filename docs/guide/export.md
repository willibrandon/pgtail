# Export and Pipe

Export filtered logs to files or pipe to external commands.

## Export to File

### Basic Export

```
pgtail> export /tmp/errors.log
```

Exports the current buffer (filtered entries) to a file.

### Export Formats

```
export --format text /tmp/logs.txt    # Plain text (default)
export --format json /tmp/logs.json   # JSON Lines
export --format csv /tmp/logs.csv     # CSV
```

### Append Mode

```
export --append /tmp/logs.txt
```

Appends to existing file instead of overwriting.

### Time-Scoped Export

```
export --since 1h /tmp/recent.log
```

Export only entries from the last hour.

### Continuous Export

```
export --follow /tmp/live.log
```

Continuously writes new entries (like `tail -f | tee`). Shows entries on screen while writing to file.

Press Ctrl+C to stop.

## Pipe to Commands

### Basic Pipe

```
pgtail> pipe wc -l
```

Pipes filtered entries to an external command.

### With Format

```
pipe --format json jq '.message'
```

### Examples

```
pipe grep ERROR                      # Search within entries
pipe wc -l                           # Count entries
pipe sort | uniq -c                  # Count unique messages
pipe --format json jq -r '.sql_state' | sort | uniq -c
```

## Buffer Behavior

Export and pipe commands work with the **tailer buffer**:

- Buffer holds up to 10,000 entries (configurable)
- Entries are filtered before export
- Both streaming mode and Textual mode populate the buffer

## Requirements

For export/pipe to work:

1. You must have tailed an instance first (`tail <id>`)
2. The buffer must have entries

If you see "No log file loaded", run `tail <id>` first.

## Configuration

### Buffer Size

```toml
[buffer]
tailer_max = 10000
```

### Export After Textual Mode

After exiting Textual tail mode, the buffer is preserved. You can immediately export:

```
pgtail> tail 0
# ... view logs, exit with 'q' ...
pgtail> export /tmp/session.log
```
