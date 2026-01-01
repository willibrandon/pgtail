"""Tests for pgtail_py.cli_tail_filters module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pgtail_py.cli_tail_filters import (
    _is_field_filter_arg,
    handle_clear_command,
    handle_filter_command,
)
from pgtail_py.field_filter import FieldFilterState
from pgtail_py.format_detector import LogFormat
from pgtail_py.regex_filter import FilterState, FilterType


class TestIsFieldFilterArg:
    """Tests for _is_field_filter_arg helper."""

    def test_valid_field_filters(self) -> None:
        """Valid field=value patterns should return True."""
        assert _is_field_filter_arg("app=myapp") is True
        assert _is_field_filter_arg("db=production") is True
        assert _is_field_filter_arg("user=postgres") is True
        assert _is_field_filter_arg("application=test") is True
        assert _is_field_filter_arg("database=mydb") is True

    def test_invalid_field_filters(self) -> None:
        """Invalid patterns should return False."""
        assert _is_field_filter_arg("/pattern/") is False
        assert _is_field_filter_arg("-/pattern/") is False
        assert _is_field_filter_arg("unknown=value") is False
        assert _is_field_filter_arg("noequalssign") is False


class TestHandleFilterCommand:
    """Tests for handle_filter_command with full syntax support."""

    @pytest.fixture
    def mock_state(self) -> MagicMock:
        """Create mock AppState."""
        state = MagicMock()
        state.regex_state = FilterState.empty()
        state.field_filter = FieldFilterState()
        return state

    @pytest.fixture
    def mock_tailer(self) -> MagicMock:
        """Create mock LogTailer."""
        tailer = MagicMock()
        tailer.format = LogFormat.JSON
        return tailer

    @pytest.fixture
    def mock_status(self) -> MagicMock:
        """Create mock TailStatus."""
        return MagicMock()

    @pytest.fixture
    def mock_log_widget(self) -> MagicMock:
        """Create mock TailLog widget."""
        return MagicMock()

    def test_include_pattern(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """Plain /pattern/ sets include filter."""
        result = handle_filter_command(
            ["/error/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        assert result is True
        assert len(mock_state.regex_state.includes) == 1
        assert mock_state.regex_state.includes[0].pattern == "error"
        assert mock_state.regex_state.includes[0].filter_type == FilterType.INCLUDE

    def test_exclude_pattern(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """-/pattern/ adds exclude filter."""
        result = handle_filter_command(
            ["-/noise/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        assert result is True
        assert len(mock_state.regex_state.excludes) == 1
        assert mock_state.regex_state.excludes[0].pattern == "noise"
        assert mock_state.regex_state.excludes[0].filter_type == FilterType.EXCLUDE

    def test_or_pattern(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """+/pattern/ adds to includes (OR logic)."""
        # First set an include
        handle_filter_command(
            ["/error/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        # Then add OR pattern
        result = handle_filter_command(
            ["+/warning/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        assert result is True
        assert len(mock_state.regex_state.includes) == 2
        assert mock_state.regex_state.includes[1].pattern == "warning"

    def test_and_pattern(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """&/pattern/ adds AND filter."""
        result = handle_filter_command(
            ["&/critical/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        assert result is True
        assert len(mock_state.regex_state.ands) == 1
        assert mock_state.regex_state.ands[0].pattern == "critical"
        assert mock_state.regex_state.ands[0].filter_type == FilterType.AND

    def test_case_sensitive_pattern(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """/pattern/c enables case-sensitive matching."""
        result = handle_filter_command(
            ["/Error/c"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )
        assert result is True
        assert mock_state.regex_state.includes[0].case_sensitive is True

    def test_field_filter(
        self,
        mock_state: MagicMock,
        mock_tailer: MagicMock,
        mock_status: MagicMock,
        mock_log_widget: MagicMock,
    ) -> None:
        """field=value sets field filter."""
        result = handle_filter_command(
            ["app=myapp"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=mock_log_widget,
        )
        assert result is True
        assert mock_state.field_filter.is_active() is True
        mock_tailer.update_field_filter.assert_called()

    def test_field_filter_warns_on_text_format(
        self,
        mock_state: MagicMock,
        mock_tailer: MagicMock,
        mock_status: MagicMock,
        mock_log_widget: MagicMock,
    ) -> None:
        """Field filter warns when log format is TEXT."""
        mock_tailer.format = LogFormat.TEXT
        result = handle_filter_command(
            ["app=myapp"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=mock_log_widget,
        )
        assert result is True
        # Should have written warning
        mock_log_widget.write_line.assert_any_call(
            "[yellow]Warning:[/] Field filtering only works for CSV/JSON logs"
        )

    def test_clear_subcommand(
        self,
        mock_state: MagicMock,
        mock_tailer: MagicMock,
        mock_status: MagicMock,
        mock_log_widget: MagicMock,
    ) -> None:
        """filter clear clears all filters including field filters."""
        # Set some filters first
        mock_state.field_filter.add("app", "test")
        handle_filter_command(
            ["/error/"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )

        # Now clear
        result = handle_filter_command(
            ["clear"],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=mock_log_widget,
        )
        assert result is True
        assert mock_state.field_filter.is_active() is False
        mock_tailer.update_field_filter.assert_called()

    def test_no_args_shows_status(
        self,
        mock_state: MagicMock,
        mock_tailer: MagicMock,
        mock_status: MagicMock,
        mock_log_widget: MagicMock,
    ) -> None:
        """No args shows current filter status."""
        result = handle_filter_command(
            [],
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=mock_log_widget,
        )
        assert result is True
        mock_log_widget.write_line.assert_called()


class TestHandleClearCommand:
    """Tests for handle_clear_command."""

    @pytest.fixture
    def mock_state(self) -> MagicMock:
        """Create mock AppState with field_filter."""
        state = MagicMock()
        state.field_filter = FieldFilterState()
        return state

    @pytest.fixture
    def mock_tailer(self) -> MagicMock:
        """Create mock LogTailer."""
        return MagicMock()

    @pytest.fixture
    def mock_status(self) -> MagicMock:
        """Create mock TailStatus."""
        return MagicMock()

    def test_clear_resets_field_filter(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """handle_clear_command should reset field_filter."""
        # Add a field filter first
        mock_state.field_filter.add("app", "test")
        assert mock_state.field_filter.is_active() is True

        result = handle_clear_command(
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )

        assert result is True
        assert mock_state.field_filter.is_active() is False
        mock_tailer.update_field_filter.assert_called_with(mock_state.field_filter)

    def test_clear_updates_tailer_field_filter(
        self, mock_state: MagicMock, mock_tailer: MagicMock, mock_status: MagicMock
    ) -> None:
        """handle_clear_command should update tailer's field filter."""
        result = handle_clear_command(
            buffer=None,
            status=mock_status,
            state=mock_state,
            tailer=mock_tailer,
            log_widget=None,
        )

        assert result is True
        mock_tailer.update_field_filter.assert_called()
