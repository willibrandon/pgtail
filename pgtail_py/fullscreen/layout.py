"""Layout components for fullscreen TUI mode."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.widgets import SearchToolbar, TextArea

from pgtail_py.fullscreen.buffer_lexer import BufferLexer

if TYPE_CHECKING:
    from pgtail_py.fullscreen.buffer import LogBuffer
    from pgtail_py.fullscreen.state import FullscreenState


def _wrap_scroll_method(
    original_method: Callable[[], None],
    state: FullscreenState,
) -> Callable[[], None]:
    """Wrap a scroll method to enter browse mode before scrolling.

    Args:
        original_method: The original _scroll_up or _scroll_down method
        state: FullscreenState to update on scroll

    Returns:
        Wrapped method that enters browse mode first
    """

    def wrapped() -> None:
        state.enter_browse()
        original_method()

    return wrapped


def _wrap_mouse_handler(
    original_handler: Callable[[MouseEvent], Any],
    state: FullscreenState,
) -> Callable[[MouseEvent], Any]:
    """Wrap a mouse handler to enter browse mode on mouse click.

    Args:
        original_handler: The original mouse_handler method
        state: FullscreenState to update on click

    Returns:
        Wrapped handler that enters browse mode on MOUSE_DOWN
    """

    def wrapped(mouse_event: MouseEvent) -> Any:
        # Enter browse mode on mouse click (not on scroll - that's handled separately)
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            state.enter_browse()
        return original_handler(mouse_event)

    return wrapped


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

    Uses BufferLexer to display the exact same styling as streaming mode.
    The buffer stores pre-styled FormattedText, and BufferLexer returns
    this styling directly rather than re-parsing with a different lexer.

    Args:
        buffer: LogBuffer for content
        state: FullscreenState for status display

    Returns:
        Tuple of (Layout, TextArea, SearchToolbar) for reference
    """
    search_toolbar = SearchToolbar()

    text = buffer.get_text()
    text_area = TextArea(
        text=text,
        read_only=True,
        scrollbar=True,
        search_field=search_toolbar,
        lexer=BufferLexer(buffer),
    )

    # Start at the end (tail) for follow mode
    text_area.buffer.cursor_position = len(text)

    # Wrap the Window's scroll methods to enter browse mode on mouse scroll
    window = text_area.window
    window._scroll_up = _wrap_scroll_method(window._scroll_up, state)  # type: ignore[method-assign]
    window._scroll_down = _wrap_scroll_method(window._scroll_down, state)  # type: ignore[method-assign]

    # Wrap the BufferControl's mouse handler to enter browse mode on click
    control = text_area.control
    control.mouse_handler = _wrap_mouse_handler(control.mouse_handler, state)  # type: ignore[method-assign]

    def get_status_text() -> str:
        """Generate dynamic status bar text."""
        mode = "FOLLOW" if state.is_following else "BROWSE"
        line_count = len(buffer)
        return f" {mode} | {line_count} lines | q=quit /=search f=follow Esc=toggle "

    status_bar = Window(
        content=FormattedTextControl(get_status_text),
        height=D.exact(1),
        style="reverse",
    )

    root = HSplit([text_area, search_toolbar, status_bar])
    return Layout(root, focused_element=text_area), text_area, search_toolbar
