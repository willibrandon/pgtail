"""Layout components for fullscreen TUI mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import SearchToolbar, TextArea

if TYPE_CHECKING:
    from pgtail_py.fullscreen.buffer import LogBuffer
    from pgtail_py.fullscreen.state import FullscreenState


def create_layout(
    buffer: LogBuffer,
    state: FullscreenState,
) -> tuple[Layout, TextArea, SearchToolbar]:
    """Create fullscreen layout with log view, search bar, and status bar.

    Layout structure:
    ┌─────────────────────────────────┐
    │         Log View                │ (flexible height)
    │    (TextArea, scrollable)       │
    ├─────────────────────────────────┤
    │ Search: /pattern                │ (conditional, height=1)
    ├─────────────────────────────────┤
    │ FOLLOW | 1234 lines | q=quit    │ (fixed height=1)
    └─────────────────────────────────┘

    Args:
        buffer: LogBuffer for content
        state: FullscreenState for status display

    Returns:
        Tuple of (Layout, TextArea, SearchToolbar) for reference
    """
    search_toolbar = SearchToolbar()

    text_area = TextArea(
        text=buffer.get_text(),
        read_only=True,
        scrollbar=True,
        search_field=search_toolbar,
    )

    def get_status_text() -> str:
        """Generate dynamic status bar text."""
        mode = "FOLLOW" if state.is_following else "BROWSE"
        line_count = len(buffer)
        return f" {mode} | {line_count} lines | q=quit "

    status_bar = Window(
        content=FormattedTextControl(get_status_text),
        height=D.exact(1),
        style="reverse",
    )

    root = HSplit([text_area, search_toolbar, status_bar])
    return Layout(root, focused_element=text_area), text_area, search_toolbar
