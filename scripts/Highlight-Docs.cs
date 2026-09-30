#!/usr/bin/env -S dotnet --
#:property TargetFramework=net10.0
#:project ../src/Pgtail.Core/Pgtail.Core.csproj
#:property PublishAot=false

// Colors the documentation's pgtail blocks with pgtail's own formatter, highlighters, themes, and prompt labels, and
// writes the spans to docs/src/generated/pgtail-tokens.json for the site's code block plugin.
//
//   ```pgtail       A transcript or a list of commands: prompts in their colors, a trailing "# note" dimmed.
//   ```pgtail-log   Entries as tail mode draws them, made from the PostgreSQL log lines in the comment above the block:
//
//                       <!-- pgtail-log
//                       2024-01-15 10:30:45.123 UTC [12345] ERROR:  relation "users" does not exist
//                       -->
//
//                   "display=compact" or "display=full" after "pgtail-log" formats them as streaming output does,
//                   "slow=100" colors slow queries from 100 ms, and a line starting "@name " came from that file.
//
// The landing page's terminal is written to docs/src/generated/HeroPrompt.astro from docs/src/hero.pgtail, a transcript
// in which a line starting "log: " is a PostgreSQL log line to print as a stream does and one starting "markup: " is
// output in pgtail's own markup.
//
// --update rewrites a pgtail-log block whose text is not what pgtail prints; --verify fails instead of writing.

using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Pgtail.Display;
using Pgtail.Highlighting;
using Pgtail.Parsing;
using Pgtail.Statistics;
using Pgtail.Styling;

bool update = args.Contains("--update", StringComparer.Ordinal);
bool verify = args.Contains("--verify", StringComparer.Ordinal);
string root = FindRoot();
string docs = Path.Join(root, "docs", "src", "content", "docs");
string output = Path.Join(root, "docs", "src", "generated", "pgtail-tokens.json");
string heroSource = Path.Join(root, "docs", "src", "hero.pgtail");
string heroOutput = Path.Join(root, "docs", "src", "generated", "HeroPrompt.astro");
Theme[] themes = [BuiltInThemes.All["dark"], BuiltInThemes.All["light"]];
HighlighterChain chain = new HighlightingConfig().GetChain();
var blocks = new SortedDictionary<string, (string Where, List<List<Span>> Lines)>(StringComparer.Ordinal);
var problems = new List<string>();

foreach (string file in Directory.EnumerateFiles(docs, "*.md*", SearchOption.AllDirectories).Order(StringComparer.Ordinal))
{
    List<string> lines = [.. File.ReadAllLines(file)];
    string relative = Path.GetRelativePath(docs, file).Replace('\\', '/');
    bool changed = false;
    for (int i = 0; i < lines.Count; i++)
    {
        if (lines[i] is not ("```pgtail" or "```pgtail-log"))
        {
            continue;
        }

        int start = i + 1;
        int end = lines.IndexOf("```", start);
        if (end < 0)
        {
            problems.Add($"{relative}:{i + 1}: the block is not closed");
            break;
        }

        string where = $"{relative}:{start + 1}";
        List<string> body = Trimmed(lines[start..end]);
        if (lines[i] == "```pgtail")
        {
            blocks[Key(body)] = (where, [.. Transcript(body)]);
        }
        else if (Source(lines, i) is not { } source)
        {
            problems.Add($"{where}: a pgtail-log block needs a <!-- pgtail-log ... --> comment of log lines above it");
        }
        else
        {
            (List<string> text, List<List<Span>> spans) = Entries(source.Options, source.Lines);
            if (!text.SequenceEqual(body, StringComparer.Ordinal))
            {
                if (!update)
                {
                    problems.Add($"{where}: the block is not what pgtail prints for its log lines; run with --update");
                }
                else
                {
                    lines.RemoveRange(start, end - start);
                    lines.InsertRange(start, text);
                    end = start + text.Count;
                    changed = true;
                }
            }

            blocks[Key(text)] = (where, spans);
        }

        i = end;
    }

    if (changed)
    {
        File.WriteAllLines(file, lines);
    }
}

