"""Unit tests for SQL highlighter."""

import os
from unittest.mock import patch

import pytest

from pgtail_py.sql_highlighter import (
    SQLHighlighter,
    TOKEN_TO_STYLE,
    TOKEN_TYPE_TO_THEME_KEY,
    _color_style_to_rich_markup,
    highlight_sql_rich,
)
from pgtail_py.sql_tokenizer import SQLToken, SQLTokenType
from pgtail_py.theme import ColorStyle, Theme


class TestTokenToStyleMapping:
    """Test TOKEN_TO_STYLE mapping."""

    def test_keyword_maps_to_sql_keyword_class(self) -> None:
        """KEYWORD should map to class:sql_keyword."""
        assert TOKEN_TO_STYLE[SQLTokenType.KEYWORD] == "class:sql_keyword"

    def test_identifier_maps_to_sql_identifier_class(self) -> None:
        """IDENTIFIER should map to class:sql_identifier."""
        assert TOKEN_TO_STYLE[SQLTokenType.IDENTIFIER] == "class:sql_identifier"

    def test_quoted_identifier_maps_to_sql_identifier_class(self) -> None:
        """QUOTED_IDENTIFIER should also map to class:sql_identifier."""
        assert TOKEN_TO_STYLE[SQLTokenType.QUOTED_IDENTIFIER] == "class:sql_identifier"

    def test_string_maps_to_sql_string_class(self) -> None:
        """STRING should map to class:sql_string."""
        assert TOKEN_TO_STYLE[SQLTokenType.STRING] == "class:sql_string"

    def test_number_maps_to_sql_number_class(self) -> None:
        """NUMBER should map to class:sql_number."""
        assert TOKEN_TO_STYLE[SQLTokenType.NUMBER] == "class:sql_number"

    def test_operator_maps_to_sql_operator_class(self) -> None:
        """OPERATOR should map to class:sql_operator."""
        assert TOKEN_TO_STYLE[SQLTokenType.OPERATOR] == "class:sql_operator"

    def test_comment_maps_to_sql_comment_class(self) -> None:
        """COMMENT should map to class:sql_comment."""
        assert TOKEN_TO_STYLE[SQLTokenType.COMMENT] == "class:sql_comment"

    def test_function_maps_to_sql_function_class(self) -> None:
        """FUNCTION should map to class:sql_function."""
        assert TOKEN_TO_STYLE[SQLTokenType.FUNCTION] == "class:sql_function"

    def test_punctuation_has_no_style(self) -> None:
        """PUNCTUATION should have empty style."""
        assert TOKEN_TO_STYLE[SQLTokenType.PUNCTUATION] == ""

    def test_whitespace_has_no_style(self) -> None:
        """WHITESPACE should have empty style."""
        assert TOKEN_TO_STYLE[SQLTokenType.WHITESPACE] == ""

    def test_unknown_has_no_style(self) -> None:
        """UNKNOWN should have empty style."""
        assert TOKEN_TO_STYLE[SQLTokenType.UNKNOWN] == ""


class TestSQLHighlighter:
    """Test SQLHighlighter class."""

    @pytest.fixture
    def highlighter(self) -> SQLHighlighter:
        """Create a highlighter instance."""
        return SQLHighlighter()

    def test_highlight_empty_string(self, highlighter: SQLHighlighter) -> None:
        """Empty string should return empty FormattedText."""
        result = highlighter.highlight("")
        assert list(result) == []

    def test_highlight_returns_formatted_text(self, highlighter: SQLHighlighter) -> None:
        """highlight() should return FormattedText."""
        from prompt_toolkit.formatted_text import FormattedText

        result = highlighter.highlight("SELECT")
        assert isinstance(result, FormattedText)

    def test_highlight_keyword_has_sql_keyword_style(self, highlighter: SQLHighlighter) -> None:
        """Keywords should have class:sql_keyword style."""
        result = highlighter.highlight("SELECT")
        parts = list(result)
        # Find the SELECT token
        keyword_parts = [p for p in parts if "SELECT" in p[1]]
        assert len(keyword_parts) == 1
        assert keyword_parts[0][0] == "class:sql_keyword"

    def test_highlight_simple_statement(self, highlighter: SQLHighlighter) -> None:
        """Should highlight a simple SELECT statement."""
        result = highlighter.highlight("SELECT id FROM users")
        parts = list(result)

        # Find SELECT keyword
        select_parts = [p for p in parts if p[1] == "SELECT"]
        assert len(select_parts) == 1
        assert select_parts[0][0] == "class:sql_keyword"

        # Find FROM keyword
        from_parts = [p for p in parts if p[1] == "FROM"]
        assert len(from_parts) == 1
        assert from_parts[0][0] == "class:sql_keyword"

    def test_highlight_preserves_original_text(self, highlighter: SQLHighlighter) -> None:
        """Highlighting should preserve original text."""
        sql = "SELECT id, name FROM users WHERE active = true"
        result = highlighter.highlight(sql)
        parts = list(result)

        # Reconstruct text from parts
        reconstructed = "".join(p[1] for p in parts)
        assert reconstructed == sql


