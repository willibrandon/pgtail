"""Built-in themes for pgtail."""

from pgtail_py.themes.dark import DARK_THEME
from pgtail_py.themes.high_contrast import HIGH_CONTRAST_THEME
from pgtail_py.themes.light import LIGHT_THEME
from pgtail_py.themes.monokai import MONOKAI_THEME
from pgtail_py.themes.solarized_dark import SOLARIZED_DARK_THEME
from pgtail_py.themes.solarized_light import SOLARIZED_LIGHT_THEME

__all__ = [
    "DARK_THEME",
    "LIGHT_THEME",
    "HIGH_CONTRAST_THEME",
    "MONOKAI_THEME",
    "SOLARIZED_DARK_THEME",
    "SOLARIZED_LIGHT_THEME",
]

# Map of theme names to theme objects
BUILTIN_THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high-contrast": HIGH_CONTRAST_THEME,
    "monokai": MONOKAI_THEME,
    "solarized-dark": SOLARIZED_DARK_THEME,
    "solarized-light": SOLARIZED_LIGHT_THEME,
}