foreach (string problem in problems)
{
    Console.Error.WriteLine(problem);
}

if (problems.Count > 0 && (verify || update))
{
    return 1;
}

string json = Json();
string hero = Hero();
if (verify)
{
    foreach ((string path, string text) in new[] { (output, json), (heroOutput, hero) })
    {
        if (!File.Exists(path) || File.ReadAllText(path) != text)
        {
            Console.Error.WriteLine($"{Path.GetRelativePath(root, path)} is out of date; run scripts/Highlight-Docs.cs");
            return 1;
        }
    }

    Console.WriteLine($"{blocks.Count} blocks and the landing page's terminal are up to date.");
    return 0;
}

Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output, json);
File.WriteAllText(heroOutput, hero);
Console.WriteLine($"Wrote {blocks.Count} blocks to {Path.GetRelativePath(root, output)} and the landing page's terminal.");
return problems.Count == 0 ? 0 : 1;

// A transcript's lines: a prompt in its colors, and a note after the command dimmed. In a block without prompts every
// line is a command.
IEnumerable<List<Span>> Transcript(List<string> body)
{
    foreach (string line in body)
    {
        var spans = new List<Span>();
        StyledText? label = Label(line);
        if (label is not null)
        {
            spans.AddRange(Spans(label, label));
        }

        // A note follows a command; a line of output may have a "#" of its own, as a table's first column does.
        int command = label?.Length ?? 0;
        int note = line.IndexOf("  #", command, StringComparison.Ordinal);
        note = note >= 0 && line[command..note].Trim().Length > 0 ? note : -1;
        if (note >= 0 || (label is null && line.StartsWith('#')))
        {
            int from = note < 0 ? 0 : note + 2;
            spans.Add(new Span(from, line.Length - from, Dim(0), Dim(1), null, null, false, false, false));
        }

        yield return spans;
    }
}

// The landing page's terminal: the transcript's lines as spans that carry their color for each ground.
string Hero()
{
    var html = new StringBuilder();
    html.Append("---\n// Written by scripts/Highlight-Docs.cs from src/hero.pgtail; edit that and run the script.\n---\n");
    html.Append("<pre class=\"hero-prompt\">");
    var rows = new List<string>();
    List<string> lines = Trimmed([.. File.ReadAllLines(heroSource)]);
    for (int i = 0; i < lines.Count; i++)
    {
        string line = lines[i];
        if (line.StartsWith("log: ", StringComparison.Ordinal))
        {
            // Consecutive log lines are read together, so a statement stays with its error.
            List<string> log = [.. lines.Skip(i).TakeWhile(next => next.StartsWith("log: ", StringComparison.Ordinal))];
            (List<string> text, List<List<Span>> spans) = Entries("display=compact", [.. log.Select(next => next["log: ".Length..])]);
            rows.AddRange(text.Select((row, index) => Html(row, spans[index])));
            i += log.Count - 1;
        }
        else if (line.StartsWith("markup: ", StringComparison.Ordinal))
        {
            StyledText text = Markup.Parse(line["markup: ".Length..]);
            rows.Add(Html(text.PlainText, Spans(text, text)));
        }
        else
        {
            rows.Add(Html(line, Transcript([line]).Single()));
        }
    }

    return html.Append(string.Join('\n', rows)).Append("</pre>\n").ToString();
}