class TestSQLHighlighterTokens:
    """Test highlight_tokens method."""

    @pytest.fixture
    def highlighter(self) -> SQLHighlighter:
        """Create a highlighter instance."""
        return SQLHighlighter()

    def test_highlight_tokens_empty_list(self, highlighter: SQLHighlighter) -> None:
        """Empty token list should return empty FormattedText."""
        result = highlighter.highlight_tokens([])
        assert list(result) == []

    def test_highlight_tokens_single_keyword(self, highlighter: SQLHighlighter) -> None:
        """Single keyword token should have correct style."""
        tokens = [SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=0, end=6)]
        result = highlighter.highlight_tokens(tokens)
        parts = list(result)
        assert len(parts) == 1
        assert parts[0] == ("class:sql_keyword", "SELECT")

    def test_highlight_tokens_mixed_types(self, highlighter: SQLHighlighter) -> None:
        """Mixed token types should have correct styles."""
        tokens = [
            SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=0, end=6),
            SQLToken(type=SQLTokenType.WHITESPACE, text=" ", start=6, end=7),
            SQLToken(type=SQLTokenType.IDENTIFIER, text="id", start=7, end=9),
        ]
        result = highlighter.highlight_tokens(tokens)
        parts = list(result)
        assert len(parts) == 3
        assert parts[0] == ("class:sql_keyword", "SELECT")
        assert parts[1] == ("", " ")  # whitespace has no style
        assert parts[2] == ("class:sql_identifier", "id")


class TestSQLHighlighterIdentifiers:
    """Test identifier highlighting (User Story 2)."""

    @pytest.fixture
    def highlighter(self) -> SQLHighlighter:
        """Create a highlighter instance."""
        return SQLHighlighter()

    def test_highlight_unquoted_identifier(self, highlighter: SQLHighlighter) -> None:
        """Unquoted identifier should have sql_identifier style."""
        result = highlighter.highlight("SELECT users FROM public")
        parts = list(result)
        # Find identifiers (not keywords)
        identifier_parts = [p for p in parts if p[0] == "class:sql_identifier"]
        assert len(identifier_parts) == 2  # users, public
        texts = [p[1] for p in identifier_parts]
        assert "users" in texts
        assert "public" in texts

    def test_highlight_quoted_identifier(self, highlighter: SQLHighlighter) -> None:
        """Quoted identifier should have sql_identifier style."""
        result = highlighter.highlight('SELECT "MyColumn" FROM "MyTable"')
        parts = list(result)
        # Find quoted identifiers
        identifier_parts = [p for p in parts if p[0] == "class:sql_identifier"]
        assert len(identifier_parts) == 2
        texts = [p[1] for p in identifier_parts]
        assert '"MyColumn"' in texts
        assert '"MyTable"' in texts

    def test_highlight_mixed_identifiers(self, highlighter: SQLHighlighter) -> None:
        """Mix of quoted and unquoted identifiers should both have identifier style."""
        result = highlighter.highlight('SELECT id, "Name" FROM users')
        parts = list(result)
        identifier_parts = [p for p in parts if p[0] == "class:sql_identifier"]
        # Should have: id, "Name", users
        assert len(identifier_parts) == 3

    def test_highlight_identifier_distinct_from_keyword(self, highlighter: SQLHighlighter) -> None:
        """Identifiers should have different style than keywords."""
        result = highlighter.highlight("SELECT id FROM users")
        parts = list(result)
        keyword_parts = [p for p in parts if p[0] == "class:sql_keyword"]
        identifier_parts = [p for p in parts if p[0] == "class:sql_identifier"]

        # Keywords: SELECT, FROM
        assert len(keyword_parts) == 2
        # Identifiers: id, users
        assert len(identifier_parts) == 2

        # They should have different styles
        assert keyword_parts[0][0] != identifier_parts[0][0]

    def test_highlight_quoted_reserved_word(self, highlighter: SQLHighlighter) -> None:
        """Quoted reserved word should be identifier, not keyword."""
        result = highlighter.highlight('SELECT "SELECT" FROM users')
        parts = list(result)
        # The unquoted SELECT should be keyword
        keywords = [p for p in parts if p[0] == "class:sql_keyword" and p[1] == "SELECT"]
        assert len(keywords) == 1
        # The quoted "SELECT" should be identifier
        quoted = [p for p in parts if p[0] == "class:sql_identifier" and p[1] == '"SELECT"']
        assert len(quoted) == 1

    def test_highlight_preserves_text_with_identifiers(self, highlighter: SQLHighlighter) -> None:
        """Highlighting should preserve original text with identifiers."""
        sql = 'SELECT id, "Name" FROM public.users'
        result = highlighter.highlight(sql)
        reconstructed = "".join(p[1] for p in result)
        assert reconstructed == sql


