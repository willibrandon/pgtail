using System.Globalization;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Pgtail.Highlighting;
using Pgtail.Parsing;
using Pgtail.Statistics;
using Pgtail.Styling;

namespace Pgtail.Display;

/// <summary>
/// Formats log entries for the REPL's streaming output and for JSON output.
/// </summary>
public static class EntryFormatter
{
    private static readonly JsonWriterOptions s_jsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    /// <summary>
    /// The time of day as <c>HH:MM:SS.mmm</c>, as the entry recorded it.
    /// </summary>
    /// <param name="timestamp">The time.</param>
    /// <returns>The text.</returns>
    public static string FormatTime(DateTime timestamp) => timestamp.ToString("HH:mm:ss.fff", CultureInfo.InvariantCulture);

    /// <summary>
    /// A level name padded to seven characters, so messages line up.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <returns>The padded name.</returns>
    public static string PadLevel(LogLevel level) => level.ToName().PadRight(7);

    /// <summary>
    /// Formats an entry for the current display mode and output format.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="display">The display settings.</param>
    /// <param name="theme">The theme.</param>
    /// <param name="chain">The semantic highlighters for messages.</param>
    /// <returns>The formatted entry; JSON output is unstyled.</returns>
    public static StyledText Format(LogEntry entry, DisplayState display, Theme theme, HighlighterChain chain)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(display);
        if (display.OutputFormat == OutputFormat.Json)
        {
            return new StyledText(Json(entry));
        }

