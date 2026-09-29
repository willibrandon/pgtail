using Pgtail.Commands;

namespace Pgtail.Tail;

/// <summary>
/// Suggests how to finish the command being typed in tail mode, shown as grey text.
/// </summary>
/// <remarks>
/// Command names, subcommands, options, and argument values come from the tail command catalog; when none fits, the
/// newest history entry that starts with the text is suggested.
/// </remarks>
/// <param name="catalog">The tail commands.</param>
/// <param name="host">The command host, for dynamic values.</param>
/// <param name="history">The command history.</param>
internal sealed class TailSuggester(CommandCatalog catalog, ICommandHost host, TailHistory history)
{
    /// <summary>
    /// The text the suggestion would add after what was typed.
    /// </summary>
    /// <param name="value">The text typed.</param>
    /// <returns>The suffix, or null.</returns>
    public string? Suffix(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        // A word that already names something, such as level, is complete, even when a longer name starts with it.
        var (start, items) = catalog.Complete(value, host, CompletionStyle.Inline);
        var partial = value[start..];
        var names = items.Select(item => item.Text).ToList();
        var best = names.Contains(partial, StringComparer.OrdinalIgnoreCase)
            ? null
            : names.Where(text => text.Length > partial.Length).Order(StringComparer.Ordinal).FirstOrDefault();
        if (best is not null)
        {
            return best[partial.Length..];
        }

        return history.SearchPrefix(value) is { } entry ? entry[value.Length..] : null;
    }
}
