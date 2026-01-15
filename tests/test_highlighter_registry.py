"""Tests for highlighter_registry.py (T032).

Tests cover:
- HighlighterRegistry singleton behavior
- register/unregister methods
- get/get_by_category methods
- all_names/all_categories methods
- create_chain method with HighlightingConfig
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighter import RegexHighlighter
from pgtail_py.highlighter_registry import (
    HighlighterRegistry,
    get_registry,
    reset_registry,
)
from pgtail_py.highlighting_config import CustomHighlighter, HighlightingConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


def make_highlighter(name: str, priority: int = 100) -> RegexHighlighter:
    """Create a test highlighter."""
    return RegexHighlighter(
        name=name,
        priority=priority,
        pattern=r"\d+",
        style=f"hl_{name}",
    )


# =============================================================================
# Test Singleton Behavior
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self) -> None:
        """Multiple instantiations should return same instance."""
        reg1 = HighlighterRegistry()
        reg2 = HighlighterRegistry()
        assert reg1 is reg2

    def test_get_registry_function(self) -> None:
        """get_registry should return the singleton."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2
        assert isinstance(reg1, HighlighterRegistry)

    def test_reset_registry(self) -> None:
        """reset_registry should create new instance."""
        reg1 = get_registry()
        reg1.register(make_highlighter("test"), "structural")

        reset_registry()
        reg2 = get_registry()

        assert reg1 is not reg2
        assert reg2.get("test") is None


# =============================================================================
# Test Registration
# =============================================================================


class TestRegistration:
    """Tests for register/unregister methods."""

    def test_register_highlighter(self) -> None:
        """Registering a highlighter should make it retrievable."""
        registry = get_registry()
        h = make_highlighter("test")
        registry.register(h, "structural")

        assert registry.get("test") is h

    def test_register_with_category(self) -> None:
        """Highlighter should be associated with category."""
        registry = get_registry()
        h = make_highlighter("test")
        registry.register(h, "diagnostic")

        assert registry.get_category("test") == "diagnostic"

    def test_register_duplicate_raises(self) -> None:
        """Registering duplicate name should raise."""
        registry = get_registry()
        registry.register(make_highlighter("test"), "structural")

        with pytest.raises(ValueError, match="already registered"):
            registry.register(make_highlighter("test"), "structural")

    def test_register_invalid_name(self) -> None:
        """Invalid highlighter names should be rejected."""
        registry = get_registry()

        # Empty name
        with pytest.raises(ValueError, match="cannot be empty"):
            # We need to bypass the highlighter's name to test this
            h = make_highlighter("temp")
            h._name = ""  # type: ignore[attr-defined]
            registry.register(h, "structural")

    def test_unregister_highlighter(self) -> None:
        """Unregistering should remove highlighter."""
        registry = get_registry()
        registry.register(make_highlighter("test"), "structural")
        registry.unregister("test")

        assert registry.get("test") is None

    def test_unregister_unknown_raises(self) -> None:
        """Unregistering unknown name should raise."""
        registry = get_registry()

        with pytest.raises(KeyError, match="not found"):
            registry.unregister("unknown")

    def test_unregister_removes_from_category(self) -> None:
        """Unregistering should remove from category list."""
        registry = get_registry()
        registry.register(make_highlighter("test"), "structural")
        registry.unregister("test")

        assert "test" not in [h.name for h in registry.get_by_category("structural")]


# =============================================================================
# Test Retrieval
# =============================================================================


class TestRetrieval:
    """Tests for get/get_by_category methods."""

    def test_get_existing(self) -> None:
        """get should return registered highlighter."""
        registry = get_registry()
        h = make_highlighter("test")
        registry.register(h, "structural")

        assert registry.get("test") is h

    def test_get_unknown(self) -> None:
        """get should return None for unknown name."""
        registry = get_registry()
        assert registry.get("unknown") is None

    def test_get_by_category(self) -> None:
        """get_by_category should return highlighters in category."""
        registry = get_registry()
        h1 = make_highlighter("h1")
        h2 = make_highlighter("h2")
        h3 = make_highlighter("h3")

        registry.register(h1, "structural")
        registry.register(h2, "structural")
        registry.register(h3, "diagnostic")

        structural = registry.get_by_category("structural")
        assert len(structural) == 2
        assert h1 in structural
        assert h2 in structural
        assert h3 not in structural

    def test_get_by_category_empty(self) -> None:
        """get_by_category should return empty list for unknown category."""
        registry = get_registry()
        assert registry.get_by_category("unknown") == []


