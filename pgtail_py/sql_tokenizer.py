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


# SQL keywords - 45+ keywords from FR-002 specification
# Covers DML, DDL, clauses, logical operators, set operations, etc.
SQL_KEYWORDS: frozenset[str] = frozenset(
    {
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
)


# Compiled regex patterns for tokenization
# Order matters: more specific patterns first

# Whitespace pattern
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Keyword/identifier pattern (word characters)
_WORD_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


class SQLTokenizer:
    """Tokenizes SQL text into a sequence of SQLToken objects.

    Stateless class that can be reused for multiple tokenization calls.
    Regex patterns are compiled at class level for performance.
    """

    def tokenize(self, sql: str) -> list[SQLToken]:
        """Parse SQL string into tokens.

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
            # Try whitespace
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

            # Try word (keyword or identifier)
            match = _WORD_PATTERN.match(sql, pos)
            if match:
                word = match.group()
                # Check if it's a keyword (case-insensitive)
                if word.upper() in SQL_KEYWORDS:
                    token_type = SQLTokenType.KEYWORD
                else:
                    token_type = SQLTokenType.IDENTIFIER

                tokens.append(
                    SQLToken(
                        type=token_type,
                        text=word,
                        start=pos,
                        end=match.end(),
                    )
                )
                pos = match.end()
                continue

            # Unknown character - consume one character
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
