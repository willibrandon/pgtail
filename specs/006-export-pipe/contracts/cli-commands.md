# CLI Command Contracts: Export and Pipe

**Date**: 2025-12-15
**Feature**: 006-export-pipe

## Command: export

Export filtered log entries to a file.

### Syntax

```
export [OPTIONS] <filename>
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `filename` | string | Yes | Path to output file (relative or absolute) |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | enum | `text` | Output format: `text`, `json`, `csv` |
| `--follow` | flag | false | Continuous export mode (like `tail -f \| tee`) |
| `--append` | flag | false | Append to existing file instead of overwriting |
| `--since` | string | none | Only export entries after time (e.g., `1h`, `30m`, `2d`, or ISO timestamp) |

### Examples

```
# Basic export (text format)
pgtail> export errors.log

# JSON format
pgtail> export --format json logs.json

# CSV with time filter
pgtail> export --format csv --since 1h recent.csv

# Continuous export
pgtail> export --follow test-run.log

# Append to existing file
pgtail> export --append daily.log
```

### Behavior

1. Applies current filters (level, regex) to entries
2. If file exists and `--append` not set, prompts for overwrite confirmation
3. Creates parent directories if they don't exist
4. Writes entries in specified format
5. Reports count of entries exported
6. In `--follow` mode, continues until Ctrl+C

### Success Output

```
Exported 47 entries to errors.log
```

```
Exporting to test-run.log (Ctrl+C to stop)
...
Stopped. Exported 2,341 entries.
```

### Error Output

```
Error: Permission denied: /etc/logs/output.log
Try a different location or check permissions.
```

```
Error: Disk full after 1,234 entries written to large-export.log
```

---

## Command: pipe

Pipe filtered log entries to an external command.

### Syntax

```
pipe [OPTIONS] <command>
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `command` | string | Yes | Shell command to pipe to (can include arguments) |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | enum | `text` | Output format for piped data: `text`, `json`, `csv` |

### Examples

```
# Basic grep
pgtail> pipe grep "connection"

# Count lines
pgtail> pipe wc -l

# JSON to jq
pgtail> pipe --format json jq '.message'

# Complex pipeline
pgtail> pipe grep ERROR | head -10

# CSV to awk
pgtail> pipe --format csv awk -F, '{print $4}'
```

### Behavior

1. Applies current filters (level, regex) to entries
2. Spawns subprocess with stdin pipe
3. Streams formatted entries to subprocess stdin
4. Displays subprocess stdout
5. Reports subprocess errors (stderr, non-zero exit)

### Success Output

```
pgtail> pipe wc -l
     47
```

```
pgtail> pipe --format json jq '.level' | sort | uniq -c
  10 "DEBUG1"
  25 "LOG"
  12 "WARNING"
```

### Error Output

```
Error: Command not found: jqq
Did you mean: jq?
```

```
Error: Command failed with exit code 1
stderr: grep: invalid option -- 'z'
```

---

## Integration with Existing Commands

### Filter Interaction

Both `export` and `pipe` respect current filter state:

```
pgtail> levels ERROR WARNING      # Set level filter
pgtail> filter /connection/       # Set regex filter
pgtail> export errors.log         # Exports only ERROR/WARNING with "connection"
```

### Autocomplete Support

| Context | Completions |
|---------|-------------|
| `export ` | File path completion |
| `export --` | `--format`, `--follow`, `--append`, `--since` |
| `export --format ` | `text`, `json`, `csv` |
| `pipe ` | (no completion - user enters command) |
| `pipe --` | `--format` |
| `pipe --format ` | `text`, `json`, `csv` |

### Help Text Addition

```
Available commands:
  ...
  export <file>     Export filtered logs to file
                    --format <fmt>  Output format (text, json, csv)
                    --follow        Continuous export (like tee)
                    --append        Append to existing file
                    --since <time>  Only entries after time (1h, 30m, etc.)
  pipe <command>    Pipe filtered logs to external command
                    --format <fmt>  Convert to format before piping
  ...
```
