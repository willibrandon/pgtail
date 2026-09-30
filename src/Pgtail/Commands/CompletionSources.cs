using System.Globalization;
using Pgtail.Configuration;
using Pgtail.Highlighting;
using Pgtail.Parsing;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// Values that completion computes from the session or the file system.
/// </summary>
internal static class CompletionSources
{
    /// <summary>
    /// Instance IDs, described by version and status, and data directories once something is typed.
    /// </summary>
    /// <param name="context">The completion context.</param>
    /// <returns>The candidates.</returns>
    public static IEnumerable<CompletionItem> Instances(CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        foreach (Detection.PostgresInstance instance in context.Session.Instances)
        {
            string id = instance.Id.ToString(CultureInfo.InvariantCulture);
            yield return new CompletionItem(id, $"v{instance.Version} ({instance.StatusText})");
            if (context.Partial.Length > 0)
            {
                yield return new CompletionItem(instance.DataDirectory, $"Instance {instance.Id}");
            }
        }
    }

    /// <summary>
    /// <c>ALL</c> and each level not already chosen, described by severity.
    /// </summary>
    /// <param name="context">The completion context.</param>
    /// <returns>The candidates.</returns>
    public static IEnumerable<CompletionItem> Levels(CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        var chosen = context.Arguments.Select(argument => argument.ToUpperInvariant()).ToHashSet(StringComparer.Ordinal);
        if (!chosen.Contains("ALL"))
        {
            yield return new CompletionItem("ALL", "Show all log levels");
        }

        foreach (LogLevel level in LogLevels.All.Where(level => !chosen.Contains(level.ToName())))
        {
            yield return new CompletionItem(level.ToName(), $"Severity {(int)level}");
        }
    }

    /// <summary>
    /// Setting keys, described by section.
    /// </summary>
    /// <param name="describe">Describes a key from its section.</param>
    /// <returns>The source.</returns>
    public static Func<CompletionContext, IEnumerable<CompletionItem>> SettingKeys(Func<string, string> describe) =>
        _ => SettingsSchema.Keys.Select(key => new CompletionItem(key, describe(key.Split('.')[0])));

    /// <summary>
    /// Built-in theme names with their descriptions, then custom theme names.
    /// </summary>
    /// <param name="context">The completion context.</param>
    /// <returns>The candidates.</returns>
    public static IEnumerable<CompletionItem> Themes(CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        (IReadOnlyList<string>? builtIn, IReadOnlyList<string>? custom) = context.Session.Themes.ListThemes();
        foreach (string name in builtIn)
        {
            string description = BuiltInThemes.All[name].Description;
            yield return new CompletionItem(name, description.Length > 0 ? description : "Built-in theme");
        }

        foreach (string? name in custom.Where(name => !BuiltInThemes.All.ContainsKey(name)))
        {
            yield return new CompletionItem(name, "Custom theme");
        }
    }

    /// <summary>
    /// The built-in highlighter names, sorted, with a description made from each.
    /// </summary>
    /// <param name="describe">Describes a highlighter from its name.</param>
    /// <returns>The source.</returns>
    public static Func<CompletionContext, IEnumerable<CompletionItem>> Highlighters(Func<string, string> describe) =>
        _ => BuiltInHighlighters.Names.Order(StringComparer.Ordinal).Select(name => new CompletionItem(name, describe(name)));

    /// <summary>
    /// The custom highlighter names, described by the start of their patterns.
    /// </summary>
    /// <param name="context">The completion context.</param>
    /// <returns>The candidates.</returns>
    public static IEnumerable<CompletionItem> CustomHighlighters(CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        return context.Session.Highlighting.CustomHighlighters.Select(custom =>
            new CompletionItem(custom.Name, $"Remove custom: {(custom.Pattern.Length > 20 ? custom.Pattern[..20] : custom.Pattern)}..."));
    }

    /// <summary>
    /// Files and directories whose names continue the word being typed; directories end with a separator.
    /// </summary>
    /// <param name="context">The completion context.</param>
    /// <returns>The candidates, directories first, each group sorted.</returns>
    public static IEnumerable<CompletionItem> Paths(CompletionContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        string typed = context.Partial;
        int separator = typed.LastIndexOfAny(['/', Path.DirectorySeparatorChar]);
        string directoryPart = separator >= 0 ? typed[..(separator + 1)] : "";
        string namePart = separator >= 0 ? typed[(separator + 1)..] : typed;
        string directory = directoryPart.Length == 0
            ? context.CurrentDirectory
            : PathDisplay.Resolve(directoryPart, context.Session.Home, context.CurrentDirectory);
        if (!Directory.Exists(directory))
        {
            return [];
        }

        try
        {
            var entries = new DirectoryInfo(directory).EnumerateFileSystemInfos()
                .Where(entry => entry.Name.StartsWith(namePart, StringComparison.OrdinalIgnoreCase))
                .Where(entry => namePart.StartsWith('.') || !entry.Name.StartsWith('.'))
                .ToList();
            return
            [
                .. entries.OfType<DirectoryInfo>().OrderBy(entry => entry.Name, StringComparer.Ordinal)
                                .Select(entry => new CompletionItem(directoryPart + entry.Name + "/", "directory", Continues: true)
                                {
                                    Display = entry.Name + "/",
                                })
,
                .. entries.OfType<FileInfo>().OrderBy(entry => entry.Name, StringComparer.Ordinal)
                        .Select(entry => new CompletionItem(directoryPart + entry.Name, "file") { Display = entry.Name }),
            ];
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return [];
        }
    }
}
