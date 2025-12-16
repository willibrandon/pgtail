"""Export functionality for log entries to files and external commands."""

import csv
import json
import re
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.filter import LogLevel
    from pgtail_py.parser import LogEntry
    from pgtail_py.regex_filter import FilterState


class ExportFormat(str, Enum):
    """Supported export output formats."""

    TEXT = "text"  # Raw log line (original format)
    JSON = "json"  # JSONL format (one JSON object per line)
    CSV = "csv"  # CSV with header row

    @classmethod
    def from_string(cls, value: str) -> "ExportFormat":
        """Parse format from case-insensitive string.

        Args:
            value: Format name (text, json, csv).

        Returns:
            ExportFormat enum value.

        Raises:
            ValueError: If value is not a valid format.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(f.value for f in cls)
            raise ValueError(f"Unknown format '{value}'. Valid formats: {valid}") from None


@dataclass
class ExportOptions:
    """Configuration for an export operation."""

    path: Path
    format: ExportFormat = ExportFormat.TEXT
    follow: bool = False
    append: bool = False
    since: datetime | None = None

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if self.follow and self.append:
            errors.append("Cannot use --follow with --append")
        return errors


@dataclass
class PipeOptions:
    """Configuration for a pipe operation."""

    command: str
    format: ExportFormat = ExportFormat.TEXT

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.command.strip():
            errors.append("Command cannot be empty")
        return errors


def parse_since(value: str) -> datetime:
    """Parse --since value into datetime.

    Supports relative times (1h, 30m, 2d, 10s) and ISO 8601 format.

    Args:
        value: Time specification string.

    Returns:
        Datetime representing the cutoff time.

    Raises:
        ValueError: If value cannot be parsed.
    """
    # Try relative time first (e.g., 1h, 30m, 2d, 10s)
    match = re.match(r"^(\d+)([smhd])$", value.lower())
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
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"Invalid time format '{value}'. Use relative (1h, 30m, 2d) or ISO 8601."
        ) from None


def format_text_entry(entry: "LogEntry") -> str:
    """Format entry as raw text (original log line).

    Args:
        entry: Log entry to format.

    Returns:
        Raw log line string.
    """
    return entry.raw


def format_json_entry(entry: "LogEntry") -> str:
    """Format entry as JSON (JSONL format).

    Args:
        entry: Log entry to format.

    Returns:
        JSON string with timestamp, level, pid, message fields.
    """
    return json.dumps(
        {
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "level": entry.level.name,
            "pid": entry.pid,
            "message": entry.message,
        },
        ensure_ascii=False,
    )


def format_csv_row(entry: "LogEntry") -> str:
    """Format entry as CSV row.

    Uses csv module with QUOTE_MINIMAL for proper escaping.

    Args:
        entry: Log entry to format.

    Returns:
        CSV row string (without trailing newline).
    """
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            entry.timestamp.isoformat() if entry.timestamp else "",
            entry.level.name,
            entry.pid if entry.pid is not None else "",
            entry.message,
        ]
    )
    # Remove trailing newline added by csv.writer
    return output.getvalue().rstrip("\r\n")


def format_entry(entry: "LogEntry", fmt: ExportFormat) -> str:
    """Format entry according to specified format.

    Args:
        entry: Log entry to format.
        fmt: Output format.

    Returns:
        Formatted string.
    """
    if fmt == ExportFormat.TEXT:
        return format_text_entry(entry)
    elif fmt == ExportFormat.JSON:
        return format_json_entry(entry)
    elif fmt == ExportFormat.CSV:
        return format_csv_row(entry)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def get_filtered_entries(
    entries: Iterable["LogEntry"],
    levels: "set[LogLevel] | None",
    regex_state: "FilterState",
    since: datetime | None = None,
) -> Generator["LogEntry", None, None]:
    """Generator that yields filtered entries.

    Args:
        entries: Source entries to filter.
        levels: Set of levels to include, or None for all.
        regex_state: Regex filter state.
        since: Only include entries after this time.

    Yields:
        Filtered log entries.
    """
    from pgtail_py.filter import should_show

    for entry in entries:
        # Filter by time
        if since is not None and entry.timestamp is not None and entry.timestamp < since:
            continue

        # Filter by level
        if not should_show(entry.level, levels):
            continue

        # Filter by regex
        if not regex_state.should_show(entry.raw):
            continue

        yield entry


def ensure_parent_dirs(path: Path) -> None:
    """Create parent directories if they don't exist.

    Args:
        path: File path whose parent directories should be created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)


# CSV header for export
CSV_HEADER = "timestamp,level,pid,message"


def confirm_overwrite(path: Path) -> bool:
    """Prompt user to confirm overwriting an existing file.

    Args:
        path: File path to check.

    Returns:
        True if file doesn't exist or user confirms overwrite, False otherwise.
    """
    from prompt_toolkit import prompt

    if not path.exists():
        return True

    response = prompt(f"File {path} exists. Overwrite? [y/N] ")
    return response.lower() in ("y", "yes")


def export_to_file(
    entries: Iterable["LogEntry"],
    path: Path,
    fmt: ExportFormat = ExportFormat.TEXT,
    append: bool = False,
) -> int:
    """Export entries to a file.

    Args:
        entries: Log entries to export.
        path: Output file path.
        fmt: Output format.
        append: If True, append to existing file.

    Returns:
        Number of entries written.
    """
    mode = "a" if append else "w"
    count = 0

    # Ensure parent directories exist
    ensure_parent_dirs(path)

    with open(path, mode, encoding="utf-8", newline="") as f:
        # Write CSV header if not appending
        if fmt == ExportFormat.CSV and not append:
            f.write(CSV_HEADER + "\n")

        for entry in entries:
            f.write(format_entry(entry, fmt) + "\n")
            count += 1

    return count
