"""SQL highlighters for PostgreSQL log output.

Highlighters in this module:
- SQLParamHighlighter: Query parameters $1, $2, etc. (priority 700)
- SQLKeywordHighlighter: SQL keywords via Aho-Corasick (priority 710)
- SQLStringHighlighter: String literals (priority 720)
- SQLNumberHighlighter: Numeric literals (priority 730)
- SQLOperatorHighlighter: SQL operators (priority 740)
- SQLContextDetector: Detects SQL context in log messages

Migrated from sql_tokenizer.py and sql_highlighter.py.
"""

from __future__ import annotations

import re

from pgtail_py.highlighter import KeywordHighlighter, RegexHighlighter

# =============================================================================
# SQL Keywords (from sql_tokenizer.py)
# =============================================================================

# SQL keywords grouped by category for differentiated styling
SQL_KEYWORDS_DML = frozenset({
    "SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT",
})

SQL_KEYWORDS_DDL = frozenset({
    "CREATE", "ALTER", "DROP", "TRUNCATE",
    "TABLE", "INDEX", "VIEW", "TRIGGER", "FUNCTION", "PROCEDURE",
    "SCHEMA", "DATABASE", "EXTENSION", "TYPE", "DOMAIN", "SEQUENCE",
    "MATERIALIZED", "TABLESPACE", "ROLE", "USER", "POLICY", "RULE",
    "OPERATOR", "AGGREGATE", "COLLATION", "CONVERSION", "LANGUAGE",
    "PUBLICATION", "SUBSCRIPTION", "STATISTICS", "TRANSFORM",
})

SQL_KEYWORDS_DCL = frozenset({
    "GRANT", "REVOKE", "PRIVILEGES", "USAGE", "CONNECT",
})

SQL_KEYWORDS_TCL = frozenset({
    "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE",
    "START", "TRANSACTION", "WORK",
})

# All other SQL keywords
SQL_KEYWORDS_OTHER = frozenset({
    # Clauses
    "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
    "ON", "AS", "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET",
    "INTO", "VALUES", "SET", "RETURNING", "FETCH", "ONLY", "NEXT",
    "PRIOR", "PERCENT", "TIES",
    # Logical operators
    "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "ILIKE",
    "SIMILAR", "IS", "ISNULL", "NOTNULL", "NULL",
    # Set operations
    "UNION", "INTERSECT", "EXCEPT", "DISTINCT", "ALL", "ANY", "SOME",
    # CASE expression
    "CASE", "WHEN", "THEN", "ELSE", "END",
    # CTE and window functions
    "WITH", "RECURSIVE", "OVER", "PARTITION", "WINDOW", "RANGE",
    "ROWS", "GROUPS", "UNBOUNDED", "PRECEDING", "FOLLOWING", "CURRENT",
    "ROW", "EXCLUDE",
    # Joins
    "CROSS", "FULL", "NATURAL", "USING", "LATERAL",
    # Ordering
    "ASC", "DESC", "NULLS", "FIRST", "LAST",
    # Constraints and keys
    "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "DEFAULT",
    "CHECK", "UNIQUE", "DEFERRABLE", "DEFERRED", "IMMEDIATE", "INITIALLY",
    # Transaction control (additional)
    "ISOLATION", "LEVEL", "SERIALIZABLE", "REPEATABLE", "READ",
    "COMMITTED", "UNCOMMITTED",
    # Utility commands
    "EXPLAIN", "ANALYZE", "VACUUM", "REINDEX", "CLUSTER", "REFRESH",
    "LOCK", "COPY", "COMMENT", "SECURITY", "LABEL", "TEMPORARY", "TEMP",
    # Prepared statements
    "PREPARE", "EXECUTE", "DEALLOCATE",
    # Cursors
    "CURSOR", "DECLARE", "CLOSE", "MOVE", "ABSOLUTE", "RELATIVE",
    "FORWARD", "BACKWARD",
    # Session management
    "DISCARD", "RESET", "SHOW", "LISTEN", "NOTIFY", "UNLISTEN",
    # Boolean literals
    "TRUE", "FALSE", "UNKNOWN",
    # Misc expressions
    "CAST", "COALESCE", "NULLIF", "GREATEST", "LEAST", "RETURNS",
    "ARRAY", "FILTER", "WITHIN",
    # Control flow (PL/pgSQL)
    "IF", "ELSIF", "LOOP", "WHILE", "FOR", "FOREACH", "EXIT",
    "CONTINUE", "RETURN", "RAISE", "EXCEPTION", "PERFORM", "GET",
    "DIAGNOSTICS",
    # Inheritance and partitioning
    "INHERITS", "OF", "ATTACH", "DETACH",
    # Miscellaneous
    "CASCADE", "RESTRICT", "NO", "ACTION", "NOTHING", "CONFLICT",
    "DO", "FORCE", "CONCURRENTLY", "OWNER", "TO", "RENAME", "ADD",
    "COLUMN", "ENABLE", "DISABLE", "ALWAYS", "REPLICA", "IDENTITY",
    "GENERATED", "STORED", "VIRTUAL", "OVERRIDING", "SYSTEM", "VALUE",
    "LOCAL", "GLOBAL", "SESSION", "VALID", "NOWAIT", "SKIP", "LOCKED",
    "SHARE", "EXCLUSIVE", "ACCESS",
})


