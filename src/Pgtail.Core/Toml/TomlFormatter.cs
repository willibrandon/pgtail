using System.Collections;
using System.Globalization;
using System.Text;

namespace Pgtail.Toml;

/// <summary>
/// Writes values and keys as TOML.
/// </summary>
public static class TomlFormatter
{
    /// <summary>
    /// Writes a value.
    /// </summary>
    /// <remarks>
    /// Strings are basic strings; lists become arrays; <see cref="TomlTable"/> values and sequences of key-value pairs
    /// become inline tables.
    /// </remarks>
    /// <param name="value">The value.</param>
    /// <returns>The TOML text.</returns>
    /// <exception cref="ArgumentException">The value has no TOML form.</exception>
    public static string Format(object value)
    {
        ArgumentNullException.ThrowIfNull(value);
        return value switch
        {
            string text => Quote(text),
            bool flag => flag ? "true" : "false",
            int number => number.ToString(CultureInfo.InvariantCulture),
            long number => number.ToString(CultureInfo.InvariantCulture),
            double number => FormatFloat(number),
            DateTimeOffset moment => moment.Offset == TimeSpan.Zero
                ? moment.ToString("yyyy-MM-dd'T'HH:mm:ss.FFFFFFF", CultureInfo.InvariantCulture) + "Z"
                : moment.ToString("yyyy-MM-dd'T'HH:mm:ss.FFFFFFFzzz", CultureInfo.InvariantCulture),
            DateTime local => local.ToString("yyyy-MM-dd'T'HH:mm:ss.FFFFFFF", CultureInfo.InvariantCulture),
            DateOnly date => date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
            TimeOnly time => time.ToString("HH:mm:ss.FFFFFFF", CultureInfo.InvariantCulture),
            TomlTable table => FormatInline(table),
            IEnumerable<KeyValuePair<string, object>> pairs => FormatInline(pairs),
            IEnumerable items => "[" + string.Join(", ", items.Cast<object>().Select(Format)) + "]",
            _ => throw new ArgumentException($"A {value.GetType().Name} has no TOML form.", nameof(value)),
        };
    }

    /// <summary>
    /// Writes a key, quoting it unless it is a bare key.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <returns>The TOML text.</returns>
    public static string FormatKey(string key)
    {
        ArgumentNullException.ThrowIfNull(key);
        return key.Length > 0 && key.All(c => c is (>= 'A' and <= 'Z') or (>= 'a' and <= 'z') or (>= '0' and <= '9') or '_' or '-')
            ? key
            : Quote(key);
    }

    /// <summary>
    /// Writes a dotted key path.
    /// </summary>
    /// <param name="path">The keys.</param>
    /// <returns>The TOML text.</returns>
    public static string FormatPath(IEnumerable<string> path) => string.Join('.', path.Select(FormatKey));

    /// <summary>
    /// Writes a string as a basic string, escaping quotes, backslashes, and control characters.
    /// </summary>
    /// <param name="text">The string.</param>
    /// <returns>The quoted string.</returns>
    public static string Quote(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        StringBuilder result = new StringBuilder(text.Length + 2).Append('"');
        foreach (char c in text)
        {
            switch (c)
            {
                case '"':
                    result.Append("\\\"");
                    break;
                case '\\':
                    result.Append("\\\\");
                    break;
                case '\b':
                    result.Append("\\b");
                    break;
                case '\t':
                    result.Append("\\t");
                    break;
                case '\n':
                    result.Append("\\n");
                    break;
                case '\f':
                    result.Append("\\f");
                    break;
                case '\r':
                    result.Append("\\r");
                    break;
                default:
                    if (c < 0x20 || c == 0x7F)
                    {
                        result.Append("\\u").Append(((int)c).ToString("X4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        result.Append(c);
                    }

                    break;
            }
        }

        return result.Append('"').ToString();
    }

    private static string FormatFloat(double value)
    {
        if (double.IsNaN(value))
        {
            return "nan";
        }

        if (double.IsInfinity(value))
        {
            return value > 0 ? "inf" : "-inf";
        }

        string text = value.ToString("R", CultureInfo.InvariantCulture);
        return text.Contains('.', StringComparison.Ordinal) || text.Contains('E', StringComparison.Ordinal) ? text : text + ".0";
    }

    private static string FormatInline(IEnumerable<KeyValuePair<string, object>> pairs) =>
        "{" + string.Join(", ", pairs.Select(pair => $"{FormatKey(pair.Key)} = {Format(pair.Value)}")) + "}";
}
