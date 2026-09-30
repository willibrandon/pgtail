using Pgtail.Parsing;

namespace Pgtail.Notifications;

/// <summary>
/// The notification rules in force, whether notifications are on, and the quiet hours.
/// </summary>
public sealed class NotificationConfig
{
    private readonly List<NotificationRule> _rules = [];

    /// <summary>
    /// Whether notifications are sent at all.
    /// </summary>
    public bool Enabled { get; set; }

    /// <summary>
    /// The rules, in the order they were added.
    /// </summary>
    public IReadOnlyList<NotificationRule> Rules => _rules;

    /// <summary>
    /// When notifications are held back, or null for never.
    /// </summary>
    public QuietHours? QuietHours { get; set; }

    /// <summary>
    /// Adds a rule.
    /// </summary>
    /// <remarks>
    /// Levels merge into the existing level rule, an error rate or slow query rule replaces the one before it, and
    /// pattern rules accumulate.
    /// </remarks>
    /// <param name="rule">The rule.</param>
    public void Add(NotificationRule rule)
    {
        ArgumentNullException.ThrowIfNull(rule);
        switch (rule.Kind)
        {
            case NotificationRuleKind.Level when _rules.Find(existing => existing.Kind == NotificationRuleKind.Level) is { } levels:
                levels.Levels.UnionWith(rule.Levels);
                return;
            case NotificationRuleKind.ErrorRate or NotificationRuleKind.SlowQuery:
                _ = _rules.RemoveAll(existing => existing.Kind == rule.Kind);
                break;
        }

        _rules.Add(rule);
    }

    /// <summary>
    /// Removes every rule.
    /// </summary>
    public void Clear() => _rules.Clear();

    /// <summary>
    /// The levels that send notifications.
    /// </summary>
    /// <returns>The levels, empty when there is no level rule.</returns>
    public IReadOnlySet<LogLevel> LevelRules() =>
        _rules.Find(rule => rule.Kind == NotificationRuleKind.Level)?.Levels ?? [];

    /// <summary>
    /// The pattern rules.
    /// </summary>
    /// <returns>The rules, in order.</returns>
    public IReadOnlyList<NotificationRule> PatternRules() => [.. _rules.Where(rule => rule.Kind == NotificationRuleKind.Pattern)];

    /// <summary>
    /// The error rate threshold, when set.
    /// </summary>
    /// <returns>The errors per minute allowed, or null.</returns>
    public long? ErrorRateThreshold() => _rules.Find(rule => rule.Kind == NotificationRuleKind.ErrorRate)?.ErrorThreshold;

    /// <summary>
    /// The slow query threshold, when set.
    /// </summary>
    /// <returns>The milliseconds allowed, or null.</returns>
    public long? SlowQueryThreshold() => _rules.Find(rule => rule.Kind == NotificationRuleKind.SlowQuery)?.SlowThresholdMs;
}
