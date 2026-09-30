using System.Text;
using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Statistics;

/// <summary>
/// Recognizes the log messages PostgreSQL writes for connections, disconnections, and failed connection attempts.
/// </summary>
public static class ConnectionMessageParser
{
    // Groups: user, database, application.
    private static readonly ByteRegex Authorized =
        ByteRegex.Compile(@"connection authorized:\s+user=(\S+)\s+database=(\S+)(?:\s+application_name=(\S+))?");

    // Groups: duration, user, database, host, port.
    private static readonly ByteRegex Disconnection = ByteRegex.Compile(
        @"disconnection:\s+session time:\s+([0-9:\.]+)\s+user=(\S+)\s+database=(\S+)\s+host=(\S+)(?:\s+port=([0-9]+))?");

    private static readonly ByteRegex FatalConnection = ByteRegex.Compile(
        "(?i)too many connections|too many clients already|connection limit exceeded|password authentication failed"
        + "|no pg_hba\\.conf entry|database .* does not exist|role .* does not exist|authentication failed");

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

        // Most lines are neither, and looking for the words each pattern starts with is much cheaper than matching it.
        var connect = message.Contains("connection authorized:", StringComparison.Ordinal);
        var disconnect = message.Contains("disconnection:", StringComparison.Ordinal);
        if (!connect && !disconnect && !isFatal)
        {
            return null;
        }

        using var text = new Utf8Text(message);
        var bytes = text.Bytes;
        if (connect && Authorized.FindCaptures(bytes) is { } authorized)
        {
            return new ConnectionMessage(ConnectionEventType.Connect, Group(bytes, authorized, 1), Group(bytes, authorized, 2),
                Group(bytes, authorized, 3));
        }

        if (disconnect && Disconnection.FindCaptures(bytes) is { } ended)
        {
            return new ConnectionMessage(ConnectionEventType.Disconnect, Group(bytes, ended, 2), Group(bytes, ended, 3),
                Host: Group(bytes, ended, 4), Port: Group(bytes, ended, 5), Duration: Group(bytes, ended, 1));
        }

        // The failure phrases are matched without regard to case, as they are written in lower case by PostgreSQL.
        return isFatal && FatalConnection.IsMatch(bytes) ? new ConnectionMessage(ConnectionEventType.ConnectionFailed) : null;
    }

    private static string? Group(ReadOnlySpan<byte> bytes, ByteRegexCaptures captures, int index) =>
        captures.GetGroup(index) is { } group ? Encoding.UTF8.GetString(group.Value(bytes)) : null;
}