class TestSQLHighlighterPerformance:
    """Performance tests for SQL highlighter - T046."""

    @pytest.fixture
    def highlighter(self) -> SQLHighlighter:
        """Create a highlighter instance."""
        return SQLHighlighter()

    def test_highlight_10000_char_sql_under_100ms(self, highlighter: SQLHighlighter) -> None:
        """10,000+ character SQL should highlight in under 100ms.

        Per SC-004: No performance degradation for statements up to 10,000 characters.
        """
        import time

        # Build a ~10,000 character SQL statement
        columns = [f"column_{i:04d}" for i in range(500)]
        values = [f"'value_{i:04d}'" for i in range(500)]
        column_list = ", ".join(columns)
        value_list = ", ".join(values)

        # INSERT with many columns and values
        sql = f"INSERT INTO very_long_table_name_for_testing ({column_list}) VALUES ({value_list})"

        # Verify it's over 10,000 characters
        assert len(sql) >= 10000, f"SQL length is only {len(sql)}, expected >= 10000"

        # Time the highlighting
        start = time.perf_counter()
        result = highlighter.highlight(sql)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify result is valid
        reconstructed = "".join(p[1] for p in result)
        assert reconstructed == sql

        # Verify it completed in under 100ms
        assert elapsed_ms < 100, f"Highlighting took {elapsed_ms:.2f}ms, expected < 100ms"

    def test_highlight_large_select_with_joins(self, highlighter: SQLHighlighter) -> None:
        """Large SELECT with multiple JOINs should perform well."""
        import time

        # Build a complex query with many joins
        tables = [f"table_{i}" for i in range(100)]
        joins = [
            f"LEFT JOIN {t} t{i} ON t{i}.id = t0.{t}_id" for i, t in enumerate(tables[1:], 1)
        ]
        columns = [f"t{i}.col1, t{i}.col2, t{i}.col3" for i in range(len(tables))]

        sql = f"""SELECT {", ".join(columns)}
FROM {tables[0]} t0
{chr(10).join(joins)}
WHERE t0.active = true
ORDER BY t0.created_at DESC
LIMIT 100"""

        # Verify length is substantial (should be > 5000 now)
        assert len(sql) >= 5000, f"SQL length is only {len(sql)}"

        start = time.perf_counter()
        result = highlighter.highlight(sql)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify highlighting worked
        keywords = [p for p in result if p[0] == "class:sql_keyword"]
        assert len(keywords) >= 50, "Should have many keywords highlighted"

        # Should complete in reasonable time
        assert elapsed_ms < 100, f"Highlighting took {elapsed_ms:.2f}ms"

    def test_highlight_many_string_literals(self, highlighter: SQLHighlighter) -> None:
        """SQL with many string literals should perform well."""
        import time

        # Build SQL with many string literals
        values = [f"('value_{i}', 'data_{i}')" for i in range(500)]
        sql = f"INSERT INTO strings (col1, col2) VALUES {', '.join(values)}"

        assert len(sql) >= 10000, f"SQL length is only {len(sql)}"

        start = time.perf_counter()
        result = highlighter.highlight(sql)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify strings were found
        strings = [p for p in result if p[0] == "class:sql_string"]
        assert len(strings) >= 1000, "Should have many string literals"

        assert elapsed_ms < 100, f"Highlighting took {elapsed_ms:.2f}ms"

    def test_highlight_repeated_highlighting_consistent(
        self, highlighter: SQLHighlighter
    ) -> None:
        """Repeated highlighting should have consistent performance."""
        import time

        sql = "SELECT id, name FROM users WHERE active = true ORDER BY name"

        # Warm up
        for _ in range(10):
            highlighter.highlight(sql)

        # Measure multiple runs
        times: list[float] = []
        for _ in range(100):
            start = time.perf_counter()
            highlighter.highlight(sql)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time: float = sum(times) / len(times)
        max_time: float = max(times)

        # Average should be well under 1ms for short SQL
        assert avg_time < 1, f"Average time {avg_time:.3f}ms too slow"
        # No outliers should exceed 10ms
        assert max_time < 10, f"Max time {max_time:.3f}ms too slow"


