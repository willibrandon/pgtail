using System.Globalization;

namespace Pgtail.Configuration;

/// <summary>
/// A configuration setting: its dotted key, default, type, and validation.
/// </summary>
/// <param name="Key">The dotted key, such as <c>slow.warn</c>.</param>
/// <param name="Default">The default value, or null when unset by default.</param>
/// <param name="Type">How the value is typed on the command line.</param>
/// <param name="Validate">Checks a value read from the file or typed by the user, returning the value to store or
/// throwing <see cref="FormatException"/> with the reason.</param>
public sealed record SettingDefinition(string Key, object? Default, SettingType Type, Func<object, object> Validate)
{
    /// <summary>
    /// The key split at its dots.
    /// </summary>
    public IReadOnlyList<string> Path => Key.Split('.');

    /// <summary>
    /// Converts words typed on the command line into a value of the setting's type.
    /// </summary>
    /// <param name="words">The words after the key.</param>
    /// <returns>The value, before validation.</returns>
    /// <exception cref="FormatException">An integer setting was given something that is not a whole number.</exception>
    public object Parse(IReadOnlyList<string> words)
    {
        ArgumentNullException.ThrowIfNull(words);
        return Type switch
        {
            SettingType.Boolean => (words.Count == 0 ? "true" : words[0]).ToLowerInvariant() is "true" or "1" or "yes",
            SettingType.Integer => long.TryParse(words.Count == 0 ? "0" : words[0], NumberStyles.Integer,
                CultureInfo.InvariantCulture, out long number)
                ? number
                : throw new FormatException("must be an integer"),
            SettingType.List => words.Select(word => Key.Contains("levels", StringComparison.Ordinal) ? word.ToUpperInvariant() : word)
                .ToList(),
            _ => string.Join(' ', words),
        };
    }
}
