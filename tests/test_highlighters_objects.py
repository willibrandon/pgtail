"""Tests for object highlighters (T053).

Tests cover:
- IdentifierHighlighter: Double-quoted identifiers
- RelationHighlighter: Table/index names in context
- SchemaHighlighter: Schema-qualified names
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.objects import (
    IdentifierHighlighter,
    RelationHighlighter,
    SchemaHighlighter,
    get_object_highlighters,
)
from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_theme() -> Theme:
    """Create a test theme with highlight styles."""
    return Theme(
        name="test",
        description="Test theme",
        levels={},
        ui={
            "hl_identifier": ColorStyle(fg="cyan"),
            "hl_relation": ColorStyle(fg="cyan", bold=True),
            "hl_schema": ColorStyle(fg="cyan"),
        },
    )


# =============================================================================
# Test IdentifierHighlighter
# =============================================================================


class TestIdentifierHighlighter:
    """Tests for IdentifierHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = IdentifierHighlighter()
        assert h.name == "identifier"
        assert h.priority == 400
        assert "identifier" in h.description.lower()

    def test_simple_identifier(self, test_theme: Theme) -> None:
        """Should match simple double-quoted identifier."""
        h = IdentifierHighlighter()
        text = '"MyTable"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == '"MyTable"'
        assert matches[0].style == "hl_identifier"

    def test_identifier_with_spaces(self, test_theme: Theme) -> None:
        """Should match identifier with spaces."""
        h = IdentifierHighlighter()
        text = '"My Table Name"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == '"My Table Name"'

    def test_identifier_with_escaped_quotes(self, test_theme: Theme) -> None:
        """Should match identifier with escaped quotes."""
        h = IdentifierHighlighter()
        text = '"Say ""Hello"""'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_reserved_word_identifier(self, test_theme: Theme) -> None:
        """Should match reserved word used as identifier."""
        h = IdentifierHighlighter()
        text = '"select"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_multiple_identifiers(self, test_theme: Theme) -> None:
        """Should match multiple identifiers in text."""
        h = IdentifierHighlighter()
        text = 'SELECT "Column1", "Column2" FROM "MyTable"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 3


# =============================================================================
# Test RelationHighlighter
# =============================================================================


class TestRelationHighlighter:
    """Tests for RelationHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = RelationHighlighter()
        assert h.name == "relation"
        assert h.priority == 410
        assert "relation" in h.description.lower() or "table" in h.description.lower()

    def test_relation_keyword(self, test_theme: Theme) -> None:
        """Should match relation keyword context."""
        h = RelationHighlighter()
        text = 'relation "users"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "users"
        assert matches[0].style == "hl_relation"

    def test_table_keyword(self, test_theme: Theme) -> None:
        """Should match table keyword context."""
        h = RelationHighlighter()
        text = 'table "orders"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "orders"

    def test_index_keyword(self, test_theme: Theme) -> None:
        """Should match index keyword context."""
        h = RelationHighlighter()
        text = "index idx_users_email"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_sequence_keyword(self, test_theme: Theme) -> None:
        """Should match sequence keyword context."""
        h = RelationHighlighter()
        text = "sequence users_id_seq"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_constraint_keyword(self, test_theme: Theme) -> None:
        """Should match constraint keyword context."""
        h = RelationHighlighter()
        text = "constraint fk_user_id"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test SchemaHighlighter
# =============================================================================


class TestSchemaHighlighter:
    """Tests for SchemaHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SchemaHighlighter()
        assert h.name == "schema"
        assert h.priority == 420
        assert "schema" in h.description.lower()

    def test_public_schema(self, test_theme: Theme) -> None:
        """Should match public schema prefix."""
        h = SchemaHighlighter()
        text = "public.users"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "public.users"
        assert matches[0].style == "hl_schema"

    def test_pg_catalog_schema(self, test_theme: Theme) -> None:
        """Should match pg_catalog schema prefix."""
        h = SchemaHighlighter()
        text = "pg_catalog.pg_class"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_custom_schema(self, test_theme: Theme) -> None:
        """Should match custom schema prefix."""
        h = SchemaHighlighter()
        text = "myschema.mytable"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_quoted_object(self, test_theme: Theme) -> None:
        """Should match schema with quoted object name."""
        h = SchemaHighlighter()
        text = 'public."MyTable"'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_multiple_schema_qualified(self, test_theme: Theme) -> None:
        """Should match multiple schema-qualified names."""
        h = SchemaHighlighter()
        text = "SELECT public.users, myschema.orders"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_object_highlighters(self) -> None:
        """get_object_highlighters should return all highlighters."""
        highlighters = get_object_highlighters()

        assert len(highlighters) == 3
        names = {h.name for h in highlighters}
        assert names == {"identifier", "relation", "schema"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 400-499 range."""
        highlighters = get_object_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(400 <= p < 500 for p in priorities)
