using System.Globalization;

namespace Pgtail.Detection;

/// <summary>
/// A detected PostgreSQL installation.
/// </summary>
/// <param name="Id">The number users refer to it by, counting from 0.</param>
/// <param name="Version">The PostgreSQL version, such as <c>16</c>, or <c>unknown</c>.</param>
/// <param name="DataDirectory">The data directory.</param>
/// <param name="LogPath">The current log file, or null when none is known.</param>
/// <param name="LogDirectory">The directory the logging collector writes to, or null when it is off.</param>
/// <param name="Source">How it was found.</param>
/// <param name="Running">Whether its postmaster is running.</param>
/// <param name="Launcher">What starts and stops it, and where its output goes when the logging collector is off.</param>
/// <param name="Pid">The postmaster's process ID when running.</param>
/// <param name="Port">The port, when configured.</param>
/// <param name="LoggingEnabled">
/// Whether the server logs to files: <c>logging_collector</c> is on, or the program that starts it, such as ankus,
/// cargo pgrx, or <c>pg_ctlcluster</c>, sends its output to a file.
/// </param>
public sealed record PostgresInstance(
    int Id,
    string Version,
    string DataDirectory,
    string? LogPath,
    string? LogDirectory,
    DetectionSource Source,
    bool Running,
    ServerLauncher Launcher,
    int? Pid = null,
    int? Port = null,
    bool LoggingEnabled = false)
{
    /// <summary>
    /// <c>running</c> or <c>stopped</c>.
    /// </summary>
    public string StatusText => Running ? "running" : "stopped";

    /// <summary>
    /// <c>on</c> or <c>off</c> for logging to files.
    /// </summary>
    public string LogStatus => LoggingEnabled ? "on" : "off";

    /// <summary>
    /// The port, or <c>-</c> when not known.
    /// </summary>
    public string PortText => Port is { } port and not 0 ? port.ToString(CultureInfo.InvariantCulture) : "-";
}
