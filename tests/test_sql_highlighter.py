"""Unit tests for SQL highlighter."""

import pytest

from pgtail_py.sql_highlighter import SQLHighlighter, TOKEN_TO_STYLE
from pgtail_py.sql_tokenizer import SQLToken, SQLTokenType


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
