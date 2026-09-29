using Pgtail.Commands;
using Pgtail.Files;
using Pgtail.Sessions;

namespace Pgtail.Tailing;

/// <summary>
/// Creates the log source a tail request reads from.
/// </summary>
internal static class LogSources
{
    /// <summary>
    /// How often files are polled for new lines.
    /// </summary>
    public static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(100);

    /// <summary>
    /// Creates a source for a request.
    /// </summary>
    /// <remarks>
    /// Existing lines are read first only while a time filter is set, so it can look back, and then only the last ones
    /// when a count is given; otherwise only new lines are read, as with <c>tail -f</c>. A single file follows rotation
    /// within its directory; an instance also consults <c>current_logfiles</c>; several files or a glob are interleaved by
    /// time.
    /// </remarks>
    /// <param name="request">The request.</param>
    /// <param name="session">The session, for the time filter and home directory.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    /// <param name="stdin">Standard input, for a standard input source.</param>
    /// <param name="lastLines">How many of each file's last lines a time filter reads back, or null for all of them.</param>
    /// <returns>The source, not yet started.</returns>
    public static ILogSource Create(
        TailRequest request,
        PgtailSession session,
        string currentDirectory,
        Func<Stream> stdin,
        int? lastLines = null)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(session);
        var source = request.Source;
        var fromStart = session.Time.IsActive;
        if (source.Stdin)
        {
            return new StreamLogSource(stdin());
        }

        if (source.Instance is { } instance)
        {
            return new LogTailer(request.LogPath!, fromStart, instance.DataDirectory, instance.LogDirectory, PollInterval, lastLines);
        }

        var files = source.Files ?? [];
        var glob = source.GlobPattern is { } pattern ? GlobPattern.FromPath(pattern, session.Home, currentDirectory) : null;
        if (files.Count == 1 && glob is null)
        {
            return new LogTailer(files[0], fromStart, null, Path.GetDirectoryName(files[0]), PollInterval, lastLines);
        }

        return new MultiFileTailer(files, glob, fromStart, PollInterval, lastLines);
    }
}
