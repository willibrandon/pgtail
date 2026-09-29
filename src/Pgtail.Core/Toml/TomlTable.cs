using System.Collections;
using System.Diagnostics.CodeAnalysis;

namespace Pgtail.Toml;

/// <summary>
/// A TOML table: keys in the order they were defined, each with a value.
/// </summary>
/// <remarks>
/// Values are <see cref="string"/>, <see cref="long"/>, <see cref="double"/>, <see cref="bool"/>,
/// <see cref="DateTimeOffset"/> (offset date-time), <see cref="DateTime"/> (local date-time), <see cref="DateOnly"/>,
/// <see cref="TimeOnly"/>, <see cref="TomlArray"/>, or <see cref="TomlTable"/>.
/// </remarks>
/// <param name="kind">How the table came to exist.</param>
public sealed class TomlTable(TomlTableKind kind = TomlTableKind.Root) : IEnumerable<KeyValuePair<string, object>>
{
    private readonly Dictionary<string, object> _values = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    /// <summary>
    /// How the table came to exist.
    /// </summary>
    public TomlTableKind Kind { get; internal set; } = kind;

    /// <summary>
    /// The number of keys.
    /// </summary>
    public int Count => _order.Count;

    /// <summary>
    /// The keys in definition order.
    /// </summary>
    public IReadOnlyList<string> Keys => _order;

    /// <summary>
    /// The value of a key.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <returns>The value.</returns>
    /// <exception cref="KeyNotFoundException">The table has no such key.</exception>
    public object this[string key] => _values[key];

    /// <summary>
    /// Whether the table has a key.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <returns>True when the key is defined.</returns>
    public bool ContainsKey(string key) => _values.ContainsKey(key);

    /// <summary>
    /// Gets the value of a key.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <param name="value">The value, when the key is defined.</param>
    /// <returns>True when the key is defined.</returns>
    public bool TryGetValue(string key, [MaybeNullWhen(false)] out object value) => _values.TryGetValue(key, out value);

    /// <summary>
    /// Gets a nested table.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <param name="table">The table, when the key holds one.</param>
    /// <returns>True when the key holds a table.</returns>
    public bool TryGetTable(string key, [MaybeNullWhen(false)] out TomlTable table)
    {
        if (_values.TryGetValue(key, out var value) && value is TomlTable found)
        {
            table = found;
            return true;
        }

        table = null;
        return false;
    }

    /// <summary>
    /// Gets a value by a dotted path of keys.
    /// </summary>
    /// <param name="path">The keys from this table down.</param>
    /// <returns>The value, or null when any key along the path is missing or not a table.</returns>
    public object? GetPath(IReadOnlyList<string> path)
    {
        ArgumentNullException.ThrowIfNull(path);
        object current = this;
        foreach (var key in path)
        {
            if (current is not TomlTable table || !table.TryGetValue(key, out var next))
            {
                return null;
            }

            current = next;
        }

        return current;
    }

    /// <summary>
    /// Adds a key that is not yet defined.
    /// </summary>
    /// <param name="key">The key.</param>
    /// <param name="value">The value.</param>
    internal void Add(string key, object value)
    {
        _values.Add(key, value);
        _order.Add(key);
    }

    /// <inheritdoc />
    public IEnumerator<KeyValuePair<string, object>> GetEnumerator() =>
        _order.Select(key => new KeyValuePair<string, object>(key, _values[key])).GetEnumerator();

    /// <inheritdoc />
    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
}
