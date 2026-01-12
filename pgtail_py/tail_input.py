"""Custom Input widget for tail mode command entry.

This module provides TailInput, a subclass of Textual's Input widget that
provides a pre-configured command input with the "tail> " placeholder for
the tail mode interface.

Classes:
    TailInput: Input widget configured for tail mode command entry.
"""

from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding, BindingType
from textual.widgets import Input


class TailInput(Input):
    """Input widget for tail mode command entry.

    Extends Textual's Input widget with pre-configured settings for the
    tail mode command input area. Provides the "tail> " placeholder and
    standard id for CSS styling.

    When the input is empty, single-key commands like 'q' are passed through
    to the app so users can quit without switching focus.

    Attributes:
        DEFAULT_ID: The default widget ID for CSS targeting.
        DEFAULT_PLACEHOLDER: The default placeholder text shown when empty.
    """

    DEFAULT_ID: ClassVar[str] = "input"
    DEFAULT_PLACEHOLDER: ClassVar[str] = "tail> "

    # Allow 'q' to quit when input is empty
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit_if_empty", "Quit", show=False),
        Binding("escape", "clear_and_blur", "Clear", show=False),
    ]

    def __init__(
        self,
        placeholder: str | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize TailInput widget.

        Args:
            placeholder: Optional custom placeholder text. Defaults to "tail> ".
            name: Widget name.
            id: Widget ID for CSS/queries. Defaults to "input".
            classes: CSS classes.
        """
        super().__init__(
            placeholder=placeholder or self.DEFAULT_PLACEHOLDER,
            name=name,
            id=id or self.DEFAULT_ID,
            classes=classes,
        )

    def action_quit_if_empty(self) -> None:
        """Quit app if input is empty, otherwise insert 'q'."""
        if not self.value:
            # Input is empty, trigger app quit
            self.app.action_quit()
        else:
            # Input has content, insert 'q' character
            self.insert_text_at_cursor("q")

    def action_clear_and_blur(self) -> None:
        """Clear input and move focus to log widget."""
        self.value = ""
        # Move focus to log widget
        try:
            log_widget = self.app.query_one("#log")
            log_widget.focus()
        except Exception:
            pass