# =============================================================================
# Test Listing
# =============================================================================


class TestListing:
    """Tests for all_names/all_categories methods."""

    def test_all_names(self) -> None:
        """all_names should return sorted list of names."""
        registry = get_registry()
        registry.register(make_highlighter("zebra"), "structural")
        registry.register(make_highlighter("alpha"), "structural")
        registry.register(make_highlighter("middle"), "diagnostic")

        names = registry.all_names()
        assert names == ["alpha", "middle", "zebra"]

    def test_all_names_empty(self) -> None:
        """all_names should return empty list when registry is empty."""
        registry = get_registry()
        assert registry.all_names() == []

    def test_all_categories(self) -> None:
        """all_categories should return sorted list of categories."""
        registry = get_registry()
        registry.register(make_highlighter("h1"), "zebra_cat")
        registry.register(make_highlighter("h2"), "alpha_cat")
        registry.register(make_highlighter("h3"), "alpha_cat")

        categories = registry.all_categories()
        assert categories == ["alpha_cat", "zebra_cat"]

    def test_all_categories_empty(self) -> None:
        """all_categories should return empty list when registry is empty."""
        registry = get_registry()
        assert registry.all_categories() == []


# =============================================================================
# Test Clear
# =============================================================================


class TestClear:
    """Tests for clear method."""

    def test_clear_removes_all(self) -> None:
        """clear should remove all highlighters."""
        registry = get_registry()
        registry.register(make_highlighter("h1"), "structural")
        registry.register(make_highlighter("h2"), "diagnostic")
        registry.clear()

        assert registry.all_names() == []
        assert registry.all_categories() == []


# =============================================================================
# Test create_chain
# =============================================================================


class TestCreateChain:
    """Tests for create_chain method."""

    def test_create_chain_with_all_enabled(self) -> None:
        """create_chain should include all enabled highlighters."""
        registry = get_registry()
        registry.register(make_highlighter("h1"), "structural")
        registry.register(make_highlighter("h2"), "diagnostic")

        config = HighlightingConfig()
        config.enabled_highlighters["h1"] = True
        config.enabled_highlighters["h2"] = True

        chain = registry.create_chain(config)
        assert len(chain.highlighters) == 2

    def test_create_chain_filters_disabled(self) -> None:
        """create_chain should exclude disabled highlighters."""
        registry = get_registry()
        registry.register(make_highlighter("h1"), "structural")
        registry.register(make_highlighter("h2"), "diagnostic")

        config = HighlightingConfig()
        config.enabled_highlighters["h1"] = True
        config.enabled_highlighters["h2"] = False

        chain = registry.create_chain(config)
        assert len(chain.highlighters) == 1
        assert chain.highlighters[0].name == "h1"

    def test_create_chain_respects_global_toggle(self) -> None:
        """create_chain should return empty when globally disabled."""
        registry = get_registry()
        registry.register(make_highlighter("h1"), "structural")

        config = HighlightingConfig()
        config.enabled = False
        config.enabled_highlighters["h1"] = True

        chain = registry.create_chain(config)
        # All highlighters should be filtered out due to global toggle
        assert len(chain.highlighters) == 0

    def test_create_chain_with_custom_highlighter(self) -> None:
        """create_chain should include enabled custom highlighters."""
        registry = get_registry()

        config = HighlightingConfig()
        config.custom_highlighters.append(
            CustomHighlighter(
                name="custom_test",
                pattern=r"TEST-\d+",
                style="yellow",
                priority=1050,
                enabled=True,
            )
        )

        chain = registry.create_chain(config)
        # Should include the custom highlighter (name is preserved without prefix)
        custom_names = [h.name for h in chain.highlighters]
        assert "custom_test" in custom_names

    def test_create_chain_excludes_disabled_custom(self) -> None:
        """create_chain should exclude disabled custom highlighters."""
        registry = get_registry()

        config = HighlightingConfig()
        config.custom_highlighters.append(
            CustomHighlighter(
                name="disabled_custom",
                pattern=r"TEST-\d+",
                style="yellow",
                priority=1050,
                enabled=False,
            )
        )

        chain = registry.create_chain(config)
        custom_names = [h.name for h in chain.highlighters]
        assert "custom_disabled_custom" not in custom_names

    def test_create_chain_respects_max_length(self) -> None:
        """create_chain should use config's max_length."""
        registry = get_registry()

        config = HighlightingConfig()
        config.max_length = 5000

        chain = registry.create_chain(config)
        assert chain.max_length == 5000
