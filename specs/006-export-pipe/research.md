# Research: Export Logs and Pipe to External Commands

**Date**: 2025-12-15
**Feature**: 006-export-pipe

## Research Topics

### 1. Python CSV Module Best Practices

**Decision**: Use Python stdlib `csv` module with `csv.writer` and `csv.DictWriter`

**Rationale**:
- Built-in module, no additional dependencies
- Handles quoting and escaping automatically (newlines, commas, quotes)
- `csv.QUOTE_MINIMAL` provides correct escaping while keeping output readable
- Cross-platform compatible

**Alternatives Considered**:
- `pandas.to_csv()`: Overkill for simple export; adds large dependency
- Manual string formatting: Error-prone for edge cases (embedded quotes, newlines)

**Implementation Notes**:
```python
import csv
from io import StringIO

def format_csv_row(entry: LogEntry) -> str:
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        entry.timestamp.isoformat() if entry.timestamp else "",
        entry.level.name,
        entry.pid or "",
        entry.message
    ])
    return output.getvalue()
```

### 2. JSON Lines (JSONL) Format Best Practices

**Decision**: Use Python stdlib `json` module with one JSON object per line

**Rationale**:
- JSONL is the standard for streaming JSON data
- Each line is a valid JSON object - enables streaming processing
- Compatible with `jq`, Python `json.loads()`, and other tools
- `json.dumps()` handles escaping automatically

**Alternatives Considered**:
- JSON array format: Requires buffering entire dataset; not streamable
- `orjson` library: Faster but adds dependency; not needed for this scale

**Implementation Notes**:
```python
import json
from datetime import datetime

def format_json_entry(entry: LogEntry) -> str:
    return json.dumps({
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "level": entry.level.name,
        "pid": entry.pid,
        "message": entry.message
    }, ensure_ascii=False)
```

### 3. Subprocess Piping Best Practices

**Decision**: Use `subprocess.Popen` with stdin pipe for streaming

**Rationale**:
- Allows streaming entries to subprocess without buffering all in memory
- Cross-platform compatible (macOS, Linux, Windows)
- Proper error handling via `returncode` and `stderr`
- `communicate()` for small outputs; line-by-line for streaming

**Alternatives Considered**:
- `subprocess.run()` with string input: Buffers entire input in memory
- `os.popen()`: Deprecated, limited error handling
- Shell pipes via `shell=True`: Security concerns, platform inconsistencies

**Implementation Notes**:
```python
import subprocess
import shlex

def pipe_to_command(entries: Iterable[LogEntry], command: str, format: ExportFormat) -> tuple[int, str]:
    # Parse command safely
    if sys.platform == "win32":
        args = command  # Windows shell parsing
        shell = True
    else:
        args = shlex.split(command)
        shell = False

    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell,
        text=True
    )

    try:
        for entry in entries:
            line = format_entry(entry, format)
            proc.stdin.write(line + "\n")
        proc.stdin.close()
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout
    except BrokenPipeError:
        # Command exited early (e.g., head -n 10)
        proc.kill()
        return 0, ""
```

### 4. File Overwrite Confirmation Pattern

**Decision**: Use prompt_toolkit's `prompt()` with yes/no validation

**Rationale**:
- Consistent with existing REPL interaction style
- Uses existing prompt_toolkit dependency
- Clear user feedback

**Alternatives Considered**:
- Silent overwrite: Dangerous, could lose data
- Always error on existing file: Too restrictive

**Implementation Notes**:
```python
from prompt_toolkit import prompt

def confirm_overwrite(path: Path) -> bool:
    if not path.exists():
        return True
    response = prompt(f"File {path} exists. Overwrite? [y/N] ")
    return response.lower() in ("y", "yes")
```

### 5. Streaming Export Pattern (Memory Efficient)

**Decision**: Use generator-based approach for memory efficiency

**Rationale**:
- Never loads all entries into memory
- Compatible with large log files (100K+ entries)
- Works with both file export and pipe commands
- Allows progress reporting during export

**Alternatives Considered**:
- Load all entries then write: Simple but memory-intensive
- Chunk-based writing: More complex, marginal benefit over generators

**Implementation Notes**:
```python
def get_filtered_entries(
    tailer: LogTailer,
    levels: set[LogLevel] | None,
    regex_state: FilterState
) -> Generator[LogEntry, None, None]:
    """Generator that yields filtered entries from buffer."""
    for entry in tailer.get_buffer():
        if should_show(entry.level, levels):
            if regex_state.matches(entry.message):
                yield entry

def export_to_file(
    entries: Iterable[LogEntry],
    path: Path,
    format: ExportFormat,
    append: bool = False
) -> int:
    """Export entries to file, returns count."""
    mode = "a" if append else "w"
    count = 0

    with open(path, mode, encoding="utf-8", newline="") as f:
        if format == ExportFormat.CSV and not append:
            f.write("timestamp,level,pid,message\n")

        for entry in entries:
            f.write(format_entry(entry, format) + "\n")
            count += 1

    return count
```

### 6. Directory Creation Pattern

**Decision**: Use `Path.mkdir(parents=True, exist_ok=True)` for parent directory creation

**Rationale**:
- Follows clarified requirement: auto-create parent directories
- Atomic operation in Python
- Cross-platform compatible
- `exist_ok=True` prevents errors if directory already exists

**Implementation Notes**:
```python
def ensure_parent_dirs(path: Path) -> None:
    """Create parent directories if they don't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
```

### 7. Continuous Export with Log Rotation

**Decision**: Leverage existing `LogTailer` which already handles rotation

**Rationale**:
- `LogTailer` already implements log rotation detection
- Reuse existing battle-tested code
- Consistent behavior with normal tailing

**Implementation Notes**:
The `--follow` export mode will use the same `LogTailer` infrastructure as the `tail` command, with the addition of writing each entry to a file as it arrives.

### 8. Time Filtering (--since option)

**Decision**: Parse relative time strings (e.g., "1h", "30m", "2d") into datetime

**Rationale**:
- Common CLI pattern (similar to `journalctl --since`)
- Human-readable and quick to type
- Absolute timestamps can use ISO 8601 format

**Implementation Notes**:
```python
import re
from datetime import datetime, timedelta

def parse_since(value: str) -> datetime:
    """Parse --since value into datetime."""
    # Try relative time first
    match = re.match(r"^(\d+)([smhd])$", value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        delta = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
        }[unit]
        return datetime.now() - delta

    # Try ISO format
    return datetime.fromisoformat(value)
```

## Summary

All research topics resolved using Python standard library. No new dependencies required. Key patterns:

1. **CSV**: Use stdlib `csv` module with QUOTE_MINIMAL
2. **JSON**: Use stdlib `json` module, one object per line (JSONL)
3. **Subprocess**: Use `Popen` with stdin pipe for streaming
4. **Confirmation**: Use prompt_toolkit's existing prompt
5. **Streaming**: Generator-based approach for memory efficiency
6. **Directories**: Use `Path.mkdir(parents=True, exist_ok=True)`
7. **Rotation**: Reuse existing `LogTailer` rotation handling
8. **Time parsing**: Custom parser for relative times (1h, 30m, 2d)
