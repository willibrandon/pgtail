using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Something a log source reports to its reader.
/// </summary>
/// <param name="Kind">What happened.</param>
/// <param name="Entry">The entry read, for <see cref="LogSourceEventKind.Entry"/>.</param>
/// <param name="Format">The detected format, for <see cref="LogSourceEventKind.FormatDetected"/>.</param>
/// <param name="Path">The file concerned, for format detection and file switches.</param>
/// <param name="LinesRead">The number of lines read, for <see cref="LogSourceEventKind.EndOfInput"/>.</param>
/// <param name="Entries">The entries read back, oldest first, for <see cref="LogSourceEventKind.Older"/>.</param>
public sealed record LogSourceEvent(
    LogSourceEventKind Kind,
    LogEntry? Entry = null,
    LogFormat? Format = null,
    string? Path = null,
    long LinesRead = 0,
    IReadOnlyList<LogEntry>? Entries = null);
