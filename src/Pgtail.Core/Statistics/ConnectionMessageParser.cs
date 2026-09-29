using System.Text.RegularExpressions;

namespace Pgtail.Statistics;

/// <summary>
/// Recognizes the log messages PostgreSQL writes for connections, disconnections, and failed connection attempts.
/// </summary>
public static partial class ConnectionMessageParser
{
    /// <summary>
    /// The FATAL messages that mean a connection attempt failed, as case-insensitive patterns.
    /// </summary>
    public static IReadOnlyList<string> FatalConnectionPatterns { get; } =
    [
        "too many connections",
        "too many clients already",
        "connection limit exceeded",
        "password authentication failed",
        "no pg_hba.conf entry",
        "database .* does not exist",
        "role .* does not exist",
        "authentication failed",
    ];

    /// <summary>
    /// Parses a message.
    /// </summary>
    /// <remarks>
    /// <c>connection received</c> messages are not events: they come before authentication and name no user or database.
    /// </remarks>
    /// <param name="message">The message.</param>
    /// <param name="isFatal">Whether the entry was logged at FATAL, where failed attempts appear.</param>
    /// <returns>The details, or null for a message about something else.</returns>
    public static ConnectionMessage? Parse(string? message, bool isFatal = false)
    {
        if (string.IsNullOrEmpty(message))
        {
            return null;
        }

        var match = Authorized().Match(message);
        if (match.Success)
        {
            return new ConnectionMessage(ConnectionEventType.Connect, match.Groups["user"].Value, match.Groups["database"].Value,
                match.Groups["application"].Success ? match.Groups["application"].Value : null);
        }

        match = Disconnection().Match(message);
        if (match.Success)
        {
            return new ConnectionMessage(ConnectionEventType.Disconnect, match.Groups["user"].Value, match.Groups["database"].Value,
                Host: match.Groups["host"].Value, Port: match.Groups["port"].Success ? match.Groups["port"].Value : null,
                Duration: match.Groups["duration"].Value);
        }

        if (isFatal)
        {
            var lower = message.ToLowerInvariant();
            if (FatalConnectionPatterns.Any(pattern => Regex.IsMatch(lower, pattern, RegexOptions.CultureInvariant)))
            {
                return new ConnectionMessage(ConnectionEventType.ConnectionFailed);
            }
        }

        return null;
    }

    [GeneratedRegex(@"connection authorized:\s+user=(?<user>\S+)\s+database=(?<database>\S+)(?:\s+application_name=(?<application>\S+))?")]
    private static partial Regex Authorized();

    [GeneratedRegex(@"disconnection:\s+session time:\s+(?<duration>[0-9:\.]+)\s+user=(?<user>\S+)\s+database=(?<database>\S+)\s+"
        + @"host=(?<host>\S+)(?:\s+port=(?<port>[0-9]+))?")]
    private static partial Regex Disconnection();
}
