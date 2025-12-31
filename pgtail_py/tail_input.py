"""Custom Input widget for tail mode command entry.

This module provides TailInput, a subclass of Textual's Input widget that
provides a pre-configured command input with the "tail> " placeholder for
the tail mode interface.

Classes:
    TailInput: Input widget configured for tail mode command entry.
"""

from __future__ import annotations

from typing import ClassVar

from textual.widgets import Input


class TailInput(Input):
    """Input widget for tail mode command entry.

    Extends Textual's Input widget with pre-configured settings for the
    tail mode command input area. Provides the "tail> " placeholder and
    standard id for CSS styling.

    Attributes:
        DEFAULT_ID: The default widget ID for CSS targeting.
        DEFAULT_PLACEHOLDER: The default placeholder text shown when empty.
    """

    DEFAULT_ID: ClassVar[str] = "input"
    DEFAULT_PLACEHOLDER: ClassVar[str] = "tail> "

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
