"""Color theming system for pgtail.

Provides Theme and ColorStyle dataclasses, ThemeManager for loading/switching themes,
and color validation utilities.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from prompt_toolkit.styles import Style

# =============================================================================
# CSS Named Colors (140 colors from CSS Color Module Level 4)
# =============================================================================

CSS_NAMED_COLORS = {
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkgrey",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "grey",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "rebeccapurple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "slategrey",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "white",
    "whitesmoke",
    "yellow",
    "yellowgreen",
    "default",
}

# ANSI color names supported by prompt_toolkit
ANSI_COLORS = {
    "ansiblack",
    "ansired",
    "ansigreen",
    "ansiyellow",
    "ansiblue",
    "ansimagenta",
    "ansicyan",
    "ansiwhite",
    "ansigray",
    "ansibrightblack",
    "ansibrightred",
    "ansibrightgreen",
    "ansibrightyellow",
    "ansibrightblue",
    "ansibrightmagenta",
    "ansibrightcyan",
    "ansibrightwhite",
    "ansidefault",
}

# Hex color pattern: #rgb or #rrggbb
HEX_COLOR_PATTERN = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# =============================================================================
# Color Validation
# =============================================================================


def validate_color(color: str | None) -> bool:
    """Validate a color value.

    Accepts:
    - ANSI color names (ansiRed, ansibrightblue, etc.)
    - Hex codes (#rgb, #rrggbb)
    - CSS named colors (140 colors)
    - "default" for terminal default
    - None/empty for no color

    Args:
        color: Color value to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not color:
        return True

    color_lower = color.lower()

    # Check ANSI colors
    if color_lower in ANSI_COLORS:
        return True

    # Check hex colors
    if HEX_COLOR_PATTERN.match(color):
        return True

    # Check CSS named colors
    return color_lower in CSS_NAMED_COLORS


def get_color_error(color: str) -> str | None:
    """Get a descriptive error message for an invalid color.

    Args:
        color: Color value to check.

    Returns:
        Error message if invalid, None if valid.
    """
    if validate_color(color):
        return None

    return (
        f"Invalid color '{color}'. Expected: "
        "ANSI name (ansiRed), hex code (#ff6b6b), or CSS name (DarkRed)"
    )


# =============================================================================
# ColorStyle Dataclass
# =============================================================================


@dataclass
class ColorStyle:
    """A single color style specification with foreground, background, and modifiers.

    Attributes:
        fg: Foreground color (ANSI name, hex code, or CSS named color).
        bg: Background color (ANSI name, hex code, or CSS named color).
        bold: Bold text modifier.
        dim: Dim/faint text modifier.
        italic: Italic text modifier.
        underline: Underline text modifier.
    """

    fg: str | None = None
    bg: str | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False

    def to_style_string(self) -> str:
        """Convert to prompt_toolkit style string.

        Returns:
            Style string like "fg:red bg:yellow bold".
        """
        parts: list[str] = []

        if self.fg:
            parts.append(f"fg:{self.fg}")
        if self.bg:
            parts.append(f"bg:{self.bg}")
        if self.bold:
            parts.append("bold")
        if self.dim:
            parts.append("dim")
        if self.italic:
            parts.append("italic")
        if self.underline:
            parts.append("underline")

        return " ".join(parts) if parts else ""

    def validate(self) -> list[str]:
        """Validate color values.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        if self.fg and not validate_color(self.fg):
            errors.append(f"Invalid foreground color: {self.fg}")
        if self.bg and not validate_color(self.bg):
            errors.append(f"Invalid background color: {self.bg}")

        return errors

    @classmethod
    def from_dict(cls, data: dict) -> ColorStyle:
        """Create ColorStyle from dictionary (e.g., from TOML).

        Args:
            data: Dictionary with fg, bg, bold, dim, italic, underline keys.

        Returns:
            ColorStyle instance.
        """
        return cls(
            fg=data.get("fg"),
            bg=data.get("bg"),
            bold=data.get("bold", False),
            dim=data.get("dim", False),
            italic=data.get("italic", False),
            underline=data.get("underline", False),
        )


# =============================================================================
# Theme Dataclass
# =============================================================================


@dataclass
class Theme:
    """A complete theme definition containing all style rules.

    Attributes:
        name: Theme identifier (e.g., "dark", "monokai").
        description: Human-readable description.
        levels: Styles for each log level.
        ui: Styles for UI elements (prompt, timestamp, pid, highlight, etc.).
    """

    name: str
    description: str = ""
    levels: dict[str, ColorStyle] = field(default_factory=dict)
    ui: dict[str, ColorStyle] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate theme definition.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        # Validate name
        if not self.name:
            errors.append("Theme name is required")
        elif not re.match(r"^[a-z0-9-]+$", self.name):
            errors.append("Theme name must be lowercase alphanumeric with hyphens")

        # Validate required log levels
        required_levels = {"ERROR", "WARNING", "LOG"}
        missing_levels = required_levels - set(self.levels.keys())
        if missing_levels:
            errors.append(f"Missing required log levels: {', '.join(sorted(missing_levels))}")

        # Validate required UI elements
        required_ui = {"timestamp", "highlight"}
        missing_ui = required_ui - set(self.ui.keys())
        if missing_ui:
            errors.append(f"Missing required UI elements: {', '.join(sorted(missing_ui))}")

        # Note: SQL color style keys are optional for theme validation
        # sql_keyword, sql_identifier, sql_string, sql_number, sql_operator, sql_comment, sql_function
        # Missing keys will gracefully fall back to default text color

        # Validate all color styles
        for level_name, style in self.levels.items():
            for error in style.validate():
                errors.append(f"levels.{level_name}: {error}")

        for ui_name, style in self.ui.items():
            for error in style.validate():
                errors.append(f"ui.{ui_name}: {error}")

        return errors

    def get_level_style(self, level: str) -> ColorStyle:
        """Get style for a log level, with fallback inheritance.

        Missing levels inherit from nearest severity:
        DEBUG1-5 → DEBUG → INFO → LOG

        Args:
            level: Log level name (e.g., "ERROR", "DEBUG1").

        Returns:
            ColorStyle for the level.
        """
        # Direct match
        if level in self.levels:
            return self.levels[level]

        # DEBUG1-5 fallback to DEBUG
        if level.startswith("DEBUG") and "DEBUG" in self.levels:
            return self.levels["DEBUG"]

        # Default fallback
        return self.levels.get("LOG", ColorStyle())

    def get_ui_style(self, element: str) -> ColorStyle:
        """Get style for a UI element.

        Args:
            element: UI element name (e.g., "timestamp", "highlight").

        Returns:
            ColorStyle for the element (empty if not defined).
        """
        return self.ui.get(element, ColorStyle())


# =============================================================================
# Platform-specific theme directory
# =============================================================================


def get_themes_dir() -> Path:
    """Return the platform-appropriate path for custom themes directory.

    Returns:
        - Linux: ~/.config/pgtail/themes/ (XDG_CONFIG_HOME)
        - macOS: ~/Library/Application Support/pgtail/themes/
        - Windows: %APPDATA%/pgtail/themes/
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux and other Unix-like systems - use XDG_CONFIG_HOME
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"

    return base / "pgtail" / "themes"


def ensure_themes_dir() -> Path:
    """Ensure the themes directory exists and return the path."""
    themes_dir = get_themes_dir()
    themes_dir.mkdir(parents=True, exist_ok=True)
    return themes_dir


# =============================================================================
# ThemeManager
# =============================================================================


class ThemeManager:
    """Manager for theme operations.

    Handles loading, switching, and validating themes. Generates prompt_toolkit
    Style objects from Theme definitions.
    """

    def __init__(self) -> None:
        """Initialize ThemeManager with default theme."""
        self.builtin_themes: dict[str, Theme] = {}
        self.custom_themes: dict[str, Theme] = {}
        self._current_theme: Theme | None = None
        self._style: Style | None = None

        # Load built-in themes
        self.load_builtin_themes()

        # Set default theme
        if "dark" in self.builtin_themes:
            self._current_theme = self.builtin_themes["dark"]
            self._style = self.generate_style(self._current_theme)

    @property
    def current_theme(self) -> Theme | None:
        """Get the currently active theme."""
        return self._current_theme

    @property
    def style(self) -> Style:
        """Get the prompt_toolkit Style for the current theme."""
        if self._style is None:
            # Fallback to generating from current theme or empty style
            if self._current_theme:
                self._style = self.generate_style(self._current_theme)
            else:
                self._style = Style([])
        return self._style

    def load_builtin_themes(self) -> None:
        """Load all built-in themes from the themes package."""
        from pgtail_py.themes import BUILTIN_THEMES

        self.builtin_themes = dict(BUILTIN_THEMES)

    def scan_custom_themes(self) -> None:
        """Scan custom themes directory and load all valid themes."""
        themes_dir = get_themes_dir()
        if not themes_dir.exists():
            return

        self.custom_themes.clear()

        for theme_file in themes_dir.glob("*.toml"):
            try:
                theme = load_custom_theme(theme_file)
                if theme:
                    self.custom_themes[theme.name] = theme
            except Exception:
                # Skip invalid theme files
                pass

    def list_themes(self) -> tuple[list[str], list[str]]:
        """List available theme names.

        Returns:
            Tuple of (builtin_names, custom_names).
        """
        # Rescan custom themes
        self.scan_custom_themes()

        builtin = sorted(self.builtin_themes.keys())
        custom = sorted(self.custom_themes.keys())

        return builtin, custom

    def get_theme(self, name: str) -> Theme | None:
        """Get a theme by name.

        Checks custom themes first, then built-in themes.

        Args:
            name: Theme name.

        Returns:
            Theme if found, None otherwise.
        """
        # Check custom themes first (allows overriding built-ins)
        if name in self.custom_themes:
            return self.custom_themes[name]

        return self.builtin_themes.get(name)

    def switch_theme(self, name: str) -> bool:
        """Switch to a named theme.

        Args:
            name: Theme name to switch to.

        Returns:
            True if successful, False if theme not found.
        """
        # Rescan custom themes
        self.scan_custom_themes()

        theme = self.get_theme(name)
        if theme is None:
            return False

        self._current_theme = theme
        self._style = self.generate_style(theme)
        return True

    def reload_current(self) -> tuple[bool, str]:
        """Reload the current theme from disk.

        Returns:
            Tuple of (success, message).
        """
        if self._current_theme is None:
            return False, "No theme is currently active"

        name = self._current_theme.name

        # For built-in themes, just regenerate the style
        if name in self.builtin_themes:
            self._style = self.generate_style(self._current_theme)
            return True, f"Theme '{name}' reloaded."

        # For custom themes, reload from disk
        themes_dir = get_themes_dir()
        theme_file = themes_dir / f"{name}.toml"

        if not theme_file.exists():
            # File was deleted - fallback to dark
            if self.switch_theme("dark"):
                return (
                    False,
                    f"Theme file not found: {theme_file}\nFalling back to default theme: dark",
                )
            return False, f"Theme file not found: {theme_file}"

        try:
            theme = load_custom_theme(theme_file)
            if theme:
                self.custom_themes[name] = theme
                self._current_theme = theme
                self._style = self.generate_style(theme)
                return True, f"Theme '{name}' reloaded."
            return False, f"Failed to parse theme file: {theme_file}"
        except Exception as e:
            return (
                False,
                f"Failed to reload theme '{name}':\n  {e}\n\nKeeping previous theme active.",
            )

    def validate_theme(self, theme: Theme) -> list[str]:
        """Validate a theme definition.

        Args:
            theme: Theme to validate.

        Returns:
            List of error messages (empty if valid).
        """
        return theme.validate()

    def generate_style(self, theme: Theme) -> Style:
        """Generate prompt_toolkit Style from Theme.

        Args:
            theme: Theme to generate style from.

        Returns:
            prompt_toolkit Style object.
        """
        rules: list[tuple[str, str]] = []

        # Add log level styles
        for level_name, style in theme.levels.items():
            style_string = style.to_style_string()
            if style_string:
                rules.append((level_name.lower(), style_string))

        # Ensure DEBUG1-5 inherit from DEBUG if not explicitly defined
        debug_levels = ["DEBUG1", "DEBUG2", "DEBUG3", "DEBUG4", "DEBUG5"]
        for debug_level in debug_levels:
            if debug_level not in theme.levels and "DEBUG" in theme.levels:
                style_string = theme.levels["DEBUG"].to_style_string()
                if style_string:
                    rules.append((debug_level.lower(), style_string))

        # Add UI element styles
        for ui_name, style in theme.ui.items():
            style_string = style.to_style_string()
            if style_string:
                rules.append((ui_name, style_string))

        # Add Pygments token mappings for fullscreen syntax highlighting
        # Maps Pygments token class names to theme's SQL style values
        # Note: Pygments tokens use dot notation (pygments.literal.number)
        pygments_mappings = {
            # Map Pygments tokens to theme SQL styles
            "pygments.keyword": "sql_keyword",
            # String tokens (Token.Literal.String)
            "pygments.literal.string": "sql_string",
            "pygments.literal.string.single": "sql_string",
            # Number tokens (Token.Literal.Number)
            "pygments.literal.number": "sql_number",
            # Operator tokens
            "pygments.operator": "sql_operator",
            # Comment tokens
            "pygments.comment": "sql_comment",
            "pygments.comment.single": "sql_comment",
            "pygments.comment.multiline": "sql_comment",
            # Name tokens
            "pygments.name.function": "sql_function",
            "pygments.name": "sql_identifier",
            "pygments.name.variable": "sql_identifier",
            "pygments.name.label": "sql_keyword",  # SQL state codes
            # Punctuation
            "pygments.punctuation": "sql_operator",
            # Generic tokens for log levels
            "pygments.generic.error": "error",
        }

        for pygments_class, theme_key in pygments_mappings.items():
            # Try to find the style from UI section (SQL styles)
            if theme_key in theme.ui:
                style_string = theme.ui[theme_key].to_style_string()
            # Fall back to levels section (for error, warning, etc.)
            elif theme_key.upper() in theme.levels:
                style_string = theme.levels[theme_key.upper()].to_style_string()
            else:
                continue

            if style_string:
                rules.append((pygments_class, style_string))

        return Style(rules)

    def get_style(self) -> Style:
        """Get the current theme's Style.

        Returns:
            prompt_toolkit Style for the current theme.
        """
        return self.style


# =============================================================================
# Custom Theme Loading
# =============================================================================


def load_custom_theme(path: Path) -> Theme | None:
    """Load a custom theme from a TOML file.

    Args:
        path: Path to the TOML file.

    Returns:
        Theme if successfully loaded, None on error.
    """
    theme, _ = load_custom_theme_with_errors(path)
    return theme


def load_custom_theme_with_errors(path: Path) -> tuple[Theme | None, list[str]]:
    """Load a custom theme from a TOML file with detailed error messages.

    Args:
        path: Path to the TOML file.

    Returns:
        Tuple of (Theme or None, list of error messages).
    """
    import tomlkit
    from tomlkit.exceptions import TOMLKitError

    errors: list[str] = []

    # Read and parse TOML
    try:
        content = path.read_text()
    except OSError as e:
        return None, [f"Cannot read file: {e}"]

    try:
        doc = tomlkit.parse(content)
    except TOMLKitError as e:
        # Extract line number from tomlkit error if available
        error_str = str(e)
        return None, [f"TOML parse error: {error_str}"]

    # Extract name from filename
    name = path.stem

    # Parse meta section
    meta = doc.get("meta", {})
    description = meta.get("description", "")

    # Parse levels section
    levels: dict[str, ColorStyle] = {}
    levels_data = doc.get("levels", {})
    for level_name, style_data in levels_data.items():
        if isinstance(style_data, dict):
            style = ColorStyle.from_dict(dict(style_data))
            style_errors = style.validate()
            for err in style_errors:
                errors.append(f"[levels.{level_name}] {err}")
            levels[level_name.upper()] = style
        else:
            errors.append(f"[levels.{level_name}] Expected table, got {type(style_data).__name__}")

    # Parse ui section
    ui: dict[str, ColorStyle] = {}
    ui_data = doc.get("ui", {})
    for ui_name, style_data in ui_data.items():
        if isinstance(style_data, dict):
            style = ColorStyle.from_dict(dict(style_data))
            style_errors = style.validate()
            for err in style_errors:
                errors.append(f"[ui.{ui_name}] {err}")
            ui[ui_name] = style
        else:
            errors.append(f"[ui.{ui_name}] Expected table, got {type(style_data).__name__}")

    theme = Theme(
        name=name,
        description=str(description),
        levels=levels,
        ui=ui,
    )

    # Validate theme structure
    structure_errors = theme.validate()
    errors.extend(structure_errors)

    # Return theme even with validation errors (allows preview of partial themes)
    return theme, errors


# =============================================================================
# Theme Template for Custom Themes
# =============================================================================


THEME_TEMPLATE = """\
# Custom pgtail theme
# See: https://github.com/user/pgtail#themes

[meta]
name = "{name}"
description = "Custom color scheme"

[levels]
# Log level colors - use ANSI names, hex codes (#rgb/#rrggbb), or CSS colors
PANIC = {{ fg = "white", bg = "red", bold = true }}
FATAL = {{ fg = "red", bold = true }}
ERROR = {{ fg = "#ff6b6b" }}
WARNING = {{ fg = "#ffd93d" }}
NOTICE = {{ fg = "#6bcb77" }}
LOG = {{ fg = "default" }}
INFO = {{ fg = "#4d96ff" }}
DEBUG = {{ fg = "#888888" }}
# DEBUG1-5 inherit from DEBUG if not specified

[ui]
# UI element colors
prompt = {{ fg = "green" }}
timestamp = {{ fg = "gray" }}
pid = {{ fg = "gray" }}
highlight = {{ bg = "yellow", fg = "black" }}
slow_warning = {{ fg = "yellow" }}
slow_slow = {{ fg = "yellow", bold = true }}
slow_critical = {{ fg = "red", bold = true }}
detail = {{ fg = "default" }}

# SQL syntax highlighting colors (optional - falls back to default text if omitted)
sql_keyword = {{ fg = "blue", bold = true }}
sql_identifier = {{ fg = "cyan" }}
sql_string = {{ fg = "green" }}
sql_number = {{ fg = "magenta" }}
sql_operator = {{ fg = "yellow" }}
sql_comment = {{ fg = "gray" }}
sql_function = {{ fg = "blue" }}
"""
