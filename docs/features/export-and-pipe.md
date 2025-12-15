# Feature: Export Logs and Pipe to External Commands

## Problem

Developers often need to:
- Save filtered log output for later analysis or sharing
- Pipe logs to other tools (grep, jq, custom scripts)
- Export in different formats (JSON, CSV) for processing
- Create reproducible log extracts for bug reports

Currently, pgtail is interactive-only with no export capability.

## Proposed Solution

Add commands to export log output to files or pipe to external commands. Support multiple output formats and the ability to apply current filters to exports.

## User Scenarios

### Scenario 1: Save Filtered Logs
Developer found relevant errors and wants to save them:
```
pgtail> levels ERROR FATAL
pgtail> since 1h
pgtail> export errors-today.log
Exported 47 entries to errors-today.log
```

### Scenario 2: JSON Export for Analysis
Data engineer wants to analyze logs programmatically:
```
pgtail> export --format json logs.json
Exported 1,234 entries to logs.json

# Output format:
{"timestamp":"2024-01-15T10:23:45.123","level":"ERROR","message":"..."}
```

### Scenario 3: Pipe to External Tool
Developer wants to use familiar tools:
```
pgtail> pipe grep "users table"
[Output flows to grep, results shown]

pgtail> pipe jq '.message' --format json
[Logs converted to JSON, piped to jq]
```

### Scenario 4: Continuous Export
Ops engineer wants to capture logs during a test:
```
pgtail> export --follow test-run.log
Exporting to test-run.log (Ctrl+C to stop)
...
Stopped. Exported 2,341 entries.
```

## Commands

```
export <filename>              Export buffer to file
export --format <fmt> <file>   Export in format (text, json, csv)
export --follow <file>         Continuous export (like tee)
export --since <time> <file>   Export time range

pipe <command>                 Pipe output to command
pipe --format <fmt> <command>  Pipe with format conversion
```

## Export Formats

| Format | Description |
|--------|-------------|
| text | Raw log lines (default) |
| json | One JSON object per line (JSONL) |
| csv | CSV with columns: timestamp, level, pid, message |

## Behavior Notes

- `export` without `--follow` exports current buffer/filter results
- Filters (level, regex, time) apply to export
- `pipe` runs command and streams matching entries
- Large exports show progress indicator
- Overwrites existing files (with warning) or use `--append`

## Success Criteria

1. Export respects current filters (level, regex, time)
2. All three formats produce valid output
3. Large exports don't consume excessive memory (streaming)
4. Pipe to common tools works (grep, jq, wc, head)
5. Continuous export handles log rotation
6. Progress feedback for large exports
7. Errors (permission, disk full) handled gracefully

## Out of Scope

- Cloud storage upload (S3, etc.)
- Compression
- Scheduled/automatic exports
- Email export