        return display.Mode switch
        {
            DisplayMode.Full => Full(entry, theme, chain),
            DisplayMode.Custom => Custom(entry, display.CustomFields, theme, chain),
            _ => Compact(entry, theme, chain),
        };
    }

    /// <summary>
    /// One line: <c>time [pid] LEVEL   SQLSTATE: message</c>.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="theme">The theme.</param>
    /// <param name="chain">The semantic highlighters for the message.</param>
    /// <returns>The formatted line.</returns>
    public static StyledText Compact(LogEntry entry, Theme theme, HighlighterChain chain)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(theme);
        ArgumentNullException.ThrowIfNull(chain);
        StyledText text = Prefix(entry, theme);
        TextStyle levelStyle = LevelStyle(entry.Level, theme);
        text.Append(entry.SqlState is { } state ? $"{PadLevel(entry.Level)} {state}: " : $"{PadLevel(entry.Level)}: ", levelStyle);
        return text.Append(chain.Apply(entry.Message, theme));
    }

    /// <summary>
    /// The compact line followed by each other available field on its own indented, labeled line.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="theme">The theme.</param>
    /// <param name="chain">The semantic highlighters for the message, query, and detail.</param>
    /// <returns>The formatted entry, which may span lines.</returns>
    public static StyledText Full(LogEntry entry, Theme theme, HighlighterChain chain)
    {
        StyledText text = Compact(entry, theme, chain);
        TextStyle detailStyle = theme.Style("detail");
        foreach ((string field, string label) in DisplayFields.Secondary)
        {
            if (entry.GetField(field) is not { } value)
            {
                continue;
            }

            text.Append($"\n  {label}: ");
            string valueText = FieldText(value);
            if (field is "query" or "detail")
            {
                text.Append(chain.Apply(valueText, theme));
            }
            else
            {
                text.Append(valueText, detailStyle);
            }
        }

        return text;
    }

    /// <summary>
    /// Only the chosen fields, separated by spaces, skipping those the entry lacks.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="fields">The field names, in order.</param>
    /// <param name="theme">The theme.</param>
    /// <param name="chain">The semantic highlighters for the message, query, and detail.</param>
    /// <returns>The formatted line.</returns>
    public static StyledText Custom(LogEntry entry, IReadOnlyList<string> fields, Theme theme, HighlighterChain chain)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(fields);
        ArgumentNullException.ThrowIfNull(theme);
        ArgumentNullException.ThrowIfNull(chain);
        var text = new StyledText();
        TextStyle levelStyle = LevelStyle(entry.Level, theme);
        bool first = true;
        foreach (string field in fields)
        {
            if (entry.GetField(field) is not { } value)
            {
                continue;
            }

            if (!first)
            {
                text.Append(" ");
            }

            first = false;
            switch (field)
            {
                case "timestamp":
                    text.Append(FormatTime(entry.WrittenTime!.Value), theme.Style("timestamp"));
                    break;
                case "pid":
                    text.Append($"[{FieldText(value)}]", theme.Style("pid"));
                    break;
                case "level":
                    text.Append(PadLevel(entry.Level), levelStyle);
                    break;
                case "sql_state":
                    text.Append(FieldText(value), levelStyle);
                    break;
                case "message" or "query" or "detail":
                    text.Append(chain.Apply(FieldText(value), theme));
                    break;
                default:
                    text.Append(FieldText(value));
                    break;
            }
        }

        return text;
    }

    /// <summary>
    /// A slow query, with its level and message colored by how slow it was.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="level">How slow the query was.</param>
    /// <param name="theme">The theme.</param>
    /// <returns>The formatted line.</returns>
    public static StyledText SlowQuery(LogEntry entry, SlowQueryLevel level, Theme theme)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(theme);
        return Prefix(entry, theme).Append($"{PadLevel(entry.Level)}: {entry.Message}", theme.Style(SlowElement(level)));
    }

    private static string SlowElement(SlowQueryLevel level) => level switch
    {
        SlowQueryLevel.Critical => "slow_critical",
        SlowQueryLevel.Slow => "slow_slow",
        _ => "slow_warning",
    };

    /// <summary>
    /// An entry whose message has highlighted ranges, from <c>highlight /pattern/</c>.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="spans">The character ranges in the message to highlight.</param>
    /// <param name="theme">The theme.</param>
    /// <returns>The formatted line.</returns>
    public static StyledText WithHighlights(LogEntry entry, IReadOnlyList<(int Start, int End)> spans, Theme theme)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(spans);
        ArgumentNullException.ThrowIfNull(theme);
        TextStyle levelStyle = LevelStyle(entry.Level, theme);
        TextStyle highlight = theme.Style("highlight");
        StyledText text = Prefix(entry, theme).Append($"{PadLevel(entry.Level)}: ", levelStyle);
        string message = entry.Message;
        int position = 0;
        foreach ((int start, int spanEnd) in spans.OrderBy(span => span.Start))
        {
            if (start < position || start >= message.Length)
            {
                continue;
            }

            int end = Math.Min(spanEnd, message.Length);
            if (start > position)
            {
                text.Append(message[position..start], levelStyle);
            }

            text.Append(message[start..end], highlight);
            position = end;
        }

        if (position < message.Length)
        {
            text.Append(message[position..], levelStyle);
        }

        return text;
    }

    /// <summary>
    /// The tail mode line: <c>[file] time [pid  ] LEVEL   SQLSTATE: message</c>.
    /// </summary>
    /// <remarks>
    /// The file appears only when several files are tailed. Levels use fixed colors so they read the same in every
    /// theme; the message uses the theme's semantic highlighting, or the theme's slow query color when the entry is a
    /// slow query.
    /// </remarks>
    /// <param name="entry">The entry.</param>
    /// <param name="theme">The theme.</param>
    /// <param name="chain">The semantic highlighters for the message.</param>
    /// <param name="slow">How slow the query was, when the entry is a slow query.</param>
    /// <returns>The formatted line.</returns>
    public static StyledText TailLine(LogEntry entry, Theme theme, HighlighterChain chain, SlowQueryLevel? slow)
    {
        ArgumentNullException.ThrowIfNull(entry);
        ArgumentNullException.ThrowIfNull(theme);
        ArgumentNullException.ThrowIfNull(chain);
        var text = new StyledText();
        if (entry.SourceFile is { } file)
        {
            text.Append($"[{file}]", TailStyles.SourceFile).Append(" ");
        }

        if (entry.WrittenTime is { } timestamp)
        {
            text.Append(FormatTime(timestamp), TailStyles.Dim).Append(" ");
        }

        if (entry.Pid is { } pid)
        {
            text.Append($"[{pid.ToString(CultureInfo.InvariantCulture).PadRight(5)}]", TailStyles.Dim).Append(" ");
        }

        text.Append(PadLevel(entry.Level), TailStyles.Level(entry.Level));
        if (entry.SqlState is { } state)
        {
            text.Append(" ").Append(state, TailStyles.SqlState);
        }

        text.Append(": ");
        return slow is { } level
            ? text.Append(entry.Message, theme.Style(SlowElement(level)))
            : text.Append(chain.Apply(entry.Message, theme));
    }

    /// <summary>
    /// The entry as one line of compact JSON with every field it has.
    /// </summary>
    /// <remarks>
    /// Times are ISO 8601, the level is its name, and the format is <c>text</c>, <c>csv</c>, or <c>json</c>.
    /// Characters outside ASCII are written as they are.
    /// </remarks>
    /// <param name="entry">The entry.</param>
    /// <returns>The JSON text.</returns>
    public static string Json(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, s_jsonOptions))
        {
            writer.WriteStartObject();
            foreach (string field in entry.AvailableFields())
            {
                object value = entry.GetField(field)!;
                switch (value)
                {
                    case DateTime when field == "timestamp":
                        writer.WriteString(field, LogTimestamps.ToIsoFormat(entry));
                        break;
                    case DateTime time:
                        writer.WriteString(field, LogTimestamps.ToIsoFormat(time));
                        break;
                    case LogLevel level:
                        writer.WriteString(field, level.ToName());
                        break;
                    case LogFormat format:
                        writer.WriteString(field, format.ToName());
                        break;
                    case int number:
                        writer.WriteNumber(field, number);
                        break;
                    case long number:
                        writer.WriteNumber(field, number);
                        break;
                    default:
                        writer.WriteString(field, (string)value);
                        break;
                }
            }

            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.GetBuffer(), 0, (int)stream.Length);
    }

    /// <summary>
    /// The style of a level in a theme.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <param name="theme">The theme.</param>
    /// <returns>The style.</returns>
    public static TextStyle LevelStyle(LogLevel level, Theme theme)
    {
        ArgumentNullException.ThrowIfNull(theme);
        return theme.GetLevelStyle(level.ToName()).ToTextStyle();
    }

    private static StyledText Prefix(LogEntry entry, Theme theme)
    {
        var text = new StyledText();
        if (entry.WrittenTime is { } timestamp)
        {
            text.Append(FormatTime(timestamp) + " ", theme.Style("timestamp"));
        }

        if (entry.Pid is { } pid)
        {
            text.Append($"[{pid.ToString(CultureInfo.InvariantCulture)}] ", theme.Style("pid"));
        }

        return text;
    }

    private static string FieldText(object value) => value switch
    {
        DateTime time => LogTimestamps.ToIsoFormat(time),
        IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? "",
    };
}
