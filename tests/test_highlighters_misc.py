"""Tests for misc highlighters (T086).

Tests cover:
- BooleanHighlighter: Boolean values on/off, true/false, yes/no
- NullHighlighter: NULL keyword
- OIDHighlighter: Object IDs
- PathHighlighter: Unix file paths
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.misc import (
    BooleanHighlighter,
    NullHighlighter,
    OIDHighlighter,
    PathHighlighter,
    get_misc_highlighters,
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
            "hl_bool_true": ColorStyle(fg="green"),
            "hl_bool_false": ColorStyle(fg="red"),
            "hl_null": ColorStyle(fg="gray", italic=True),
            "hl_oid": ColorStyle(fg="cyan"),
            "hl_path": ColorStyle(fg="blue", underline=True),
        },
    )


# =============================================================================
# Test BooleanHighlighter
# =============================================================================


class TestBooleanHighlighter:
    """Tests for BooleanHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = BooleanHighlighter()
        assert h.name == "boolean"
        assert h.priority == 1000
        assert "boolean" in h.description.lower()

    def test_on_value(self, test_theme: Theme) -> None:
        """Should match 'on' as true value."""
        h = BooleanHighlighter()
        text = "logging_collector = on"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "on"
        assert matches[0].style == "hl_bool_true"

    def test_off_value(self, test_theme: Theme) -> None:
        """Should match 'off' as false value."""
        h = BooleanHighlighter()
        text = "ssl = off"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "off"
        assert matches[0].style == "hl_bool_false"

    def test_true_value(self, test_theme: Theme) -> None:
        """Should match 'true' as true value."""
        h = BooleanHighlighter()
        text = "enabled = true"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "true"
        assert matches[0].style == "hl_bool_true"

    def test_false_value(self, test_theme: Theme) -> None:
        """Should match 'false' as false value."""
        h = BooleanHighlighter()
        text = "enabled = false"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "false"
        assert matches[0].style == "hl_bool_false"

    def test_yes_value(self, test_theme: Theme) -> None:
        """Should match 'yes' as true value."""
        h = BooleanHighlighter()
        text = "archive_mode = yes"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_bool_true"

    def test_no_value(self, test_theme: Theme) -> None:
        """Should match 'no' as false value."""
        h = BooleanHighlighter()
        text = "archive_mode = no"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_bool_false"

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = BooleanHighlighter()
        text = "enabled = TRUE"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_bool_true"

    def test_multiple_booleans(self, test_theme: Theme) -> None:
        """Should match multiple boolean values."""
        h = BooleanHighlighter()
        text = "ssl = on, archive = off, debug = true"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 3


# =============================================================================
# Test NullHighlighter
# =============================================================================


class TestNullHighlighter:
    """Tests for NullHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = NullHighlighter()
        assert h.name == "null"
        assert h.priority == 1010
        assert "null" in h.description.lower()

    def test_null_keyword(self, test_theme: Theme) -> None:
        """Should match NULL keyword."""
        h = NullHighlighter()
        text = "WHERE value IS NULL"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "NULL"
        assert matches[0].style == "hl_null"

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = NullHighlighter()
        text = "value is null"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_multiple_nulls(self, test_theme: Theme) -> None:
        """Should match multiple NULL keywords."""
        h = NullHighlighter()
        text = "WHERE a IS NULL AND b IS NULL"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2

    def test_no_match_in_word(self, test_theme: Theme) -> None:
        """Should not match NULL within other words."""
        h = NullHighlighter()
        text = "NULLIFY the result"
        matches = h.find_matches(text, test_theme)

        # Should not match NULLIFY
        assert len(matches) == 0


# =============================================================================
# Test OIDHighlighter
# =============================================================================


class TestOIDHighlighter:
    """Tests for OIDHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = OIDHighlighter()
        assert h.name == "oid"
        assert h.priority == 1020
        assert "oid" in h.description.lower()

    def test_oid_keyword(self, test_theme: Theme) -> None:
        """Should match OID with number."""
        h = OIDHighlighter()
        text = "OID 16384"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert "OID" in matches[0].text
        assert "16384" in matches[0].text
        assert matches[0].style == "hl_oid"

    def test_oid_equals(self, test_theme: Theme) -> None:
        """Should match oid=number format."""
        h = OIDHighlighter()
        text = "relation oid=12345"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_regclass(self, test_theme: Theme) -> None:
        """Should match regclass with number."""
        h = OIDHighlighter()
        text = "regclass 16384"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_regtype(self, test_theme: Theme) -> None:
        """Should match regtype with number."""
        h = OIDHighlighter()
        text = "regtype 23"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_regproc(self, test_theme: Theme) -> None:
        """Should match regproc with number."""
        h = OIDHighlighter()
        text = "regproc 2200"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = OIDHighlighter()
        text = "oid 12345"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test PathHighlighter
# =============================================================================


class TestPathHighlighter:
    """Tests for PathHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = PathHighlighter()
        assert h.name == "path"
        assert h.priority == 1030
        assert "path" in h.description.lower()

    def test_postgresql_data_path(self, test_theme: Theme) -> None:
        """Should match PostgreSQL data directory path."""
        h = PathHighlighter()
        text = "data directory: /var/lib/postgresql/data"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert "/var/lib/postgresql/data" in matches[0].text
        assert matches[0].style == "hl_path"

    def test_pg_wal_path(self, test_theme: Theme) -> None:
        """Should match pg_wal path."""
        h = PathHighlighter()
        text = "writing to /pg_wal/000000010000000000000001"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_tmp_path(self, test_theme: Theme) -> None:
        """Should match tmp directory path."""
        h = PathHighlighter()
        text = "temp file: /tmp/pg_stat_tmp/pgstat.stat"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_usr_path(self, test_theme: Theme) -> None:
        """Should match /usr path."""
        h = PathHighlighter()
        text = "using /usr/local/pgsql/bin/postgres"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_multiple_paths(self, test_theme: Theme) -> None:
        """Should match multiple paths in text."""
        h = PathHighlighter()
        text = "copy from /data/input.csv to /data/output.csv"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_misc_highlighters(self) -> None:
        """get_misc_highlighters should return all highlighters."""
        highlighters = get_misc_highlighters()

        assert len(highlighters) == 4
        names = {h.name for h in highlighters}
        assert names == {"boolean", "null", "oid", "path"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 1000+ range."""
        highlighters = get_misc_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(p >= 1000 for p in priorities)
