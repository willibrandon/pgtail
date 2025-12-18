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


class TestSQLTokenizerIdentifiers:
    """Test identifier tokenization (User Story 2)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_unquoted_identifier_simple(self, tokenizer: SQLTokenizer) -> None:
        """Simple unquoted identifier should be recognized."""
        tokens = tokenizer.tokenize("users")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.IDENTIFIER
        assert tokens[0].text == "users"

    def test_unquoted_identifier_with_underscore(self, tokenizer: SQLTokenizer) -> None:
        """Identifier with underscore should be recognized."""
        tokens = tokenizer.tokenize("user_name")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.IDENTIFIER
        assert tokens[0].text == "user_name"

    def test_unquoted_identifier_starting_with_underscore(self, tokenizer: SQLTokenizer) -> None:
        """Identifier starting with underscore should be recognized."""
        tokens = tokenizer.tokenize("_private")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.IDENTIFIER
        assert tokens[0].text == "_private"

    def test_unquoted_identifier_with_numbers(self, tokenizer: SQLTokenizer) -> None:
        """Identifier with numbers should be recognized."""
        tokens = tokenizer.tokenize("table1")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.IDENTIFIER
        assert tokens[0].text == "table1"

    def test_quoted_identifier_simple(self, tokenizer: SQLTokenizer) -> None:
        """Double-quoted identifier should be recognized as QUOTED_IDENTIFIER."""
        tokens = tokenizer.tokenize('"MyTable"')
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.QUOTED_IDENTIFIER
        assert tokens[0].text == '"MyTable"'

    def test_quoted_identifier_with_spaces(self, tokenizer: SQLTokenizer) -> None:
        """Quoted identifier with spaces should be recognized."""
        tokens = tokenizer.tokenize('"My Table"')
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.QUOTED_IDENTIFIER
        assert tokens[0].text == '"My Table"'

    def test_quoted_identifier_with_reserved_word(self, tokenizer: SQLTokenizer) -> None:
        """Quoted reserved word should be QUOTED_IDENTIFIER, not keyword."""
        tokens = tokenizer.tokenize('"SELECT"')
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.QUOTED_IDENTIFIER
        assert tokens[0].text == '"SELECT"'

    def test_quoted_identifier_preserves_case(self, tokenizer: SQLTokenizer) -> None:
        """Quoted identifier should preserve original case."""
        tokens = tokenizer.tokenize('"MixedCase"')
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.QUOTED_IDENTIFIER
        assert tokens[0].text == '"MixedCase"'

    def test_quoted_identifier_with_escaped_quote(self, tokenizer: SQLTokenizer) -> None:
        """Quoted identifier with escaped double quote should be recognized."""
        tokens = tokenizer.tokenize('"Say ""Hello"""')
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.QUOTED_IDENTIFIER
        assert tokens[0].text == '"Say ""Hello"""'

    def test_identifier_in_select_statement(self, tokenizer: SQLTokenizer) -> None:
        """Identifiers in SELECT should be recognized."""
        tokens = tokenizer.tokenize("SELECT id, name FROM users")
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        assert len(identifiers) == 3
        assert identifiers[0].text == "id"
        assert identifiers[1].text == "name"
        assert identifiers[2].text == "users"

    def test_quoted_identifier_in_select_statement(self, tokenizer: SQLTokenizer) -> None:
        """Quoted identifiers in SELECT should be recognized."""
        tokens = tokenizer.tokenize('SELECT "Id" FROM "MyTable"')
        quoted = [t for t in tokens if t.type == SQLTokenType.QUOTED_IDENTIFIER]
        assert len(quoted) == 2
        assert quoted[0].text == '"Id"'
        assert quoted[1].text == '"MyTable"'

    def test_mixed_identifiers(self, tokenizer: SQLTokenizer) -> None:
        """Mix of quoted and unquoted identifiers should work."""
        tokens = tokenizer.tokenize('SELECT id, "Name" FROM users')
        unquoted = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        quoted = [t for t in tokens if t.type == SQLTokenType.QUOTED_IDENTIFIER]
        assert len(unquoted) == 2  # id, users
        assert len(quoted) == 1  # "Name"

    def test_schema_qualified_identifier(self, tokenizer: SQLTokenizer) -> None:
        """Schema.table should tokenize as separate identifiers."""
        tokens = tokenizer.tokenize("public.users")
        # Should be: public, ., users
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        assert len(identifiers) == 2
        assert identifiers[0].text == "public"
        assert identifiers[1].text == "users"


