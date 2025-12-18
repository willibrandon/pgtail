"""Unit tests for SQL tokenizer."""

import pytest

from pgtail_py.sql_tokenizer import SQLToken, SQLTokenizer, SQLTokenType


class TestSQLTokenType:
    """Test SQLTokenType enum."""

    def test_keyword_type_exists(self) -> None:
        """KEYWORD type should exist."""
        assert SQLTokenType.KEYWORD.value == "keyword"

    def test_identifier_type_exists(self) -> None:
        """IDENTIFIER type should exist."""
        assert SQLTokenType.IDENTIFIER.value == "identifier"

    def test_all_token_types_defined(self) -> None:
        """All expected token types should be defined."""
        expected = {
            "keyword",
            "identifier",
            "quoted_identifier",
            "string",
            "number",
            "operator",
            "comment",
            "function",
            "punctuation",
            "whitespace",
            "unknown",
        }
        actual = {t.value for t in SQLTokenType}
        assert actual == expected


class TestSQLToken:
    """Test SQLToken dataclass."""

    def test_create_token(self) -> None:
        """Should create token with all fields."""
        token = SQLToken(
            type=SQLTokenType.KEYWORD,
            text="SELECT",
            start=0,
            end=6,
        )
        assert token.type == SQLTokenType.KEYWORD
        assert token.text == "SELECT"
        assert token.start == 0
        assert token.end == 6

    def test_token_is_frozen(self) -> None:
        """Token should be immutable."""
        token = SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=0, end=6)
        with pytest.raises(Exception):  # FrozenInstanceError
            token.text = "INSERT"  # type: ignore[misc]

    def test_invalid_start_position(self) -> None:
        """Should reject negative start position."""
        with pytest.raises(ValueError, match="start must be >= 0"):
            SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=-1, end=6)

    def test_invalid_end_position(self) -> None:
        """Should reject end <= start."""
        with pytest.raises(ValueError, match="end must be > start"):
            SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=0, end=0)


class TestSQLTokenizerKeywords:
    """Test keyword tokenization (User Story 1)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_tokenize_empty_string(self, tokenizer: SQLTokenizer) -> None:
        """Empty string should return empty list."""
        tokens = tokenizer.tokenize("")
        assert tokens == []

    def test_tokenize_select_keyword(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize SELECT as keyword."""
        tokens = tokenizer.tokenize("SELECT")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.KEYWORD
        assert tokens[0].text == "SELECT"

    def test_tokenize_select_lowercase(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize lowercase 'select' as keyword (case-insensitive)."""
        tokens = tokenizer.tokenize("select")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.KEYWORD
        assert tokens[0].text == "select"

    def test_tokenize_select_mixed_case(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize 'SeLeCt' as keyword (case-insensitive)."""
        tokens = tokenizer.tokenize("SeLeCt")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.KEYWORD

    def test_tokenize_basic_dml_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize basic DML keywords."""
        for keyword in ["INSERT", "UPDATE", "DELETE", "SELECT"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"
            assert tokens[0].text == keyword

    def test_tokenize_from_where_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize FROM and WHERE as keywords."""
        for keyword in ["FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_logical_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize logical operators as keywords."""
        for keyword in ["AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "IS", "NULL"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_ordering_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize ordering keywords."""
        for keyword in ["ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "ASC", "DESC"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_set_operation_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize set operation keywords."""
        for keyword in ["UNION", "INTERSECT", "EXCEPT", "ALL", "DISTINCT"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_ddl_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize DDL keywords."""
        for keyword in ["CREATE", "ALTER", "DROP", "TABLE", "INDEX", "VIEW"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_case_expression_keywords(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize CASE expression keywords."""
        for keyword in ["CASE", "WHEN", "THEN", "ELSE", "END"]:
            tokens = tokenizer.tokenize(keyword)
            assert len(tokens) == 1
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{keyword} should be KEYWORD"

    def test_tokenize_simple_statement(self, tokenizer: SQLTokenizer) -> None:
        """Should tokenize a simple SELECT statement."""
        tokens = tokenizer.tokenize("SELECT id FROM users")
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) == 2
        assert keywords[0].text == "SELECT"
        assert keywords[1].text == "FROM"

    def test_tokenize_preserves_whitespace(self, tokenizer: SQLTokenizer) -> None:
        """Whitespace should be preserved in tokens."""
        tokens = tokenizer.tokenize("SELECT id")
        # Should have at least SELECT, whitespace, and 'id'
        assert len(tokens) >= 3
        whitespace = [t for t in tokens if t.type == SQLTokenType.WHITESPACE]
        assert len(whitespace) == 1
        assert whitespace[0].text == " "

    def test_token_positions_are_correct(self, tokenizer: SQLTokenizer) -> None:
        """Token start/end positions should be correct."""
        sql = "SELECT id"
        tokens = tokenizer.tokenize(sql)

        # Verify positions reconstruct original
        reconstructed = "".join(t.text for t in tokens)
        assert reconstructed == sql

        # Verify positions are sequential
        for i, token in enumerate(tokens):
            assert token.text == sql[token.start : token.end]
            if i > 0:
                assert token.start == tokens[i - 1].end

    def test_keyword_word_boundaries(self, tokenizer: SQLTokenizer) -> None:
        """Keywords should only match at word boundaries."""
        # 'selected' should NOT match as SELECT + ed
        tokens = tokenizer.tokenize("selected")
        assert len(tokens) == 1
        # Should be identifier, not keyword
        assert tokens[0].type != SQLTokenType.KEYWORD

    def test_all_45_keywords_recognized(self, tokenizer: SQLTokenizer) -> None:
        """All 45+ SQL keywords from FR-002 should be recognized."""
        keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
            "FROM",
            "WHERE",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "ON",
            "AND",
            "OR",
            "NOT",
            "IN",
            "EXISTS",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "AS",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "UNION",
            "INTERSECT",
            "EXCEPT",
            "WITH",
            "VALUES",
            "SET",
            "INTO",
            "DISTINCT",
            "ALL",
            "ANY",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
        ]
        for kw in keywords:
            tokens = tokenizer.tokenize(kw)
            assert tokens[0].type == SQLTokenType.KEYWORD, f"{kw} should be recognized as keyword"
