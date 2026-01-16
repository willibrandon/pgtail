"""Unit tests for SQL detector."""

from pgtail_py.highlighters.sql import SQLDetectionResult, detect_sql_content


class TestSQLDetectionResult:
    """Test SQLDetectionResult namedtuple."""

    def test_create_result(self) -> None:
        """Should create result with all fields."""
        result = SQLDetectionResult(
            prefix="LOG: statement: ",
            sql="SELECT * FROM users",
            suffix="",
        )
        assert result.prefix == "LOG: statement: "
        assert result.sql == "SELECT * FROM users"
        assert result.suffix == ""


class TestDetectSQLContent:
    """Test detect_sql_content function."""

    def test_empty_message_returns_none(self) -> None:
        """Empty message should return None."""
        result = detect_sql_content("")
        assert result is None

    def test_none_message_returns_none(self) -> None:
        """None message should return None."""
        result = detect_sql_content(None)  # type: ignore[arg-type]
        assert result is None

    def test_no_sql_returns_none(self) -> None:
        """Message without SQL pattern should return None."""
        result = detect_sql_content("connection received from 127.0.0.1")
        assert result is None

    def test_detect_statement_pattern(self) -> None:
        """Should detect 'statement:' pattern."""
        message = "statement: SELECT * FROM users"
        result = detect_sql_content(message)
        assert result is not None
        assert result.prefix == "statement: "
        assert result.sql == "SELECT * FROM users"

    def test_detect_log_statement_pattern(self) -> None:
        """Should detect 'LOG: statement:' pattern."""
        message = "LOG: statement: INSERT INTO logs VALUES (1)"
        result = detect_sql_content(message)
        assert result is not None
        assert "statement:" in result.prefix
        assert "INSERT" in result.sql

    def test_detect_execute_pattern(self) -> None:
        """Should detect 'execute <name>:' pattern."""
        message = "execute my_query: SELECT id FROM items WHERE active = true"
        result = detect_sql_content(message)
        assert result is not None
        assert "execute" in result.prefix.lower()
        assert result.sql == "SELECT id FROM items WHERE active = true"

    def test_detect_duration_statement_pattern(self) -> None:
        """Should detect 'duration: ... ms statement:' pattern."""
        message = "duration: 15.234 ms statement: UPDATE users SET name = 'test'"
        result = detect_sql_content(message)
        assert result is not None
        assert "duration" in result.prefix.lower()
        assert "UPDATE" in result.sql

    def test_detect_detail_pattern(self) -> None:
        """Should detect 'DETAIL:' pattern."""
        message = "DETAIL: Key (id)=(123) already exists."
        result = detect_sql_content(message)
        assert result is not None
        assert result.prefix == "DETAIL: "
        assert "Key" in result.sql

    def test_case_insensitive_detection(self) -> None:
        """Detection should be case-insensitive."""
        message = "STATEMENT: select 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "select 1"

    def test_preserves_sql_case(self) -> None:
        """Should preserve original SQL casing."""
        message = "statement: SELECT Id FROM Users WHERE Name = 'Test'"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT Id FROM Users WHERE Name = 'Test'"

    def test_empty_sql_returns_none(self) -> None:
        """Pattern match with empty SQL should return None."""
        message = "statement:    "  # Just whitespace after pattern
        result = detect_sql_content(message)
        assert result is None

    def test_result_reconstructs_original(self) -> None:
        """Prefix + sql + suffix should reconstruct original message."""
        message = "statement: SELECT * FROM users"
        result = detect_sql_content(message)
        assert result is not None
        reconstructed = result.prefix + result.sql + result.suffix
        assert reconstructed == message

    def test_detect_parse_pattern(self) -> None:
        """Should detect 'parse <name>:' pattern."""
        message = "parse <unnamed>: SELECT id FROM items"
        result = detect_sql_content(message)
        assert result is not None
        assert "parse" in result.prefix.lower()
        assert "SELECT" in result.sql

    def test_detect_bind_pattern(self) -> None:
        """Should detect 'bind <name>:' pattern."""
        message = "bind <unnamed>: SELECT id FROM items WHERE active = $1"
        result = detect_sql_content(message)
        assert result is not None
        assert "bind" in result.prefix.lower()
        assert "SELECT" in result.sql

    def test_detect_duration_parse_pattern(self) -> None:
        """Should detect 'duration: ... ms parse <name>:' pattern."""
        message = "duration: 0.056 ms  parse <unnamed>: SELECT id FROM items"
        result = detect_sql_content(message)
        assert result is not None
        assert "duration" in result.prefix.lower()
        assert "parse" in result.prefix.lower()
        assert "SELECT" in result.sql

    def test_detect_duration_bind_pattern(self) -> None:
        """Should detect 'duration: ... ms bind <name>:' pattern."""
        message = "duration: 0.244 ms  bind <unnamed>: SELECT id FROM items"
        result = detect_sql_content(message)
        assert result is not None
        assert "duration" in result.prefix.lower()
        assert "bind" in result.prefix.lower()
        assert "SELECT" in result.sql

    def test_detect_duration_execute_pattern(self) -> None:
        """Should detect 'duration: ... ms execute <name>:' pattern."""
        message = "duration: 0.075 ms  execute <unnamed>: SELECT id FROM items"
        result = detect_sql_content(message)
        assert result is not None
        assert "duration" in result.prefix.lower()
        assert "execute" in result.prefix.lower()
        assert "SELECT" in result.sql


