using System.Globalization;
using System.Text;

namespace Pgtail.Toml;

/// <summary>
/// Basic, literal, and multi-line strings.
/// </summary>
internal sealed partial class TomlParser
{
    private string ParseString()
    {
        ReadOnlySpan<char> rest = _text.AsSpan(_position);
        if (rest.StartsWith("\"\"\""))
        {
            return ParseMultilineBasicString();
        }

        if (rest.StartsWith("'''"))
        {
            return ParseMultilineLiteralString();
        }

        return Current == '"' ? ParseBasicString() : ParseLiteralString();
    }

    private string ParseBasicString()
    {
        _position++;
        var result = new StringBuilder();
        while (true)
        {
            if (AtEnd || Current is '\n' or '\r')
            {
                throw Error("Unterminated string");
            }

            char c = Current;
            if (c == '"')
            {
                _position++;
                return result.ToString();
            }

            if (c == '\\')
            {
                AppendEscape(result);
                continue;
            }

            CheckStringCharacter(c);
            result.Append(c);
            _position++;
        }
    }

    private string ParseLiteralString()
    {
        _position++;
        int start = _position;
        while (true)
        {
            if (AtEnd || Current is '\n' or '\r')
            {
                throw Error("Unterminated literal string");
            }

            if (Current == '\'')
            {
                string value = _text[start.._position];
                _position++;
                return value;
            }

            CheckStringCharacter(Current);
            _position++;
        }
    }

    private string ParseMultilineBasicString()
    {
        _position += 3;
        SkipFirstNewline();
        var result = new StringBuilder();
        while (true)
        {
            if (AtEnd)
            {
                throw Error("Unterminated multi-line string");
            }

            char c = Current;
            if (c == '"' && _text.AsSpan(_position).StartsWith("\"\"\""))
            {
                // Up to two quotes may end the content just before the closing delimiter.
                int quotes = 3;
                while (quotes < 5 && _position + quotes < _text.Length && _text[_position + quotes] == '"')
                {
                    quotes++;
                }

                result.Append('"', quotes - 3);
                _position += quotes;
                return result.ToString();
            }

            if (c == '\\')
            {
                int save = _position;
                _position++;
                SkipWhitespace();
                if (!AtEnd && Current is '\n' or '\r')
                {
                    // A line ending backslash trims the newline and all whitespace that follows it.
                    while (!AtEnd && Current is ' ' or '\t' or '\n' or '\r')
                    {
                        if (Current == '\r')
                        {
                            ExpectLineEnd();
                        }
                        else
                        {
                            _position++;
                        }
                    }

                    continue;
                }

                _position = save;
                AppendEscape(result);
                continue;
            }

            if (c == '\r')
            {
                ExpectLineEnd();
                result.Append('\n');
                continue;
            }

            if (c != '\n')
            {
                CheckStringCharacter(c);
            }

            result.Append(c);
            _position++;
        }
    }

    private string ParseMultilineLiteralString()
    {
        _position += 3;
        SkipFirstNewline();
        var result = new StringBuilder();
        while (true)
        {
            if (AtEnd)
            {
                throw Error("Unterminated multi-line literal string");
            }

            char c = Current;
            if (c == '\'' && _text.AsSpan(_position).StartsWith("'''"))
            {
                int quotes = 3;
                while (quotes < 5 && _position + quotes < _text.Length && _text[_position + quotes] == '\'')
                {
                    quotes++;
                }

                result.Append('\'', quotes - 3);
                _position += quotes;
                return result.ToString();
            }

            if (c == '\r')
            {
                ExpectLineEnd();
                result.Append('\n');
                continue;
            }

            if (c != '\n')
            {
                CheckStringCharacter(c);
            }

            result.Append(c);
            _position++;
        }
    }

    private void SkipFirstNewline()
    {
        if (!AtEnd && Current == '\n')
        {
            _position++;
        }
        else if (!AtEnd && Current == '\r' && _position + 1 < _text.Length && _text[_position + 1] == '\n')
        {
            _position += 2;
        }
    }

    private void CheckStringCharacter(char c)
    {
        if ((c < 0x20 && c != '\t') || c == 0x7F)
        {
            throw Error("Control characters must be escaped in strings");
        }
    }

    private void AppendEscape(StringBuilder result)
    {
        _position++;
        if (AtEnd)
        {
            throw Error("Unterminated escape sequence");
        }

        char c = Current;
        _position++;
        switch (c)
        {
            case 'b':
                result.Append('\b');
                break;
            case 't':
                result.Append('\t');
                break;
            case 'n':
                result.Append('\n');
                break;
            case 'f':
                result.Append('\f');
                break;
            case 'r':
                result.Append('\r');
                break;
            case '"':
                result.Append('"');
                break;
            case '\\':
                result.Append('\\');
                break;
            case 'u':
                AppendCodePoint(result, 4);
                break;
            case 'U':
                AppendCodePoint(result, 8);
                break;
            default:
                throw Error($"Invalid escape sequence '\\{c}'", _position - 2);
        }
    }

    private void AppendCodePoint(StringBuilder result, int digits)
    {
        if (_position + digits > _text.Length
            || !uint.TryParse(_text.AsSpan(_position, digits), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out uint value)
            || _text.AsSpan(_position, digits).ContainsAny('+', '-'))
        {
            throw Error($"Expected {digits} hexadecimal digits in a Unicode escape");
        }

        if (value is (>= 0xD800 and <= 0xDFFF) or > 0x10FFFF)
        {
            throw Error("A Unicode escape must be a Unicode scalar value");
        }

        result.Append(char.ConvertFromUtf32((int)value));
        _position += digits;
    }
}
