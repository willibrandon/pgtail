"""Unit tests for FullscreenState mode transitions."""

from pgtail_py.fullscreen.state import DisplayMode, FullscreenState


class TestFullscreenStateInit:
    """Tests for FullscreenState initialization."""

    def test_default_mode_is_follow(self) -> None:
        """Initial mode is FOLLOW."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

    def test_is_following_true_initially(self) -> None:
        """is_following is True initially."""
        state = FullscreenState()
        assert state.is_following is True

    def test_search_not_active_initially(self) -> None:
        """search_active is False initially."""
        state = FullscreenState()
        assert state.search_active is False

    def test_search_pattern_none_initially(self) -> None:
        """search_pattern is None initially."""
        state = FullscreenState()
        assert state.search_pattern is None


class TestToggleFollow:
    """Tests for FullscreenState.toggle_follow()."""

    def test_toggle_from_follow_to_browse(self) -> None:
        """toggle_follow() switches from FOLLOW to BROWSE."""
        state = FullscreenState()
        state.toggle_follow()
        assert state.mode == DisplayMode.BROWSE
        assert state.is_following is False

    def test_toggle_from_browse_to_follow(self) -> None:
        """toggle_follow() switches from BROWSE to FOLLOW."""
        state = FullscreenState()
        state.enter_browse()
        state.toggle_follow()
        assert state.mode == DisplayMode.FOLLOW
        assert state.is_following is True

    def test_toggle_noop_during_search(self) -> None:
        """toggle_follow() is a no-op when search is active."""
        state = FullscreenState()
        state.set_search_active(True)
        state.toggle_follow()
        assert state.mode == DisplayMode.FOLLOW  # Unchanged


class TestEnterBrowse:
    """Tests for FullscreenState.enter_browse()."""

    def test_enter_browse_from_follow(self) -> None:
        """enter_browse() switches from FOLLOW to BROWSE."""
        state = FullscreenState()
        state.enter_browse()
        assert state.mode == DisplayMode.BROWSE

    def test_enter_browse_idempotent(self) -> None:
        """enter_browse() when already in BROWSE is a no-op."""
        state = FullscreenState()
        state.enter_browse()
        state.enter_browse()
        assert state.mode == DisplayMode.BROWSE


class TestEnterFollow:
    """Tests for FullscreenState.enter_follow()."""

    def test_enter_follow_from_browse(self) -> None:
        """enter_follow() switches from BROWSE to FOLLOW."""
        state = FullscreenState()
        state.enter_browse()
        state.enter_follow()
        assert state.mode == DisplayMode.FOLLOW

    def test_enter_follow_idempotent(self) -> None:
        """enter_follow() when already in FOLLOW is a no-op."""
        state = FullscreenState()
        state.enter_follow()
        assert state.mode == DisplayMode.FOLLOW


class TestSearchState:
    """Tests for search state management."""

    def test_set_search_active_true(self) -> None:
        """set_search_active(True) enables search mode."""
        state = FullscreenState()
        state.set_search_active(True)
        assert state.search_active is True

    def test_set_search_active_false(self) -> None:
        """set_search_active(False) disables search mode."""
        state = FullscreenState()
        state.set_search_active(True)
        state.set_search_active(False)
        assert state.search_active is False

    def test_set_search_pattern(self) -> None:
        """set_search_pattern() sets the pattern."""
        state = FullscreenState()
        state.set_search_pattern("error")
        assert state.search_pattern == "error"

    def test_clear_search_pattern(self) -> None:
        """set_search_pattern(None) clears the pattern."""
        state = FullscreenState()
        state.set_search_pattern("error")
        state.set_search_pattern(None)
        assert state.search_pattern is None


class TestDisplayModeEnum:
    """Tests for DisplayMode enum."""

    def test_follow_mode_exists(self) -> None:
        """FOLLOW mode exists."""
        assert DisplayMode.FOLLOW is not None

    def test_browse_mode_exists(self) -> None:
        """BROWSE mode exists."""
        assert DisplayMode.BROWSE is not None

    def test_modes_are_distinct(self) -> None:
        """FOLLOW and BROWSE are distinct values."""
        assert DisplayMode.FOLLOW != DisplayMode.BROWSE