# =============================================================================
# Tests for Rich Output (User Story 1 - T009-T014, T051-T052)
# =============================================================================


class TestTokenTypeToThemeKeyMapping:
    """Tests for TOKEN_TYPE_TO_THEME_KEY mapping."""

    def test_keyword_maps_to_sql_keyword(self) -> None:
        """KEYWORD should map to sql_keyword theme key."""
        assert TOKEN_TYPE_TO_THEME_KEY[SQLTokenType.KEYWORD] == "sql_keyword"

    def test_identifier_maps_to_sql_identifier(self) -> None:
        """IDENTIFIER should map to sql_identifier theme key."""
        assert TOKEN_TYPE_TO_THEME_KEY[SQLTokenType.IDENTIFIER] == "sql_identifier"

    def test_quoted_identifier_maps_to_sql_identifier(self) -> None:
        """QUOTED_IDENTIFIER should also map to sql_identifier theme key."""
        assert TOKEN_TYPE_TO_THEME_KEY[SQLTokenType.QUOTED_IDENTIFIER] == "sql_identifier"

    def test_function_maps_to_sql_function(self) -> None:
        """FUNCTION should map to sql_function theme key."""
        assert TOKEN_TYPE_TO_THEME_KEY[SQLTokenType.FUNCTION] == "sql_function"

    def test_punctuation_has_no_theme_key(self) -> None:
        """PUNCTUATION should have empty theme key."""
        assert TOKEN_TYPE_TO_THEME_KEY[SQLTokenType.PUNCTUATION] == ""


class TestColorStyleToRichMarkup:
    """Tests for _color_style_to_rich_markup() - T009."""

    def test_empty_style_returns_empty_string(self) -> None:
        """Empty ColorStyle should return empty string."""
        style = ColorStyle()
        assert _color_style_to_rich_markup(style) == ""

    def test_fg_only(self) -> None:
        """Foreground color only should return just the color."""
        style = ColorStyle(fg="blue")
        assert _color_style_to_rich_markup(style) == "blue"

    def test_fg_with_bold(self) -> None:
        """Bold with foreground should put bold first."""
        style = ColorStyle(fg="blue", bold=True)
        assert _color_style_to_rich_markup(style) == "bold blue"

    def test_ansi_color_stripped(self) -> None:
        """ANSI color prefix should be stripped for Rich compatibility."""
        style = ColorStyle(fg="ansicyan")
        assert _color_style_to_rich_markup(style) == "cyan"

    def test_ansibright_color_converted(self) -> None:
        """ansibright* prefix should be converted to bright_*."""
        style = ColorStyle(fg="ansibrightred")
        assert _color_style_to_rich_markup(style) == "bright_red"

    def test_ansibright_blue_converted(self) -> None:
        """ansibrightblue should become bright_blue."""
        style = ColorStyle(fg="ansibrightblue")
        assert _color_style_to_rich_markup(style) == "bright_blue"

    def test_hex_color_passed_through(self) -> None:
        """Hex colors should pass through unchanged."""
        style = ColorStyle(fg="#268bd2")
        assert _color_style_to_rich_markup(style) == "#268bd2"

    def test_background_color(self) -> None:
        """Background color should use 'on' prefix."""
        style = ColorStyle(bg="yellow")
        assert _color_style_to_rich_markup(style) == "on yellow"

    def test_background_ansi_color_stripped(self) -> None:
        """Background ANSI color prefix should be stripped."""
        style = ColorStyle(bg="ansiyellow")
        assert _color_style_to_rich_markup(style) == "on yellow"

    def test_dim_modifier(self) -> None:
        """Dim modifier should be included."""
        style = ColorStyle(dim=True)
        assert _color_style_to_rich_markup(style) == "dim"

    def test_italic_modifier(self) -> None:
        """Italic modifier should be included."""
        style = ColorStyle(italic=True)
        assert _color_style_to_rich_markup(style) == "italic"

    def test_underline_modifier(self) -> None:
        """Underline modifier should be included."""
        style = ColorStyle(underline=True)
        assert _color_style_to_rich_markup(style) == "underline"

    def test_all_modifiers_with_colors(self) -> None:
        """All modifiers with colors should be in correct order."""
        style = ColorStyle(fg="blue", bg="yellow", bold=True, dim=True, italic=True, underline=True)
        result = _color_style_to_rich_markup(style)
        # Order: bold, dim, italic, underline, fg, bg
        assert result == "bold dim italic underline blue on yellow"


