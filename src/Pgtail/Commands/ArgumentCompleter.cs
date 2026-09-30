namespace Pgtail.Commands;

/// <summary>
/// Completes a command's arguments from its <see cref="ArgumentSpec"/>.
/// </summary>
/// <remarks>
/// Finished words are scanned left to right: a known option that takes a value claims the next word, an option
/// written as <c>--name=value</c> claims nothing more, and any other word fills the next positional slot. The word
/// being typed then completes as the pending option's value, an option name, or the current positional argument.
/// </remarks>
internal static class ArgumentCompleter
{
    /// <summary>
    /// The candidates for the word being typed.
    /// </summary>
    /// <param name="spec">The command's arguments.</param>
    /// <param name="context">The words and session; its arguments are those after the command name.</param>
    /// <param name="style">How options are offered.</param>
    /// <returns>The candidates that start with the word being typed, ignoring case, in order.</returns>
    public static List<CompletionItem> Complete(ArgumentSpec spec, CompletionContext context, CompletionStyle style)
    {
        ArgumentNullException.ThrowIfNull(spec);
        ArgumentNullException.ThrowIfNull(context);
        if (spec.NoArguments)
        {
            return [];
        }

        IReadOnlyList<string> arguments = context.Arguments;
        string partial = context.Partial;
        if (spec.Subcommands.Count > 0)
        {
            if (arguments.Count == 0)
            {
                var items = spec.Subcommands.Select(sub => new CompletionItem(sub.Name, sub.Description)).ToList();
                if (spec.Positionals is [{ } first, ..])
                {
                    items.AddRange(Values(first, context));
                }

                return Filter(items, partial);
            }

            SubcommandSpec? chosen = spec.Subcommands.FirstOrDefault(
                sub => sub.Name.Equals(arguments[0], StringComparison.OrdinalIgnoreCase));
            if (chosen is not null)
            {
                return Complete(chosen.Arguments, context with { Arguments = [.. arguments.Skip(1)] }, style);
            }
        }

        return CompleteArguments(spec, context, style);
    }

    /// <summary>
    /// The values a spec offers for the word being typed, before filtering.
    /// </summary>
    /// <param name="spec">The spec.</param>
    /// <param name="context">The context.</param>
    /// <returns>The values.</returns>
    public static IEnumerable<CompletionItem> Values(ArgumentSpec spec, CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(spec);
        return spec.Source is { } source ? spec.Values.Concat(source(context)) : spec.Values;
    }

    /// <summary>
    /// Keeps the items that start with a prefix, ignoring case, dropping repeats.
    /// </summary>
    /// <param name="items">The items.</param>
    /// <param name="prefix">The prefix.</param>
    /// <returns>The matching items, in order.</returns>
    public static List<CompletionItem> Filter(IEnumerable<CompletionItem> items, string prefix)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        return [.. items.Where(item => item.Text.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) && seen.Add(item.Text))];
    }

    private static List<CompletionItem> CompleteArguments(ArgumentSpec spec, CompletionContext context, CompletionStyle style)
    {
        string partial = context.Partial;
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        FlagSpec? pending = null;
        int position = 0;
        foreach (string word in context.Arguments)
        {
            if (pending is not null)
            {
                pending = null;
                continue;
            }

            if (word.StartsWith('-') && FindFlag(spec, word) is { } flag)
            {
                _ = used.Add(flag.Key);
                pending = flag.Value is not null && !flag.Attached ? flag : null;
                continue;
            }

            if (word.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }

            position++;
        }

        if (pending is not null && !partial.StartsWith('-'))
        {
            return Filter(Values(pending.Value!, context), partial);
        }

        int equals = partial.IndexOf('=', StringComparison.Ordinal);
        if (partial.StartsWith('-') && equals > 0)
        {
            string key = partial[..equals];
            FlagSpec? attached = spec.Flags.FirstOrDefault(
                flag => flag.Attached && flag.Key.Equals(key, StringComparison.OrdinalIgnoreCase));
            if (attached is { Value: { } value })
            {
                IEnumerable<CompletionItem> prefixed = Values(value, context with { Partial = partial[(equals + 1)..] })
                    .Select(item => item with { Text = key + "=" + item.Text, Display = item.Label });
                return Filter(prefixed, partial);
            }

            return [];
        }

        var results = new List<CompletionItem>();
        bool offerFlags = style == CompletionStyle.Inline
            ? partial.StartsWith("--", StringComparison.Ordinal)
            : partial.Length == 0 || partial.StartsWith('-');
        if (offerFlags)
        {
            foreach (FlagSpec flag in spec.Flags)
            {
                bool shortFlag = !flag.Name.StartsWith("--", StringComparison.Ordinal);
                if (shortFlag && (!partial.StartsWith('-') || partial.StartsWith("--", StringComparison.Ordinal)))
                {
                    continue;
                }

                if ((!flag.Repeatable && used.Contains(flag.Key)) || flag.Excludes.Any(used.Contains))
                {
                    continue;
                }

                results.Add(new CompletionItem(flag.Name, flag.Description, flag.Attached));
            }

            if (style == CompletionStyle.Inline || partial.StartsWith('-'))
            {
                return Filter(results, partial);
            }
        }

        ArgumentSpec? slot = position < spec.Positionals.Count ? spec.Positionals[position] : spec.Rest;
        if (slot is not null)
        {
            results.AddRange(Values(slot, context));
        }

        return Filter(results, partial);
    }

    private static FlagSpec? FindFlag(ArgumentSpec spec, string word)
    {
        int equals = word.IndexOf('=', StringComparison.Ordinal);
        string key = equals > 0 ? word[..equals] : word;
        return spec.Flags.FirstOrDefault(flag => flag.Key.Equals(key, StringComparison.OrdinalIgnoreCase)
            && (equals > 0) == flag.Attached);
    }
}
