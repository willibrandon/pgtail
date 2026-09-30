using Pgtail.Parsing;
using Scout.IO.Ignore;

namespace Pgtail.Tailing;

/// <summary>
/// Reads the lines appended to one log file since the last read.
/// </summary>
/// <remarks>
/// <para>
/// Rotation is detected when the file becomes shorter than the read position, when the path names a different file
/// (another device and file ID), or, outside Windows, when its modification time changes while its size stays the same
/// and everything has been read, as happens when a deleted file's inode is reused at once. A rotated file is read again
/// from its start, and its format is detected again.
/// </para>
/// <para>
/// A line is read once its line ending arrives. A last line without one is held until the file stops growing, so a line
/// PostgreSQL is still writing is never split in two.
/// </para>
/// </remarks>
/// <param name="path">The file.</param>
public sealed class FileCursor(string path)
{
    private const int ChunkSize = 1 << 20;
    private byte[] _pending = [];
    private bool _pendingSeen;
    private FileIdentity? _identity;
    private DateTime? _modified;
    private const int OlderChunkSize = 1 << 20;
    private long _lastSize;
    private byte[]? _formatSample;

    /// <summary>
    /// The file.
    /// </summary>
    public string Path { get; } = path;

    /// <summary>
    /// The byte offset of the next read.
    /// </summary>
    public long Position { get; private set; }

    /// <summary>
    /// The format detected from the first non-blank line, or null before one is read.
    /// </summary>
    public LogFormat? Format { get; private set; }

    /// <summary>
    /// Positions the cursor at the start or the end of the file, or at the first entry of its last lines.
    /// </summary>
    /// <remarks>
    /// Reading the last lines finds where they start by counting line endings back from the end, then moves on to the
    /// first line that starts an entry, so no entry is read from its middle. The format is still detected from the first
    /// line of the file.
    /// </remarks>
    /// <param name="fromStart">True to read existing lines; false to read only lines written from now on.</param>
    /// <param name="lastLines">With <paramref name="fromStart"/>, how many of the last lines to read, or null for all.</param>
    public void Open(bool fromStart, int? lastLines = null)
    {
        var info = new FileInfo(Path);
        if (!info.Exists)
        {
            Position = 0;
            return;
        }

        Position = !fromStart ? info.Length : lastLines is { } count ? StartOfLastLines(count, info.Length) : 0;
        _identity = FileIdentity.FromPath(Path);
        _modified = info.LastWriteTimeUtc;
        _lastSize = info.Length;
    }

    /// <summary>
    /// How many times the file was found rotated, after which offsets read before no longer apply.
    /// </summary>
    public int Generation { get; private set; }

    /// <summary>
    /// Whether the last read reached the end of the file, or found nothing to read.
    /// </summary>
    public bool AtEnd { get; private set; }

    /// <summary>
    /// Reads the complete lines appended since the last read.
    /// </summary>
    /// <param name="lines">Receives each non-blank line without its line ending.</param>
    /// <param name="formatDetected">Receives the format when the first non-blank line is read.</param>
    /// <returns>How the read went.</returns>
    public ReadOutcome Read(List<ReadOnlyMemory<byte>> lines, Action<LogFormat> formatDetected)
    {
        ArgumentNullException.ThrowIfNull(lines);
        ArgumentNullException.ThrowIfNull(formatDetected);
        var info = new FileInfo(Path);
        AtEnd = true;
        if (!info.Exists)
        {
            return ReadOutcome.Unavailable;
        }

        CheckRotation(info);
        byte[] data;
        try
        {
            using var stream = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete, 1,
                FileOptions.SequentialScan);
            stream.Seek(Position, SeekOrigin.Begin);
            data = new byte[(int)Math.Clamp(stream.Length - Position, 0, ChunkSize)];
            int total = 0;
            while (total < data.Length)
            {
                int read = stream.Read(data, total, data.Length - total);
                if (read == 0)
                {
                    break;
                }

                total += read;
            }

            if (total < data.Length)
            {
                Array.Resize(ref data, total);
            }

            AtEnd = Position + total >= stream.Length;
        }
        catch (UnauthorizedAccessException)
        {
            return File.Exists(Path) ? ReadOutcome.PermissionDenied : ReadOutcome.Unavailable;
        }
        catch (IOException)
        {
            return ReadOutcome.Unavailable;
        }