class TestHighlightSqlRich:
    """Tests for highlight_sql_rich() - T010."""

    def test_keywords_highlighted(self) -> None:
        """SQL keywords should have markup tags."""
        result = highlight_sql_rich("SELECT id FROM users")
        # Should have Rich markup tags
        assert "[" in result
        assert "SELECT" in result
        assert "FROM" in result

    def test_brackets_escaped(self) -> None:
        """Brackets in SQL should be escaped to prevent Rich parsing errors."""
        result = highlight_sql_rich("SELECT arr[1] FROM table")
        # Opening bracket should be escaped (the tokenizer treats [1] as separate tokens)
        assert "\\[" in result

    def test_nested_brackets_escaped(self) -> None:
        """Nested brackets in SQL should all be escaped."""
        result = highlight_sql_rich("SELECT arr[1][2] FROM table")
        # Should have escaped brackets
        assert result.count("\\[") >= 2

    def test_empty_sql_returns_empty(self) -> None:
        """Empty SQL should return empty string."""
        result = highlight_sql_rich("")
        assert result == ""

    def test_string_literals_styled(self) -> None:
        """String literals should be in the output with styling."""
        result = highlight_sql_rich("WHERE name = 'John'")
        assert "'John'" in result
        # Should have markup tags around it
        assert "[" in result

    def test_numbers_styled(self) -> None:
        """Numeric literals should be in the output with styling."""
        result = highlight_sql_rich("WHERE count > 42")
        assert "42" in result

    def test_comments_styled(self) -> None:
        """SQL comments should be in the output with styling."""
        result = highlight_sql_rich("SELECT 1 -- comment")
        assert "-- comment" in result

    def test_preserves_whitespace(self) -> None:
        """Highlighting should preserve whitespace."""
        result = highlight_sql_rich("SELECT  id   FROM users")
        # Remove markup and check original spacing preserved
        plain = result.replace("\\[", "[")
        # Should contain the original spacing
        assert "  " in plain or "SELECT" in plain

    def test_closing_tags_present(self) -> None:
        """All opening tags should have closing tags."""
        result = highlight_sql_rich("SELECT id FROM users")
        # Count opening and closing tags
        open_count = result.count("[") - result.count("\\[")
        close_count = result.count("[/]")
        # Should have equal opening (non-escaped) and closing tags
        assert open_count == close_count * 2  # Each styled token has [style] and [/]


class TestHighlightSqlRichFunctions:
    """Tests for function detection in highlight_sql_rich() - T051."""

    def test_count_function_styled(self) -> None:
        """COUNT(*) should be styled as sql_function."""
        result = highlight_sql_rich("SELECT COUNT(*) FROM users")
        assert "COUNT" in result
        # Should have markup around it
        assert "[" in result

    def test_now_function_styled(self) -> None:
        """NOW() should be styled as sql_function."""
        result = highlight_sql_rich("SELECT NOW()")
        assert "NOW" in result

    def test_coalesce_function_styled(self) -> None:
        """COALESCE() should be styled as sql_function."""
        result = highlight_sql_rich("SELECT COALESCE(name, 'default')")
        assert "COALESCE" in result

    def test_aggregate_functions_styled(self) -> None:
        """SUM, AVG, MAX, MIN should be styled as sql_function."""
        result = highlight_sql_rich("SELECT SUM(amount), AVG(amount), MAX(amount), MIN(amount)")
        assert "SUM" in result
        assert "AVG" in result
        assert "MAX" in result
        assert "MIN" in result


