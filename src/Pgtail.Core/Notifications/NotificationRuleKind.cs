namespace Pgtail.Notifications;

/// <summary>
/// What triggers a notification rule.
/// </summary>
public enum NotificationRuleKind
{
    /// <summary>
    /// An entry at one of the chosen levels.
    /// </summary>
    Level,

    /// <summary>
    /// A message matching a pattern.
    /// </summary>
    Pattern,

    /// <summary>
    /// More errors in the current minute than a threshold.
    /// </summary>
    ErrorRate,

    /// <summary>
    /// A query slower than a threshold.
    /// </summary>
    SlowQuery,
}