class TestSQLTokenizerStrings:
    """Test string literal tokenization (User Story 3 - T027)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_single_quoted_string_simple(self, tokenizer: SQLTokenizer) -> None:
        """Simple single-quoted string should be recognized."""
        tokens = tokenizer.tokenize("'hello'")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "'hello'"

    def test_single_quoted_string_with_spaces(self, tokenizer: SQLTokenizer) -> None:
        """Single-quoted string with spaces should be recognized."""
        tokens = tokenizer.tokenize("'hello world'")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "'hello world'"

    def test_single_quoted_string_escaped_quote(self, tokenizer: SQLTokenizer) -> None:
        """Single-quoted string with escaped quote ('') should be recognized."""
        tokens = tokenizer.tokenize("'it''s a test'")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "'it''s a test'"

    def test_single_quoted_string_empty(self, tokenizer: SQLTokenizer) -> None:
        """Empty single-quoted string should be recognized."""
        tokens = tokenizer.tokenize("''")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "''"

    def test_dollar_quoted_string_simple(self, tokenizer: SQLTokenizer) -> None:
        """Simple dollar-quoted string ($$...$$) should be recognized."""
        tokens = tokenizer.tokenize("$$hello$$")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "$$hello$$"

    def test_dollar_quoted_string_with_tag(self, tokenizer: SQLTokenizer) -> None:
        """Tagged dollar-quoted string ($tag$...$tag$) should be recognized."""
        tokens = tokenizer.tokenize("$body$SELECT 1$body$")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "$body$SELECT 1$body$"

    def test_dollar_quoted_string_empty(self, tokenizer: SQLTokenizer) -> None:
        """Empty dollar-quoted string should be recognized."""
        tokens = tokenizer.tokenize("$$$$")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "$$$$"

    def test_dollar_quoted_string_with_single_quotes(self, tokenizer: SQLTokenizer) -> None:
        """Dollar-quoted string containing single quotes should be recognized."""
        tokens = tokenizer.tokenize("$$it's a test$$")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "$$it's a test$$"

    def test_dollar_quoted_string_with_newlines(self, tokenizer: SQLTokenizer) -> None:
        """Dollar-quoted string with newlines should be recognized."""
        tokens = tokenizer.tokenize("$$line1\nline2$$")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.STRING
        assert tokens[0].text == "$$line1\nline2$$"

    def test_string_in_where_clause(self, tokenizer: SQLTokenizer) -> None:
        """String literal in WHERE clause should be recognized."""
        tokens = tokenizer.tokenize("WHERE name = 'test'")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        assert len(strings) == 1
        assert strings[0].text == "'test'"

    def test_multiple_strings(self, tokenizer: SQLTokenizer) -> None:
        """Multiple string literals should all be recognized."""
        tokens = tokenizer.tokenize("'a', 'b', 'c'")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        assert len(strings) == 3

    def test_string_does_not_consume_next_token(self, tokenizer: SQLTokenizer) -> None:
        """String should not consume following tokens."""
        tokens = tokenizer.tokenize("'test' AND")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(strings) == 1
        assert len(keywords) == 1


class TestSQLTokenizerNumbers:
    """Test numeric literal tokenization (User Story 3 - T028)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_integer_simple(self, tokenizer: SQLTokenizer) -> None:
        """Simple integer should be recognized."""
        tokens = tokenizer.tokenize("42")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "42"

    def test_integer_zero(self, tokenizer: SQLTokenizer) -> None:
        """Zero should be recognized."""
        tokens = tokenizer.tokenize("0")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "0"

    def test_integer_large(self, tokenizer: SQLTokenizer) -> None:
        """Large integer should be recognized."""
        tokens = tokenizer.tokenize("123456789")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "123456789"

    def test_decimal_simple(self, tokenizer: SQLTokenizer) -> None:
        """Simple decimal should be recognized."""
        tokens = tokenizer.tokenize("3.14")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "3.14"

    def test_decimal_leading_zero(self, tokenizer: SQLTokenizer) -> None:
        """Decimal with leading zero should be recognized."""
        tokens = tokenizer.tokenize("0.5")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "0.5"

    def test_decimal_multiple_places(self, tokenizer: SQLTokenizer) -> None:
        """Decimal with multiple places should be recognized."""
        tokens = tokenizer.tokenize("123.456789")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.NUMBER
        assert tokens[0].text == "123.456789"

    def test_number_in_comparison(self, tokenizer: SQLTokenizer) -> None:
        """Number in comparison should be recognized."""
        tokens = tokenizer.tokenize("id = 42")
        numbers = [t for t in tokens if t.type == SQLTokenType.NUMBER]
        assert len(numbers) == 1
        assert numbers[0].text == "42"

    def test_number_in_limit(self, tokenizer: SQLTokenizer) -> None:
        """Number in LIMIT clause should be recognized."""
        tokens = tokenizer.tokenize("LIMIT 10")
        numbers = [t for t in tokens if t.type == SQLTokenType.NUMBER]
        assert len(numbers) == 1
        assert numbers[0].text == "10"

    def test_multiple_numbers(self, tokenizer: SQLTokenizer) -> None:
        """Multiple numbers should all be recognized."""
        tokens = tokenizer.tokenize("1, 2, 3")
        numbers = [t for t in tokens if t.type == SQLTokenType.NUMBER]
        assert len(numbers) == 3

    def test_negative_number_as_operator_and_number(self, tokenizer: SQLTokenizer) -> None:
        """Negative number should tokenize as operator + number (- 42)."""
        # In SQL tokenization, -42 is typically operator (-) + number (42)
        tokens = tokenizer.tokenize("-42")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        numbers = [t for t in tokens if t.type == SQLTokenType.NUMBER]
        assert len(operators) == 1
        assert len(numbers) == 1
        assert numbers[0].text == "42"