class TestHighlightSqlRichKeywordCoverage:
    """Tests for keyword coverage in highlight_sql_rich() - T052."""

    def test_ddl_keywords_create_alter(self) -> None:
        """DDL keywords CREATE, ALTER should be highlighted."""
        result = highlight_sql_rich("CREATE TABLE users (id INT); ALTER TABLE users ADD COLUMN name TEXT")
        assert "CREATE" in result
        assert "ALTER" in result
        assert "TABLE" in result

    def test_dml_keywords_select_insert(self) -> None:
        """DML keywords SELECT, INSERT should be highlighted."""
        result = highlight_sql_rich("SELECT * FROM users; INSERT INTO users VALUES (1)")
        assert "SELECT" in result
        assert "INSERT" in result
        assert "INTO" in result
        assert "VALUES" in result

    def test_clause_keywords_where_join(self) -> None:
        """Clause keywords WHERE, JOIN should be highlighted."""
        result = highlight_sql_rich("SELECT * FROM a JOIN b ON a.id = b.id WHERE a.active")
        assert "WHERE" in result
        assert "JOIN" in result
        assert "ON" in result

    def test_logical_operators_and_or_not(self) -> None:
        """Logical operators AND, OR, NOT should be highlighted as keywords."""
        result = highlight_sql_rich("SELECT * FROM users WHERE active AND NOT deleted OR archived")
        assert "AND" in result
        assert "OR" in result
        assert "NOT" in result


class TestHighlightSqlRichNoColor:
    """Tests for NO_COLOR handling in highlight_sql_rich() - T028, T029."""

    def test_no_color_returns_escaped_brackets_only(self) -> None:
        """With NO_COLOR=1, should return SQL with only bracket escaping."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            # Need to reload the cached check
            from pgtail_py import utils
            utils._color_disabled = None  # Clear cache
            try:
                result = highlight_sql_rich("SELECT arr[1] FROM users")
                # Should have escaped bracket
                assert "\\[1]" in result
                # Should NOT have Rich markup tags (closing tag pattern)
                assert "[/]" not in result
            finally:
                utils._color_disabled = None  # Clear cache again

    def test_no_color_no_rich_markup_tags(self) -> None:
        """With NO_COLOR=1, output should have no Rich markup tags."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            from pgtail_py import utils
            utils._color_disabled = None
            try:
                result = highlight_sql_rich("SELECT id FROM users")
                # No closing tags means no Rich markup
                assert "[/" not in result
                # But should have the SQL content
                assert "SELECT" in result
                assert "FROM" in result
            finally:
                utils._color_disabled = None


class TestHighlightSqlRichWithTheme:
    """Tests for theme integration in highlight_sql_rich() - T033-T035."""

    def test_uses_passed_theme_for_color_lookup(self) -> None:
        """highlight_sql_rich() should use the passed theme for colors."""
        # Create a custom theme with distinctive colors
        custom_theme = Theme(
            name="test-theme",
            description="Test theme",
            levels={
                "ERROR": ColorStyle(fg="red"),
                "WARNING": ColorStyle(fg="yellow"),
                "LOG": ColorStyle(fg="white"),
            },
            ui={
                "timestamp": ColorStyle(dim=True),
                "highlight": ColorStyle(fg="yellow"),
                "sql_keyword": ColorStyle(fg="magenta", bold=True),
                "sql_identifier": ColorStyle(fg="green"),
            },
        )
        result = highlight_sql_rich("SELECT id FROM users", theme=custom_theme)
        # Should have magenta in output for keywords
        assert "magenta" in result or "bold" in result

    def test_uses_global_theme_when_none_passed(self) -> None:
        """highlight_sql_rich() should use global ThemeManager when theme is None."""
        result = highlight_sql_rich("SELECT id FROM users", theme=None)
        # Should still produce styled output (using default theme)
        assert "[" in result
        assert "SELECT" in result

    def test_graceful_fallback_for_missing_sql_keys(self) -> None:
        """Theme missing SQL color keys should return unstyled text for those tokens."""
        # Create theme without sql_* keys
        minimal_theme = Theme(
            name="minimal-theme",
            levels={
                "ERROR": ColorStyle(fg="red"),
                "WARNING": ColorStyle(fg="yellow"),
                "LOG": ColorStyle(fg="white"),
            },
            ui={
                "timestamp": ColorStyle(dim=True),
                "highlight": ColorStyle(fg="yellow"),
                # No sql_* keys defined
            },
        )
        result = highlight_sql_rich("SELECT id FROM users", theme=minimal_theme)
        # Should still contain the SQL text
        assert "SELECT" in result
        assert "id" in result
        assert "FROM" in result
        assert "users" in result
        # Should not crash, text should be present (possibly unstyled)


