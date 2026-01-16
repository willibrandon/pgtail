"""SQL highlighters for PostgreSQL log output.

Highlighters in this module:
- SQLParamHighlighter: Query parameters $1, $2, etc. (priority 700)
- SQLKeywordHighlighter: SQL keywords via Aho-Corasick (priority 710)
- SQLStringHighlighter: String literals (priority 720)
- SQLNumberHighlighter: Numeric literals (priority 730)
- SQLOperatorHighlighter: SQL operators (priority 740)
- SQLContextDetector: Detects SQL context in log messages

Also provides legacy compatibility exports:
- SQLTokenType, SQLToken, SQLTokenizer (from sql_tokenizer.py)
- SQLHighlighter, highlight_sql, highlight_sql_rich (from sql_highlighter.py)
- SQLDetectionResult, detect_sql_content (from sql_detector.py)

Migrated from sql_tokenizer.py, sql_highlighter.py, and sql_detector.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.highlighter import KeywordHighlighter, RegexHighlighter
from pgtail_py.theme import ColorStyle, Theme
from pgtail_py.utils import is_color_disabled

if TYPE_CHECKING:
    from pgtail_py.theme import ThemeManager

# =============================================================================
# SQL Keywords (from sql_tokenizer.py)
# =============================================================================

# SQL keywords grouped by category for differentiated styling
SQL_KEYWORDS_DML = frozenset(
    {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
    }
)

SQL_KEYWORDS_DDL = frozenset(
    {
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "TABLE",
        "INDEX",
        "VIEW",
        "TRIGGER",
        "FUNCTION",
        "PROCEDURE",
        "SCHEMA",
        "DATABASE",
        "EXTENSION",
        "TYPE",
        "DOMAIN",
        "SEQUENCE",
        "MATERIALIZED",
        "TABLESPACE",
        "ROLE",
        "USER",
        "POLICY",
        "RULE",
        "OPERATOR",
        "AGGREGATE",
        "COLLATION",
        "CONVERSION",
        "LANGUAGE",
        "PUBLICATION",
        "SUBSCRIPTION",
        "STATISTICS",
        "TRANSFORM",
    }
)

SQL_KEYWORDS_DCL = frozenset(
    {
        "GRANT",
        "REVOKE",
        "PRIVILEGES",
        "USAGE",
        "CONNECT",
    }
)

SQL_KEYWORDS_TCL = frozenset(
    {
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "START",
        "TRANSACTION",
        "WORK",
    }
)

# All other SQL keywords
SQL_KEYWORDS_OTHER = frozenset(
    {
        # Clauses
        "FROM",
        "WHERE",
        "JOIN",
        "LEFT",
        "RIGHT",
        "INNER",
        "OUTER",
        "ON",
        "AS",
        "ORDER",
        "BY",
        "GROUP",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "INTO",
        "VALUES",
        "SET",
        "RETURNING",
        "FETCH",
        "ONLY",
        "NEXT",
        "PRIOR",
        "PERCENT",
        "TIES",
        # Logical operators
        "AND",
        "OR",
        "NOT",
        "IN",
        "EXISTS",
        "BETWEEN",
        "LIKE",
        "ILIKE",
        "SIMILAR",
        "IS",
        "ISNULL",
        "NOTNULL",
        "NULL",
        # Set operations
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "DISTINCT",
        "ALL",
        "ANY",
        "SOME",
        # CASE expression
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        # CTE and window functions
        "WITH",
        "RECURSIVE",
        "OVER",
        "PARTITION",
        "WINDOW",
        "RANGE",
        "ROWS",
        "GROUPS",
        "UNBOUNDED",
        "PRECEDING",
        "FOLLOWING",
        "CURRENT",
        "ROW",
        "EXCLUDE",
        # Joins
        "CROSS",
        "FULL",
        "NATURAL",
        "USING",
        "LATERAL",
        # Ordering
        "ASC",
        "DESC",
        "NULLS",
        "FIRST",
        "LAST",
        # Constraints and keys
        "PRIMARY",
        "KEY",
        "FOREIGN",
        "REFERENCES",
        "CONSTRAINT",
        "DEFAULT",
        "CHECK",
        "UNIQUE",
        "DEFERRABLE",
        "DEFERRED",
        "IMMEDIATE",
        "INITIALLY",
        # Transaction control (additional)
        "ISOLATION",
        "LEVEL",
        "SERIALIZABLE",
        "REPEATABLE",
        "READ",
        "COMMITTED",
        "UNCOMMITTED",
        # Utility commands
        "EXPLAIN",
        "ANALYZE",
        "VACUUM",
        "REINDEX",
        "CLUSTER",
        "REFRESH",
        "LOCK",
        "COPY",
        "COMMENT",
        "SECURITY",
        "LABEL",
        "TEMPORARY",
        "TEMP",
        # Prepared statements
        "PREPARE",
        "EXECUTE",
        "DEALLOCATE",
        # Cursors
        "CURSOR",
        "DECLARE",
        "CLOSE",
        "MOVE",
        "ABSOLUTE",
        "RELATIVE",
        "FORWARD",
        "BACKWARD",
        # Session management
        "DISCARD",
        "RESET",
        "SHOW",
        "LISTEN",
        "NOTIFY",
        "UNLISTEN",
        # Boolean literals
        "TRUE",
        "FALSE",
        "UNKNOWN",
        # Misc expressions
        "CAST",
        "COALESCE",
        "NULLIF",
        "GREATEST",
        "LEAST",
        "RETURNS",
        "ARRAY",
        "FILTER",
        "WITHIN",
        # Control flow (PL/pgSQL)
        "IF",
        "ELSIF",
        "LOOP",
        "WHILE",
        "FOR",
        "FOREACH",
        "EXIT",
        "CONTINUE",
        "RETURN",
        "RAISE",
        "EXCEPTION",
        "PERFORM",
        "GET",
        "DIAGNOSTICS",
        # Inheritance and partitioning
        "INHERITS",
        "OF",
        "ATTACH",
        "DETACH",
        # Miscellaneous
        "CASCADE",
        "RESTRICT",
        "NO",
        "ACTION",
        "NOTHING",
        "CONFLICT",
        "DO",
        "FORCE",
        "CONCURRENTLY",
        "OWNER",
        "TO",
        "RENAME",
        "ADD",
        "COLUMN",
        "ENABLE",
        "DISABLE",
        "ALWAYS",
        "REPLICA",
        "IDENTITY",
        "GENERATED",
        "STORED",
        "VIRTUAL",
        "OVERRIDING",
        "SYSTEM",
        "VALUE",
        "LOCAL",
        "GLOBAL",
        "SESSION",
        "VALID",
        "NOWAIT",
        "SKIP",
        "LOCKED",
        "SHARE",
        "EXCLUSIVE",
        "ACCESS",
    }
)

# Combined keyword set for tokenizer
SQL_KEYWORDS: frozenset[str] = (
    SQL_KEYWORDS_DML | SQL_KEYWORDS_DDL | SQL_KEYWORDS_DCL | SQL_KEYWORDS_TCL | SQL_KEYWORDS_OTHER
)


# =============================================================================
# SQL Tokenizer (from sql_tokenizer.py)
# =============================================================================


class SQLTokenType(Enum):
    """Categories of tokens parsed from SQL text.

    Each token type maps to a style class for highlighting.
    """

    KEYWORD = "keyword"  # SQL reserved words (SELECT, FROM, WHERE, etc.)
    IDENTIFIER = "identifier"  # Table/column names (unquoted)
    QUOTED_IDENTIFIER = "quoted_identifier"  # Double-quoted identifiers ("MyTable")
    STRING = "string"  # String literals ('value', $$value$$)
    NUMBER = "number"  # Numeric literals (42, 3.14)
    OPERATOR = "operator"  # Operators (=, <>, ||, ::, etc.)
    COMMENT = "comment"  # Comments (-- line, /* block */)
    FUNCTION = "function"  # Function names followed by (
    PUNCTUATION = "punctuation"  # Parentheses, commas, semicolons
    WHITESPACE = "whitespace"  # Spaces, tabs, newlines
    UNKNOWN = "unknown"  # Unrecognized tokens


@dataclass(frozen=True, slots=True)
class SQLToken:
    """A single parsed token with type, text, and position.

    Attributes:
        type: Token category.
        text: The actual token text.
        start: Start position in source string.
        end: End position in source string (exclusive).
    """

    type: SQLTokenType
    text: str
    start: int
    end: int

    def __post_init__(self) -> None:
        """Validate token invariants."""
        if self.start < 0:
            raise ValueError(f"start must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"end must be > start, got end={self.end}, start={self.start}")


# Compiled regex patterns for tokenization
# Order matters: comments → strings → numbers → keywords → functions → operators → identifiers

# Whitespace pattern
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Comment patterns (must match before operators containing - or /)
_BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)  # /* ... */
_LINE_COMMENT_PATTERN = re.compile(r"--[^\n]*")  # -- to end of line

# String patterns (must match before other patterns that could match inside strings)
# Dollar-quoted strings: $$...$$ or $tag$...$tag$
_DOLLAR_EMPTY_STRING_PATTERN = re.compile(r"\$\$.*?\$\$", re.DOTALL)  # $$...$$
_DOLLAR_TAG_STRING_PATTERN = re.compile(
    r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$.*?\$\1\$", re.DOTALL
)  # $tag$...$tag$
# Single-quoted strings with '' escape handling
_SINGLE_STRING_PATTERN = re.compile(r"'(?:[^']|'')*'")

# Quoted identifier pattern: "..." with "" for escaped quotes
_QUOTED_IDENTIFIER_PATTERN = re.compile(r'"(?:[^"]|"")*"')

# Number pattern: integers and decimals
_NUMBER_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)?")

# Keyword/identifier pattern (word characters)
_WORD_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Multi-character operators (must match before single-char operators)
_MULTI_OP_PATTERN = re.compile(r"<>|!=|<=|>=|\|\||::")

# Single-character operators
_SINGLE_OP_PATTERN = re.compile(r"[=<>+\-*/%!|:&^~]")

# Punctuation characters
_PUNCTUATION_PATTERN = re.compile(r"[(),;.\[\]]")


class SQLTokenizer:
    """Tokenizes SQL text into a sequence of SQLToken objects.

    Stateless class that can be reused for multiple tokenization calls.
    Regex patterns are compiled at class level for performance.
    """

    def tokenize(self, sql: str) -> list[SQLToken]:
        """Parse SQL string into tokens.

        Token matching order:
        1. Whitespace
        2. Block comments (/* ... */)
        3. Line comments (--)
        4. Dollar-quoted strings ($$...$$ or $tag$...$tag$)
        5. Single-quoted strings ('...')
        6. Quoted identifiers ("...")
        7. Numbers
        8. Words (keywords, functions, identifiers)
        9. Multi-character operators (<>, !=, etc.)
        10. Single-character operators
        11. Punctuation
        12. Unknown

        Args:
            sql: SQL text to tokenize.

        Returns:
            List of SQLToken objects covering the entire input.
        """
        if not sql:
            return []

        tokens: list[SQLToken] = []
        pos = 0
        length = len(sql)

        while pos < length:
            # 1. Try whitespace
            match = _WHITESPACE_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.WHITESPACE,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 2. Try block comment (/* ... */)
            match = _BLOCK_COMMENT_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.COMMENT,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 3. Try line comment (--)
            match = _LINE_COMMENT_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.COMMENT,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 4. Try dollar-quoted string ($$...$$ or $tag$...$tag$)
            # Try tagged version first ($tag$...$tag$), then empty ($$...$$)
            match = _DOLLAR_TAG_STRING_PATTERN.match(sql, pos)
            if not match:
                match = _DOLLAR_EMPTY_STRING_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.STRING,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 5. Try single-quoted string ('...')
            match = _SINGLE_STRING_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.STRING,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 6. Try quoted identifier ("...")
            match = _QUOTED_IDENTIFIER_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.QUOTED_IDENTIFIER,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 7. Try number
            match = _NUMBER_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.NUMBER,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 8. Try word (keyword, function, or identifier)
            match = _WORD_PATTERN.match(sql, pos)
            if match:
                word = match.group()
                word_end = match.end()

                # Look ahead to see if followed by ( to detect function
                is_function = word_end < length and sql[word_end] == "("

                # Check if it's a keyword (case-insensitive)
                if word.upper() in SQL_KEYWORDS and not is_function:
                    token_type = SQLTokenType.KEYWORD
                elif is_function:
                    token_type = SQLTokenType.FUNCTION
                else:
                    token_type = SQLTokenType.IDENTIFIER

                tokens.append(
                    SQLToken(
                        type=token_type,
                        text=word,
                        start=pos,
                        end=word_end,
                    )
                )
                pos = word_end
                continue

            # 9. Try multi-character operators
            match = _MULTI_OP_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.OPERATOR,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 10. Try single-character operators
            match = _SINGLE_OP_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.OPERATOR,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 11. Try punctuation
            match = _PUNCTUATION_PATTERN.match(sql, pos)
            if match:
                tokens.append(
                    SQLToken(
                        type=SQLTokenType.PUNCTUATION,
                        text=match.group(),
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # 12. Unknown character - consume one character
            tokens.append(
                SQLToken(
                    type=SQLTokenType.UNKNOWN,
                    text=sql[pos],
                    start=pos,
                    end=pos + 1,
                )
            )
            pos += 1

        return tokens


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
            len(SQL_KEYWORDS_DML)
            + len(SQL_KEYWORDS_DDL)
            + len(SQL_KEYWORDS_DCL)
            + len(SQL_KEYWORDS_TCL)
            + len(SQL_KEYWORDS_OTHER)
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
# SQL Detection Result (from sql_detector.py)
# =============================================================================


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


# Combined SQL detection pattern for fast matching
# Uses alternation with named groups to identify which pattern matched
# Order: duration (most specific) -> statement -> execute -> parse -> bind -> DETAIL
_SQL_DETECTION_PATTERN = re.compile(
    r"^(?:"
    # Duration with SQL command (most specific)
    r"(?P<dur_prefix>.*?duration:\s*[\d.]+\s*ms\s+(?:statement|parse|bind|execute)\s*(?:\S+)?:\s*)(?P<dur_sql>.*?)(?P<dur_suffix>\s*)$"
    r"|"
    # Plain statement
    r"(?P<stmt_prefix>.*?statement:\s*)(?P<stmt_sql>.*?)(?P<stmt_suffix>\s*)$"
    r"|"
    # Execute prepared statement
    r"(?P<exec_prefix>.*?execute\s+\S+:\s*)(?P<exec_sql>.*?)(?P<exec_suffix>\s*)$"
    r"|"
    # Parse prepared statement
    r"(?P<parse_prefix>.*?parse\s+\S+:\s*)(?P<parse_sql>.*?)(?P<parse_suffix>\s*)$"
    r"|"
    # Bind prepared statement
    r"(?P<bind_prefix>.*?bind\s+\S+:\s*)(?P<bind_sql>.*?)(?P<bind_suffix>\s*)$"
    r"|"
    # DETAIL line
    r"(?P<detail_prefix>DETAIL:\s*)(?P<detail_sql>.*?)(?P<detail_suffix>\s*)$"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# Group name prefixes for extraction
_SQL_GROUP_PREFIXES = ("dur", "stmt", "exec", "parse", "bind", "detail")


def detect_sql_content(message: str) -> SQLDetectionResult | None:
    """Detect SQL content in a log message.

    Looks for PostgreSQL log message patterns that contain SQL:
    - LOG: statement: <SQL>
    - LOG: execute <name>: <SQL>
    - LOG: parse <name>: <SQL>
    - LOG: bind <name>: <SQL>
    - LOG: duration: ... ms statement/parse/bind/execute: <SQL>
    - DETAIL: <SQL context>

    Uses a single combined regex for performance.

    Args:
        message: Log message to analyze.

    Returns:
        SQLDetectionResult with prefix, sql, and suffix if SQL found.
        None if no SQL detected.
    """
    if not message:
        return None

    match = _SQL_DETECTION_PATTERN.match(message)
    if not match:
        return None

    # Find which group matched
    groups = match.groupdict()
    for prefix_name in _SQL_GROUP_PREFIXES:
        sql = groups.get(f"{prefix_name}_sql")
        if sql is not None and sql.strip():
            return SQLDetectionResult(
                prefix=groups[f"{prefix_name}_prefix"],
                sql=sql,
                suffix=groups[f"{prefix_name}_suffix"],
            )

    return None


# =============================================================================
# SQL Highlighter Compatibility (from sql_highlighter.py)
# =============================================================================


# Style class mapping for token types (prompt_toolkit)
TOKEN_TO_STYLE: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "class:sql_keyword",
    SQLTokenType.IDENTIFIER: "class:sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "class:sql_identifier",
    SQLTokenType.STRING: "class:sql_string",
    SQLTokenType.NUMBER: "class:sql_number",
    SQLTokenType.OPERATOR: "class:sql_operator",
    SQLTokenType.COMMENT: "class:sql_comment",
    SQLTokenType.FUNCTION: "class:sql_function",
    SQLTokenType.PUNCTUATION: "",  # No special styling
    SQLTokenType.WHITESPACE: "",  # Preserved as-is
    SQLTokenType.UNKNOWN: "",  # No special styling
}

# Token type to theme key mapping for Rich output
TOKEN_TYPE_TO_THEME_KEY: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "sql_keyword",
    SQLTokenType.IDENTIFIER: "sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "sql_identifier",
    SQLTokenType.STRING: "sql_string",
    SQLTokenType.NUMBER: "sql_number",
    SQLTokenType.OPERATOR: "sql_operator",
    SQLTokenType.COMMENT: "sql_comment",
    SQLTokenType.FUNCTION: "sql_function",
    SQLTokenType.PUNCTUATION: "",
    SQLTokenType.WHITESPACE: "",
    SQLTokenType.UNKNOWN: "",
}

# Module-level theme manager for Rich color lookups
_theme_manager: ThemeManager | None = None


def _get_theme_manager() -> ThemeManager:
    """Get or create the module-level ThemeManager singleton.

    Returns:
        ThemeManager instance for theme lookups.
    """
    from pgtail_py.theme import ThemeManager as TM

    global _theme_manager
    if _theme_manager is None:
        _theme_manager = TM()
    return _theme_manager


def _color_style_to_rich_markup(style: ColorStyle) -> str:
    """Convert ColorStyle to Rich markup tag content.

    Translates a ColorStyle dataclass into a string suitable for use
    inside Rich markup tags. Handles ANSI color prefix stripping for
    Rich compatibility.

    Args:
        style: ColorStyle with fg, bg, bold, dim, italic, underline.

    Returns:
        Rich markup tag content (e.g., "bold blue", "dim", "#268bd2").
        Empty string if no styling defined.

    Examples:
        >>> _color_style_to_rich_markup(ColorStyle(fg="blue", bold=True))
        "bold blue"
        >>> _color_style_to_rich_markup(ColorStyle(fg="#268bd2"))
        "#268bd2"
        >>> _color_style_to_rich_markup(ColorStyle(dim=True))
        "dim"
        >>> _color_style_to_rich_markup(ColorStyle())
        ""
    """
    parts: list[str] = []

    # Add modifiers
    if style.bold:
        parts.append("bold")
    if style.dim:
        parts.append("dim")
    if style.italic:
        parts.append("italic")
    if style.underline:
        parts.append("underline")

    # Add foreground color
    if style.fg:
        fg = style.fg
        # Strip "ansi" prefix for Rich compatibility
        if fg.startswith("ansibright"):
            fg = "bright_" + fg[10:]  # ansibrightred → bright_red
        elif fg.startswith("ansi"):
            fg = fg[4:]  # ansired → red
        parts.append(fg)

    # Add background color
    if style.bg:
        bg = style.bg
        if bg.startswith("ansibright"):
            bg = "bright_" + bg[10:]
        elif bg.startswith("ansi"):
            bg = bg[4:]
        parts.append(f"on {bg}")

    return " ".join(parts)


def highlight_sql_rich(sql: str, theme: Theme | None = None) -> str:
    """Convert SQL text to Rich console markup string.

    Tokenizes SQL and wraps each token in Rich markup tags using
    colors from the active theme. Brackets in SQL text are escaped
    to prevent Rich parsing errors.

    Args:
        sql: SQL text to highlight.
        theme: Theme for color lookup. If None, uses global ThemeManager.

    Returns:
        Rich markup string with styled tokens.
        If NO_COLOR is set, returns SQL with only bracket escaping.

    Examples:
        >>> highlight_sql_rich("SELECT id FROM users")
        "[bold blue]SELECT[/] [cyan]id[/] [bold blue]FROM[/] [cyan]users[/]"
        >>> highlight_sql_rich("SELECT arr[1]")
        "[bold blue]SELECT[/] [cyan]arr[/]\\[1]"
    """
    # Empty SQL returns empty string
    if not sql:
        return ""

    # Respect NO_COLOR environment variable
    if is_color_disabled():
        return sql.replace("[", "\\[")

    # Get theme for color lookup
    if theme is None:
        theme = _get_theme_manager().current_theme

    # Tokenize SQL
    tokens = SQLTokenizer().tokenize(sql)

    # Build Rich markup string
    parts: list[str] = []
    for token in tokens:
        # Escape brackets in token text to prevent Rich parsing errors
        escaped_text = token.text.replace("[", "\\[")

        # Get theme key for this token type
        theme_key = TOKEN_TYPE_TO_THEME_KEY.get(token.type, "")

        if theme_key and theme:
            # Get color style from theme
            style = theme.get_ui_style(theme_key)
            markup = _color_style_to_rich_markup(style)

            if markup:
                parts.append(f"[{markup}]{escaped_text}[/]")
            else:
                parts.append(escaped_text)
        else:
            parts.append(escaped_text)

    return "".join(parts)


class SQLHighlighter:
    """Converts tokenized SQL into styled FormattedText.

    Uses SQLTokenizer for tokenization and maps token types to theme styles.
    Respects NO_COLOR environment variable.
    """

    def __init__(self) -> None:
        """Initialize highlighter with tokenizer."""
        self._tokenizer = SQLTokenizer()

    def highlight(self, sql: str) -> FormattedText:
        """Tokenize and style SQL.

        Args:
            sql: SQL text to highlight.

        Returns:
            FormattedText with styled tokens.
            If NO_COLOR is set, returns unstyled FormattedText.
        """
        # Respect NO_COLOR environment variable
        if is_color_disabled():
            return FormattedText([("", sql)])

        tokens = self._tokenizer.tokenize(sql)
        return self.highlight_tokens(tokens)

    def highlight_tokens(self, tokens: list[SQLToken]) -> FormattedText:
        """Style pre-tokenized SQL.

        Args:
            tokens: List of SQLToken objects.

        Returns:
            FormattedText with styled tokens.
        """
        parts: list[tuple[str, str]] = []

        for token in tokens:
            style = TOKEN_TO_STYLE.get(token.type, "")
            parts.append((style, token.text))

        return FormattedText(parts)


# Module-level singleton for convenience
_highlighter: SQLHighlighter | None = None


def get_highlighter() -> SQLHighlighter:
    """Get the module-level SQLHighlighter singleton.

    Lazy initialization for performance.

    Returns:
        SQLHighlighter instance.
    """
    global _highlighter
    if _highlighter is None:
        _highlighter = SQLHighlighter()
    return _highlighter


def highlight_sql(sql: str) -> FormattedText:
    """Convenience function to highlight SQL text.

    Args:
        sql: SQL text to highlight.

    Returns:
        FormattedText with styled tokens.
    """
    return get_highlighter().highlight(sql)


# =============================================================================
# Module-level registration
# =============================================================================


def get_sql_highlighters() -> list[
    SQLParamHighlighter
    | SQLKeywordHighlighter
    | SQLStringHighlighter
    | SQLNumberHighlighter
    | SQLOperatorHighlighter
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
    # SQL Highlighter classes (new system)
    "SQLParamHighlighter",
    "SQLKeywordHighlighter",
    "SQLStringHighlighter",
    "SQLNumberHighlighter",
    "SQLOperatorHighlighter",
    # SQL Keywords
    "SQL_KEYWORDS",
    "SQL_KEYWORDS_DML",
    "SQL_KEYWORDS_DDL",
    "SQL_KEYWORDS_DCL",
    "SQL_KEYWORDS_TCL",
    "SQL_KEYWORDS_OTHER",
    # SQL Tokenizer (from sql_tokenizer.py)
    "SQLTokenType",
    "SQLToken",
    "SQLTokenizer",
    # SQL Detection (from sql_detector.py)
    "SQLDetectionResult",
    "detect_sql_content",
    # SQL Highlighter compatibility (from sql_highlighter.py)
    "SQLHighlighter",
    "highlight_sql",
    "highlight_sql_rich",
    "TOKEN_TO_STYLE",
    "TOKEN_TYPE_TO_THEME_KEY",
    "_get_theme_manager",  # Internal but used by tests
    "_color_style_to_rich_markup",  # Internal but used by tests
    # Context detection
    "detect_sql_context",
    "get_sql_highlighters",
]
