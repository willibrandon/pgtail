namespace Pgtail.Toml;

/// <summary>
/// How a table came to exist, which decides how it may still be extended.
/// </summary>
public enum TomlTableKind
{
    /// <summary>
    /// The document itself.
    /// </summary>
    Root,

    /// <summary>
    /// Created as a parent of a table header, such as <c>a</c> for <c>[a.b]</c>; it may still get a header of its own.
    /// </summary>
    Implicit,

    /// <summary>
    /// Defined by a <c>[table]</c> header.
    /// </summary>
    Header,

    /// <summary>
    /// Created by a dotted key such as <c>a.b = 1</c>.
    /// </summary>
    Dotted,

    /// <summary>
    /// Written inline as <c>{ ... }</c>, and complete as written.
    /// </summary>
    Inline,

    /// <summary>
    /// An element of an array of tables.
    /// </summary>
    ArrayElement,
}
