using Pgtail.Filtering;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// Level, regular expression, and field filters.
/// </summary>
/// <remarks>
/// The REPL has <c>levels</c> and <c>filter</c>; tail mode has <c>level</c> and <c>filter</c>.
/// </remarks>
internal static class FilterCommands
{
    /// <summary>
    /// The REPL's <c>levels</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Levels(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var available = $"Available levels: {string.Join(' ', LogLevels.Names)}";
        if (invocation.Args.Count == 0)
        {
            output.Line(session.ActiveLevels is { } active ? $"Filter: {Names(active, ' ')}" : "Filter: ALL (showing all levels)");
            output.Line();
            output.Line("Usage: levels [LEVEL...]  Set filter to specific levels");
            output.Line("       levels ALL         Show all levels");
            output.Line();
            output.Line(available);
            return Task.CompletedTask;
        }

        var (levels, invalid) = LogLevels.ParseArguments(SplitCommas(invocation.Args));
        if (invalid.Count > 0)
        {
            output.Line($"Unknown level(s): {string.Join(", ", invalid)}");
            output.Line($"Valid levels: {string.Join(' ', LogLevels.Names)}");
            return Task.CompletedTask;
        }

        session.ActiveLevels = levels;
        output.Line(levels is null ? "Filter cleared - showing all levels" : $"Filter set: {Names(levels, ' ')}");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Tail mode's <c>level</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailLevel(CommandInvocation invocation)
    {
        var host = (ITailHost)invocation.Host;
        var (levels, invalid) = LogLevels.ParseArguments(SplitCommas(invocation.Args));
        if (invalid.Count > 0)
        {
            invocation.Output.Markup($"[bold red]✗[/] Unknown level(s): {Markup.Escape(string.Join(", ", invalid))}");
            return Task.CompletedTask;
        }

        invocation.Session.ActiveLevels = levels;
        host.RefreshStatus();
        host.Rebuild();
        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL's <c>filter</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Filter(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        if (invocation.Args.Count == 0)
        {
            ShowFilters(session, output);
            return Task.CompletedTask;
        }

        var argument = invocation.Args[0];
        if (argument.Equals("clear", StringComparison.OrdinalIgnoreCase))
        {
            session.Regex.ClearFilters();
            session.Fields.Clear();
            output.Line("All filters cleared");
            return Task.CompletedTask;
        }

        if (IsFieldFilter(argument))
        {
            if (session.DetectedFormat == LogFormat.Text)
            {
                output.Line("Warning: Field filtering is only effective for CSV/JSON log formats.");
                output.Line("Text format logs don't have structured fields.");
                output.Line();
            }

            var (field, value) = SplitField(argument);
            if (value.Length == 0)
            {
                output.Line($"Empty value for field filter: {argument}");
                return Task.CompletedTask;
            }

            try
            {
                session.Fields.Add(field, value);
            }
            catch (ArgumentException exception)
            {
                output.Line($"Error: {exception.Message}");
                return Task.CompletedTask;
            }

            output.Line($"Field filter set: {FieldNames.Resolve(field)}={value}");
            return Task.CompletedTask;
        }

        if (Parse(argument) is not { } parsed)
        {
            output.Line($"Invalid filter syntax: {argument}");
            output.Line("Use /pattern/ syntax (e.g., filter /error/)");
            return Task.CompletedTask;
        }

        if (parsed.Error is { } error)
        {
            output.Line(error);
            return Task.CompletedTask;
        }

        var filter = parsed.Filter!;
        var sensitivity = filter.CaseSensitive ? " (case-sensitive)" : "";
        if (parsed.Replace)
        {
            session.Regex.SetInclude(filter);
            output.Line($"Filter set: /{filter.Pattern}/{sensitivity}");
        }
        else
        {
            session.Regex.Add(filter);
            output.Line($"Filter added ({TypeName(filter.Type)}): /{filter.Pattern}/{sensitivity}");
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Tail mode's <c>filter</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailFilter(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var host = (ITailHost)invocation.Host;
        if (invocation.Args.Count == 0)
        {
            if (!session.Regex.HasFilters && !session.Fields.IsActive)
            {
                output.Markup("[dim]No filters active[/]");
                return Task.CompletedTask;
            }

            foreach (var (filter, label, color, prefix) in session.Regex.Includes.Select(f => (f, "include", "cyan", ""))
                .Concat(session.Regex.Excludes.Select(f => (f, "exclude", "yellow", "-")))
                .Concat(session.Regex.Ands.Select(f => (f, "and", "green", "&"))))
            {
                output.Markup($"[dim]{label}:[/] [{color}]{prefix}/{Markup.Escape(filter.Pattern)}/{(filter.CaseSensitive ? "c" : "")}[/]");
            }

            if (session.Fields.IsActive)
            {
                output.Markup($"[dim]{Markup.Escape(session.Fields.FormatStatus())}[/]");
            }

            return Task.CompletedTask;
        }

        var argument = invocation.Args[0];
        if (argument.Equals("clear", StringComparison.OrdinalIgnoreCase))
        {
            session.Regex.ClearFilters();
            session.Fields.Clear();
            output.Markup("[bold green]✓[/] All filters cleared");
            host.RefreshStatus();
            host.Rebuild();
            return Task.CompletedTask;
        }

        if (IsFieldFilter(argument))
        {
            if (host.Format == LogFormat.Text)
            {
                output.Markup("[yellow]Warning:[/] Field filtering only works for CSV/JSON logs");
            }

            var (field, value) = SplitField(argument);
            if (value.Length > 0)
            {
                try
                {
                    session.Fields.Add(field, value);
                    output.Markup($"[bold green]✓[/] Field filter: [cyan]{Markup.Escape($"{FieldNames.Resolve(field)}={value}")}[/]");
                    host.Rebuild();
                }
                catch (ArgumentException exception)
                {
                    output.Markup($"[bold red]✗[/] Error: {Markup.Escape(exception.Message)}");
                }
            }

            return Task.CompletedTask;
        }

        if (Parse(argument) is not { } parsed)
        {
            output.Markup($"[bold red]✗[/] Invalid filter syntax: {Markup.Escape(argument)}");
            output.Markup("[dim]Use /pattern/, -/pattern/, +/pattern/, &/pattern/, or field=value[/]");
            return Task.CompletedTask;
        }

        if (parsed.Error is { } error)
        {
            output.Markup($"[bold red]✗[/] {Markup.Escape(error)}");
            return Task.CompletedTask;
        }

        var added = parsed.Filter!;
        if (parsed.Replace)
        {
            session.Regex.SetInclude(added);
        }
        else
        {
            session.Regex.Add(added);
        }

        var pattern = $"/{added.Pattern}/{(added.CaseSensitive ? "c" : "")}";
        output.Markup($"[bold green]✓[/] Filter {TypeName(added.Type)}: [cyan]{Markup.Escape(pattern)}[/]");
        host.RefreshStatus();
        host.Rebuild();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Splits comma-separated arguments, as in <c>level error,warning</c>.
    /// </summary>
    /// <param name="arguments">The arguments.</param>
    /// <returns>The separate words.</returns>
    public static List<string> SplitCommas(IEnumerable<string> arguments) =>
        [.. arguments.SelectMany(argument => argument.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))];

    private static void ShowFilters(PgtailSession session, CommandOutput output)
    {
        if (!session.Regex.HasFilters && !session.Fields.IsActive)
        {
            output.Line("No filters active");
        }
        else
        {
            if (session.Regex.HasFilters)
            {
                output.Line("Active regex filters:");
                foreach (var (filter, label) in session.Regex.Includes.Select(f => (f, "include"))
                    .Concat(session.Regex.Excludes.Select(f => (f, "exclude")))
                    .Concat(session.Regex.Ands.Select(f => (f, "and"))))
                {
                    output.Line($"  {label}: /{filter.Pattern}/{(filter.CaseSensitive ? " (case-sensitive)" : "")}");
                }
            }

            if (session.Fields.IsActive)
            {
                output.Line(session.Fields.FormatStatus());
            }
        }

        output.Line();
        output.Lines(
        [
            "Usage: filter /pattern/       Include only matching lines (regex)",
            "       filter -/pattern/      Exclude matching lines",
            "       filter +/pattern/      Add OR pattern",
            "       filter &/pattern/      Add AND pattern",
            "       filter /pattern/c      Case-sensitive match",
            "       filter field=value     Filter by field (CSV/JSON only)",
            "       filter clear           Clear all filters",
            "",
            $"Available fields: {string.Join(", ", FieldNames.Aliases.Keys.Order(StringComparer.Ordinal))}",
        ]);
    }

    private static bool IsFieldFilter(string argument)
    {
        var equals = argument.IndexOf('=', StringComparison.Ordinal);
        return equals > 0 && FieldNames.Aliases.ContainsKey(argument[..equals].ToLowerInvariant());
    }

    private static (string Field, string Value) SplitField(string argument)
    {
        var equals = argument.IndexOf('=', StringComparison.Ordinal);
        return (argument[..equals], argument[(equals + 1)..].Trim());
    }

    private static (RegexFilter? Filter, bool Replace, string? Error)? Parse(string argument)
    {
        var (type, pattern, replace) = argument switch
        {
            ['-', '/', ..] => (FilterType.Exclude, argument[1..], false),
            ['+', '/', ..] => (FilterType.Include, argument[1..], false),
            ['&', '/', ..] => (FilterType.And, argument[1..], false),
            ['/', ..] => (FilterType.Include, argument, true),
            _ => (FilterType.Include, "", false),
        };

        if (pattern.Length == 0)
        {
            return null;
        }

        (string Pattern, bool CaseSensitive) parsed;
        try
        {
            parsed = FilterSyntax.Parse(pattern);
        }
        catch (FormatException exception)
        {
            return (null, false, $"Error: {exception.Message}");
        }

        try
        {
            return (RegexFilter.Create(parsed.Pattern, type, parsed.CaseSensitive), replace, null);
        }
        catch (FormatException exception)
        {
            return (null, false, $"Invalid regex pattern: {exception.Message}");
        }
    }

    private static string TypeName(FilterType type) => type switch
    {
        FilterType.Exclude => "exclude",
        FilterType.And => "and",
        _ => "include",
    };

    private static string Names(IEnumerable<LogLevel> levels, char separator) =>
        string.Join(separator, levels.Select(level => level.ToName()).Order(StringComparer.Ordinal));
}
