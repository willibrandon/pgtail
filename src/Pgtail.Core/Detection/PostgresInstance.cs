using System.Globalization;

namespace Pgtail.Detection;

/// <summary>
/// A detected PostgreSQL installation.
/// </summary>
/// <param name="Id">The number users refer to it by, counting from 0.</param>
/// <param name="Version">The PostgreSQL version, such as <c>16</c>, or <c>unknown</c>.</param>
/// <param name="DataDirectory">The data directory.</param>
/// <param name="LogPath">The current log file, or null when none is known.</param>
/// <param name="LogDirectory">The directory log files are written to, or null when logging is off.</param>
/// <param name="Source">How it was found.</param>
/// <param name="Running">Whether its postmaster is running.</param>
/// <param name="Pid">The postmaster's process ID when running.</param>
/// <param name="Port">The port, when configured.</param>
/// <param name="LoggingEnabled">Whether <c>logging_collector</c> is on.</param>
/// <param name="ConfigPath">The <c>postgresql.conf</c> in use, when found.</param>
public sealed record PostgresInstance(
    int Id,
    string Version,
    string DataDirectory,
    string? LogPath,
    string? LogDirectory,
    DetectionSource Source,
    bool Running,
    int? Pid = null,
    int? Port = null,
    bool LoggingEnabled = false,
    string? ConfigPath = null)
{
    /// <summary>
    /// <c>running</c> or <c>stopped</c>.
    /// </summary>
    public string StatusText => Running ? "running" : "stopped";

    /// <summary>
    /// <c>on</c> or <c>off</c> for the logging collector.
    /// </summary>
    public string LogStatus => LoggingEnabled ? "on" : "off";

    /// <summary>
    /// The port, or <c>-</c> when not known.
    /// </summary>
    public string PortText => Port is { } port and not 0 ? port.ToString(CultureInfo.InvariantCulture) : "-";
}