static string Html(string text, List<Span> spans)
{
    var html = new StringBuilder();
    int at = 0;
    foreach (Span span in spans)
    {
        string?[] declarations =
        [
            span.Dark is null ? null : "--d:" + span.Dark,
            span.Light is null ? null : "--l:" + span.Light,
            span.DarkBackground is null ? null : "--db:" + span.DarkBackground,
            span.LightBackground is null ? null : "--lb:" + span.LightBackground,
            span.Bold ? "font-weight:600" : null,
            span.Italic ? "font-style:italic" : null,
            span.Underline ? "text-decoration:underline" : null,
        ];
        html.Append(WebUtility.HtmlEncode(text[at..span.Start]))
            .Append("<span style=\"").AppendJoin(';', declarations.OfType<string>()).Append("\">")
            .Append(WebUtility.HtmlEncode(text.Substring(span.Start, span.Length)))
            .Append("</span>");
        at = span.Start + span.Length;
    }

    return html.Append(WebUtility.HtmlEncode(text[at..])).ToString();
}

StyledText? Label(string line)
{
    if (line.StartsWith(PromptLabels.Tail.TrimEnd(), StringComparison.Ordinal))
    {
        // Tail mode draws its label in the terminal's own color.
        return new StyledText(PromptLabels.Tail.TrimEnd());
    }

    StyledText[] labels = [PromptLabels.Repl, PromptLabels.Shell];
    foreach (StyledText label in labels.Where(label => line.StartsWith(label.PlainText.TrimEnd(), StringComparison.Ordinal)))
    {
        return label;
    }

    if (line.StartsWith("paused [", StringComparison.Ordinal) && line.IndexOf("]>", StringComparison.Ordinal) is > 0 and int close)
    {
        return PromptLabels.Paused(line["paused [".Length..close]);
    }

    return null;
}

// The entries pgtail makes of log lines, as text and as spans, one line of each per row drawn.
(List<string> Text, List<List<Span>> Spans) Entries(string options, List<string> source)
{
    string display = Option(options, "display") ?? "tail";
    SlowQueryConfig? slow = double.TryParse(Option(options, "slow"), out double warning)
        ? new SlowQueryConfig { Enabled = true, WarningMs = warning, SlowMs = warning * 2, CriticalMs = warning * 5 }
        : null;
    var grouper = new EntryGrouper();
    var entries = new List<LogEntry>();
    foreach (string raw in source)
    {
        string? file = raw.StartsWith('@') ? raw[1..raw.IndexOf(' ', StringComparison.Ordinal)] : null;
        string line = file is null ? raw : raw[(file.Length + 2)..];
        byte[] bytes = Encoding.UTF8.GetBytes(line);
        LogEntry entry = LogLineParser.Parse(bytes, LogFormatDetector.Detect(bytes));
        entry.SourceFile = file;
        if (grouper.Add(entry) is { } complete)
        {
            entries.Add(complete);
        }
    }

    if (grouper.Flush() is { } last)
    {
        entries.Add(last);
    }

    var text = new List<string>();
    var spans = new List<List<Span>>();
    foreach (LogEntry entry in entries)
    {
        StyledText[] drawn = [.. themes.Select(theme => Format(entry, display, slow, theme))];
        IReadOnlyList<StyledText> dark = drawn[0].SplitLines();
        IReadOnlyList<StyledText> light = drawn[1].SplitLines();
        for (int row = 0; row < dark.Count; row++)
        {
            text.Add(dark[row].PlainText.TrimEnd());
            spans.Add(Spans(dark[row], light[row]));
        }
    }

    return (text, spans);
}

StyledText Format(LogEntry entry, string display, SlowQueryConfig? slow, Theme theme)
{
    SlowQueryLevel? level = slow is not null && DurationExtractor.Extract(entry.Message) is { } duration ? slow.GetLevel(duration) : null;
    return display switch
    {
        "full" => EntryFormatter.Full(entry, theme, chain),
        "compact" => level is { } found ? EntryFormatter.SlowQuery(entry, found, theme) : EntryFormatter.Compact(entry, theme, chain),
        _ => EntryFormatter.TailLine(entry, theme, chain, level),
    };
}

