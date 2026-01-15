"""Tests for SQL highlighters (T072).

Tests cover:
- SQLParamHighlighter: Query parameters ($1, $2, etc.)
- SQLKeywordHighlighter: SQL keywords via Aho-Corasick
- SQLStringHighlighter: String literals
- SQLNumberHighlighter: Numeric literals
- SQLOperatorHighlighter: SQL operators
- SQL context detection
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.sql import (
    SQL_KEYWORDS_DDL,
    SQL_KEYWORDS_DML,
    SQL_KEYWORDS_OTHER,
    SQL_KEYWORDS_TCL,
    SQLKeywordHighlighter,
    SQLNumberHighlighter,
    SQLOperatorHighlighter,
    SQLParamHighlighter,
    SQLStringHighlighter,
    detect_sql_context,
    get_sql_highlighters,
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
            "hl_param": ColorStyle(fg="magenta"),
            "sql_keyword": ColorStyle(fg="blue", bold=True),
            "sql_string": ColorStyle(fg="green"),
            "sql_number": ColorStyle(fg="magenta"),
            "sql_operator": ColorStyle(fg="yellow"),
        },
    )


# =============================================================================
# Test SQLParamHighlighter
# =============================================================================


class TestSQLParamHighlighter:
    """Tests for SQLParamHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLParamHighlighter()
        assert h.name == "sql_param"
        assert h.priority == 700
        assert "parameter" in h.description.lower()

    def test_single_param(self, test_theme: Theme) -> None:
        """Should match single parameter."""
        h = SQLParamHighlighter()
        text = "SELECT * FROM users WHERE id = $1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "$1"
        assert matches[0].style == "hl_param"

    def test_multiple_params(self, test_theme: Theme) -> None:
        """Should match multiple parameters."""
        h = SQLParamHighlighter()
        text = "INSERT INTO users (name, email) VALUES ($1, $2)"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2
        texts = {m.text for m in matches}
        assert texts == {"$1", "$2"}

    def test_high_numbered_param(self, test_theme: Theme) -> None:
        """Should match high-numbered parameters."""
        h = SQLParamHighlighter()
        text = "WHERE col1 = $123"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "$123"


# =============================================================================
# Test SQLKeywordHighlighter
# =============================================================================


class TestSQLKeywordHighlighter:
    """Tests for SQLKeywordHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLKeywordHighlighter()
        assert h.name == "sql_keyword"
        assert h.priority == 710
        assert "keyword" in h.description.lower()

    def test_dml_keyword(self, test_theme: Theme) -> None:
        """Should match DML keywords."""
        h = SQLKeywordHighlighter()
        text = "SELECT * FROM users"
        matches = h.find_matches(text, test_theme)

        keywords = {m.text.upper() for m in matches}
        assert "SELECT" in keywords
        assert "FROM" in keywords

    def test_ddl_keyword(self, test_theme: Theme) -> None:
        """Should match DDL keywords."""
        h = SQLKeywordHighlighter()
        text = "CREATE TABLE users"
        matches = h.find_matches(text, test_theme)

        keywords = {m.text.upper() for m in matches}
        assert "CREATE" in keywords
        assert "TABLE" in keywords

    def test_tcl_keyword(self, test_theme: Theme) -> None:
        """Should match TCL keywords."""
        h = SQLKeywordHighlighter()
        text = "BEGIN TRANSACTION"
        matches = h.find_matches(text, test_theme)

        keywords = {m.text.upper() for m in matches}
        assert "BEGIN" in keywords
        assert "TRANSACTION" in keywords

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = SQLKeywordHighlighter()
        text = "select * from users"
        matches = h.find_matches(text, test_theme)

        keywords = {m.text.upper() for m in matches}
        assert "SELECT" in keywords
        assert "FROM" in keywords

    def test_keyword_count(self) -> None:
        """Should have at least 100 keywords."""
        total = (
            len(SQL_KEYWORDS_DML) + len(SQL_KEYWORDS_DDL) +
            len(SQL_KEYWORDS_TCL) + len(SQL_KEYWORDS_OTHER)
        )
        assert total >= 100


# =============================================================================
# Test SQLStringHighlighter
# =============================================================================


class TestSQLStringHighlighter:
    """Tests for SQLStringHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLStringHighlighter()
        assert h.name == "sql_string"
        assert h.priority == 720
        assert "string" in h.description.lower()

    def test_single_quoted_string(self, test_theme: Theme) -> None:
        """Should match single-quoted strings."""
        h = SQLStringHighlighter()
        text = "WHERE name = 'John'"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "'John'"
        assert matches[0].style == "sql_string"

    def test_escaped_quotes(self, test_theme: Theme) -> None:
        """Should match strings with escaped quotes."""
        h = SQLStringHighlighter()
        text = "SELECT 'it''s a test'"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "'it''s a test'"

    def test_dollar_quoted_string(self, test_theme: Theme) -> None:
        """Should match dollar-quoted strings."""
        h = SQLStringHighlighter()
        text = "SELECT $$hello world$$"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "$$hello world$$"

    def test_tagged_dollar_quote(self, test_theme: Theme) -> None:
        """Should match tagged dollar-quoted strings."""
        h = SQLStringHighlighter()
        text = "CREATE FUNCTION $func$body$func$"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test SQLNumberHighlighter
