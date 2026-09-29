using System.Globalization;
using System.Text;

namespace Pgtail.Tests;

/// <summary>
/// Writes PostgreSQL log lines for tests.
/// </summary>
internal static class LogFiles
{
    /// <summary>
    /// A text-format line stamped with a UTC time.
    /// </summary>
    /// <param name="time">The time, in UTC.</param>
    /// <param name="pid">The process ID.</param>
    /// <param name="level">The level name.</param>
    /// <param name="message">The message.</param>
    /// <returns>The line.</returns>
    public static string Text(DateTime time, int pid, string level, string message) =>
        $"{time.ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture)} UTC [{pid}] {level}:  {message}";

    /// <summary>
    /// Appends lines to a file, creating it and its directory.
    /// </summary>
    /// <param name="path">The file.</param>
    /// <param name="lines">The lines.</param>
    public static void Append(string path, params IEnumerable<string> lines)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.AppendAllText(path, string.Concat(lines.Select(line => line + "\n")), new UTF8Encoding(false));
    }
}
