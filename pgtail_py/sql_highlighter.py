"""SQL syntax highlighter.

Converts tokenized SQL into styled FormattedText for prompt_toolkit rendering,
and Rich markup strings for Textual rendering.
"""

from __future__ import annotations

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.sql_tokenizer import SQLToken, SQLTokenizer, SQLTokenType
from pgtail_py.theme import ColorStyle, Theme, ThemeManager
from pgtail_py.utils import is_color_disabled

# Style class mapping for token types (prompt_toolkit)
TOKEN_TO_STYLE: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "class:sql_keyword",
    SQLTokenType.IDENTIFIER: "class:sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "class:sql_identifier",
    SQLTokenType.STRING: "class:sql_string",
    SQLTokenType.NUMBER: "class:sql_number",
    SQLTokenType.OPERATOR: "class:sql_operator",
    SQLTokenType.COMMENT: "class:sql_comment",
    SQLTokenType.FUNCTION: "class:sql_function",
    SQLTokenType.PUNCTUATION: "",  # No special styling
    SQLTokenType.WHITESPACE: "",  # Preserved as-is
    SQLTokenType.UNKNOWN: "",  # No special styling
}

# Token type to theme key mapping for Rich output
TOKEN_TYPE_TO_THEME_KEY: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "sql_keyword",
    SQLTokenType.IDENTIFIER: "sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "sql_identifier",
    SQLTokenType.STRING: "sql_string",
    SQLTokenType.NUMBER: "sql_number",
    SQLTokenType.OPERATOR: "sql_operator",
    SQLTokenType.COMMENT: "sql_comment",
    SQLTokenType.FUNCTION: "sql_function",
    SQLTokenType.PUNCTUATION: "",
    SQLTokenType.WHITESPACE: "",
    SQLTokenType.UNKNOWN: "",
}

# Module-level theme manager for Rich color lookups
_theme_manager: ThemeManager | None = None


def _get_theme_manager() -> ThemeManager:
    """Get or create the module-level ThemeManager singleton.

    Returns:
        ThemeManager instance for theme lookups.
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def _color_style_to_rich_markup(style: ColorStyle) -> str:
    """Convert ColorStyle to Rich markup tag content.

    Translates a ColorStyle dataclass into a string suitable for use
    inside Rich markup tags. Handles ANSI color prefix stripping for
    Rich compatibility.

    Args:
        style: ColorStyle with fg, bg, bold, dim, italic, underline.

    Returns:
        Rich markup tag content (e.g., "bold blue", "dim", "#268bd2").
        Empty string if no styling defined.

    Examples:
        >>> _color_style_to_rich_markup(ColorStyle(fg="blue", bold=True))
        "bold blue"
        >>> _color_style_to_rich_markup(ColorStyle(fg="#268bd2"))
        "#268bd2"
        >>> _color_style_to_rich_markup(ColorStyle(dim=True))
        "dim"
        >>> _color_style_to_rich_markup(ColorStyle())
        ""
    """
    parts: list[str] = []

    # Add modifiers
    if style.bold:
        parts.append("bold")
    if style.dim:
        parts.append("dim")
    if style.italic:
        parts.append("italic")
    if style.underline:
        parts.append("underline")

    # Add foreground color
    if style.fg:
        fg = style.fg
        # Strip "ansi" prefix for Rich compatibility
        if fg.startswith("ansibright"):
            fg = "bright_" + fg[10:]  # ansibrightred → bright_red
        elif fg.startswith("ansi"):
            fg = fg[4:]  # ansired → red
        parts.append(fg)

    # Add background color
    if style.bg:
        bg = style.bg
        if bg.startswith("ansibright"):
            bg = "bright_" + bg[10:]
        elif bg.startswith("ansi"):
            bg = bg[4:]
        parts.append(f"on {bg}")

    return " ".join(parts)


def highlight_sql_rich(sql: str, theme: Theme | None = None) -> str:
    """Convert SQL text to Rich console markup string.

    Tokenizes SQL and wraps each token in Rich markup tags using
    colors from the active theme. Brackets in SQL text are escaped
    to prevent Rich parsing errors.

    Args:
        sql: SQL text to highlight.
        theme: Theme for color lookup. If None, uses global ThemeManager.

    Returns:
        Rich markup string with styled tokens.
        If NO_COLOR is set, returns SQL with only bracket escaping.

    Examples:
        >>> highlight_sql_rich("SELECT id FROM users")
        "[bold blue]SELECT[/] [cyan]id[/] [bold blue]FROM[/] [cyan]users[/]"
        >>> highlight_sql_rich("SELECT arr[1]")
        "[bold blue]SELECT[/] [cyan]arr[/]\\[1]"
    """
    # Empty SQL returns empty string
    if not sql:
        return ""

    # Respect NO_COLOR environment variable
    if is_color_disabled():
        return sql.replace("[", "\\[")

    # Get theme for color lookup
    if theme is None:
        theme = _get_theme_manager().current_theme

    # Tokenize SQL
    tokens = SQLTokenizer().tokenize(sql)

    # Build Rich markup string
    parts: list[str] = []
    for token in tokens:
        # Escape brackets in token text to prevent Rich parsing errors
        escaped_text = token.text.replace("[", "\\[")

        # Get theme key for this token type
        theme_key = TOKEN_TYPE_TO_THEME_KEY.get(token.type, "")

        if theme_key and theme:
            # Get color style from theme
            style = theme.get_ui_style(theme_key)
            markup = _color_style_to_rich_markup(style)

            if markup:
                parts.append(f"[{markup}]{escaped_text}[/]")
            else:
                parts.append(escaped_text)
        else:
            parts.append(escaped_text)

    return "".join(parts)


class SQLHighlighter:
    """Converts tokenized SQL into styled FormattedText.

    Uses SQLTokenizer for tokenization and maps token types to theme styles.
    Respects NO_COLOR environment variable.
    """

    def __init__(self) -> None:
        """Initialize highlighter with tokenizer."""
        self._tokenizer = SQLTokenizer()

    def highlight(self, sql: str) -> FormattedText:
        """Tokenize and style SQL.

        Args:
            sql: SQL text to highlight.

        Returns:
            FormattedText with styled tokens.
            If NO_COLOR is set, returns unstyled FormattedText.
        """
        # Respect NO_COLOR environment variable
        if is_color_disabled():
            return FormattedText([("", sql)])

        tokens = self._tokenizer.tokenize(sql)
        return self.highlight_tokens(tokens)

    def highlight_tokens(self, tokens: list[SQLToken]) -> FormattedText:
        """Style pre-tokenized SQL.

        Args:
            tokens: List of SQLToken objects.

        Returns:
            FormattedText with styled tokens.
        """
        parts: list[tuple[str, str]] = []

        for token in tokens:
            style = TOKEN_TO_STYLE.get(token.type, "")
            parts.append((style, token.text))

        return FormattedText(parts)


# Module-level singleton for convenience
_highlighter: SQLHighlighter | None = None


def get_highlighter() -> SQLHighlighter:
    """Get the module-level SQLHighlighter singleton.

    Lazy initialization for performance.

    Returns:
        SQLHighlighter instance.
    """
    global _highlighter
    if _highlighter is None:
        _highlighter = SQLHighlighter()
    return _highlighter


def highlight_sql(sql: str) -> FormattedText:
    """Convenience function to highlight SQL text.

    Args:
        sql: SQL text to highlight.

    Returns:
        FormattedText with styled tokens.
    """
    return get_highlighter().highlight(sql)
