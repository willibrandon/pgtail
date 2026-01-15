"""Tests for connection highlighters (T063).

Tests cover:
- ConnectionHighlighter: Host, port, user, database info
- IPHighlighter: IPv4, IPv6, CIDR notation
- BackendHighlighter: Backend process names
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.connection import (
    BackendHighlighter,
    ConnectionHighlighter,
    IPHighlighter,
    get_connection_highlighters,
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
            "hl_connection": ColorStyle(fg="cyan"),
            "hl_host": ColorStyle(fg="cyan"),
            "hl_port": ColorStyle(fg="cyan"),
            "hl_user": ColorStyle(fg="magenta"),
            "hl_database": ColorStyle(fg="green"),
            "hl_ip": ColorStyle(fg="cyan"),
            "hl_backend": ColorStyle(fg="yellow"),
        },
    )


# =============================================================================
# Test ConnectionHighlighter
# =============================================================================


class TestConnectionHighlighter:
    """Tests for ConnectionHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = ConnectionHighlighter()
        assert h.name == "connection"
        assert h.priority == 600
        assert "connection" in h.description.lower()

    def test_host_field(self, test_theme: Theme) -> None:
        """Should match host=value pattern."""
        h = ConnectionHighlighter()
        text = "connection from host=192.168.1.1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "host=192.168.1.1"
        assert matches[0].style == "hl_host"

    def test_port_field(self, test_theme: Theme) -> None:
        """Should match port=value pattern."""
        h = ConnectionHighlighter()
        text = "listening on port=5432"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "port=5432"
        assert matches[0].style == "hl_port"

    def test_user_field(self, test_theme: Theme) -> None:
        """Should match user=value pattern."""
        h = ConnectionHighlighter()
        text = "connection authorized: user=postgres"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "user=postgres"
        assert matches[0].style == "hl_user"

    def test_database_field(self, test_theme: Theme) -> None:
        """Should match database=value pattern."""
        h = ConnectionHighlighter()
        text = "connection to database=mydb"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "database=mydb"
        assert matches[0].style == "hl_database"

    def test_application_name_field(self, test_theme: Theme) -> None:
        """Should match application_name=value pattern."""
        h = ConnectionHighlighter()
        text = 'application_name=psql connected'
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "application_name=psql"

    def test_multiple_fields(self, test_theme: Theme) -> None:
        """Should match multiple connection fields."""
        h = ConnectionHighlighter()
        text = "connection received: host=192.168.1.1 port=5432 user=postgres database=mydb"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 4
        fields = {m.text.split("=")[0] for m in matches}
        assert fields == {"host", "port", "user", "database"}


# =============================================================================
# Test IPHighlighter
# =============================================================================


class TestIPHighlighter:
    """Tests for IPHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = IPHighlighter()
        assert h.name == "ip"
        assert h.priority == 610
        assert "ip" in h.description.lower()

    def test_ipv4_address(self, test_theme: Theme) -> None:
        """Should match IPv4 addresses."""
        h = IPHighlighter()
        text = "connecting from 192.168.1.100"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "192.168.1.100"
        assert matches[0].style == "hl_ip"

    def test_ipv4_with_cidr(self, test_theme: Theme) -> None:
        """Should match IPv4 with CIDR notation."""
        h = IPHighlighter()
        text = "allowed from 10.0.0.0/8"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert "10.0.0.0/8" in matches[0].text

    def test_ipv6_localhost(self, test_theme: Theme) -> None:
        """Should match IPv6 localhost."""
        h = IPHighlighter()
        text = "listening on ::1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_ipv6_full(self, test_theme: Theme) -> None:
        """Should match full IPv6 address."""
        h = IPHighlighter()
        text = "from 2001:db8:85a3:0000:0000:8a2e:0370:7334"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_multiple_ips(self, test_theme: Theme) -> None:
        """Should match multiple IP addresses."""
        h = IPHighlighter()
        text = "connection from 192.168.1.1 to 10.0.0.1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2


# =============================================================================
# Test BackendHighlighter
# =============================================================================


class TestBackendHighlighter:
    """Tests for BackendHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = BackendHighlighter()
        assert h.name == "backend"
        assert h.priority == 620
        assert "backend" in h.description.lower()

    def test_autovacuum(self, test_theme: Theme) -> None:
        """Should match autovacuum backend."""
        h = BackendHighlighter()
        text = "autovacuum: processing table"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "autovacuum"
        assert matches[0].style == "hl_backend"

    def test_checkpointer(self, test_theme: Theme) -> None:
        """Should match checkpointer backend."""
        h = BackendHighlighter()
        text = "checkpointer: starting"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "checkpointer"

    def test_background_writer(self, test_theme: Theme) -> None:
        """Should match background writer."""
        h = BackendHighlighter()
        text = "background writer: flushed 5 pages"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_walwriter(self, test_theme: Theme) -> None:
        """Should match WAL writer."""
        h = BackendHighlighter()
        text = "walwriter: syncing segment"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_walsender(self, test_theme: Theme) -> None:
        """Should match WAL sender."""
        h = BackendHighlighter()
        text = "walsender: streaming to replica"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_parallel_worker(self, test_theme: Theme) -> None:
        """Should match parallel worker."""
        h = BackendHighlighter()
        text = "parallel worker: starting"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = BackendHighlighter()
        text = "AUTOVACUUM: processing"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_connection_highlighters(self) -> None:
        """get_connection_highlighters should return all highlighters."""
        highlighters = get_connection_highlighters()

        assert len(highlighters) == 3
        names = {h.name for h in highlighters}
        assert names == {"connection", "ip", "backend"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 600-699 range."""
        highlighters = get_connection_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(600 <= p < 700 for p in priorities)
