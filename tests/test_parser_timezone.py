"""Tests for timezone parsing in parser_csv.py and parser_json.py."""

from __future__ import annotations

from datetime import timezone

from pgtail_py.parser_csv import parse_timestamp as parse_csv_timestamp
from pgtail_py.parser_json import parse_timestamp as parse_json_timestamp


class TestCSVTimestampParsing:
    """Tests for CSV parser timestamp handling."""

    def test_parses_utc_timezone(self) -> None:
        """Parses timestamp with UTC timezone."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 UTC")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10
        assert result.minute == 30

    def test_parses_gmt_timezone(self) -> None:
        """Parses timestamp with GMT timezone."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 GMT")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10

    def test_parses_pst_timezone(self) -> None:
        """Parses timestamp with PST timezone and converts to UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 PST")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # PST is UTC-8, so 10:30 PST = 18:30 UTC
        assert result.hour == 18

    def test_parses_pdt_timezone(self) -> None:
        """Parses timestamp with PDT timezone and converts to UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 PDT")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # PDT is UTC-7, so 10:30 PDT = 17:30 UTC
        assert result.hour == 17

    def test_parses_est_timezone(self) -> None:
        """Parses timestamp with EST timezone and converts to UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 EST")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # EST is UTC-5, so 10:30 EST = 15:30 UTC
        assert result.hour == 15

    def test_parses_cet_timezone(self) -> None:
        """Parses timestamp with CET timezone and converts to UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 CET")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # CET is UTC+1, so 10:30 CET = 09:30 UTC
        assert result.hour == 9

    def test_parses_jst_timezone(self) -> None:
        """Parses timestamp with JST timezone and converts to UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 JST")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # JST is UTC+9, so 10:30 JST = 01:30 UTC
        assert result.hour == 1

    def test_parses_iso8601_z_suffix(self) -> None:
        """Parses ISO 8601 timestamp with Z suffix."""
        result = parse_csv_timestamp("2024-01-15T10:30:45.123Z")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10

    def test_parses_iso8601_positive_offset(self) -> None:
        """Parses ISO 8601 timestamp with positive offset."""
        result = parse_csv_timestamp("2024-01-15T10:30:45.123+05:00")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # +05:00 means 10:30 local = 05:30 UTC
        assert result.hour == 5

    def test_parses_iso8601_negative_offset(self) -> None:
        """Parses ISO 8601 timestamp with negative offset."""
        result = parse_csv_timestamp("2024-01-15T10:30:45.123-08:00")
        assert result is not None
        assert result.tzinfo == timezone.utc
        # -08:00 means 10:30 local = 18:30 UTC
        assert result.hour == 18

    def test_parses_iso8601_short_offset(self) -> None:
        """Parses ISO 8601 timestamp with short offset format."""
        result = parse_csv_timestamp("2024-01-15T10:30:45.123+00")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10

    def test_parses_without_microseconds(self) -> None:
        """Parses timestamp without microseconds."""
        result = parse_csv_timestamp("2024-01-15 10:30:45 UTC")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.second == 45

    def test_unknown_timezone_assumes_utc(self) -> None:
        """Unknown timezone abbreviation assumes UTC."""
        result = parse_csv_timestamp("2024-01-15 10:30:45.123 XYZ")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        result = parse_csv_timestamp("")
        assert result is None

    def test_returns_none_for_invalid_format(self) -> None:
        """Returns None for invalid timestamp format."""
        result = parse_csv_timestamp("not a timestamp")
        assert result is None


class TestJSONTimestampParsing:
    """Tests for JSON parser timestamp handling."""

    def test_parses_utc_timezone(self) -> None:
        """Parses timestamp with UTC timezone."""
        result = parse_json_timestamp("2024-01-15 10:30:45.123 UTC")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parses_iso8601_z_suffix(self) -> None:
        """Parses ISO 8601 timestamp with Z suffix."""
        result = parse_json_timestamp("2024-01-15T10:30:45.123Z")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parses_iso8601_offset(self) -> None:
        """Parses ISO 8601 timestamp with offset."""
        result = parse_json_timestamp("2024-01-15T10:30:45.123+00:00")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_returns_none_for_none_input(self) -> None:
        """Returns None for None input."""
        result = parse_json_timestamp(None)
        assert result is None
