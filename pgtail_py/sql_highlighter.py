"""SQL syntax highlighter.

Converts tokenized SQL into styled FormattedText for prompt_toolkit rendering.
"""

from __future__ import annotations

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.sql_tokenizer import SQLToken, SQLTokenizer, SQLTokenType
from pgtail_py.utils import is_color_disabled

# Style class mapping for token types
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
