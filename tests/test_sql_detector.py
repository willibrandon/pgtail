"""Unit tests for SQL detector."""

import pytest

from pgtail_py.sql_detector import SQLDetectionResult, detect_sql_content


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
