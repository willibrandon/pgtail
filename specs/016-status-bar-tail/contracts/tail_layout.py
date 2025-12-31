"""Contract: TailLayout interface for Status Bar Tail Mode.

This module defines the interface for the HSplit-based layout builder
that creates the three-pane interface.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Container, Layout


class TailLayoutProtocol(Protocol):
    """Protocol for the split-screen layout manager."""

    @property
    def root(self) -> Container:
        """Top-level container (HSplit) for the layout."""
        ...

    @property
    def layout(self) -> Layout:
        """prompt_toolkit Layout wrapping the root container."""
        ...

    @property
    def input_buffer(self) -> Buffer:
        """Editable buffer for the command input line."""
        ...

    def get_key_bindings(self) -> KeyBindings:
        """Return key bindings for tail mode navigation.

        Returns:
            KeyBindings with handlers for:
            - Up/Down: single line scroll
            - Page Up/Page Down: page scroll
            - Home: scroll to start
            - End: resume follow
            - Ctrl+L: redraw
            - Enter: submit command
        """
        ...


class TailLayoutBuilder(Protocol):
    """Protocol for building the tail mode layout."""

    def build(
        self,
        log_content_callback: Callable[[], FormattedText],
        status_content_callback: Callable[[], FormattedText],
        on_command_submit: Callable[[str], None],
        on_scroll_up: Callable[[int], None],
        on_scroll_down: Callable[[int], None],
        on_scroll_to_top: Callable[[], None],
        on_resume_follow: Callable[[], None],
    ) -> TailLayoutProtocol:
        """Build the complete tail mode layout.

        Args:
            log_content_callback: Returns FormattedText for log area
            status_content_callback: Returns FormattedText for status bar
            on_command_submit: Called when user presses Enter in input
            on_scroll_up: Called with line count for scroll up events
            on_scroll_down: Called with line count for scroll down events
            on_scroll_to_top: Called for Home key
            on_resume_follow: Called for End key

        Returns:
            Configured TailLayoutProtocol instance
        """
        ...


# Layout dimensions
LAYOUT_CONFIG = {
    'status_bar_height': 1,  # Fixed 1 line
    'input_line_height': 1,  # Fixed 1 line
    'min_log_height': 5,     # Minimum lines for log area
    'min_terminal_width': 40,
    'min_terminal_height': 10,
    'scroll_lines_per_wheel': 3,  # Lines per mouse wheel tick
}


# Style classes used in the layout
LAYOUT_STYLES = {
    # Log area
    'class:log': '',  # Base log text

    # Status bar
    'class:status': 'bg:ansiblue fg:ansiwhite',
    'class:status.follow': 'fg:ansigreen bold',
    'class:status.paused': 'fg:ansiyellow bold',
    'class:status.error': 'fg:ansired',
    'class:status.warning': 'fg:ansiyellow',
    'class:status.sep': 'fg:ansibrightblack',
    'class:status.filter': 'fg:ansicyan',
    'class:status.instance': 'fg:ansiwhite',

    # Input line
    'class:input': '',
    'class:input.prompt': 'fg:ansigreen bold',

    # Command output separators
    'class:separator': 'fg:ansibrightblack',

    # Warning for small terminal
    'class:warning': 'fg:ansiyellow bold',
}
