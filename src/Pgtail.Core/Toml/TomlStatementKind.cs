namespace Pgtail.Toml;

/// <summary>
/// What a top-level line of a TOML document declares.
/// </summary>
public enum TomlStatementKind
{
    /// <summary>
    /// A <c>key = value</c> pair.
    /// </summary>
    KeyValue,

    /// <summary>
    /// A <c>[table]</c> header.
    /// </summary>
    Table,

    /// <summary>
    /// A <c>[[array.of.tables]]</c> header.
    /// </summary>
    ArrayTable,
}
