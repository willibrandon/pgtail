using System.Text;

namespace Pgtail.Toml;

/// <summary>
/// A TOML document that can be read and edited without disturbing its comments and layout.
/// </summary>
/// <remarks>
/// Every edit changes only the text it has to: a value in place, a line added to the end of its table, or the lines of
/// a removed key or table. The edited text is parsed again, so the document always holds valid TOML.
/// </remarks>
public sealed class TomlDocument
{
    private static readonly UTF8Encoding s_strictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);
    private string _text;
    private IReadOnlyList<TomlStatement> _statements;

    private TomlDocument(string text)
    {
        _text = text;
        (Root, _statements) = TomlParser.Parse(text);
    }

    /// <summary>
    /// The parsed contents.
    /// </summary>
    public TomlTable Root { get; private set; }

    /// <summary>
    /// The top-level statements in document order.
    /// </summary>
    public IReadOnlyList<TomlStatement> Statements => _statements;

    /// <summary>
    /// Parses a document.
    /// </summary>
    /// <param name="text">The TOML text.</param>
    /// <returns>The document.</returns>
    /// <exception cref="TomlException">The text is not valid TOML.</exception>
    public static TomlDocument Parse(string text) => new(text);

    /// <summary>
    /// Parses a document from UTF-8 bytes, as TOML files are stored.
    /// </summary>
    /// <param name="utf8">The file contents, with or without a byte order mark.</param>
    /// <returns>The document.</returns>
    /// <exception cref="TomlException">The bytes are not UTF-8 or the text is not valid TOML.</exception>
    public static TomlDocument Parse(ReadOnlySpan<byte> utf8)
    {
        try
        {
            return new TomlDocument(s_strictUtf8.GetString(utf8));
        }
        catch (DecoderFallbackException)
        {
            throw new TomlException("The document is not valid UTF-8", 1, 1);
        }
    }

    /// <summary>
    /// Reads and parses a TOML file.
    /// </summary>
    /// <param name="path">The file.</param>
    /// <returns>The document.</returns>
    /// <exception cref="TomlException">The file is not valid TOML.</exception>
    /// <exception cref="IOException">The file cannot be read.</exception>
    public static TomlDocument Load(string path) => Parse(File.ReadAllBytes(path));

    /// <summary>
    /// Sets a value, replacing it where it is written or adding it to the end of its table.
    /// </summary>
    /// <remarks>
    /// A table that does not exist yet gets a header of its own at the end of the document.
    /// </remarks>
    /// <param name="path">The table path followed by the key.</param>
    /// <param name="value">The value, in any form <see cref="TomlFormatter.Format"/> accepts.</param>
    /// <exception cref="InvalidOperationException">The key is written inside an inline table, an array, or an array of
    /// tables, where it cannot be edited on its own.</exception>
    public void Set(IReadOnlyList<string> path, object value)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentOutOfRangeException.ThrowIfZero(path.Count);
        string formatted = TomlFormatter.Format(value);
        if (_statements.FirstOrDefault(s => s.Kind == TomlStatementKind.KeyValue && Same(s.Path, path)) is { } existing)
        {
            Replace(existing.ValueStart, existing.ValueEnd, formatted);
            return;
        }

        if (Root.GetPath(path) is not null)
        {
            throw new InvalidOperationException($"'{string.Join('.', path)}' cannot be edited on its own.");
        }

        var tablePath = path.Take(path.Count - 1).ToList();
        string key = path[^1];
        string line = $"{TomlFormatter.FormatKey(key)} = {formatted}";
        if (tablePath.Count == 0)
        {
            InsertInSection(-1, line);
            return;
        }

        (TomlStatement statement, int index) header = _statements
            .Select((statement, index) => (statement, index))
            .FirstOrDefault(pair => pair.statement.Kind == TomlStatementKind.Table && Same(pair.statement.Path, tablePath));
        if (header.statement is not null)
        {
            InsertInSection(header.index, line);
            return;
        }

        switch (Root.GetPath(tablePath))
        {
            case null or TomlTable { Kind: TomlTableKind.Implicit }:
                AppendSection(tablePath, line);
                break;
            case TomlTable { Kind: TomlTableKind.Dotted }:
                TomlStatement last = _statements.Last(s => s.Kind == TomlStatementKind.KeyValue && StartsWith(s.Path, tablePath));
                IEnumerable<string> relative = path.Skip(last.TablePath.Count);
                Insert(last.End, $"{TomlFormatter.FormatPath(relative)} = {formatted}\n");
                break;
            default:
                throw new InvalidOperationException($"'{string.Join('.', tablePath)}' cannot take new keys on its own.");
        }
    }

    /// <summary>
    /// Removes a key written on its own line.
    /// </summary>
    /// <param name="path">The table path followed by the key.</param>
    /// <returns>True when the key was removed; false when it is not written on its own line.</returns>
    public bool Remove(IReadOnlyList<string> path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (_statements.FirstOrDefault(s => s.Kind == TomlStatementKind.KeyValue && Same(s.Path, path)) is not { } existing)
        {
            return false;
        }

        Replace(existing.Start, existing.End, "");
        return true;
    }

    /// <summary>
    /// Removes a table or array with everything written in it: its sections, its sub-tables, and its keys.
    /// </summary>
    /// <param name="path">The path of the table or array.</param>
    /// <returns>True when anything was removed.</returns>
    public bool RemoveTable(IReadOnlyList<string> path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var spans = new List<(int Start, int End)>();
        for (int i = 0; i < _statements.Count; i++)
        {
            TomlStatement statement = _statements[i];
            if (!StartsWith(statement.Path, path))
            {
                continue;
            }

            if (statement.Kind == TomlStatementKind.KeyValue)
            {
                if (!StartsWith(statement.TablePath, path))
                {
                    spans.Add((statement.Start, statement.End));
                }

                continue;
            }

            spans.Add((statement.Start, SectionEnd(i)));
        }

        if (spans.Count == 0)
        {
            return false;
        }

        string text = _text;
        foreach ((int start, int end) in spans.OrderByDescending(span => span.Start))
        {
            text = text.Remove(start, end - start);
        }

        Update(text);
        return true;
    }

    /// <summary>
    /// The document text.
    /// </summary>
    /// <returns>The TOML text.</returns>
    public override string ToString() => _text;

    private int SectionEnd(int headerIndex)
    {
        for (int i = headerIndex + 1; i < _statements.Count; i++)
        {
            if (_statements[i].Kind != TomlStatementKind.KeyValue)
            {
                return _statements[i].Start;
            }
        }

        return _text.Length;
    }

    private void InsertInSection(int headerIndex, string line)
    {
        int start = headerIndex < 0 ? 0 : _statements[headerIndex].End;
        int end = headerIndex < 0
            ? _statements.FirstOrDefault(s => s.Kind != TomlStatementKind.KeyValue)?.Start ?? _text.Length
            : SectionEnd(headerIndex);
        TomlStatement? last = _statements.LastOrDefault(s => s.Kind == TomlStatementKind.KeyValue && s.Start >= start && s.End <= end);
        int position = last?.End ?? start;
        if (last is null)
        {
            // Without keys, the new line joins the comments written directly under the header, which usually document it.
            while (position < end)
            {
                int newline = _text.IndexOf('\n', position, end - position);
                int lineEnd = newline < 0 ? end : newline + 1;
                if (string.IsNullOrWhiteSpace(_text[position..lineEnd]))
                {
                    break;
                }

                position = lineEnd;
            }
        }

        string prefix = position > 0 && _text[position - 1] != '\n' ? "\n" : "";
        Insert(position, prefix + line + "\n");
    }

    private void AppendSection(IReadOnlyList<string> tablePath, string line)
    {
        string separator = _text.Length == 0 || _text.EndsWith("\n\n", StringComparison.Ordinal) ? ""
            : _text.EndsWith('\n') ? "\n" : "\n\n";
        Insert(_text.Length, $"{separator}[{TomlFormatter.FormatPath(tablePath)}]\n{line}\n");
    }

    private void Insert(int position, string text) => Replace(position, position, text);

    private void Replace(int start, int end, string text) => Update(string.Concat(_text.AsSpan(0, start), text, _text.AsSpan(end)));

    private void Update(string text)
    {
        (Root, _statements) = TomlParser.Parse(text);
        _text = text;
    }

    private static bool Same(IReadOnlyList<string> left, IReadOnlyList<string> right) => left.SequenceEqual(right, StringComparer.Ordinal);

    private static bool StartsWith(IReadOnlyList<string> path, IReadOnlyList<string> prefix) =>
        path.Count >= prefix.Count && path.Take(prefix.Count).SequenceEqual(prefix, StringComparer.Ordinal);
}
