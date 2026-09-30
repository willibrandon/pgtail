using System.Globalization;
using Pgtail.Filtering;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Repl;

/// <summary>
/// The REPL's bottom toolbar: instance count, active filters, and theme, or the shell mode notice.
/// </summary>
internal static class ReplToolbar
{
    /// <summary>
    /// Builds the toolbar text.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <param name="shellMode">Whether shell mode is on.</param>
    /// <returns>The styled toolbar.</returns>
    public static StyledText Build(PgtailSession session, bool shellMode)
    {
        ArgumentNullException.ThrowIfNull(session);
        Theme theme = session.Theme;
        var text = new StyledText();
        TextStyle normal = theme.Style("toolbar");
        TextStyle dim = theme.Style("toolbar.dim");
        if (shellMode)
        {
            return text.Append(" SHELL ", theme.Style("toolbar.shell")).Append("• Press Escape to exit ", dim);
        }

        switch (session.Instances.Count)
        {
            case 0:
                text.Append(" No instances ", theme.Style("toolbar.warning")).Append("(run 'refresh') ", dim);
                break;
            case 1:
                text.Append(" 1 instance ", normal);
                break;
            case var count:
                text.Append($" {count} instances ", normal);
                break;
        }

        string filters = FormatFilters(session);
        if (filters.Length > 0)
        {
            text.Append("• ", dim).Append(filters, theme.Style("toolbar.filter")).Append(" ", normal);
        }

        string name = theme.Name.Length > 15 ? theme.Name[..14] + "…" : theme.Name;
        return text.Append("• ", dim).Append($"Theme: {name} ", normal);
    }

    /// <summary>
    /// The active filters, space separated, or empty when none differ from the defaults.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <returns>The description.</returns>
    public static string FormatFilters(PgtailSession session)
    {
        ArgumentNullException.ThrowIfNull(session);
        var parts = new List<string>();
        if (session.ActiveLevels is { } levels && levels.Count != LogLevels.All.Count)
        {
            parts.Add("levels:" + string.Join(',', levels.Select(level => level.ToName()).Order(StringComparer.Ordinal)));
        }

        RegexFilterState regex = session.Regex;
        if (regex.HasFilters)
        {
            RegexFilter first = regex.Includes.Concat(regex.Excludes).Concat(regex.Ands).First();
            int extra = regex.Includes.Count + regex.Excludes.Count + regex.Ands.Count - 1;
            string part = $"filter:/{first.Pattern}/{(first.CaseSensitive ? "" : "i")}";
            parts.Add(extra > 0 ? $"{part} +{extra} more" : part);
        }

        if (session.Time.IsActive)
        {
            parts.Add(session.Time.FormatDescription());
        }

        if (session.Slow.Enabled && session.Slow.WarningMs != 100)
        {
            parts.Add($"slow:>{session.Slow.WarningMs.ToString("0.###", CultureInfo.InvariantCulture)}ms");
        }

        return string.Join(' ', parts);
    }
}
