namespace Pgtail.Toml;

/// <summary>
/// A top-level statement of a TOML document with where it was written.
/// </summary>
/// <param name="Kind">What the statement declares.</param>
/// <param name="Path">The full key path: the table path of a header, or the table path and dotted key of a pair.</param>
/// <param name="TablePath">The path of the table the statement belongs to; for a header, the table it opens.</param>
/// <param name="Start">The offset of the start of the statement's first line.</param>
/// <param name="End">The offset just past the statement's last line, including its line ending.</param>
/// <param name="ValueStart">For a pair, the offset where the value starts.</param>
/// <param name="ValueEnd">For a pair, the offset just past the value.</param>
public sealed record TomlStatement(
    TomlStatementKind Kind,
    IReadOnlyList<string> Path,
    IReadOnlyList<string> TablePath,
    int Start,
    int End,
    int ValueStart,
    int ValueEnd);
