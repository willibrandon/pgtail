# Quickstart: pgtail

**Date**: 2025-12-14
**Branch**: `001-pgtail-cli`

## Prerequisites

- Go 1.21 or later installed
- At least one PostgreSQL instance (running or stopped)

## Build from Source

```bash
# Clone the repository
git clone https://github.com/your-org/pgtail.git
cd pgtail

# Build
go build -o pgtail ./cmd/pgtail

# Or install to GOBIN
go install ./cmd/pgtail
```

## Basic Usage

### 1. Launch pgtail

```bash
./pgtail
```

You'll see the interactive prompt:
```
pgtail>
```

### 2. List PostgreSQL Instances

```
pgtail> list

  #  VERSION  PORT   STATUS   SOURCE  DATA DIRECTORY
  0  16.1     5432   running  pgrx    ~/.pgrx/data-16
  1  15.4     5433   stopped  pgrx    ~/.pgrx/data-15
```

### 3. Tail Logs

Tail by index:
```
pgtail> tail 0
[Following: ~/.pgrx/data-16/log/postgresql-2024-01-15.log]
[Press Ctrl+C to stop]

2024-01-15 10:23:45.123 PST [12345] LOG:  statement: SELECT 1
```

Or by path fragment:
```
pgtail> tail pgrx
```

### 4. Filter by Log Level

Show only errors and warnings:
```
pgtail> levels ERROR WARNING
[Filter set: ERROR, WARNING]
```

Clear filter:
```
pgtail> levels
[Filter cleared - showing all levels]
```

### 5. Exit

```
pgtail> quit
```

Or press Ctrl+D.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Autocomplete commands and arguments |
| Up/Down | Navigate command history |
| Ctrl+C | Stop current tail / Clear input |
| Ctrl+D | Exit pgtail |
| Ctrl+L | Clear screen |

## Common Workflows

### pgrx Extension Development

pgtail auto-detects pgrx instances. Typical workflow:

```bash
# Terminal 1: Build and test your extension
cargo pgrx run pg16

# Terminal 2: Monitor logs
pgtail
pgtail> list
pgtail> tail 0
```

### Debugging Errors

Filter to see only errors:
```
pgtail> levels ERROR FATAL PANIC
pgtail> tail 0
```

### Monitor Multiple Instances

Use `list` to see all instances, then switch between them:
```
pgtail> list
pgtail> tail 0
# Ctrl+C to stop
pgtail> tail 1
```

## Verification Steps

After building, verify the tool works:

1. **Launch**: `./pgtail` should show prompt
2. **Help**: `help` should display command list
3. **List**: `list` should detect PostgreSQL instances
4. **Tail**: `tail 0` should stream logs (if instances exist)
5. **Filter**: `levels ERROR` should set filter
6. **Exit**: `quit` should exit cleanly

## Troubleshooting

### "No instances found"

- Check PostgreSQL is installed
- Try running `refresh` after starting a PostgreSQL instance
- Verify PGDATA environment variable if using non-standard location

### "Permission denied"

- Log files may require elevated privileges
- On Linux: `sudo ./pgtail`
- On macOS: Check if logs are in restricted directories

### Colors not showing

- Verify terminal supports ANSI colors
- Check `NO_COLOR` environment variable is not set
- Try a different terminal emulator

## What's Next

- See the full [CLI Interface Contract](./contracts/cli-interface.md) for all commands
- Review the [Data Model](./data-model.md) for technical details
- Check the [Research](./research.md) for implementation patterns
