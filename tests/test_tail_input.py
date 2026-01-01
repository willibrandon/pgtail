"""Tests for pgtail_py.tail_input module."""

from __future__ import annotations

import pytest

from pgtail_py.tail_input import TailInput


class TestTailInput:
    """Tests for TailInput widget."""

    def test_default_id(self) -> None:
        """Test that TailInput has default ID 'input'."""
        widget = TailInput()
        assert widget.id == "input"

    def test_default_placeholder(self) -> None:
        """Test that TailInput has default placeholder 'tail> '."""
        widget = TailInput()
        assert widget.placeholder == "tail> "

    def test_custom_placeholder(self) -> None:
        """Test that TailInput accepts custom placeholder."""
        widget = TailInput(placeholder="custom> ")
        assert widget.placeholder == "custom> "

    def test_custom_id(self) -> None:
        """Test that TailInput accepts custom ID."""
        widget = TailInput(id="custom-input")
        assert widget.id == "custom-input"

    def test_custom_classes(self) -> None:
        """Test that TailInput accepts custom classes."""
        widget = TailInput(classes="my-class")
        assert "my-class" in widget.classes

    def test_inherits_from_input(self) -> None:
        """Test that TailInput inherits from Textual Input."""
        from textual.widgets import Input

        widget = TailInput()
        assert isinstance(widget, Input)
