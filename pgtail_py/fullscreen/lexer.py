"""Pygments lexer for PostgreSQL log lines with SQL syntax highlighting.

This lexer is used with prompt_toolkit's PygmentsLexer wrapper to provide
both syntax highlighting AND navigation support in the fullscreen TextArea.
"""

from __future__ import annotations

from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import (
    Comment,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
)

# Custom token types for log levels
# These will be styled via prompt_toolkit styles
LogLevel = Token.LogLevel
LogLevel.Error = Token.LogLevel.Error
LogLevel.Fatal = Token.LogLevel.Fatal
LogLevel.Panic = Token.LogLevel.Panic
LogLevel.Warning = Token.LogLevel.Warning
LogLevel.Log = Token.LogLevel.Log
LogLevel.Info = Token.LogLevel.Info
LogLevel.Debug = Token.LogLevel.Debug

# SQL keywords (same as sql_tokenizer.py)
SQL_KEYWORDS = {
    # DML
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
    # DDL
    "CREATE",
    "ALTER",
    "DROP",
    "TABLE",
    "INDEX",
    "VIEW",
    "TRIGGER",
    "FUNCTION",
    "PROCEDURE",
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
    # Logical operators
    "AND",
    "OR",
    "NOT",
    "IN",
    "EXISTS",
    "BETWEEN",
    "LIKE",
    "IS",
    "NULL",
    # Set operations
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "DISTINCT",
    "ALL",
    "ANY",
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
    # Other
    "CAST",
    "COALESCE",
    "NULLIF",
    "RETURNS",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "GRANT",
    "REVOKE",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "REFERENCES",
    "CONSTRAINT",
    "DEFAULT",
    "CHECK",
    "UNIQUE",
    "TRUE",
    "FALSE",
}


def _make_keyword_pattern() -> str:
    """Create regex pattern for SQL keywords (case-insensitive)."""
    # Sort by length descending to match longer keywords first
    sorted_keywords = sorted(SQL_KEYWORDS, key=len, reverse=True)
    pattern = r"\b(" + "|".join(sorted_keywords) + r")\b"
    return pattern


class LogLineLexer(RegexLexer):
    """Pygments lexer for PostgreSQL log lines with SQL highlighting.

    Handles log line structure:
    - Timestamp: HH:MM:SS.mmm
    - PID: [12345]
    - Level: ERROR, WARNING, LOG, etc.
    - SQL state: 42P01 (optional)
    - Message: may contain SQL statements

    SQL syntax highlighting within messages:
    - Keywords: SELECT, FROM, WHERE, etc.
    - Strings: 'value', $$dollar$$
    - Numbers: 42, 3.14
    - Operators: =, <>, ||, ::
    - Comments: -- line, /* block */
    """

    name = "PostgreSQL Log"
    aliases = ["pglog"]
    filenames = []

    # Flags for case-insensitive SQL keyword matching
    flags = 0  # We'll handle case-insensitivity in patterns

    tokens = {
        "root": [
            # Full log line pattern with timestamp, PID, level
            # Example: 10:23:45.123 [12345] ERROR 42P01: message
            (
                r"(\d{2}:\d{2}:\d{2}\.\d{3})"  # Timestamp
                r"(\s+)"
                r"(\[\d+\])"  # PID
                r"(\s+)"
                r"(PANIC|FATAL|ERROR|WARNING|LOG|INFO|DEBUG[0-5]?|NOTICE|STATEMENT)"  # Level
                r"(\s+)"
                r"([A-Z0-9]{5})?"  # SQL state (optional)
                r"(:?\s*)",  # Colon separator
                bygroups(
                    Comment,  # Timestamp
                    Text,  # Space
                    Number,  # PID
                    Text,  # Space
                    Generic.Error,  # Level (will be restyled)
                    Text,  # Space
                    Name.Label,  # SQL state
                    Text,  # Colon/space
                ),
                "message",
            ),
            # Lines without full prefix - just parse as message
            (r"", Text, "message"),
        ],
        "message": [
            # Include SQL patterns for message content
            include("sql"),
            # Newline returns to root state
            (r"\n", Text, "#pop"),
            # Single character fallback (not greedy - allows SQL patterns to match)
            (r".", Text),
        ],
        "sql": [
            # Whitespace
            (r"\s+", Text),
            # Block comments /* ... */
            (r"/\*", Comment.Multiline, "block_comment"),
            # Line comments --
            (r"--[^\n]*", Comment.Single),
            # Dollar-quoted strings $$...$$ or $tag$...$tag$
            (r"\$\$", String, "dollar_string_empty"),
            (r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$", String, "dollar_string_tag"),
            # Single-quoted strings
            (r"'", String.Single, "string"),
            # Double-quoted identifiers
            (r'"', Name.Variable, "quoted_identifier"),
            # Numbers (integers and decimals)
            (r"\d+(?:\.\d+)?", Number),
            # SQL keywords (case-insensitive, non-capturing group)
            (
                r"(?i)\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TABLE|INDEX|"
                r"VIEW|TRIGGER|FUNCTION|PROCEDURE|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|"
                r"OUTER|ON|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|INTO|VALUES|SET|"
                r"AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|UNION|INTERSECT|EXCEPT|"
                r"DISTINCT|ALL|ANY|CASE|WHEN|THEN|ELSE|END|WITH|RECURSIVE|OVER|"
                r"PARTITION|WINDOW|CROSS|FULL|NATURAL|USING|LATERAL|ASC|DESC|NULLS|"
                r"FIRST|LAST|CAST|COALESCE|NULLIF|RETURNS|BEGIN|COMMIT|ROLLBACK|"
                r"GRANT|REVOKE|PRIMARY|KEY|FOREIGN|REFERENCES|CONSTRAINT|DEFAULT|"
                r"CHECK|UNIQUE|TRUE|FALSE)\b",
                Keyword,
            ),
            # Function names (identifier followed by parenthesis)
            (r"\b([a-zA-Z_][a-zA-Z0-9_]*)(\()", bygroups(Name.Function, Punctuation)),
            # Multi-character operators
            (r"<>|!=|<=|>=|\|\||::", Operator),
            # Single-character operators
            (r"[=<>+\-*/%!|&^~]", Operator),
            # Punctuation
            (r"[(),;.\[\]]", Punctuation),
            # Identifiers (words that aren't keywords)
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
        ],
        "block_comment": [
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[^*]+", Comment.Multiline),
            (r"\*", Comment.Multiline),
        ],
        "string": [
            (r"''", String.Single),  # Escaped quote
            (r"'", String.Single, "#pop"),
            (r"[^']+", String.Single),
        ],
        "quoted_identifier": [
            (r'""', Name.Variable),  # Escaped quote
            (r'"', Name.Variable, "#pop"),
            (r'[^"]+', Name.Variable),
        ],
        "dollar_string_empty": [
            (r"\$\$", String, "#pop"),
            (r"[^$]+", String),
            (r"\$", String),
        ],
        "dollar_string_tag": [
            # This state handles $tag$...$tag$ - the tag is captured in group 1
            # Pygments handles this by popping when the closing tag is found
            (r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$", String, "#pop"),
            (r"[^$]+", String),
            (r"\$", String),
        ],
    }
