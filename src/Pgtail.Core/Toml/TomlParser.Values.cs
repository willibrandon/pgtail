using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Toml;

/// <summary>
/// Values: strings, numbers, booleans, date-times, arrays, and inline tables.
/// </summary>
internal sealed partial class TomlParser
{
    private object ParseValue()
    {
        if (AtEnd)
        {
            throw Error("Expected a value");
        }

        switch (Current)
        {
            case '"' or '\'':
                return ParseString();
            case '[':
                return ParseArray();
            case '{':
                return ParseInlineTable();
            case 't' when _text.AsSpan(_position).StartsWith("true") && EndsToken(_position + 4):
                _position += 4;
                return true;
            case 'f' when _text.AsSpan(_position).StartsWith("false") && EndsToken(_position + 5):
                _position += 5;
                return false;
            default:
                return ParseScalar();
        }
    }

    private bool EndsToken(int position) => position >= _text.Length || !IsScalarCharacter(_text[position]);

    private static bool IsScalarCharacter(char c) =>
        c is (>= 'A' and <= 'Z') or (>= 'a' and <= 'z') or (>= '0' and <= '9') or '_' or '+' or '-' or '.' or ':';

    private TomlArray ParseArray()
    {
        _position++;
        var array = new TomlArray();
        while (true)
        {
            SkipWhitespaceCommentsAndNewlines();
            if (AtEnd)
            {
                throw Error("Unterminated array");
            }

            if (Current == ']')
            {
                _position++;
                return array;
            }

            array.Add(ParseValue());
            SkipWhitespaceCommentsAndNewlines();
            if (AtEnd)
            {
                throw Error("Unterminated array");
            }

            if (Current == ',')
            {
                _position++;
                continue;
            }

            if (Current != ']')
            {
                throw Error("Expected ',' or ']' in an array");
            }
        }
    }

    private TomlTable ParseInlineTable()
    {
        _position++;
        var table = new TomlTable(TomlTableKind.Inline);
        SkipWhitespace();
        if (!AtEnd && Current == '}')
        {
            _position++;
            return table;
        }

        while (true)
        {
            SkipWhitespace();
            var keyStart = _position;
            var key = ParseKey();
            SkipWhitespace();
            Expect('=', "Expected '=' after the key");
            SkipWhitespace();
            var value = ParseValue();
            Insert(table, key, value, keyStart);
            SkipWhitespace();
            if (AtEnd || Current is '\n' or '\r')
            {
                throw Error("An inline table must be closed on the line it starts");
            }

            if (Current == '}')
            {
                _position++;
                FreezeInline(table);
                return table;
            }

            Expect(',', "Expected ',' or '}' in an inline table");
            SkipWhitespace();
            if (!AtEnd && Current == '}')
            {
                throw Error("Trailing commas are not allowed in inline tables");
            }
        }
    }

    private static void FreezeInline(TomlTable table)
    {
        table.Kind = TomlTableKind.Inline;
        foreach (var (_, value) in table)
        {
            if (value is TomlTable nested)
            {
                FreezeInline(nested);
            }
        }
    }

    private object ParseScalar()
    {
        var start = _position;
        while (!AtEnd && IsScalarCharacter(Current))
        {
            _position++;
        }

        // A date may be followed by a space and a time.
        if (_position - start == 10 && LocalDate().IsMatch(_text.AsSpan(start, 10)) && _position + 2 < _text.Length
            && _text[_position] == ' ' && char.IsAsciiDigit(_text[_position + 1]) && char.IsAsciiDigit(_text[_position + 2]))
        {
            _position++;
            while (!AtEnd && IsScalarCharacter(Current))
            {
                _position++;
            }
        }

        var token = _text[start.._position];
        if (token.Length == 0)
        {
            throw Error($"Unexpected '{Current}' where a value was expected");
        }

        return ReadScalar(token) ?? throw Error($"Invalid value '{token}'", start);
    }

    private object? ReadScalar(string token)
    {
        if (DecimalInteger().IsMatch(token))
        {
            return long.TryParse(token.Replace("_", "", StringComparison.Ordinal), NumberStyles.AllowLeadingSign,
                CultureInfo.InvariantCulture, out var value) ? value : throw Error($"Integer '{token}' is out of range");
        }

        if (token.Length > 2 && token[0] == '0' && token[1] is 'x' or 'o' or 'b')
        {
            return ReadPrefixedInteger(token);
        }

        if (Float().IsMatch(token))
        {
            return double.Parse(token.Replace("_", "", StringComparison.Ordinal), NumberStyles.Float, CultureInfo.InvariantCulture);
        }

        if (SpecialFloat().Match(token) is { Success: true } special)
        {
            var negative = token.StartsWith('-');
            return special.Groups[1].Value == "inf"
                ? negative ? double.NegativeInfinity : double.PositiveInfinity
                : double.NaN;
        }