class TestSQLTokenizerOperators:
    """Test operator tokenization (User Story 3 - T029)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_equals_operator(self, tokenizer: SQLTokenizer) -> None:
        """Equals operator should be recognized."""
        tokens = tokenizer.tokenize("=")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "="

    def test_not_equals_operator(self, tokenizer: SQLTokenizer) -> None:
        """Not equals (<>) operator should be recognized as single token."""
        tokens = tokenizer.tokenize("<>")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "<>"

    def test_not_equals_bang_operator(self, tokenizer: SQLTokenizer) -> None:
        """Not equals (!=) operator should be recognized as single token."""
        tokens = tokenizer.tokenize("!=")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "!="

    def test_less_than_or_equal(self, tokenizer: SQLTokenizer) -> None:
        """Less than or equal (<=) should be recognized."""
        tokens = tokenizer.tokenize("<=")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "<="

    def test_greater_than_or_equal(self, tokenizer: SQLTokenizer) -> None:
        """Greater than or equal (>=) should be recognized."""
        tokens = tokenizer.tokenize(">=")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == ">="

    def test_less_than(self, tokenizer: SQLTokenizer) -> None:
        """Less than (<) should be recognized."""
        tokens = tokenizer.tokenize("<")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "<"

    def test_greater_than(self, tokenizer: SQLTokenizer) -> None:
        """Greater than (>) should be recognized."""
        tokens = tokenizer.tokenize(">")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == ">"

    def test_concatenation_operator(self, tokenizer: SQLTokenizer) -> None:
        """Concatenation (||) operator should be recognized."""
        tokens = tokenizer.tokenize("||")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "||"

    def test_type_cast_operator(self, tokenizer: SQLTokenizer) -> None:
        """Type cast (::) operator should be recognized."""
        tokens = tokenizer.tokenize("::")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "::"

    def test_plus_operator(self, tokenizer: SQLTokenizer) -> None:
        """Plus operator should be recognized."""
        tokens = tokenizer.tokenize("+")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "+"

    def test_minus_operator(self, tokenizer: SQLTokenizer) -> None:
        """Minus operator should be recognized."""
        tokens = tokenizer.tokenize("-")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "-"

    def test_multiply_operator(self, tokenizer: SQLTokenizer) -> None:
        """Multiply operator should be recognized."""
        tokens = tokenizer.tokenize("*")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "*"

    def test_divide_operator(self, tokenizer: SQLTokenizer) -> None:
        """Divide operator should be recognized."""
        tokens = tokenizer.tokenize("/")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "/"

    def test_modulo_operator(self, tokenizer: SQLTokenizer) -> None:
        """Modulo (%) operator should be recognized."""
        tokens = tokenizer.tokenize("%")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.OPERATOR
        assert tokens[0].text == "%"

    def test_operator_in_expression(self, tokenizer: SQLTokenizer) -> None:
        """Operators in expression should be recognized."""
        tokens = tokenizer.tokenize("a + b * c")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 2
        assert operators[0].text == "+"
        assert operators[1].text == "*"

    def test_comparison_expression(self, tokenizer: SQLTokenizer) -> None:
        """Comparison operators in expression should be recognized."""
        tokens = tokenizer.tokenize("x >= 5 AND y <> 10")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 2
        assert operators[0].text == ">="
        assert operators[1].text == "<>"

    def test_type_cast_in_expression(self, tokenizer: SQLTokenizer) -> None:
        """Type cast in expression should be recognized."""
        tokens = tokenizer.tokenize("value::integer")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) == 1
        assert operators[0].text == "::"


class TestSQLTokenizerComments:
    """Test comment tokenization (User Story 3 - T030)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_single_line_comment_simple(self, tokenizer: SQLTokenizer) -> None:
        """Single line comment (--) should be recognized."""
        tokens = tokenizer.tokenize("-- this is a comment")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert tokens[0].text == "-- this is a comment"

    def test_single_line_comment_empty(self, tokenizer: SQLTokenizer) -> None:
        """Empty single line comment should be recognized."""
        tokens = tokenizer.tokenize("--")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert tokens[0].text == "--"

    def test_single_line_comment_after_sql(self, tokenizer: SQLTokenizer) -> None:
        """Single line comment after SQL should be recognized."""
        tokens = tokenizer.tokenize("SELECT 1 -- comment")
        comments = [t for t in tokens if t.type == SQLTokenType.COMMENT]
        assert len(comments) == 1
        assert comments[0].text == "-- comment"

    def test_block_comment_simple(self, tokenizer: SQLTokenizer) -> None:
        """Block comment (/* */) should be recognized."""
        tokens = tokenizer.tokenize("/* comment */")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert tokens[0].text == "/* comment */"

    def test_block_comment_empty(self, tokenizer: SQLTokenizer) -> None:
        """Empty block comment should be recognized."""
        tokens = tokenizer.tokenize("/**/")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert tokens[0].text == "/**/"

    def test_block_comment_multiline(self, tokenizer: SQLTokenizer) -> None:
        """Multi-line block comment should be recognized."""
        tokens = tokenizer.tokenize("/* line1\nline2 */")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert "line1" in tokens[0].text
        assert "line2" in tokens[0].text

    def test_block_comment_with_asterisks(self, tokenizer: SQLTokenizer) -> None:
        """Block comment with asterisks inside should be recognized."""
        tokens = tokenizer.tokenize("/* * * * */")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.COMMENT
        assert tokens[0].text == "/* * * * */"

    def test_block_comment_in_select(self, tokenizer: SQLTokenizer) -> None:
        """Block comment in SELECT should be recognized."""
        tokens = tokenizer.tokenize("SELECT /* columns */ id FROM users")
        comments = [t for t in tokens if t.type == SQLTokenType.COMMENT]
        assert len(comments) == 1
        assert comments[0].text == "/* columns */"

    def test_comment_does_not_consume_following_code(self, tokenizer: SQLTokenizer) -> None:
        """Comment should not consume following code."""
        tokens = tokenizer.tokenize("-- comment\nSELECT")
        comments = [t for t in tokens if t.type == SQLTokenType.COMMENT]
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(comments) == 1
        assert len(keywords) == 1
        assert keywords[0].text == "SELECT"

    def test_minus_not_comment_without_second_dash(self, tokenizer: SQLTokenizer) -> None:
        """Single minus should be operator, not start of comment."""
        tokens = tokenizer.tokenize("5 - 3")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        comments = [t for t in tokens if t.type == SQLTokenType.COMMENT]
        assert len(operators) == 1
        assert operators[0].text == "-"
        assert len(comments) == 0

    def test_slash_not_comment_without_asterisk(self, tokenizer: SQLTokenizer) -> None:
        """Single slash should be operator, not start of comment."""
        tokens = tokenizer.tokenize("10 / 2")
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        comments = [t for t in tokens if t.type == SQLTokenType.COMMENT]
        assert len(operators) == 1
        assert operators[0].text == "/"
        assert len(comments) == 0


