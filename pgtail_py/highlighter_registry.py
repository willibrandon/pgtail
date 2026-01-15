"""HighlighterRegistry: Central registry for all highlighters.

Provides:
- Singleton registry for built-in and custom highlighters
- Category-based organization
- Factory method to create HighlighterChain from HighlightingConfig
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.highlighter import Highlighter, HighlighterChain

if TYPE_CHECKING:
    from pgtail_py.highlighting_config import HighlightingConfig


# =============================================================================
# HighlighterRegistry
# =============================================================================


class HighlighterRegistry:
    """Singleton registry of all available highlighters.

    Highlighters are organized by category (structural, diagnostic, etc.)
    and can be queried by name or category.
    """

    _instance: HighlighterRegistry | None = None

    def __new__(cls) -> HighlighterRegistry:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize registry (only once)."""
        if self._initialized:  # type: ignore[has-type]
            return

        self._highlighters: dict[str, Highlighter] = {}
        self._categories: dict[str, list[str]] = {}
        self._highlighter_categories: dict[str, str] = {}
        self._initialized = True

    def register(
        self,
        highlighter: Highlighter,
        category: str,
    ) -> None:
        """Register a highlighter.

        Args:
            highlighter: Highlighter to register.
            category: Category name (e.g., "structural", "diagnostic").

        Raises:
            ValueError: If name already registered or invalid.
        """
        name = highlighter.name

        # Validate name format
        if not name:
            raise ValueError("Highlighter name cannot be empty")
        if not name.replace("_", "").isalnum() or not name.islower():
            raise ValueError(
                f"Invalid highlighter name '{name}': must be lowercase alphanumeric with underscores"
            )

        # Check for duplicate
        if name in self._highlighters:
            raise ValueError(f"Highlighter '{name}' already registered")

        # Register highlighter
        self._highlighters[name] = highlighter
        self._highlighter_categories[name] = category

        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

    def unregister(self, name: str) -> None:
        """Unregister a highlighter.

        Args:
            name: Highlighter name to remove.

        Raises:
            KeyError: If name not found.
        """
        if name not in self._highlighters:
            raise KeyError(f"Highlighter '{name}' not found")

        # Remove from category
        category = self._highlighter_categories[name]
        self._categories[category].remove(name)
        if not self._categories[category]:
            del self._categories[category]

        # Remove highlighter
        del self._highlighters[name]
        del self._highlighter_categories[name]

    def get(self, name: str) -> Highlighter | None:
        """Get a highlighter by name.

        Args:
            name: Highlighter name.

        Returns:
            Highlighter if found, None otherwise.
        """
        return self._highlighters.get(name)

    def get_by_category(self, category: str) -> list[Highlighter]:
        """Get all highlighters in a category.

        Args:
            category: Category name.

        Returns:
            List of highlighters (empty if category not found).
        """
        names = self._categories.get(category, [])
        return [self._highlighters[name] for name in names]

    def all_names(self) -> list[str]:
        """Get all registered highlighter names.

        Returns:
            Sorted list of highlighter names.
        """
        return sorted(self._highlighters.keys())

    def all_categories(self) -> list[str]:
        """Get all category names.

        Returns:
            Sorted list of category names.
        """
        return sorted(self._categories.keys())

    def get_category(self, name: str) -> str | None:
        """Get the category for a highlighter.

        Args:
            name: Highlighter name.

        Returns:
            Category name or None if not found.
        """
        return self._highlighter_categories.get(name)

    def clear(self) -> None:
        """Clear all registered highlighters.

        Useful for testing.
        """
        self._highlighters.clear()
        self._categories.clear()
        self._highlighter_categories.clear()

    def create_chain(self, config: HighlightingConfig) -> HighlighterChain:
        """Create a HighlighterChain from configuration.

        Filters highlighters based on enabled/disabled state in config.
        Custom highlighters from config are also included.

        Args:
            config: Highlighting configuration.

        Returns:
            HighlighterChain with enabled highlighters.
        """
        from pgtail_py.highlighter import RegexHighlighter

        # Collect enabled built-in highlighters
        enabled_highlighters: list[Highlighter] = []

        for name, highlighter in self._highlighters.items():
            if config.is_highlighter_enabled(name):
                enabled_highlighters.append(highlighter)

        # Add custom highlighters from config
        for custom in config.custom_highlighters:
            if custom.enabled:
                try:
                    custom_highlighter = RegexHighlighter(
                        name=f"custom_{custom.name}",
                        priority=custom.priority,
                        pattern=custom.pattern,
                        style=custom.style,
                    )
                    enabled_highlighters.append(custom_highlighter)
                except ValueError:
                    # Invalid custom pattern - skip silently
                    pass

        return HighlighterChain(
            highlighters=enabled_highlighters,
            max_length=config.max_length,
        )


# =============================================================================
# Module-level Singleton Access
# =============================================================================


def get_registry() -> HighlighterRegistry:
    """Get the global highlighter registry.

    Returns:
        The singleton HighlighterRegistry instance.
    """
    return HighlighterRegistry()


def reset_registry() -> None:
    """Reset the registry singleton.

    Used primarily for testing.
    """
    HighlighterRegistry._instance = None
