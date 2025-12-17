"""Log format detection for PostgreSQL log files.

Detects TEXT, CSV (csvlog), and JSON (jsonlog) formats using content-based
heuristics on the first non-empty line of a log file.
"""

from __future__ import annotations

import csv
import json
from enum import Enum
from io import StringIO
from pathlib import Path

# Valid PostgreSQL log severity levels
_VALID_SEVERITY_LEVELS = frozenset(
    {
        "DEBUG5",
        "DEBUG4",
        "DEBUG3",
        "DEBUG2",
        "DEBUG1",
        "DEBUG",
        "INFO",
        "NOTICE",
        "WARNING",
        "ERROR",
        "LOG",
        "FATAL",
        "PANIC",
    }
)


class LogFormat(Enum):
    """Supported PostgreSQL log formats."""

    TEXT = "text"  # Default stderr format
    CSV = "csv"  # csvlog format (26 fields)
    JSON = "json"  # jsonlog format (PG15+)


def is_valid_json_log(line: str) -> bool:
    """Check if a line appears to be valid PostgreSQL JSON log format.

    Validates:
    - Is valid JSON
    - Contains expected keys (timestamp, error_severity, message)
    - error_severity is a valid PostgreSQL log level

    Args:
        line: Line to check

    Returns:
        True if line appears to be valid JSON log format
    """
    line = line.strip()
    if not line.startswith("{"):
        return False

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return False

    # Must be a dict, not a list or primitive
    if not isinstance(data, dict):
        return False

    # Must have essential keys for PostgreSQL jsonlog
    # At minimum, we need error_severity and message
    if "error_severity" not in data or "message" not in data:
        return False

    # Validate error_severity is a known level
    severity = data.get("error_severity", "")
    return severity.upper() in _VALID_SEVERITY_LEVELS


def is_valid_csv_log(line: str) -> bool:
    """Check if a line appears to be valid PostgreSQL CSV log format.

    Validates:
    - Can be parsed as CSV
    - Has 22-26 fields (older versions have fewer fields)
    - First field looks like a timestamp (contains date pattern)
    - Field 11 (error_severity) is a valid level name

    Args:
        line: Line to check

    Returns:
        True if line appears to be valid CSV log format
    """
    line = line.strip()
    if not line:
        return False

    try:
        # Use csv module to properly parse quoted fields
        reader = csv.reader(StringIO(line))
        fields = next(reader)
    except (csv.Error, StopIteration):
        return False

    # PostgreSQL CSV logs have 22-26 fields depending on version
    # Version 14+ has 26 fields, older versions have fewer
    if not (22 <= len(fields) <= 26):
        return False

    # First field should be timestamp (log_time)
    # Format: "2024-01-15 10:30:45.123 PST"
    timestamp = fields[0]
    if not timestamp or len(timestamp) < 19:
        return False

    # Basic timestamp validation: should contain YYYY-MM-DD HH:MM:SS
    if not (
        timestamp[4] == "-"
        and timestamp[7] == "-"
        and timestamp[10] == " "
        and timestamp[13] == ":"
        and timestamp[16] == ":"
    ):
        return False

    # Field 11 (index 11) is error_severity
    if len(fields) > 11:
        severity = fields[11]
        if severity.upper() not in _VALID_SEVERITY_LEVELS:
            return False

    return True


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
    line = line.strip()
    if not line:
        return LogFormat.TEXT

    # Try JSON first (most specific check)
    if line.startswith("{") and is_valid_json_log(line):
        return LogFormat.JSON

    # Try CSV
    if is_valid_csv_log(line):
        return LogFormat.CSV

    # Default to TEXT
    return LogFormat.TEXT


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
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read(max_bytes)

    if not content:
        return LogFormat.TEXT

    # Find first complete non-empty line
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line:
            return detect_format(line)

    return LogFormat.TEXT