        return ReadDateTime(token);
    }

    private long? ReadPrefixedInteger(string token)
    {
        var (pattern, radix) = token[1] switch
        {
            'x' => (HexInteger(), 16),
            'o' => (OctalInteger(), 8),
            _ => (BinaryInteger(), 2),
        };

        if (!pattern.IsMatch(token))
        {
            return null;
        }

        ulong value = 0;
        foreach (var c in token[2..])
        {
            if (c == '_')
            {
                continue;
            }

            var digit = (ulong)Convert.ToInt32(c.ToString(), 16);
            if (value > (ulong.MaxValue - digit) / (ulong)radix)
            {
                throw Error($"Integer '{token}' is out of range");
            }

            value = (value * (ulong)radix) + digit;
        }

        return value > long.MaxValue ? throw Error($"Integer '{token}' is out of range") : (long)value;
    }

    private static object? ReadDateTime(string token)
    {
        var match = DateTimePattern().Match(token);
        if (match.Success)
        {
            var date = ReadDate(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value);
            var time = ReadTime(match.Groups[4].Value, match.Groups[5].Value, match.Groups[6].Value, match.Groups[7].Value);
            if (date is null || time is null)
            {
                return null;
            }

            var local = date.Value.ToDateTime(time.Value, DateTimeKind.Unspecified);
            if (!match.Groups[8].Success)
            {
                return local;
            }

            var zone = match.Groups[8].Value;
            if (zone is "Z" or "z")
            {
                return new DateTimeOffset(local, TimeSpan.Zero);
            }

            var hours = int.Parse(zone.AsSpan(1, 2), CultureInfo.InvariantCulture);
            var minutes = int.Parse(zone.AsSpan(4, 2), CultureInfo.InvariantCulture);
            if (hours > 23 || minutes > 59)
            {
                return null;
            }

            var offset = new TimeSpan(hours, minutes, 0);
            return new DateTimeOffset(local, zone[0] == '-' ? -offset : offset);
        }

        match = LocalDate().Match(token);
        if (match.Success)
        {
            return ReadDate(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value);
        }

        match = LocalTime().Match(token);
        return match.Success
            ? ReadTime(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value, match.Groups[4].Value)
            : null;
    }

    private static DateOnly? ReadDate(string year, string month, string day)
    {
        var y = int.Parse(year, CultureInfo.InvariantCulture);
        var m = int.Parse(month, CultureInfo.InvariantCulture);
        var d = int.Parse(day, CultureInfo.InvariantCulture);
        return y >= 1 && m is >= 1 and <= 12 && d >= 1 && d <= DateTime.DaysInMonth(y, m) ? new DateOnly(y, m, d) : null;
    }

    private static TimeOnly? ReadTime(string hour, string minute, string second, string fraction)
    {
        var h = int.Parse(hour, CultureInfo.InvariantCulture);
        var m = int.Parse(minute, CultureInfo.InvariantCulture);
        var s = int.Parse(second, CultureInfo.InvariantCulture);
        if (h > 23 || m > 59 || s > 59)
        {
            return null;
        }

        var digits = fraction.Length == 0 ? "0" : fraction.Length > 7 ? fraction[..7] : fraction.PadRight(7, '0');
        return new TimeOnly(h, m, s).Add(TimeSpan.FromTicks(long.Parse(digits, CultureInfo.InvariantCulture)));
    }

    [GeneratedRegex("^[+-]?(?:0|[1-9](?:_?[0-9])*)$")]
    private static partial Regex DecimalInteger();

    [GeneratedRegex("^0x[0-9A-Fa-f](?:_?[0-9A-Fa-f])*$")]
    private static partial Regex HexInteger();

    [GeneratedRegex("^0o[0-7](?:_?[0-7])*$")]
    private static partial Regex OctalInteger();

    [GeneratedRegex("^0b[01](?:_?[01])*$")]
    private static partial Regex BinaryInteger();

    [GeneratedRegex("^[+-]?(?:0|[1-9](?:_?[0-9])*)(?:\\.[0-9](?:_?[0-9])*(?:[eE][+-]?[0-9](?:_?[0-9])*)?|[eE][+-]?[0-9](?:_?[0-9])*)$")]
    private static partial Regex Float();

    [GeneratedRegex("^[+-]?(inf|nan)$")]
    private static partial Regex SpecialFloat();

    [GeneratedRegex("^([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt ]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\\.([0-9]+))?([Zz]|[+-][0-9]{2}:[0-9]{2})?$")]
    private static partial Regex DateTimePattern();

    [GeneratedRegex("^([0-9]{4})-([0-9]{2})-([0-9]{2})$")]
    private static partial Regex LocalDate();

    [GeneratedRegex("^([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\\.([0-9]+))?$")]
    private static partial Regex LocalTime();
}
