# Quickstart: Export Logs and Pipe to External Commands

**Feature**: 006-export-pipe

## Overview

This feature adds `export` and `pipe` commands to pgtail for saving filtered log output to files or streaming to external tools.

## Quick Examples

### Export Filtered Logs

```bash
# Start pgtail and set up filters
pgtail> levels ERROR WARNING
Filter set: ERROR WARNING

pgtail> export errors.log
Exported 47 entries to errors.log
```

### Export as JSON for Analysis

```bash
pgtail> export --format json logs.json
Exported 1,234 entries to logs.json

# View with jq
$ jq '.message' logs.json | head -5
"connection received: host=localhost"
"statement: SELECT * FROM users"
...
```

### Pipe to External Tools

```bash
# Count matching lines
pgtail> pipe wc -l
     47

# Filter with grep
pgtail> pipe grep "users table"
2024-01-15 10:23:45 LOG: statement: SELECT * FROM users table...

# JSON to jq
pgtail> pipe --format json jq '.message' | grep SELECT
```

### Continuous Export During Testing

```bash
# Start capturing logs before running tests
pgtail> export --follow test-session.log
Exporting to test-session.log (Ctrl+C to stop)

# ... run your tests in another terminal ...

^C
Stopped. Exported 2,341 entries.
```

## Key Features

| Feature | Command | Description |
|---------|---------|-------------|
| File export | `export file.log` | Save filtered entries to file |
| JSON format | `export --format json` | JSONL output for programmatic use |
| CSV format | `export --format csv` | Spreadsheet-compatible output |
| Continuous | `export --follow` | Real-time export (like tee) |
| Append mode | `export --append` | Add to existing file |
| Time filter | `export --since 1h` | Only recent entries |
| Pipe to tools | `pipe grep pattern` | Stream to external commands |

## Output Formats

### Text (default)
```
2024-01-15 10:23:45.123 UTC [12345] ERROR: connection refused
```

### JSON (JSONL)
```json
{"timestamp":"2024-01-15T10:23:45.123000","level":"ERROR","pid":12345,"message":"connection refused"}
```

### CSV
```csv
timestamp,level,pid,message
2024-01-15T10:23:45.123000,ERROR,12345,connection refused
```

## Common Workflows

### Bug Report Extraction
```bash
pgtail> levels ERROR FATAL
pgtail> filter /deadlock/
pgtail> export --since 2h bug-report.log
Exported 3 entries to bug-report.log
```

### Performance Analysis
```bash
pgtail> export --format json slow-queries.json
$ jq -r 'select(.message | contains("duration")) | .message' slow-queries.json
```

### Log Rotation Test
```bash
# Continuous export handles log rotation automatically
pgtail> export --follow rotation-test.log
# Rotate logs in another terminal: pg_ctl rotate
# Export continues capturing from new log file
```

## Error Handling

The commands handle common errors gracefully:

```bash
# Permission denied
pgtail> export /etc/system.log
Error: Permission denied: /etc/system.log
Try a different location or check permissions.

# Command not found
pgtail> pipe jqq '.message'
Error: Command not found: jqq
Did you mean: jq?

# No entries to export
pgtail> export empty.log
Exported 0 entries to empty.log
```

## Tips

1. **Set filters first**: Both `export` and `pipe` respect your current level and regex filters
2. **Use JSON for scripting**: JSONL format works great with `jq`, Python, and other tools
3. **Append for daily logs**: Use `--append` to build up a log file over multiple sessions
4. **Time filters are relative**: `1h` means "last hour", `2d` means "last 2 days"
