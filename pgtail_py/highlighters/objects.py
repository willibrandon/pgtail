"""Object highlighters for PostgreSQL log output.

Highlighters in this module:
- IdentifierHighlighter: Double-quoted identifiers (priority 400)
- RelationHighlighter: Table/index names in context (priority 410)
- SchemaHighlighter: Schema-qualified names (priority 420)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# IdentifierHighlighter
# =============================================================================


class IdentifierHighlighter(RegexHighlighter):
    """Highlights double-quoted identifiers.

    PostgreSQL uses double quotes for identifiers that:
    - Contain special characters
    - Are reserved keywords
    - Need case preservation

    Example: "MyTable", "column-name", "select"
    """

    # Pattern: Double-quoted string (with escaped quotes handled)
    # Matches: "identifier", "with""quotes"
    PATTERN = r'"(?:[^"\\]|""|\\.)*"'

    def __init__(self) -> None:
        """Initialize identifier highlighter."""
        super().__init__(
            name="identifier",
            priority=400,
            pattern=self.PATTERN,
            style="hl_identifier",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return 'Double-quoted identifiers ("table_name")'


# =============================================================================
# RelationHighlighter
# =============================================================================


class RelationHighlighter(RegexHighlighter):
    """Highlights relation names in PostgreSQL log contexts.

    Matches table/index/sequence names when preceded by keywords:
    - relation "users"
    - table "orders"
    - index "idx_name"
    - sequence "seq_id"
    - constraint "fk_user"
    """

    # Pattern: keyword followed by quoted or unquoted identifier
    PATTERN = r'\b(relation|table|index|sequence|constraint|view|materialized view|foreign table)\s+"?([a-zA-Z_][a-zA-Z0-9_]*)"?'

    def __init__(self) -> None:
        """Initialize relation highlighter."""
        super().__init__(
            name="relation",
            priority=410,
            pattern=self.PATTERN,
            style="hl_relation",
            flags=re.IGNORECASE,
        )
        # Compiled pattern for extracting the relation name
        self._extract_pattern = re.compile(self.PATTERN, re.IGNORECASE)

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Table/index/sequence names (relation X, table Y)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all relation name matches.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects for relation names only (not the keyword).
        """
        matches: list[Match] = []

        for m in self._extract_pattern.finditer(text):
            # Get the relation name (group 2)
            name_start = m.start(2)
            name_end = m.end(2)

            if name_start != -1 and name_end != -1:
                matches.append(
                    Match(
                        start=name_start,
                        end=name_end,
                        style=self._style,
                        text=m.group(2),
                    )
                )

        return matches


# =============================================================================
# SchemaHighlighter
# =============================================================================


class SchemaHighlighter(RegexHighlighter):
    """Highlights schema-qualified names.

    Matches patterns like:
    - public.users
    - pg_catalog.pg_class
    - myschema.mytable

    Does NOT match:
    - Single identifiers (handled by other highlighters)
    - IP addresses (handled by IPHighlighter)
    """

    # Pattern: schema.object or schema."object"
    # Must not start with digit to avoid matching version numbers
    # Note: No trailing \b as quoted identifiers end with " which is not a word char
    PATTERN = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.(?:"[^"]+"|[a-zA-Z_][a-zA-Z0-9_]*)'

    def __init__(self) -> None:
        """Initialize schema highlighter."""
        super().__init__(
            name="schema",
            priority=420,
            pattern=self.PATTERN,
            style="hl_schema",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Schema-qualified names (schema.table)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_object_highlighters() -> list[
    IdentifierHighlighter | RelationHighlighter | SchemaHighlighter
]:
    """Return all object highlighters for registration.

    Returns:
        List of object highlighter instances.
    """
    return [
        IdentifierHighlighter(),
        RelationHighlighter(),
        SchemaHighlighter(),
    ]


__all__ = [
    "IdentifierHighlighter",
    "RelationHighlighter",
    "SchemaHighlighter",
    "get_object_highlighters",
]
