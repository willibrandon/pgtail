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
    /// Writes a log whose error line ends exactly where the first read of it stops, with its statement after.
    /// </summary>
    /// <remarks>
    /// Filler entries come first, then the error, then its statement and a checkpoint entry. The error is <c>relation
    /// "nope" does not exist</c> and the statement <c>select * from nope</c>.
    /// </remarks>
    /// <param name="path">The file.</param>
    /// <param name="read">How much one read takes, in bytes.</param>
    /// <returns>The file.</returns>
    public static string ErrorAtBoundary(string path, int read)
    {
        DateTime time = DateTime.UtcNow.AddMinutes(-5);
        string error = Text(time, 2001, "ERROR", "relation \"nope\" does not exist");
        string filler = Text(time, 2000, "LOG", "statement: select 1");
        int room = read - (error.Length + 1);
        int lines = room / (filler.Length + 1);
        string last = Text(time, 2000, "LOG", "statement: select 1" + new string('-', room - (lines * (filler.Length + 1))));
        Append(path, [.. Enumerable.Repeat(filler, lines - 1), last, error]);
        Assert.AreEqual(read, new FileInfo(path).Length, "the error ends the first read");
        Append(path,
            Text(time, 2001, "STATEMENT", "select * from nope"),
            Text(time.AddSeconds(1), 2002, "LOG", "checkpoint starting: time"));
        return path;
    }

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