        Position += data.Length;
        Split(data, lines, formatDetected);
        return ReadOutcome.Read;
    }

    private void Split(byte[] data, List<ReadOnlyMemory<byte>> lines, Action<LogFormat> formatDetected)
    {
        if (data.Length == 0)
        {
            // A partial last line that did not grow for a whole poll is complete.
            if (_pending.Length > 0 && _pendingSeen)
            {
                Emit(_pending, lines, formatDetected);
                _pending = [];
                _pendingSeen = false;
            }
            else
            {
                _pendingSeen = _pending.Length > 0;
            }

            return;
        }

        byte[] buffer = _pending.Length == 0 ? data : [.. _pending, .. data];
        int start = 0;
        for (int i = 0; i < buffer.Length; i++)
        {
            if (buffer[i] == (byte)'\n')
            {
                Emit(buffer.AsMemory(start, i - start), lines, formatDetected);
                start = i + 1;
            }
        }

        _pending = buffer[start..];
        _pendingSeen = false;
    }

    private void Emit(ReadOnlyMemory<byte> line, List<ReadOnlyMemory<byte>> lines, Action<LogFormat> formatDetected)
    {
        ReadOnlySpan<byte> span = line.Span;
        int length = span.Length;
        if (length > 0 && span[length - 1] == (byte)'\r')
        {
            length--;
        }

        line = line[..length];
        if (line.Span.Trim(" \t\r\n\v\f"u8).IsEmpty)
        {
            return;
        }

        if (Format is null)
        {
            Format = LogFormatDetector.Detect(_formatSample ?? line);
            formatDetected(Format.Value);
        }

        lines.Add(line.ToArray());
    }

    private long StartOfLastLines(int count, long length)
    {
        try
        {
            using var stream = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            byte[] buffer = new byte[64 * 1024];
            int seen = 0;
            for (long end = length; end > 0;)
            {
                long start = Math.Max(0, end - buffer.Length);
                stream.Seek(start, SeekOrigin.Begin);
                stream.ReadExactly(buffer, 0, (int)(end - start));
                for (int i = (int)(end - start) - 1; i >= 0; i--)
                {
                    // The file's last line ending closes its last line rather than starting another.
                    if (buffer[i] == (byte)'\n' && start + i != length - 1 && ++seen >= count)
                    {
                        return EntryStartFrom(stream, start + i + 1, length);
                    }
                }

                end = start;
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // Reading from the start reports the problem as usual.
        }

        return 0;
    }

    // The first line from an offset that starts an entry, judged in the format of the file's first line.
    private long EntryStartFrom(FileStream stream, long offset, long length)
    {
        stream.Seek(0, SeekOrigin.Begin);
        byte[] head = new byte[(int)Math.Min(length, 64 * 1024)];
        stream.ReadExactly(head);
        int firstEnd = Array.IndexOf(head, (byte)'\n');
        _formatSample = head[..(firstEnd < 0 ? head.Length : firstEnd)];
        stream.Seek(offset, SeekOrigin.Begin);
        byte[] window = new byte[(int)Math.Min(length - offset, 1024 * 1024)];
        stream.ReadExactly(window);
        return EntryStart(window, 0, LogFormatDetector.Detect(_formatSample)) is { } start ? offset + start : offset;
    }

    /// <summary>
    /// Reads the lines of the entries in the chunk before an offset.
    /// </summary>
    /// <remarks>
    /// The chunk starts at the first line in it that starts an entry, and grows until it holds one.
    /// </remarks>
    /// <param name="end">Where the lines read end: the start of what was read before.</param>
    /// <param name="lines">Receives the lines, oldest first.</param>
    /// <returns>Where the lines read start, which the next chunk ends at; 0 at the start of the file.</returns>
    public long ReadOlder(long end, List<ReadOnlyMemory<byte>> lines)
    {
        ArgumentNullException.ThrowIfNull(lines);
        LogFormat format = Format ?? LogFormat.Text;
        try
        {
            using var stream = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            for (int size = OlderChunkSize; ; size *= 2)
            {
                long start = Math.Max(0, end - size);
                byte[] data = new byte[end - start];
                stream.Seek(start, SeekOrigin.Begin);
                stream.ReadExactly(data);

                // Past the file's start, the chunk's first line may be the end of an entry the next chunk reads.
                int skip = start == 0 ? 0 : Array.IndexOf(data, (byte)'\n') + 1;
                if (start > 0 && (skip == 0 || EntryStart(data, skip, format) is not { } first))
                {
                    continue;
                }

                int from = start == 0 ? 0 : EntryStart(data, skip, format)!.Value;
                for (int at = from; at < data.Length;)
                {
                    int newline = Array.IndexOf(data, (byte)'\n', at);
                    int stop = newline < 0 ? data.Length : newline;
                    int length = stop > at && data[stop - 1] == (byte)'\r' ? stop - at - 1 : stop - at;
                    if (data.AsSpan(at, length).Trim(" \t\r\n\v\f"u8).Length > 0)
                    {
                        lines.Add(data.AsMemory(at, length));
                    }

                    at = stop + 1;
                }

                return start + from;
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return 0;
        }
    }

    // The offset of the first line at or after an offset in a buffer that starts an entry, or null when none does.
    private static int? EntryStart(byte[] data, int offset, LogFormat format)
    {
        for (int start = offset; start < data.Length;)
        {
            int end = Array.IndexOf(data, (byte)'\n', start);
            if (end < 0)
            {
                return null;
            }

            if (LogLineParser.Parse(data.AsMemory(start, end - start), format) is { Timestamp: not null, Continues: false })
            {
                return start;
            }

            start = end + 1;
        }

        return null;
    }

    private void CheckRotation(FileInfo info)
    {
        long size = info.Length;
        var identity = FileIdentity.FromPath(Path);
        DateTime modified = info.LastWriteTimeUtc;
        bool truncated = size < Position;
        bool recreated = _identity is { } before && identity != before;
        bool reused = !OperatingSystem.IsWindows() && _modified is { } last && modified != last && size == _lastSize && Position >= size
            && size > 0;
        _identity = identity;
        _modified = modified;
        _lastSize = size;
        if (truncated || recreated || reused)
        {
            Generation++;
            Position = 0;
            Format = null;
            _formatSample = null;
            _pending = [];
            _pendingSeen = false;
        }
    }
}
