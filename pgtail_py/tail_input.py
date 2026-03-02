"""Custom Input widget for tail mode command entry.

This module provides TailInput, a subclass of Textual's Input widget that
provides a pre-configured command input with the "tail> " placeholder for
the tail mode interface. Supports optional command history navigation
(Up/Down arrows) and ghost text suggestions via Textual's Suggester API.

Classes:
    TailInput: Input widget configured for tail mode command entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.suggester import Suggester
from textual.widgets import Input

if TYPE_CHECKING:
    from pgtail_py.tail_history import TailCommandHistory


class TailInput(Input):
    """Input widget for tail mode command entry.

    Extends Textual's Input widget with pre-configured settings for the
    tail mode command input area. Provides the "tail> " placeholder and
    standard id for CSS styling.

    When the input is empty, single-key commands like 'q' are passed through
    to the app so users can quit without switching focus.

    Optional history navigation (Up/Down arrows) and ghost text suggestions
    are enabled by passing ``history`` and ``suggester`` to the constructor.

    Attributes:
        DEFAULT_ID: The default widget ID for CSS targeting.
        DEFAULT_PLACEHOLDER: The default placeholder text shown when empty.
    """

    DEFAULT_ID: ClassVar[str] = "input"
    DEFAULT_PLACEHOLDER: ClassVar[str] = "tail> "

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit_if_empty", "Quit", show=False),
        Binding("escape", "clear_and_blur", "Clear", show=False),
        Binding("up", "history_back", "History back", show=False),
        Binding("down", "history_forward", "History forward", show=False),
    ]

    def __init__(
        self,
        placeholder: str | None = None,
        *,
        history: TailCommandHistory | None = None,
        suggester: Suggester | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize TailInput widget.

        Args:
            placeholder: Optional custom placeholder text. Defaults to "tail> ".
            history: Optional command history for Up/Down navigation (FR-023).
            suggester: Optional ghost text suggester (FR-023).
            name: Widget name.
            id: Widget ID for CSS/queries. Defaults to "input".
            classes: CSS classes.
        """
        super().__init__(
            placeholder=placeholder or self.DEFAULT_PLACEHOLDER,
            suggester=suggester,
            name=name,
            id=id or self.DEFAULT_ID,
            classes=classes,
        )
        self._history: TailCommandHistory | None = history
        self._navigating: bool = False

    def watch_value(self, value: str) -> None:
        """Reset history navigation on non-guarded value changes.

        When the user types, deletes, or accepts a ghost suggestion, the
        value changes without the ``_navigating`` guard being set. This
        resets history navigation to at-rest (FR-004, FR-025, FR-026).

        Programmatic value changes during navigation set the guard first,
        so this watcher skips the reset in that case.
        """
        if not self._navigating and self._history:
            self._history.reset_navigation()

    def action_history_back(self) -> None:
        """Navigate to an older history entry (FR-002).

        Sets the ``_navigating`` guard around the programmatic value
        assignment to prevent ``watch_value`` from resetting navigation.
        """
        if not self._history:
            return
        entry = self._history.navigate_back(self.value)
        if entry is not None:
            self._navigating = True
            try:
                self.value = entry
                self.cursor_position = len(entry)
            finally:
                self._navigating = False

    def action_history_forward(self) -> None:
        """Navigate to a newer history entry or restore saved input (FR-003).

        Sets the ``_navigating`` guard around the programmatic value
        assignment to prevent ``watch_value`` from resetting navigation.
        """
        if not self._history:
            return
        text, _restored = self._history.navigate_forward()
        if text is None:
            return  # no-op (already at-rest)
        self._navigating = True
        try:
            self.value = text
            self.cursor_position = len(text)
        finally:
            self._navigating = False

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
