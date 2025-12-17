# Format Detector Contract

**Module**: `pgtail_py/format_detector.py`

## LogFormat Enum

```python
from enum import Enum

class LogFormat(Enum):
    """Supported PostgreSQL log formats."""
    TEXT = "text"   # Default stderr format
    CSV = "csv"     # csvlog format (26 fields)
    JSON = "json"   # jsonlog format (PG15+)
```

---

## Detection Functions

```python
def detect_format(line: str) -> LogFormat:
    """Detect log format from a single line.

    Detection strategy:
    1. If line starts with '{' and is valid JSON → JSON
    2. If line parses as CSV with 22-26 fields → CSV
    3. Otherwise → TEXT

    Args:
        line: First non-empty line from log file

    Returns:
        Detected LogFormat
    """
    ...


def detect_format_from_file(path: Path, max_bytes: int = 4096) -> LogFormat:
    """Detect log format by reading the beginning of a file.

    Reads up to max_bytes and finds the first complete line.
    Empty files default to TEXT format.

    Args:
        path: Path to log file
        max_bytes: Maximum bytes to read for detection

    Returns:
        Detected LogFormat

    Raises:
        OSError: If file cannot be read
    """
    ...


def is_valid_csv_log(line: str) -> bool:
    """Check if a line appears to be valid PostgreSQL CSV log format.

    Validates:
    - Can be parsed as CSV
    - Has 22-26 fields (older versions have fewer fields)
    - First field looks like a timestamp
    - Field 11 (error_severity) is a valid level name

    Args:
        line: Line to check

    Returns:
        True if line appears to be valid CSV log format
    """
    ...


def is_valid_json_log(line: str) -> bool:
    """Check if a line appears to be valid PostgreSQL JSON log format.

    Validates:
    - Is valid JSON
    - Contains expected keys (timestamp, error_severity, message)
    - timestamp field is ISO 8601 format

    Args:
        line: Line to check

    Returns:
        True if line appears to be valid JSON log format
    """
    ...
```

---

## Integration with LogTailer

The `LogTailer` class will be extended to:

1. Detect format on first line read
2. Store detected format
3. Pass format to parser for each subsequent line

```python
class LogTailer:
    def __init__(self, ...):
        ...
        self._detected_format: LogFormat | None = None

    def _detect_format_if_needed(self, line: str) -> None:
        """Detect format from first non-empty line."""
        if self._detected_format is None:
            self._detected_format = detect_format(line)
            # Optionally notify user of detected format
            ...

    @property
    def format(self) -> LogFormat:
        """Get detected format. Returns TEXT if not yet detected."""
        return self._detected_format or LogFormat.TEXT
```