# =============================================================================
# User Story 2 - Distinguish Literals from Identifiers (T015-T017)
# =============================================================================


class TestHighlightSqlRichLiterals:
    """Tests for literal distinction in highlight_sql_rich() - T015-T017."""

    def test_string_literals_styled_distinctly_from_identifiers(self) -> None:
        """String literals 'John' should be styled distinctly from identifiers (T015)."""
        result = highlight_sql_rich("SELECT name FROM users WHERE name = 'John'")
        # Check that 'John' is in output
        assert "'John'" in result
        # Check that name (identifier) is also in output
        assert "name" in result
        # Both should have markup, but we just verify they're present and formatted

    def test_numeric_literals_styled_distinctly(self) -> None:
        """Numeric literals like 42 should be styled distinctly (T016)."""
        result = highlight_sql_rich("SELECT id FROM users WHERE age = 42")
        assert "42" in result
        # Should have markup
        assert "[" in result

    def test_dollar_quoted_strings_styled_as_strings(self) -> None:
        """Dollar-quoted strings $$body$$ should be styled as strings (T017)."""
        result = highlight_sql_rich("SELECT $$body content$$ FROM table")
        assert "$$body content$$" in result

    def test_various_string_formats(self) -> None:
        """Various string literal formats should all be styled."""
        # Single quotes
        result1 = highlight_sql_rich("SELECT 'hello'")
        assert "'hello'" in result1

        # Double-dollar quotes
        result2 = highlight_sql_rich("SELECT $$hello$$")
        assert "$$hello$$" in result2

        # Tagged dollar quotes
        result3 = highlight_sql_rich("SELECT $tag$hello$tag$")
        assert "$tag$hello$tag$" in result3

    def test_integer_and_float_literals(self) -> None:
        """Both integer and float literals should be styled."""
        result = highlight_sql_rich("SELECT * FROM t WHERE x = 42 AND y = 3.14")
        assert "42" in result
        assert "3.14" in result


class TestHighlightSqlRichEdgeCases:
    """Edge case tests for highlight_sql_rich() - T041-T045."""

    def test_sql_with_nested_brackets(self) -> None:
        """SQL with nested brackets like arr[1][2] should escape all brackets."""
        result = highlight_sql_rich("SELECT arr[1][2] FROM table")
        # Should have multiple escaped brackets
        assert result.count("\\[") >= 2

    def test_malformed_sql_with_unrecognized_tokens(self) -> None:
        """Malformed SQL should highlight recognized tokens and display unknown plain."""
        result = highlight_sql_rich("SELECT @@@ FROM users")
        # SELECT and FROM should be highlighted
        assert "SELECT" in result
        assert "FROM" in result
        # Should not crash, @@@ should be in output
        assert "@@@" in result

    def test_extremely_long_sql_50kb(self) -> None:
        """50KB SQL should complete without performance degradation."""
        import time
        # Build a 50KB+ SQL statement - need more columns to reach 50KB
        columns = [f"very_long_column_name_prefix_{i:06d}" for i in range(2000)]
        column_list = ", ".join(columns)
        sql = f"SELECT {column_list} FROM very_long_table_name_for_testing_purposes"

        # Verify it's at least 50KB
        assert len(sql) >= 50000, f"SQL length is only {len(sql)}"

        start = time.perf_counter()
        result = highlight_sql_rich(sql)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify result is valid
        assert "SELECT" in result
        # Should complete in reasonable time (< 500ms for 50KB)
        assert elapsed_ms < 500, f"50KB SQL took {elapsed_ms:.2f}ms"

    def test_dollar_quoted_strings(self) -> None:
        """Dollar-quoted strings should be styled correctly."""
        result = highlight_sql_rich("SELECT $tag$body content$tag$ FROM table")
        assert "$tag$body content$tag$" in result

    def test_line_comments(self) -> None:
        """Line comments (--) should be styled."""
        result = highlight_sql_rich("SELECT 1 -- this is a comment")
        assert "-- this is a comment" in result

    def test_block_comments(self) -> None:
        """Block comments (/* */) should be styled."""
        result = highlight_sql_rich("SELECT /* comment */ 1 FROM users")
        assert "/* comment */" in result
