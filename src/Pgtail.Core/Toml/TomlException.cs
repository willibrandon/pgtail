namespace Pgtail.Toml;

/// <summary>
/// A TOML document that does not follow the TOML 1.0 specification.
/// </summary>
/// <param name="message">What is wrong.</param>
/// <param name="line">The one-based line of the problem.</param>
/// <param name="column">The one-based column of the problem.</param>
public sealed class TomlException(string message, int line, int column)
    : FormatException($"{message} (line {line}, column {column})")
{
    /// <summary>
    /// The one-based line of the problem.
    /// </summary>
    public int Line { get; } = line;

    /// <summary>
    /// The one-based column of the problem.
    /// </summary>
    public int Column { get; } = column;
}
