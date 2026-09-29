using System.Collections;

namespace Pgtail.Toml;

/// <summary>
/// A TOML array: a value array written with brackets, or an array of tables built from <c>[[header]]</c> sections.
/// </summary>
/// <param name="isTableArray">True for an array of tables.</param>
public sealed class TomlArray(bool isTableArray = false) : IReadOnlyList<object>
{
    private readonly List<object> _items = [];

    /// <summary>
    /// Whether the array was built from <c>[[header]]</c> sections, which may add more elements.
    /// </summary>
    public bool IsTableArray { get; } = isTableArray;

    /// <inheritdoc />
    public int Count => _items.Count;

    /// <inheritdoc />
    public object this[int index] => _items[index];

    /// <summary>
    /// Appends an element.
    /// </summary>
    /// <param name="item">The element.</param>
    internal void Add(object item) => _items.Add(item);

    /// <inheritdoc />
    public IEnumerator<object> GetEnumerator() => _items.GetEnumerator();

    /// <inheritdoc />
    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
}
