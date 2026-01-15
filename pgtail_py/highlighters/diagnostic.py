"""Diagnostic highlighters for PostgreSQL log output.

Highlighters in this module:
- SQLStateHighlighter: 5-character SQLSTATE codes with class-based coloring (priority 200)
- ErrorNameHighlighter: PostgreSQL error names like unique_violation (priority 210)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.highlighter import KeywordHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# SQLStateHighlighter
# =============================================================================


class SQLStateHighlighter(RegexHighlighter):
    """Highlights SQLSTATE codes with class-based coloring.

    SQLSTATE codes are 5-character codes where the first two characters
    indicate the class:
    - 00xxx: Success (green)
    - 01xxx: Warning (yellow)
    - 02xxx: No data (yellow)
    - Other: Error (red)
    - XX/YY/ZZ prefixes: Internal error (bold red)
    """

    # Pattern: 5 alphanumeric characters, typically appearing after "SQLSTATE"
    # or in specific contexts
    PATTERN = r"\b([0-9A-Z]{5})\b"

    # SQLSTATE class prefixes and their severity
    SUCCESS_CLASSES = {"00"}
    WARNING_CLASSES = {"01", "02"}
    INTERNAL_CLASSES = {"XX", "YY", "ZZ", "P0", "F0"}

    def __init__(self) -> None:
        """Initialize SQLSTATE highlighter."""
        super().__init__(
            name="sqlstate",
            priority=200,
            pattern=self.PATTERN,
            style="hl_sqlstate_error",  # Default, overridden in find_matches
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "SQLSTATE error codes with class-based coloring"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all SQLSTATE code matches with appropriate styling.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects with severity-based styles.
        """
        matches: list[Match] = []

        for m in self._pattern.finditer(text):
            code = m.group(1)
            class_prefix = code[:2]

            # Determine style based on SQLSTATE class
            if class_prefix in self.SUCCESS_CLASSES:
                style = "hl_sqlstate_success"
            elif class_prefix in self.WARNING_CLASSES:
                style = "hl_sqlstate_warning"
            elif class_prefix in self.INTERNAL_CLASSES:
                style = "hl_sqlstate_internal"
            else:
                style = "hl_sqlstate_error"

            matches.append(
                Match(
                    start=m.start(1),
                    end=m.end(1),
                    style=style,
                    text=code,
                )
            )

        return matches


# =============================================================================
# ErrorNameHighlighter
# =============================================================================


class ErrorNameHighlighter(KeywordHighlighter):
    """Highlights PostgreSQL error names.

    Uses Aho-Corasick for efficient multi-keyword matching of common
    PostgreSQL error condition names.
    """

    # Common PostgreSQL error condition names
    # These appear in log messages and can help identify error types quickly
    ERROR_NAMES = {
        # Integrity constraint violations (Class 23)
        "unique_violation": "hl_error_name",
        "foreign_key_violation": "hl_error_name",
        "not_null_violation": "hl_error_name",
        "check_violation": "hl_error_name",
        "exclusion_violation": "hl_error_name",
        "restrict_violation": "hl_error_name",
        # Serialization/concurrency (Class 40)
        "deadlock_detected": "hl_error_name",
        "serialization_failure": "hl_error_name",
        "lock_not_available": "hl_error_name",
        # Data errors (Class 22)
        "data_exception": "hl_error_name",
        "division_by_zero": "hl_error_name",
        "invalid_text_representation": "hl_error_name",
        "numeric_value_out_of_range": "hl_error_name",
        "string_data_right_truncation": "hl_error_name",
        "datetime_field_overflow": "hl_error_name",
        # Insufficient resources (Class 53)
        "insufficient_resources": "hl_error_name",
        "disk_full": "hl_error_name",
        "out_of_memory": "hl_error_name",
        "too_many_connections": "hl_error_name",
        # Program limit exceeded (Class 54)
        "statement_too_complex": "hl_error_name",
        "too_many_columns": "hl_error_name",
        "too_many_arguments": "hl_error_name",
        # Object not found/exists (Class 42)
        "undefined_table": "hl_error_name",
        "undefined_column": "hl_error_name",
        "undefined_function": "hl_error_name",
        "undefined_object": "hl_error_name",
        "duplicate_table": "hl_error_name",
        "duplicate_column": "hl_error_name",
        "duplicate_object": "hl_error_name",
        "duplicate_database": "hl_error_name",
        "duplicate_schema": "hl_error_name",
        "ambiguous_column": "hl_error_name",
        "ambiguous_function": "hl_error_name",
        # Syntax errors (Class 42)
        "syntax_error": "hl_error_name",
        # Connection errors (Class 08)
        "connection_exception": "hl_error_name",
        "connection_failure": "hl_error_name",
        "protocol_violation": "hl_error_name",
        # Transaction errors (Class 25)
        "invalid_transaction_state": "hl_error_name",
        "read_only_sql_transaction": "hl_error_name",
        "no_active_sql_transaction": "hl_error_name",
        # System errors (Class 58)
        "system_error": "hl_error_name",
        "io_error": "hl_error_name",
        # Configuration errors (Class F0)
        "config_file_error": "hl_error_name",
        # Operator intervention (Class 57)
        "query_canceled": "hl_error_name",
        "admin_shutdown": "hl_error_name",
        "crash_shutdown": "hl_error_name",
        "cannot_connect_now": "hl_error_name",
        # PL/pgSQL errors
        "raise_exception": "hl_error_name",
        "no_data_found": "hl_error_name",
        "too_many_rows": "hl_error_name",
    }

    def __init__(self) -> None:
        """Initialize error name highlighter."""
        super().__init__(
            name="error_name",
            priority=210,
            keywords=self.ERROR_NAMES,
            case_sensitive=False,
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return f"PostgreSQL error names ({len(self.ERROR_NAMES)} patterns)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_diagnostic_highlighters() -> list[SQLStateHighlighter | ErrorNameHighlighter]:
    """Return all diagnostic highlighters for registration.

    Returns:
        List of diagnostic highlighter instances.
    """
    return [
        SQLStateHighlighter(),
        ErrorNameHighlighter(),
    ]


__all__ = [
    "SQLStateHighlighter",
    "ErrorNameHighlighter",
    "get_diagnostic_highlighters",
]
