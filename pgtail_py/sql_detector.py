"""SQL detection in PostgreSQL log messages.

Detects SQL content within log messages based on PostgreSQL log prefixes.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class SQLDetectionResult(NamedTuple):
    """Represents detected SQL content within a log message.

    Attributes:
        prefix: Text before SQL (e.g., "LOG: statement: ").
        sql: The SQL content to highlight.
        suffix: Text after SQL (often empty).
    """

    prefix: str
    sql: str
    suffix: str


# Compiled patterns for SQL detection (ordered by specificity)
# Pattern 1: LOG: duration: ... ms statement/parse/bind/execute: <SQL>
_DURATION_SQL_PATTERN = re.compile(
    r"^(.*?duration:\s*[\d.]+\s*ms\s+(?:statement|parse|bind|execute)\s*(?:\S+)?:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)

# Pattern 2: LOG: statement: <SQL>
_STATEMENT_PATTERN = re.compile(
    r"^(.*?statement:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)

# Pattern 3: LOG: execute <name>: <SQL>
_EXECUTE_PATTERN = re.compile(
    r"^(.*?execute\s+\S+:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)

# Pattern 4: LOG: parse <name>: <SQL>
_PARSE_PATTERN = re.compile(
    r"^(.*?parse\s+\S+:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)

# Pattern 5: LOG: bind <name>: <SQL>
_BIND_PATTERN = re.compile(
    r"^(.*?bind\s+\S+:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)

# Pattern 6: DETAIL: <SQL context> - often contains SQL in error contexts
_DETAIL_PATTERN = re.compile(
    r"^(DETAIL:\s*)(.*?)(\s*)$",
    re.IGNORECASE | re.DOTALL,
)


def detect_sql_content(message: str) -> SQLDetectionResult | None:
    """Detect SQL content in a log message.

    Looks for PostgreSQL log message patterns that contain SQL:
    - LOG: statement: <SQL>
    - LOG: execute <name>: <SQL>
    - LOG: parse <name>: <SQL>
    - LOG: bind <name>: <SQL>
    - LOG: duration: ... ms statement/parse/bind/execute: <SQL>
    - DETAIL: <SQL context>

    Args:
        message: Log message to analyze.

    Returns:
        SQLDetectionResult with prefix, sql, and suffix if SQL found.
        None if no SQL detected.
    """
    if not message:
        return None

    # Try patterns in order of specificity
    # Duration + SQL command is most specific
    match = _DURATION_SQL_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    # Plain statement
    match = _STATEMENT_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    # Execute prepared statement
    match = _EXECUTE_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    # Parse prepared statement
    match = _PARSE_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    # Bind prepared statement
    match = _BIND_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    # DETAIL line (often contains SQL context in errors)
    match = _DETAIL_PATTERN.match(message)
    if match:
        prefix, sql, suffix = match.groups()
        if sql.strip():
            return SQLDetectionResult(prefix=prefix, sql=sql, suffix=suffix)

    return None
