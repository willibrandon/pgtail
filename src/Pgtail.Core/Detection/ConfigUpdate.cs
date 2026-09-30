namespace Pgtail.Detection;

/// <summary>
/// The outcome of changing <c>postgresql.conf</c>.
/// </summary>
/// <param name="Success">Whether the change was made or was not needed.</param>
/// <param name="Message">What happened.</param>
/// <param name="Changes">One line per change made.</param>
public sealed record ConfigUpdate(bool Success, string Message, IReadOnlyList<string> Changes);
