# CLI Commands Contract

**Module**: `pgtail_py/cli.py`, `pgtail_py/commands.py`

## New Commands

### display

Control how log entries are displayed.

```
display                     # Show current display mode
display compact             # One line per entry (default)
display full                # All available fields
display fields <field,...>  # Show only specified fields
```

**Examples**:
```
pgtail> display compact
Display mode: compact

pgtail> display full
Display mode: full

pgtail> display fields timestamp,level,application_name,message
Display mode: custom (4 fields)

pgtail> display fields foo
Unknown field: foo. Valid fields: timestamp, pid, level, message, ...
```

---

### filter (extended)

Add field-based filtering to existing `filter` command.

```
filter app=<value>          # Filter by application name
filter db=<value>           # Filter by database name
filter user=<value>         # Filter by user name
filter pid=<value>          # Filter by process ID
filter backend=<value>      # Filter by backend type
filter clear                # Clear all field filters
filter                      # Show current field filters
```

**Field filter behavior**:
- Multiple field filters use AND logic
- Case-sensitive exact match
- Only available for CSV/JSON format logs
- Text format logs show informative error

**Examples**:
```
pgtail> filter app=myapp
Field filter: app=myapp

pgtail> filter db=production
Field filters: app=myapp, db=production

pgtail> filter clear
Field filters cleared

# On text format log:
pgtail> filter app=myapp
Field filtering requires CSV or JSON log format. Current format: text
```

---

### output

Control output format for piping to other tools.

```
output                      # Show current output format
output json                 # JSON output (one object per line)
output text                 # Human-readable text (default)
```

**Examples**:
```
pgtail> output json
Output format: json

pgtail> output text
Output format: text
```

---

## Command Registration

Add to `pgtail_py/commands.py`:

```python
# Command definitions for autocomplete
COMMANDS: dict[str, list[str]] = {
    # Existing commands...
    "tail": [],
    "level": ["ERROR", "WARNING", "LOG", "INFO", "DEBUG", "ALL"],
    "since": [],
    "until": [],
    "between": [],
    "export": ["json", "csv", "text"],

    # New commands
    "display": ["compact", "full", "fields"],
    "output": ["json", "text"],
    # filter already exists, extend with field syntax
}

# Field names for autocomplete
FILTER_FIELDS: list[str] = ["app=", "db=", "user=", "pid=", "backend=", "clear"]
DISPLAY_FIELDS: list[str] = [
    "timestamp", "pid", "level", "message", "sql_state",
    "user", "database", "application", "query", "detail",
    "hint", "context", "location", "backend_type", "session_id",
]
```

---

## Command Handler Signatures

```python
# In cli.py

def handle_display(state: AppState, args: list[str]) -> None:
    """Handle 'display' command.

    Args:
        state: Application state
        args: Command arguments

    Subcommands:
        (none): Show current display mode
        compact: Set compact mode
        full: Set full mode
        fields <list>: Set custom mode with specified fields
    """
    ...


def handle_filter_field(state: AppState, args: list[str]) -> None:
    """Handle field filter arguments in 'filter' command.

    Called when filter args contain '=' character.

    Args:
        state: Application state
        args: Field filter arguments (e.g., ["app=myapp", "db=prod"])
    """
    ...


def handle_output(state: AppState, args: list[str]) -> None:
    """Handle 'output' command.

    Args:
        state: Application state
        args: Command arguments

    Subcommands:
        (none): Show current output format
        json: Set JSON output
        text: Set text output
    """
    ...
```

---

## Status Line Updates

The status line should reflect active filters and display mode:

```python
def format_status_line(state: AppState) -> str:
    """Format the status line shown in prompt.

    Example outputs:
        "Tailing: /var/log/postgresql.csv [csvlog] | Level: ERROR | Display: full"
        "Tailing: /var/log/postgresql.json [jsonlog] | Filter: app=myapp"
        "Tailing: /var/log/postgresql.log [text] | Output: json"
    """
    parts = []

    # Instance info
    if state.active_instance:
        parts.append(f"Tailing: {state.active_instance.log_path}")
        if state.detected_format:
            parts.append(f"[{state.detected_format.value}]")

    # Level filter
    if state.active_levels:
        levels = ", ".join(l.name for l in state.active_levels)
        parts.append(f"Level: {levels}")

    # Field filters
    if state.field_filter and state.field_filter.is_active():
        parts.append(state.field_filter.format_status())

    # Display mode (only if not default)
    if state.display_state.mode != DisplayMode.COMPACT:
        parts.append(f"Display: {state.display_state.mode.value}")

    # Output format (only if JSON)
    if state.display_state.output_format == OutputFormat.JSON:
        parts.append("Output: json")

    return " | ".join(parts)
```