class TestSQLTokenizerFunctions:
    """Test function name tokenization (User Story 3)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_function_simple(self, tokenizer: SQLTokenizer) -> None:
        """Function name followed by ( should be recognized."""
        tokens = tokenizer.tokenize("count(")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].text == "count"

    def test_function_with_argument(self, tokenizer: SQLTokenizer) -> None:
        """Function with argument should have function type."""
        tokens = tokenizer.tokenize("count(id)")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].text == "count"

    def test_function_upper_case(self, tokenizer: SQLTokenizer) -> None:
        """Uppercase function name should be recognized."""
        tokens = tokenizer.tokenize("COUNT(id)")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].text == "COUNT"

    def test_function_nested(self, tokenizer: SQLTokenizer) -> None:
        """Nested functions should both be recognized."""
        tokens = tokenizer.tokenize("UPPER(TRIM(name))")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        assert len(functions) == 2
        texts = [f.text for f in functions]
        assert "UPPER" in texts
        assert "TRIM" in texts

    def test_aggregate_functions(self, tokenizer: SQLTokenizer) -> None:
        """Aggregate functions should be recognized."""
        for func in ["sum", "avg", "min", "max", "count"]:
            tokens = tokenizer.tokenize(f"{func}(value)")
            functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
            assert len(functions) == 1, f"{func} should be recognized as function"
            assert functions[0].text == func

    def test_string_function(self, tokenizer: SQLTokenizer) -> None:
        """String functions should be recognized."""
        tokens = tokenizer.tokenize("substring('hello', 1, 3)")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].text == "substring"

    def test_identifier_not_followed_by_paren_is_not_function(
        self, tokenizer: SQLTokenizer
    ) -> None:
        """Identifier not followed by ( should NOT be function."""
        tokens = tokenizer.tokenize("count = 5")
        functions = [t for t in tokens if t.type == SQLTokenType.FUNCTION]
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        assert len(functions) == 0
        assert len(identifiers) == 1
        assert identifiers[0].text == "count"


class TestSQLTokenizerPunctuation:
    """Test punctuation tokenization (User Story 3)."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_comma(self, tokenizer: SQLTokenizer) -> None:
        """Comma should be recognized as punctuation."""
        tokens = tokenizer.tokenize(",")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.PUNCTUATION
        assert tokens[0].text == ","

    def test_semicolon(self, tokenizer: SQLTokenizer) -> None:
        """Semicolon should be recognized as punctuation."""
        tokens = tokenizer.tokenize(";")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.PUNCTUATION
        assert tokens[0].text == ";"

    def test_open_paren(self, tokenizer: SQLTokenizer) -> None:
        """Open parenthesis should be recognized as punctuation."""
        tokens = tokenizer.tokenize("(")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.PUNCTUATION
        assert tokens[0].text == "("

    def test_close_paren(self, tokenizer: SQLTokenizer) -> None:
        """Close parenthesis should be recognized as punctuation."""
        tokens = tokenizer.tokenize(")")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.PUNCTUATION
        assert tokens[0].text == ")"

    def test_dot(self, tokenizer: SQLTokenizer) -> None:
        """Dot should be recognized as punctuation."""
        tokens = tokenizer.tokenize(".")
        assert len(tokens) == 1
        assert tokens[0].type == SQLTokenType.PUNCTUATION
        assert tokens[0].text == "."

    def test_punctuation_in_expression(self, tokenizer: SQLTokenizer) -> None:
        """Punctuation in expression should be recognized."""
        tokens = tokenizer.tokenize("(a, b)")
        punctuation = [t for t in tokens if t.type == SQLTokenType.PUNCTUATION]
        assert len(punctuation) == 3
        texts = [p.text for p in punctuation]
        assert "(" in texts
        assert "," in texts
        assert ")" in texts


class TestSQLTokenizerMalformedSQL:
    """Test malformed SQL handling (graceful degradation) - T044."""

    @pytest.fixture
    def tokenizer(self) -> SQLTokenizer:
        """Create a tokenizer instance."""
        return SQLTokenizer()

    def test_unclosed_single_quote_partial(self, tokenizer: SQLTokenizer) -> None:
        """Unclosed single quote should tokenize what it can."""
        # An unclosed string will match as much as possible or fall through
        # The tokenizer should not crash
        tokens = tokenizer.tokenize("SELECT 'unclosed")
        # Should have at least SELECT token
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) >= 1
        assert keywords[0].text == "SELECT"

    def test_unclosed_double_quote_partial(self, tokenizer: SQLTokenizer) -> None:
        """Unclosed double quote should tokenize what it can."""
        tokens = tokenizer.tokenize('SELECT "unclosed')
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) >= 1
        assert keywords[0].text == "SELECT"

    def test_unclosed_block_comment_partial(self, tokenizer: SQLTokenizer) -> None:
        """Unclosed block comment should tokenize what it can."""
        tokens = tokenizer.tokenize("SELECT /* unclosed comment")
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) >= 1
        assert keywords[0].text == "SELECT"

    def test_unclosed_dollar_quote_partial(self, tokenizer: SQLTokenizer) -> None:
        """Unclosed dollar quote should tokenize what it can."""
        tokens = tokenizer.tokenize("SELECT $$unclosed")
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) >= 1
        assert keywords[0].text == "SELECT"

    def test_mixed_valid_invalid_tokens(self, tokenizer: SQLTokenizer) -> None:
        """Mix of valid and invalid content should tokenize valid parts."""
        # Unicode and special characters that aren't valid SQL
        tokens = tokenizer.tokenize("SELECT \x00 FROM \x01 users")
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        # SELECT and FROM should be recognized
        assert len(keywords) == 2
        # users should be recognized
        assert len(identifiers) == 1
        assert identifiers[0].text == "users"

    def test_invalid_operator_sequence(self, tokenizer: SQLTokenizer) -> None:
        """Invalid operator sequences should be handled gracefully."""
        # Multiple operators in sequence
        tokens = tokenizer.tokenize("SELECT ><><>< FROM users")
        # Should still recognize keywords
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        assert len(keywords) == 2
        # Operators should be tokenized individually or as pairs
        operators = [t for t in tokens if t.type == SQLTokenType.OPERATOR]
        assert len(operators) >= 1

    def test_special_unicode_characters(self, tokenizer: SQLTokenizer) -> None:
        """Unicode characters should be handled as unknown tokens."""
        tokens = tokenizer.tokenize("SELECT \u2603 FROM users")  # snowman
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        unknown = [t for t in tokens if t.type == SQLTokenType.UNKNOWN]
        assert len(keywords) == 2
        assert len(identifiers) == 1
        # Snowman should be unknown
        assert len(unknown) == 1
        assert "\u2603" in unknown[0].text

    def test_empty_quoted_strings_edge_case(self, tokenizer: SQLTokenizer) -> None:
        """Empty quoted strings should be handled."""
        tokens = tokenizer.tokenize("SELECT '' FROM users")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        assert len(strings) == 1
        assert strings[0].text == "''"

    def test_consecutive_strings(self, tokenizer: SQLTokenizer) -> None:
        """Consecutive strings (PostgreSQL string concatenation) should be handled."""
        tokens = tokenizer.tokenize("SELECT 'a''b' FROM users")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        # This is a single string with escaped quote
        assert len(strings) == 1
        assert strings[0].text == "'a''b'"

    def test_very_long_identifier(self, tokenizer: SQLTokenizer) -> None:
        """Very long identifier should be handled."""
        long_id = "a" * 1000
        tokens = tokenizer.tokenize(f"SELECT {long_id} FROM users")
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        assert len(identifiers) == 2
        assert identifiers[0].text == long_id

    def test_very_long_string(self, tokenizer: SQLTokenizer) -> None:
        """Very long string literal should be handled."""
        long_str = "x" * 1000
        tokens = tokenizer.tokenize(f"SELECT '{long_str}' FROM users")
        strings = [t for t in tokens if t.type == SQLTokenType.STRING]
        assert len(strings) == 1
        assert strings[0].text == f"'{long_str}'"

    def test_malformed_numeric_literal(self, tokenizer: SQLTokenizer) -> None:
        """Malformed numeric should be tokenized as best as possible."""
        # Multiple dots - should be tokenized as number + dot + number
        tokens = tokenizer.tokenize("SELECT 1.2.3 FROM users")
        # Should recognize at least some parts
        numbers = [t for t in tokens if t.type == SQLTokenType.NUMBER]
        assert len(numbers) >= 1

    def test_mixed_newlines_and_whitespace(self, tokenizer: SQLTokenizer) -> None:
        """Mixed newlines, tabs, and spaces should be handled."""
        tokens = tokenizer.tokenize("SELECT\n\t  id\r\n  FROM\tusers")
        keywords = [t for t in tokens if t.type == SQLTokenType.KEYWORD]
        identifiers = [t for t in tokens if t.type == SQLTokenType.IDENTIFIER]
        whitespace = [t for t in tokens if t.type == SQLTokenType.WHITESPACE]
        assert len(keywords) == 2
        assert len(identifiers) == 2
        # Whitespace gets merged into continuous runs
        assert len(whitespace) >= 1

    def test_reconstructs_original_with_malformed(self, tokenizer: SQLTokenizer) -> None:
        """Even with malformed SQL, tokens should reconstruct original."""
        sql = "SELECT \x00 'unclosed FROM \u2603 users"
        tokens = tokenizer.tokenize(sql)
        reconstructed = "".join(t.text for t in tokens)
        assert reconstructed == sql

    def test_no_exceptions_on_random_bytes(self, tokenizer: SQLTokenizer) -> None:
        """Random byte sequences should not cause exceptions."""
        # Create a string with various problematic characters
        problematic = "SELECT \x00\x01\x02\x03\xff FROM users"
        # Should not raise any exceptions
        tokens = tokenizer.tokenize(problematic)
        # Should have at least some tokens
        assert len(tokens) > 0
        # Should reconstruct
        reconstructed = "".join(t.text for t in tokens)
        assert reconstructed == problematic