# =============================================================================
# SQLParamHighlighter
# =============================================================================


class SQLParamHighlighter(RegexHighlighter):
    """Highlights query parameter placeholders.

    Matches PostgreSQL parameter syntax:
    - $1, $2, $3, etc.
    """

    PATTERN = r"\$\d+"

    def __init__(self) -> None:
        """Initialize param highlighter."""
        super().__init__(
            name="sql_param",
            priority=700,
            pattern=self.PATTERN,
            style="hl_param",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Query parameters ($1, $2, etc.)"


# =============================================================================
# SQLKeywordHighlighter
# =============================================================================


class SQLKeywordHighlighter(KeywordHighlighter):
    """Highlights SQL keywords with category-based styling.

    Uses Aho-Corasick for efficient matching of 120+ keywords.
    Keywords are styled by category:
    - DML (SELECT, INSERT, etc.): sql_keyword_dml
    - DDL (CREATE, ALTER, etc.): sql_keyword_ddl
    - DCL (GRANT, REVOKE): sql_keyword_dcl
    - TCL (BEGIN, COMMIT, etc.): sql_keyword_tcl
    - Other: sql_keyword
    """

    def __init__(self) -> None:
        """Initialize keyword highlighter with all SQL keywords."""
        # Build keyword -> style mapping
        keywords: dict[str, str] = {}

        for kw in SQL_KEYWORDS_DML:
            keywords[kw] = "sql_keyword"  # Could use sql_keyword_dml for differentiation
        for kw in SQL_KEYWORDS_DDL:
            keywords[kw] = "sql_keyword"  # Could use sql_keyword_ddl for differentiation
        for kw in SQL_KEYWORDS_DCL:
            keywords[kw] = "sql_keyword"  # Could use sql_keyword_dcl for differentiation
        for kw in SQL_KEYWORDS_TCL:
            keywords[kw] = "sql_keyword"  # Could use sql_keyword_tcl for differentiation
        for kw in SQL_KEYWORDS_OTHER:
            keywords[kw] = "sql_keyword"

        super().__init__(
            name="sql_keyword",
            priority=710,
            keywords=keywords,
            case_sensitive=False,
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        total = (
            len(SQL_KEYWORDS_DML) + len(SQL_KEYWORDS_DDL) +
            len(SQL_KEYWORDS_DCL) + len(SQL_KEYWORDS_TCL) +
            len(SQL_KEYWORDS_OTHER)
        )
        return f"SQL keywords ({total} keywords)"


# =============================================================================
# SQLStringHighlighter
# =============================================================================


class SQLStringHighlighter(RegexHighlighter):
    """Highlights string literals in SQL.

    Matches:
    - Single-quoted strings: 'value', 'it''s'
    - Dollar-quoted strings: $$value$$, $tag$value$tag$
    """

    # Combined pattern for all string types
    # Order: tagged dollar quotes first, then empty dollar quotes, then single quotes
    PATTERN = r"\$([a-zA-Z_][a-zA-Z0-9_]*)?\$.*?\$\1?\$|'(?:[^']|'')*'"

    def __init__(self) -> None:
        """Initialize string highlighter."""
        super().__init__(
            name="sql_string",
            priority=720,
            pattern=self.PATTERN,
            style="sql_string",
            flags=re.DOTALL,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "SQL string literals ('...', $$...$$)"


# =============================================================================
# SQLNumberHighlighter
# =============================================================================


class SQLNumberHighlighter(RegexHighlighter):
    """Highlights numeric literals in SQL.

    Matches:
    - Integers: 42, 1234
    - Decimals: 3.14, 0.5
    - Scientific notation: 1.23e10, 5E-3
    - Hex: 0x1A2B
    """

    # Pattern for various numeric formats
    PATTERN = r"\b(?:0x[0-9A-Fa-f]+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\b"

    def __init__(self) -> None:
        """Initialize number highlighter."""
        super().__init__(
            name="sql_number",
            priority=730,
            pattern=self.PATTERN,
            style="sql_number",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "SQL numeric literals (42, 3.14, 1e10)"


# =============================================================================
# SQLOperatorHighlighter
# =============================================================================


class SQLOperatorHighlighter(RegexHighlighter):
    """Highlights SQL operators.

    Matches:
    - Comparison: =, <, >, <=, >=, <>, !=
    - Logical: ||, &&
    - Type cast: ::
    - Other: +, -, *, /, %, @, #, ~, ^, |, &
    """

    # Pattern: multi-char operators first, then single-char
    PATTERN = r"<>|!=|<=|>=|\|\||::|[=<>+\-*/%!|:&^~@#]"

    def __init__(self) -> None:
        """Initialize operator highlighter."""
        super().__init__(
            name="sql_operator",
            priority=740,
            pattern=self.PATTERN,
            style="sql_operator",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "SQL operators (=, <>, ||, ::, etc.)"


# =============================================================================
# SQL Context Detection
# =============================================================================


# Patterns that indicate SQL content in log messages
SQL_CONTEXT_PATTERNS = [
    re.compile(r"^statement:\s*", re.IGNORECASE),
    re.compile(r"^execute\s+\w+:\s*", re.IGNORECASE),
    re.compile(r"^parse\s+\w+:\s*", re.IGNORECASE),
    re.compile(r"^bind\s+\w+:\s*", re.IGNORECASE),
    re.compile(r"duration:\s*[\d.]+\s*ms\s+statement:\s*", re.IGNORECASE),
]


def detect_sql_context(text: str) -> tuple[bool, int]:
    """Detect if text contains SQL and find where it starts.

    Args:
        text: Log message text to analyze.

    Returns:
        Tuple of (contains_sql, sql_start_position).
        If no SQL detected, returns (False, 0).
    """
    for pattern in SQL_CONTEXT_PATTERNS:
        match = pattern.search(text)
        if match:
            return (True, match.end())
    return (False, 0)


# =============================================================================
# Module-level registration
# =============================================================================


def get_sql_highlighters() -> list[
    SQLParamHighlighter | SQLKeywordHighlighter | SQLStringHighlighter |
    SQLNumberHighlighter | SQLOperatorHighlighter
]:
    """Return all SQL highlighters for registration.

    Returns:
        List of SQL highlighter instances.
    """
    return [
        SQLParamHighlighter(),
        SQLKeywordHighlighter(),
        SQLStringHighlighter(),
        SQLNumberHighlighter(),
        SQLOperatorHighlighter(),
    ]


__all__ = [
    "SQLParamHighlighter",
    "SQLKeywordHighlighter",
    "SQLStringHighlighter",
    "SQLNumberHighlighter",
    "SQLOperatorHighlighter",
    "SQL_KEYWORDS_DML",
    "SQL_KEYWORDS_DDL",
    "SQL_KEYWORDS_DCL",
    "SQL_KEYWORDS_TCL",
    "SQL_KEYWORDS_OTHER",
    "detect_sql_context",
    "get_sql_highlighters",
]
