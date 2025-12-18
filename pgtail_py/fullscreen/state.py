"""State management for fullscreen TUI mode."""

from enum import Enum, auto


class DisplayMode(Enum):
    """Fullscreen display mode."""

    FOLLOW = auto()  # Auto-scroll to latest entries
    BROWSE = auto()  # Manual navigation


class FullscreenState:
    """Runtime state for fullscreen TUI mode.

    Manages follow/browse mode toggling and search state.
    All state is session-scoped (not persisted).
    """

    def __init__(self) -> None:
        """Initialize with follow mode enabled."""
        self._mode = DisplayMode.FOLLOW
        self._search_active = False
        self._search_pattern: str | None = None

    @property
    def mode(self) -> DisplayMode:
        """Current display mode (FOLLOW or BROWSE)."""
        return self._mode

    @property
    def is_following(self) -> bool:
        """True if in follow mode (auto-scroll)."""
        return self._mode == DisplayMode.FOLLOW

    @property
    def search_active(self) -> bool:
        """True if search prompt is currently visible."""
        return self._search_active

    @property
    def search_pattern(self) -> str | None:
        """Current search pattern, or None if no active search."""
        return self._search_pattern

    def toggle_follow(self) -> None:
        """Toggle between FOLLOW and BROWSE modes.

        If search is active, this is a no-op.
        """
        if not self._search_active:
            self._mode = (
                DisplayMode.BROWSE if self._mode == DisplayMode.FOLLOW else DisplayMode.FOLLOW
            )

    def enter_browse(self) -> None:
        """Switch to browse mode (e.g., on manual scroll)."""
        self._mode = DisplayMode.BROWSE

    def enter_follow(self) -> None:
        """Switch to follow mode and scroll to bottom."""
        self._mode = DisplayMode.FOLLOW

    def set_search_active(self, active: bool) -> None:
        """Set search prompt visibility state."""
        self._search_active = active

    def set_search_pattern(self, pattern: str | None) -> None:
        """Set the current search pattern."""
        self._search_pattern = pattern