# =============================================================================


class TestSQLNumberHighlighter:
    """Tests for SQLNumberHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLNumberHighlighter()
        assert h.name == "sql_number"
        assert h.priority == 730
        assert "numeric" in h.description.lower()

    def test_integer(self, test_theme: Theme) -> None:
        """Should match integers."""
        h = SQLNumberHighlighter()
        text = "WHERE id = 42"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "42"
        assert matches[0].style == "sql_number"

    def test_decimal(self, test_theme: Theme) -> None:
        """Should match decimals."""
        h = SQLNumberHighlighter()
        text = "SET price = 3.14"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "3.14"

    def test_scientific_notation(self, test_theme: Theme) -> None:
        """Should match scientific notation."""
        h = SQLNumberHighlighter()
        text = "WHERE val > 1.23e10"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "1.23e10"

    def test_hex_number(self, test_theme: Theme) -> None:
        """Should match hex numbers."""
        h = SQLNumberHighlighter()
        text = "WHERE flags = 0x1A2B"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "0x1A2B"


# =============================================================================
# Test SQLOperatorHighlighter
# =============================================================================


class TestSQLOperatorHighlighter:
    """Tests for SQLOperatorHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLOperatorHighlighter()
        assert h.name == "sql_operator"
        assert h.priority == 740
        assert "operator" in h.description.lower()

    def test_equals(self, test_theme: Theme) -> None:
        """Should match equals operator."""
        h = SQLOperatorHighlighter()
        text = "WHERE id = 1"
        matches = h.find_matches(text, test_theme)

        assert any(m.text == "=" for m in matches)

    def test_not_equals(self, test_theme: Theme) -> None:
        """Should match not equals operators."""
        h = SQLOperatorHighlighter()
        text = "WHERE id <> 1 AND val != 2"
        matches = h.find_matches(text, test_theme)

        texts = {m.text for m in matches}
        assert "<>" in texts
        assert "!=" in texts

    def test_comparison_operators(self, test_theme: Theme) -> None:
        """Should match comparison operators."""
        h = SQLOperatorHighlighter()
        text = "WHERE a <= b AND c >= d"
        matches = h.find_matches(text, test_theme)

        texts = {m.text for m in matches}
        assert "<=" in texts
        assert ">=" in texts

    def test_concat_operator(self, test_theme: Theme) -> None:
        """Should match concatenation operator."""
        h = SQLOperatorHighlighter()
        text = "SELECT 'a' || 'b'"
        matches = h.find_matches(text, test_theme)

        assert any(m.text == "||" for m in matches)

    def test_typecast_operator(self, test_theme: Theme) -> None:
        """Should match type cast operator."""
        h = SQLOperatorHighlighter()
        text = "SELECT 42::text"
        matches = h.find_matches(text, test_theme)

        assert any(m.text == "::" for m in matches)


# =============================================================================
# Test SQL Context Detection
# =============================================================================


class TestSQLContextDetection:
    """Tests for SQL context detection."""

    def test_statement_prefix(self) -> None:
        """Should detect statement: prefix."""
        text = "statement: SELECT * FROM users"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is True
        assert pos > 0
        assert text[pos:].startswith("SELECT")

    def test_execute_prefix(self) -> None:
        """Should detect execute <name>: prefix."""
        text = "execute my_query: SELECT 1"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is True
        assert pos > 0

    def test_parse_prefix(self) -> None:
        """Should detect parse <name>: prefix."""
        text = "parse my_stmt: SELECT * FROM users"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is True

    def test_bind_prefix(self) -> None:
        """Should detect bind <name>: prefix."""
        text = "bind stmt_1: some parameters"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is True

    def test_duration_statement(self) -> None:
        """Should detect duration: ... statement: prefix."""
        text = "duration: 5.123 ms statement: SELECT 1"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is True

    def test_no_sql_context(self) -> None:
        """Should not detect SQL in regular text."""
        text = "LOG: checkpointer starting"
        has_sql, pos = detect_sql_context(text)

        assert has_sql is False
        assert pos == 0


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_sql_highlighters(self) -> None:
        """get_sql_highlighters should return all highlighters."""
        highlighters = get_sql_highlighters()

        assert len(highlighters) == 5
        names = {h.name for h in highlighters}
        assert names == {"sql_param", "sql_keyword", "sql_string", "sql_number", "sql_operator"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 700-799 range."""
        highlighters = get_sql_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(700 <= p < 800 for p in priorities)
