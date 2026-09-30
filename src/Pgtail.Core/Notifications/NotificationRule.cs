using Pgtail.Matching;
using Pgtail.Parsing;

namespace Pgtail.Notifications;

/// <summary>
/// One condition that sends a notification.
/// </summary>
public sealed class NotificationRule
{
    private NotificationRule(NotificationRuleKind kind)
    {
        Kind = kind;
    }

    /// <summary>
    /// What triggers the rule.
    /// </summary>
    public NotificationRuleKind Kind { get; }

    /// <summary>
    /// The levels of a level rule.
    /// </summary>
    public HashSet<LogLevel> Levels { get; } = [];

    /// <summary>
    /// The pattern of a pattern rule.
    /// </summary>
    public LogPattern? Pattern { get; private init; }

    /// <summary>
    /// The errors per minute an error rate rule allows.
    /// </summary>
    public long ErrorThreshold { get; private init; }

    /// <summary>
    /// The query duration in milliseconds a slow query rule allows.
    /// </summary>
    public long SlowThresholdMs { get; private init; }

    /// <summary>
    /// A rule for entries at any of some levels.
    /// </summary>
    /// <param name="levels">The levels.</param>
    /// <returns>The rule.</returns>
    public static NotificationRule ForLevels(IEnumerable<LogLevel> levels)
    {
        ArgumentNullException.ThrowIfNull(levels);
        var rule = new NotificationRule(NotificationRuleKind.Level);
        rule.Levels.UnionWith(levels);
        return rule;
    }

    /// <summary>
    /// A rule for messages matching a pattern.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The rule.</returns>
    /// <exception cref="FormatException">The pattern is not a valid regular expression.</exception>
    public static NotificationRule ForPattern(string pattern, bool caseSensitive = true) =>
        new(NotificationRuleKind.Pattern) { Pattern = LogPattern.Compile(pattern, caseSensitive) };

    /// <summary>
    /// A rule for more than a number of errors in a minute.
    /// </summary>
    /// <param name="threshold">The errors per minute allowed.</param>
    /// <returns>The rule.</returns>
    public static NotificationRule ForErrorRate(long threshold) => new(NotificationRuleKind.ErrorRate) { ErrorThreshold = threshold };

    /// <summary>
    /// A rule for queries slower than a duration.
    /// </summary>
    /// <param name="thresholdMs">The duration in milliseconds allowed.</param>
    /// <returns>The rule.</returns>
    public static NotificationRule ForSlowQuery(long thresholdMs) => new(NotificationRuleKind.SlowQuery) { SlowThresholdMs = thresholdMs };

    /// <summary>
    /// The pattern as saved in the configuration: <c>/pattern/</c>, or <c>/pattern/i</c> when it ignores case.
    /// </summary>
    /// <returns>The text, or null for a rule that is not a pattern rule.</returns>
    public string? FormatPattern() => Pattern is { } pattern ? $"/{pattern.Pattern}/{(pattern.CaseSensitive ? "" : "i")}" : null;
}