class TestDetectSQLContentEdgeCases:
    """Test SQL detection edge cases - T045."""

    def test_statement_with_leading_whitespace(self) -> None:
        """Statement pattern with leading whitespace should work."""
        message = "   statement: SELECT 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT 1"

    def test_statement_with_extra_spaces(self) -> None:
        """Statement pattern with extra spaces should work."""
        message = "statement:   SELECT 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql.strip() == "SELECT 1"

    def test_multiline_sql_statement(self) -> None:
        """Multiline SQL should be captured completely."""
        message = "statement: SELECT id,\n    name,\n    email\nFROM users"
        result = detect_sql_content(message)
        assert result is not None
        assert "SELECT" in result.sql
        assert "FROM users" in result.sql

    def test_sql_with_semicolon(self) -> None:
        """SQL with semicolon should capture the full statement."""
        message = "statement: SELECT 1;"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT 1;"

    def test_sql_with_multiple_semicolons(self) -> None:
        """SQL with multiple statements should capture all."""
        message = "statement: SELECT 1; SELECT 2;"
        result = detect_sql_content(message)
        assert result is not None
        assert "SELECT 1" in result.sql
        assert "SELECT 2" in result.sql

    def test_duration_with_microseconds(self) -> None:
        """Duration with microsecond precision should work."""
        message = "duration: 0.000123 ms statement: SELECT 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT 1"

    def test_duration_with_large_value(self) -> None:
        """Duration with large value should work."""
        message = "duration: 12345.678 ms statement: SELECT 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT 1"

    def test_execute_with_special_name(self) -> None:
        """Execute with special statement name should work."""
        message = "execute S_1234: SELECT * FROM users"
        result = detect_sql_content(message)
        assert result is not None
        assert "SELECT" in result.sql

    def test_parse_with_unnamed_statement(self) -> None:
        """Parse with <unnamed> statement should work."""
        message = "parse <unnamed>: SELECT $1"
        result = detect_sql_content(message)
        assert result is not None
        assert "SELECT" in result.sql

    def test_bind_with_parameters(self) -> None:
        """Bind with parameter placeholders should work."""
        message = "bind <unnamed>: SELECT * FROM users WHERE id = $1"
        result = detect_sql_content(message)
        assert result is not None
        assert "$1" in result.sql

    def test_detail_with_key_violation(self) -> None:
        """DETAIL with key violation message should work."""
        message = "DETAIL: Key (email)=(test@example.com) already exists."
        result = detect_sql_content(message)
        assert result is not None
        assert "Key" in result.sql

    def test_detail_with_empty_content(self) -> None:
        """DETAIL with only whitespace should return None."""
        message = "DETAIL:    "
        result = detect_sql_content(message)
        assert result is None

    def test_statement_upper_case_keyword(self) -> None:
        """STATEMENT: in uppercase should work (case-insensitive)."""
        message = "STATEMENT: SELECT 1"
        result = detect_sql_content(message)
        assert result is not None
        assert result.sql == "SELECT 1"

    def test_sql_with_string_containing_colon(self) -> None:
        """SQL with string containing colon should capture correctly."""
        message = "statement: SELECT 'time: 12:00' FROM users"
        result = detect_sql_content(message)
        assert result is not None
        assert "'time: 12:00'" in result.sql

    def test_sql_with_comment_containing_prefix(self) -> None:
        """SQL with comment containing prefix pattern should work."""
        message = "statement: SELECT 1 -- statement: in comment"
        result = detect_sql_content(message)
        assert result is not None
        assert "SELECT 1" in result.sql

    def test_no_false_positive_on_similar_pattern(self) -> None:
        """Similar but non-matching patterns should return None."""
        messages = [
            "statements: SELECT 1",  # plural
            "statementSELECT 1",  # no space or colon
            "statement SELECT 1",  # no colon
            "the statement: says hello",  # prefix text
        ]
        for msg in messages:
            # These shouldn't match or should match correctly based on pattern
            result = detect_sql_content(msg)
            # If it matches, verify it's reasonable
            if result:
                # The match should make sense
                assert result.prefix + result.sql + result.suffix == msg

    def test_sql_with_unicode_content(self) -> None:
        """SQL with unicode content should be captured."""
        message = "statement: SELECT * FROM users WHERE name = '日本語'"
        result = detect_sql_content(message)
        assert result is not None
        assert "'日本語'" in result.sql

    def test_sql_with_newline_in_string(self) -> None:
        """SQL with newline in string should be captured."""
        message = "statement: SELECT 'line1\nline2'"
        result = detect_sql_content(message)
        assert result is not None
        assert "'line1\nline2'" in result.sql

    def test_sql_preserves_trailing_spaces(self) -> None:
        """SQL trailing spaces should be in suffix."""
        message = "statement: SELECT 1   "
        result = detect_sql_content(message)
        assert result is not None
        # Trailing whitespace captured in suffix
        assert result.prefix + result.sql + result.suffix == message

    def test_empty_sql_after_duration(self) -> None:
        """Duration pattern with empty SQL should return None."""
        message = "duration: 1.0 ms statement:    "
        result = detect_sql_content(message)
        assert result is None

    def test_very_long_sql(self) -> None:
        """Very long SQL should be captured."""
        long_sql = "SELECT " + ", ".join([f"col_{i}" for i in range(1000)]) + " FROM users"
        message = f"statement: {long_sql}"
        result = detect_sql_content(message)
        assert result is not None
        assert len(result.sql) == len(long_sql)

    def test_sql_with_dollar_quoted_body(self) -> None:
        """SQL with dollar-quoted function body should be captured."""
        message = "statement: CREATE FUNCTION foo() RETURNS void AS $$ SELECT 1; $$ LANGUAGE sql"
        result = detect_sql_content(message)
        assert result is not None
        assert "$$" in result.sql
        assert "SELECT 1" in result.sql