// The runs of one style in a line drawn on the dark ground and on the light one; the text is the same on both.
List<Span> Spans(StyledText dark, StyledText light)
{
    TextStyle[] onDark = Styles(dark);
    TextStyle[] onLight = Styles(light);
    var spans = new List<Span>();
    int from = 0;
    for (int i = 1; i <= onDark.Length; i++)
    {
        if (i < onDark.Length && onDark[i] == onDark[from] && onLight[i] == onLight[from])
        {
            continue;
        }

        if (!onDark[from].IsPlain || !onLight[from].IsPlain)
        {
            TextStyle style = onDark[from];
            bool reverse = style.Attributes.HasFlag(TextAttributes.Reverse);
            (string? fg, string? bg) = (Color(style, 0, !reverse), Color(style, 0, reverse, background: true));
            (string? lightFg, string? lightBg) = (Color(onLight[from], 1, !reverse), Color(onLight[from], 1, reverse, background: true));
            spans.Add(new Span(from, i - from, fg, lightFg, bg, lightBg, style.Attributes.HasFlag(TextAttributes.Bold),
                style.Attributes.HasFlag(TextAttributes.Italic), style.Attributes.HasFlag(TextAttributes.Underline)));
        }

        from = i;
    }

    return spans;
}

static TextStyle[] Styles(StyledText text)
{
    var styles = new TextStyle[text.Length];
    int at = 0;
    foreach (StyledSpan span in text.Spans)
    {
        Array.Fill(styles, span.Style, at, span.Text.Length);
        at += span.Text.Length;
    }

    return styles;
}

// A style's color as the site shows it on a ground, or null for the ground's own. A reversed style shows its colors
// exchanged, and dim text without a color of its own takes the ground's grey.
string? Color(TextStyle style, int ground, bool foreground, bool background = false)
{
    TerminalColor? color = foreground ? style.Foreground : style.Background;
    if (color is { Kind: not TerminalColorKind.Default } set)
    {
        return Hex(set, ground);
    }

    bool reversed = style.Attributes.HasFlag(TextAttributes.Reverse);
    return background
        ? reversed ? Ground(ground, text: true) : null
        : reversed ? Ground(ground, text: false)
        : style.Attributes.HasFlag(TextAttributes.Dim) ? Dim(ground) : null;
}

static string Hex(TerminalColor color, int ground)
{
    // The sixteen terminal colors as a terminal of each ground shows them; the rest are the same in every terminal.
    string[][] ansi =
    [
        [
            "#3f4451", "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd", "#56b6c2", "#d7dae0",
            "#7f848e", "#f07882", "#a9d18b", "#f0d197", "#7dbfff", "#d78ff0", "#6fd0dc", "#ffffff",
        ],
        [
            "#383a42", "#e45649", "#50a14f", "#c18401", "#4078f2", "#a626a4", "#0184bc", "#a0a1a7",
            "#696c77", "#ca1243", "#2f7d32", "#986801", "#2257d6", "#8a1f9e", "#026e9c", "#fafafa",
        ],
    ];
    switch (color.Kind)
    {
        case TerminalColorKind.Standard:
            return ansi[ground][color.Index];
        case TerminalColorKind.Bright:
            return ansi[ground][color.Index + 8];
        case TerminalColorKind.Indexed when color.Index < 16:
            return ansi[ground][color.Index];
        case TerminalColorKind.Indexed when color.Index >= 232:
            int grey = 8 + ((color.Index - 232) * 10);
            return $"#{grey:x2}{grey:x2}{grey:x2}";
        case TerminalColorKind.Indexed:
            int[] steps = [0, 95, 135, 175, 215, 255];
            int cube = color.Index - 16;
            return $"#{steps[cube / 36]:x2}{steps[cube / 6 % 6]:x2}{steps[cube % 6]:x2}";
        default:
            return $"#{color.R:x2}{color.G:x2}{color.B:x2}";
    }
}

static string Dim(int ground) => ground == 0 ? "#7f848e" : "#696c77";

static string Ground(int ground, bool text) => (ground == 0) == text ? "#d7dae0" : "#383a42";

