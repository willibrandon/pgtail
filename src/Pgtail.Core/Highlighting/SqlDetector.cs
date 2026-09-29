using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Finds SQL in log messages so SQL highlighters touch only the SQL.
/// </summary>
/// <remarks>
/// SQL follows <c>statement:</c>, <c>execute name:</c>, <c>parse name:</c>, <c>bind name:</c>, the same after
/// <c>duration: N ms</c>, or a leading <c>DETAIL:</c>. Keeping SQL highlighters inside it stops words such as
/// "for" or "at" in ordinary messages from being styled as keywords.
/// </remarks>
public static partial class SqlDetector
{
    private static readonly string[] Prefixes = ["dur", "stmt", "exec", "parse", "bind", "detail"];

    /// <summary>
    /// Detects the SQL in a message.
    /// </summary>
    /// <param name="message">The message.</param>
    /// <returns>The SQL and the text around it, or null when the message has none.</returns>
    public static SqlDetection? Detect(string message)
    {
        ArgumentNullException.ThrowIfNull(message);
        if (message.Length == 0)
        {
            return null;
        }

        var match = Pattern().Match(message);
        if (!match.Success)
        {
            return null;
        }

        foreach (var prefix in Prefixes)
        {
            var sql = match.Groups[prefix + "_sql"];
            if (sql.Success && !string.IsNullOrWhiteSpace(sql.Value))
            {
                return new SqlDetection(match.Groups[prefix + "_prefix"].Value, sql.Value, match.Groups[prefix + "_suffix"].Value);
            }
        }

        return null;
    }

    [GeneratedRegex(
        @"^(?:(?<dur_prefix>.*?duration:\s*[\d.]+\s*ms\s+(?:statement|parse|bind|execute)\s*(?:\S+)?:\s*)(?<dur_sql>.*?)(?<dur_suffix>\s*)$"
        + @"|(?<stmt_prefix>.*?statement:\s*)(?<stmt_sql>.*?)(?<stmt_suffix>\s*)$"
        + @"|(?<exec_prefix>.*?execute\s+\S+:\s*)(?<exec_sql>.*?)(?<exec_suffix>\s*)$"
        + @"|(?<parse_prefix>.*?parse\s+\S+:\s*)(?<parse_sql>.*?)(?<parse_suffix>\s*)$"
        + @"|(?<bind_prefix>.*?bind\s+\S+:\s*)(?<bind_sql>.*?)(?<bind_suffix>\s*)$"
        + @"|(?<detail_prefix>DETAIL:\s*)(?<detail_sql>.*?)(?<detail_suffix>\s*)$)",
        RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}
