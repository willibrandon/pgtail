"""Theme command handlers for pgtail."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.config import get_config_path, save_config

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def theme_command(state: AppState, args: list[str]) -> None:
    """Handle the 'theme' command - display or switch themes.

    Args:
        state: Current application state.
        args: Subcommand and arguments.
    """
    # No args - show current theme
    if not args:
        handle_theme_show(state)
        return

    subcommand = args[0].lower()

    # Handle 'theme <name>' - switch to theme
    # First check if it's NOT a known subcommand
    if subcommand not in ("list", "preview", "edit", "reload"):
        handle_theme_switch(state, subcommand)
        return

    # Handle subcommands
    if subcommand == "list":
        handle_theme_list(state)
    elif subcommand == "preview":
        if len(args) < 2:
            print("Usage: theme preview <name>")
            return
        handle_theme_preview(state, args[1])
    elif subcommand == "edit":
        if len(args) < 2:
            print("Usage: theme edit <name>")
            print("Create or edit a custom theme file.")
            return
        handle_theme_edit(state, args[1])
    elif subcommand == "reload":
        handle_theme_reload(state)


def handle_theme_show(state: AppState) -> None:
    """Display current theme information.

    Args:
        state: Current application state.
    """
    theme = state.theme_manager.current_theme
    if theme is None:
        print("No theme active (using default colors)")
        return

    # Check if custom or built-in
    is_builtin = theme.name in state.theme_manager.builtin_themes

    print(f"Current theme: {theme.name}")
    if theme.description:
        print(f"  {theme.description}")
    print(f"  Type: {'built-in' if is_builtin else 'custom'}")
    print()
    print("Use 'theme list' to see available themes.")
    print("Use 'theme <name>' to switch themes.")


def handle_theme_switch(state: AppState, name: str) -> None:
    """Switch to a named theme.

    Args:
        state: Current application state.
        name: Theme name to switch to.
    """
    # Try to switch theme
    if not state.theme_manager.switch_theme(name):
        # Theme not found - show helpful error
        builtin, custom = state.theme_manager.list_themes()
        all_themes = builtin + custom

        print(f"Unknown theme: {name}")
        print()
        print("Available themes:")
        for theme_name in builtin:
            print(f"  {theme_name} (built-in)")
        for theme_name in custom:
            print(f"  {theme_name} (custom)")

        # Suggest similar names
        similar = [t for t in all_themes if t.startswith(name[:3]) or name in t]
        if similar and similar != [name]:
            print()
            print(f"Did you mean: {', '.join(similar)}?")
        return

    # Success - persist to config
    save_config("theme.name", name)

    # Update in-memory config
    state.config.theme.name = name

    # Show confirmation
    theme = state.theme_manager.current_theme
    print(f"Switched to theme: {name}")
    if theme and theme.description:
        print(f"  {theme.description}")
    print(f"Saved to {get_config_path()}")


def handle_theme_list(state: AppState) -> None:
    """List available themes.

    Args:
        state: Current application state.
    """
    builtin, custom = state.theme_manager.list_themes()
    current = state.theme_manager.current_theme
    current_name = current.name if current else None

    print("Available themes:")
    print()

    # Built-in themes
    print("Built-in:")
    for name in builtin:
        marker = " *" if name == current_name else ""
        theme = state.theme_manager.get_theme(name)
        desc = f"  - {theme.description}" if theme and theme.description else ""
        print(f"  {name}{marker}{desc}")

    # Custom themes
    if custom:
        print()
        print("Custom:")
        for name in custom:
            marker = " *" if name == current_name else ""
            theme = state.theme_manager.get_theme(name)
            desc = f"  - {theme.description}" if theme and theme.description else ""
            print(f"  {name}{marker}{desc}")

    print()
    print("* = current theme")
    print()
    print("Use 'theme <name>' to switch themes.")
    print("Use 'theme preview <name>' to preview a theme.")


def handle_theme_preview(state: AppState, name: str) -> None:
    """Preview a theme with sample log output.

    Args:
        state: Current application state.
        name: Theme name to preview.
    """
    # This will be implemented in Phase 4 (User Story 2)
    print(f"Preview for theme '{name}' - coming soon")
    print("Use 'theme <name>' to switch to this theme.")


def handle_theme_edit(state: AppState, name: str) -> None:
    """Create or edit a custom theme file.

    Args:
        state: Current application state.
        name: Theme name to edit.
    """
    # This will be implemented in Phase 5 (User Story 3)
    print(f"Theme editing for '{name}' - coming soon")


def handle_theme_reload(state: AppState) -> None:
    """Reload the current theme from disk.

    Args:
        state: Current application state.
    """
    # This will be implemented in Phase 6 (User Story 4)
    success, message = state.theme_manager.reload_current()
    print(message)
