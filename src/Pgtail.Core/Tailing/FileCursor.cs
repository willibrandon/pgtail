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
    private long _lastSize;

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
    /// Positions the cursor at the start or the end of the file.
    /// </summary>
    /// <param name="fromStart">True to read existing lines; false to read only lines written from now on.</param>
    public void Open(bool fromStart)
    {
        var info = new FileInfo(Path);
        if (!info.Exists)
        {
            Position = 0;
            return;
        }

        Position = fromStart ? 0 : info.Length;
        _identity = FileIdentity.FromPath(Path);
        _modified = info.LastWriteTimeUtc;
        _lastSize = info.Length;
    }

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
            var total = 0;
            while (total < data.Length)
            {
                var read = stream.Read(data, total, data.Length - total);
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

        var buffer = _pending.Length == 0 ? data : [.. _pending, .. data];
        var start = 0;
        for (var i = 0; i < buffer.Length; i++)
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
        var span = line.Span;
        var length = span.Length;
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
            Format = LogFormatDetector.Detect(line);
            formatDetected(Format.Value);
        }

        lines.Add(line.ToArray());
    }

    private void CheckRotation(FileInfo info)
    {
        var size = info.Length;
        var identity = FileIdentity.FromPath(Path);
        var modified = info.LastWriteTimeUtc;
        var truncated = size < Position;
        var recreated = _identity is { } before && identity != before;
        var reused = !OperatingSystem.IsWindows() && _modified is { } last && modified != last && size == _lastSize && Position >= size
            && size > 0;
        _identity = identity;
        _modified = modified;
        _lastSize = size;
        if (truncated || recreated || reused)
        {
            Position = 0;
            Format = null;
            _pending = [];
            _pendingSeen = false;
        }
    }
}
