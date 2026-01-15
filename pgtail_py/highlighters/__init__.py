"""Semantic highlighters for PostgreSQL log output.

This package provides pattern-based highlighters for various PostgreSQL log elements:

- **structural**: Timestamps, PIDs, context labels (DETAIL:, HINT:, etc.)
- **diagnostic**: SQLSTATE codes, error names
- **performance**: Duration, memory/size, statistics
- **objects**: Identifiers, relations, schema-qualified names
- **wal**: LSN, WAL segments, transaction IDs
- **connection**: Connection info, IP addresses, backend types
- **sql**: SQL keywords, strings, numbers, parameters, operators
- **lock**: Lock types, lock wait info
- **checkpoint**: Checkpoint stats, recovery progress
- **misc**: Booleans, NULL, OIDs, file paths

Each highlighter conforms to the Highlighter protocol defined in highlighter.py.
Highlighters are registered in the HighlighterRegistry at module load time.
"""

from __future__ import annotations

# Import all highlighter modules
from pgtail_py.highlighters.checkpoint import (
    CheckpointHighlighter,
    RecoveryHighlighter,
    get_checkpoint_highlighters,
)
from pgtail_py.highlighters.connection import (
    BackendHighlighter,
    ConnectionHighlighter,
    IPHighlighter,
    get_connection_highlighters,
)
from pgtail_py.highlighters.diagnostic import (
    ErrorNameHighlighter,
    SQLStateHighlighter,
    get_diagnostic_highlighters,
)
from pgtail_py.highlighters.lock import (
    LockTypeHighlighter,
    LockWaitHighlighter,
    get_lock_highlighters,
)
from pgtail_py.highlighters.misc import (
    BooleanHighlighter,
    NullHighlighter,
    OIDHighlighter,
    PathHighlighter,
    get_misc_highlighters,
)
from pgtail_py.highlighters.objects import (
    IdentifierHighlighter,
    RelationHighlighter,
    SchemaHighlighter,
    get_object_highlighters,
)
from pgtail_py.highlighters.performance import (
    DurationHighlighter,
    MemoryHighlighter,
    StatisticsHighlighter,
    get_performance_highlighters,
)
from pgtail_py.highlighters.sql import (
    SQLKeywordHighlighter,
    SQLNumberHighlighter,
    SQLOperatorHighlighter,
    SQLParamHighlighter,
    SQLStringHighlighter,
    detect_sql_context,
    get_sql_highlighters,
)
from pgtail_py.highlighters.structural import (
    ContextLabelHighlighter,
    PIDHighlighter,
    TimestampHighlighter,
    get_structural_highlighters,
)
from pgtail_py.highlighters.wal import (
    LSNHighlighter,
    TxidHighlighter,
    WALSegmentHighlighter,
    get_wal_highlighters,
)

# Priority ranges by category (documented in research.md):
# 100-199: Structural (timestamp, pid, context)
# 200-299: Diagnostic (sqlstate, error_name)
# 300-399: Performance (duration, memory, statistics)
# 400-499: Objects (identifier, relation, schema)
# 500-599: WAL (lsn, wal_segment, txid)
# 600-699: Connection (connection, ip, backend)
# 700-799: SQL (sql_param, sql_keyword, sql_string, sql_number, sql_operator)
# 800-899: Lock (lock_type, lock_wait)
# 900-999: Checkpoint (checkpoint, recovery)
# 1000+: Misc/Custom (boolean, null, oid, path, custom patterns)


def get_all_highlighters(
    duration_slow: int = 100,
    duration_very_slow: int = 500,
    duration_critical: int = 5000,
) -> list:
    """Return all built-in highlighters for registration.

    Args:
        duration_slow: Slow query threshold (ms).
        duration_very_slow: Very slow query threshold (ms).
        duration_critical: Critical query threshold (ms).

    Returns:
        List of all highlighter instances.
    """
    highlighters = []

    # Add highlighters in priority order
    highlighters.extend(get_structural_highlighters())  # 100-199
    highlighters.extend(get_diagnostic_highlighters())  # 200-299
    highlighters.extend(get_performance_highlighters(
        duration_slow=duration_slow,
        duration_very_slow=duration_very_slow,
        duration_critical=duration_critical,
    ))  # 300-399
    highlighters.extend(get_object_highlighters())  # 400-499
    highlighters.extend(get_wal_highlighters())  # 500-599
    highlighters.extend(get_connection_highlighters())  # 600-699
    highlighters.extend(get_sql_highlighters())  # 700-799
    highlighters.extend(get_lock_highlighters())  # 800-899
    highlighters.extend(get_checkpoint_highlighters())  # 900-999
    highlighters.extend(get_misc_highlighters())  # 1000+

    return highlighters


# Export all public classes and functions
__all__ = [
    # Structural
    "TimestampHighlighter",
    "PIDHighlighter",
    "ContextLabelHighlighter",
    "get_structural_highlighters",
    # Diagnostic
    "SQLStateHighlighter",
    "ErrorNameHighlighter",
    "get_diagnostic_highlighters",
    # Performance
    "DurationHighlighter",
    "MemoryHighlighter",
    "StatisticsHighlighter",
    "get_performance_highlighters",
    # Objects
    "IdentifierHighlighter",
    "RelationHighlighter",
    "SchemaHighlighter",
    "get_object_highlighters",
    # WAL
    "LSNHighlighter",
    "WALSegmentHighlighter",
    "TxidHighlighter",
    "get_wal_highlighters",
    # Connection
    "ConnectionHighlighter",
    "IPHighlighter",
    "BackendHighlighter",
    "get_connection_highlighters",
    # SQL
    "SQLParamHighlighter",
    "SQLKeywordHighlighter",
    "SQLStringHighlighter",
    "SQLNumberHighlighter",
    "SQLOperatorHighlighter",
    "detect_sql_context",
    "get_sql_highlighters",
    # Lock
    "LockTypeHighlighter",
    "LockWaitHighlighter",
    "get_lock_highlighters",
    # Checkpoint
    "CheckpointHighlighter",
    "RecoveryHighlighter",
    "get_checkpoint_highlighters",
    # Misc
    "BooleanHighlighter",
    "NullHighlighter",
    "OIDHighlighter",
    "PathHighlighter",
    "get_misc_highlighters",
    # All highlighters
    "get_all_highlighters",
]
