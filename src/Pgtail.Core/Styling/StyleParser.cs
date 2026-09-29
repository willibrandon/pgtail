namespace Pgtail.Styling;

/// <summary>
/// Reads style strings such as <c>bold red on blue</c>, <c>italic #ff6b6b</c>, or <c>fg:ansiyellow bg:black bold</c>.
/// </summary>
/// <remarks>
/// A style is a list of words: attributes (<c>bold</c> or <c>b</c>, <c>dim</c> or <c>d</c>, <c>italic</c> or <c>i</c>,
/// <c>underline</c> or <c>u</c>, <c>blink</c>, <c>reverse</c> or <c>r</c>, <c>strike</c> or <c>s</c>, <c>conceal</c>,
/// <c>overline</c> or <c>o</c>), <c>not</c> or <c>no</c> before an attribute to turn it off, a color for the foreground,
/// <c>on</c> followed by a background color, or <c>fg:</c> and <c>bg:</c> prefixed colors.
/// </remarks>
public static class StyleParser
{
    /// <summary>
    /// Parses a style.
    /// </summary>
    /// <param name="text">The style string; empty or <c>none</c> for no style.</param>
    /// <returns>The style.</returns>
    /// <exception cref="FormatException">A word is neither an attribute nor a color.</exception>
    public static TextStyle Parse(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var style = TextStyle.Plain;
        var words = text.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
        for (var i = 0; i < words.Length; i++)
        {
            var word = words[i].ToLowerInvariant();
            if (word == "none")
            {
                continue;
            }

            if (word == "on")
            {
                if (i + 1 >= words.Length || !ColorParser.TryParse(words[i + 1], out var background))
                {
                    throw new FormatException($"Expected a color after 'on' in style '{text}'");
                }

                style = style with { Background = background };
                i++;
                continue;
            }

            if (word == "not")
            {
                if (i + 1 >= words.Length || Attribute(words[i + 1]) is not { } cleared)
                {
                    throw new FormatException($"Expected an attribute after 'not' in style '{text}'");
                }

                style = style with { Attributes = style.Attributes & ~cleared, Cleared = style.Cleared | cleared };
                i++;
                continue;
            }

            if (word.StartsWith("no", StringComparison.Ordinal) && word.Length > 2 && Attribute(word[2..]) is { } negated)
            {
                style = style with { Attributes = style.Attributes & ~negated, Cleared = style.Cleared | negated };
                continue;
            }

            if (Attribute(word) is { } attribute)
            {
                style = style with { Attributes = style.Attributes | attribute, Cleared = style.Cleared & ~attribute };
                continue;
            }

            if (word.StartsWith("fg:", StringComparison.Ordinal) || word.StartsWith("bg:", StringComparison.Ordinal))
            {
                if (!ColorParser.TryParse(word[3..], out var prefixed))
                {
                    throw new FormatException($"Unknown color '{words[i][3..]}' in style '{text}'");
                }

                style = word[0] == 'f' ? style with { Foreground = prefixed } : style with { Background = prefixed };
                continue;
            }

            if (!ColorParser.TryParse(word, out var foreground))
            {
                throw new FormatException($"Unknown color or attribute '{words[i]}' in style '{text}'");
            }

            style = style with { Foreground = foreground };
        }

        return style;
    }

    /// <summary>
    /// Parses a style, reporting a problem as a message instead of an exception.
    /// </summary>
    /// <param name="text">The style string.</param>
    /// <param name="style">The style, when valid.</param>
    /// <param name="error">The problem, when invalid.</param>
    /// <returns>True when the style is valid.</returns>
    public static bool TryParse(string text, out TextStyle style, out string error)
    {
        try
        {
            style = Parse(text);
            error = "";
            return true;
        }
        catch (FormatException exception)
        {
            style = default;
            error = exception.Message;
            return false;
        }
    }

    private static TextAttributes? Attribute(string word) => word.ToLowerInvariant() switch
    {
        "bold" or "b" => TextAttributes.Bold,
        "dim" or "d" => TextAttributes.Dim,
        "italic" or "i" => TextAttributes.Italic,
        "underline" or "u" or "underline2" or "uu" => TextAttributes.Underline,
        "blink" or "blink2" => TextAttributes.Blink,
        "reverse" or "r" => TextAttributes.Reverse,
        "strike" or "s" or "strikethrough" => TextAttributes.Strikethrough,
        "conceal" or "hidden" => TextAttributes.Hidden,
        "overline" or "o" => TextAttributes.Overline,
        _ => null,
    };
}
