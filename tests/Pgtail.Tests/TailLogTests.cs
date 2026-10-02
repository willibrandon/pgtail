using Hex1b;
using Pgtail.Display;
using Pgtail.Parsing;
using Pgtail.Styling;
using Pgtail.Tail;

namespace Pgtail.Tests;

/// <summary>
/// The tail log's widest row, which sets how far tail mode scrolls sideways.
/// </summary>
[TestClass]
public sealed class TailLogTests
{
    /// <summary>
    /// The width measured from an entry's text is the width of the widest row drawn from it.
    /// </summary>
    [TestMethod]
    public void WidestMatchesTheDrawnRows()
    {
        string[] texts =
        [
            "plain ascii text",
            "a\tb\tc",
            "héllo wörld\twith a tab",
            "日本語のテキスト\tand more",
            "line one\nmuch longer second line\nthree",
            "\tx\r\n\ty",
            "",
        ];
        foreach (string text in texts)
        {
            int drawn = TailLine.From(new StyledText(text))
                .Select(row => GraphemeHelper.IndexToDisplayColumn(row.Text, row.Text.Length))
                .Max();
            Assert.AreEqual(drawn, TailLine.Widest(text), text);
        }
    }

    /// <summary>
    /// The prefix length worked out without formatting is the length of the formatted prefix, for every kind of entry.
    /// </summary>
    [TestMethod]
    public void PrefixLengthMatchesTheFormattedPrefix()
    {
        DateTime time = new(2026, 10, 2, 9, 30, 15, 123, DateTimeKind.Utc);
        LogEntry[] entries =
        [
            new() { Message = "no fields at all" },
            new() { Timestamp = time, Offset = TimeSpan.Zero, Pid = 42, Level = LogLevel.Error, Message = "short pid" },
            new() { Timestamp = time, Offset = TimeSpan.Zero, Pid = 1234567, Level = LogLevel.Notice, Message = "long pid" },
            new() { Pid = -1, Level = LogLevel.Warning, SqlState = "40P01", Message = "a negative pid and a code" },
            new() { Timestamp = time, Offset = TimeSpan.Zero, SourceFile = "a.log", Level = LogLevel.Debug5, Message = "with a file" },
        ];
        foreach (LogEntry entry in entries)
        {
            Assert.AreEqual(EntryFormatter.TailPrefix(entry).Length, EntryFormatter.TailPrefixLength(entry), entry.Message);
        }

        Assert.IsNull(EntryFormatter.TailPrefixLength(new LogEntry { SourceFile = "日誌.log", Message = "a file name in kanji" }));
    }

    /// <summary>
    /// An entry's rows measured after its prefix are as wide as the rows drawn from the whole line.
    /// </summary>
    [TestMethod]
    public void WidestAfterThePrefixMatchesTheDrawnRows()
    {
        foreach (string message in new[] { "plain", "tab\tafter the prefix", "ünïcode\tand a tab", "first\n\tsecond, indented" })
        {
            var entry = new LogEntry { Pid = 7, Level = LogLevel.Log, Message = message };
            int drawn = TailLine.From(new StyledText(EntryFormatter.TailPrefix(entry).PlainText + message))
                .Select(row => GraphemeHelper.IndexToDisplayColumn(row.Text, row.Text.Length))
                .Max();
            Assert.AreEqual(drawn, TailLine.Widest(EntryFormatter.TailPrefixLength(entry)!.Value, message), message);
        }
    }

    /// <summary>
    /// The widest row is the widest of those kept, as rows are added in front and behind, dropped, and cleared.
    /// </summary>
    [TestMethod]
    public void WidestFollowsRowsAddedDroppedAndCleared()
    {
        var log = new TailLog();
        _ = log.Append([Segment(1, 300), Segment(1, 80)]);
        Assert.AreEqual(300, log.Widest);
        _ = log.Append([Segment(TailLog.MaxLines - 1, 120)]);
        Assert.AreEqual(120, log.Widest, "the widest row was dropped");
        _ = log.Prepend([Segment(1, 500)]);
        Assert.AreEqual(120, log.Widest, "nothing fits in front of a full log");
        log.Clear();
        Assert.AreEqual(0, log.Widest);
        _ = log.Prepend([Segment(1, 500)]);
        Assert.AreEqual(500, log.Widest);
    }

    private static TailSegment Segment(int rows, int width) => new(rows, width, () => [TailLine.Blank]);
}
