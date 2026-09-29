using System.Globalization;
using System.Text;
using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Tail;

/// <summary>
/// Finds the PostgreSQL version and port in startup messages, for the status bar when tailing a file.
/// </summary>
internal static class InstanceDetection
{
    private static readonly ByteRegex Version = ByteRegex.Compile(@"(?i)starting PostgreSQL ([0-9]+)(?:\.([0-9]+))?");
    private static readonly ByteRegex Port = ByteRegex.Compile(@"listening on .*port ([0-9]+)");
    private static readonly ByteRegex SocketPort = ByteRegex.Compile(@"\.s\.PGSQL\.([0-9]+)");

    /// <summary>
    /// The version from <c>starting PostgreSQL 17.0 on ...</c> and the port from a <c>listening on</c> message.
    /// </summary>
    /// <param name="message">The log message.</param>
    /// <returns>The version, such as <c>17.0</c>, and the port; either may be null.</returns>
    public static (string? Version, int? Port) Find(string message)
    {
        ArgumentNullException.ThrowIfNull(message);
        using var text = new Utf8Text(message);
        var bytes = text.Bytes;
        string? version = null;
        if (Version.FindCaptures(bytes) is { } found && found.GetGroup(1) is { } major)
        {
            version = Encoding.UTF8.GetString(major.Value(bytes));
            if (found.GetGroup(2) is { } minor)
            {
                version += "." + Encoding.UTF8.GetString(minor.Value(bytes));
            }
        }

        var port = Number(Port, bytes) ?? Number(SocketPort, bytes);
        return (version, port);
    }

    private static int? Number(ByteRegex regex, ReadOnlySpan<byte> bytes) =>
        regex.FindCaptures(bytes) is { } found && found.GetGroup(1) is { } group
        && int.TryParse(group.Value(bytes), NumberStyles.None, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
}