// The log lines and options of the comment that ends just above a block.
static (string Options, List<string> Lines)? Source(List<string> lines, int fence)
{
    int close = fence - 1;
    while (close >= 0 && lines[close].Trim().Length == 0)
    {
        close--;
    }

    if (close < 0 || lines[close].Trim() != "-->")
    {
        return null;
    }

    int open = lines.FindLastIndex(close, line => line.StartsWith("<!-- pgtail-log", StringComparison.Ordinal));
    return open < 0 ? null : (lines[open]["<!-- pgtail-log".Length..].Trim(), lines[(open + 1)..close]);
}

static string? Option(string options, string name) =>
    options.Split(' ', StringSplitOptions.RemoveEmptyEntries)
        .Where(option => option.StartsWith(name + "=", StringComparison.Ordinal))
        .Select(option => option[(name.Length + 1)..])
        .FirstOrDefault();

static List<string> Trimmed(List<string> body)
{
    while (body.Count > 0 && body[^1].Trim().Length == 0)
    {
        body.RemoveAt(body.Count - 1);
    }

    return body;
}

// A block's text as the site's plugin keys it: its lines without trailing blank ones, joined by newlines.
static string Key(List<string> body) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(string.Join('\n', body))));

string Json()
{
    using var stream = new MemoryStream();
    using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
    {
        writer.WriteStartObject();
        writer.WriteStartObject("blocks");
        foreach ((string key, (string where, List<List<Span>> lines)) in blocks)
        {
            writer.WriteStartObject(key);
            writer.WriteString("where", where);
            writer.WriteStartArray("lines");
            foreach (List<Span> line in lines)
            {
                writer.WriteStartArray();
                foreach (Span span in line)
                {
                    writer.WriteStartObject();
                    writer.WriteNumber("start", span.Start);
                    writer.WriteNumber("length", span.Length);
                    Write(writer, "dark", span.Dark);
                    Write(writer, "light", span.Light);
                    Write(writer, "darkBackground", span.DarkBackground);
                    Write(writer, "lightBackground", span.LightBackground);
                    Flag(writer, "bold", span.Bold);
                    Flag(writer, "italic", span.Italic);
                    Flag(writer, "underline", span.Underline);
                    writer.WriteEndObject();
                }

                writer.WriteEndArray();
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        writer.WriteEndObject();
        writer.WriteEndObject();
    }

    return Encoding.UTF8.GetString(stream.ToArray()) + "\n";
}

static void Write(Utf8JsonWriter writer, string name, string? value)
{
    if (value is not null)
    {
        writer.WriteString(name, value);
    }
}

static void Flag(Utf8JsonWriter writer, string name, bool value)
{
    if (value)
    {
        writer.WriteBoolean(name, true);
    }
}

static string FindRoot()
{
    for (DirectoryInfo? directory = new(Directory.GetCurrentDirectory()); directory is not null; directory = directory.Parent)
    {
        if (File.Exists(Path.Join(directory.FullName, "Pgtail.slnx")))
        {
            return directory.FullName;
        }
    }

    throw new InvalidOperationException("Run this from inside the pgtail repository.");
}

/// <summary>
/// A run of one style in a line of a block.
/// </summary>
/// <param name="Start">The first character.</param>
/// <param name="Length">The number of characters.</param>
/// <param name="Dark">The text color on the dark ground, or null for the ground's own.</param>
/// <param name="Light">The text color on the light ground, or null for the ground's own.</param>
/// <param name="DarkBackground">The background on the dark ground, or null for none.</param>
/// <param name="LightBackground">The background on the light ground, or null for none.</param>
/// <param name="Bold">Whether the text is bold.</param>
/// <param name="Italic">Whether the text is italic.</param>
/// <param name="Underline">Whether the text is underlined.</param>
internal sealed record Span(
    int Start,
    int Length,
    string? Dark,
    string? Light,
    string? DarkBackground,
    string? LightBackground,
    bool Bold,
    bool Italic,
    bool Underline);
