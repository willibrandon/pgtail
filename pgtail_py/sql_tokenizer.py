"""SQL tokenizer for syntax highlighting.

Provides SQLTokenType enum and SQLToken dataclass for categorizing SQL text,
plus SQLTokenizer class for parsing SQL into tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


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


# SQL keywords - comprehensive list for PostgreSQL syntax highlighting.
# Covers DML, DDL, clauses, logical operators, set operations, utility commands, etc.
SQL_KEYWORDS: frozenset[str] = frozenset(
    {
        # DML
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
        # DDL - Basic
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
        # DDL - Object types
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
        # Transaction control
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "START",
        "TRANSACTION",
        "WORK",
        "ISOLATION",
        "LEVEL",
        "SERIALIZABLE",
        "REPEATABLE",
        "READ",
        "COMMITTED",
        "UNCOMMITTED",
        # Access control
        "GRANT",
        "REVOKE",
        "PRIVILEGES",
        "USAGE",
        "CONNECT",
        "TEMPORARY",
        "TEMP",
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


# Compiled regex patterns for tokenization
# Order matters per research.md: comments → strings → numbers → keywords → functions → operators → identifiers

# Whitespace pattern
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Comment patterns (must match before operators containing - or /)
_BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)  # /* ... */
_LINE_COMMENT_PATTERN = re.compile(r"--[^\n]*")  # -- to end of line

# String patterns (must match before other patterns that could match inside strings)
# Dollar-quoted strings: $$...$$ or $tag$...$tag$
# Use a function-based approach since regex backreferences don't handle empty groups well
_DOLLAR_EMPTY_STRING_PATTERN = re.compile(r"\$\$.*?\$\$", re.DOTALL)  # $$...$$
_DOLLAR_TAG_STRING_PATTERN = re.compile(
    r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$.*?\$\1\$", re.DOTALL
)  # $tag$...$tag$
# Single-quoted strings with '' escape handling
_SINGLE_STRING_PATTERN = re.compile(r"'(?:[^']|'')*'")

# Quoted identifier pattern: "..." with "" for escaped quotes
# Matches: "MyTable", "My Table", "Say ""Hello"""
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

        Token matching order per research.md:
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
