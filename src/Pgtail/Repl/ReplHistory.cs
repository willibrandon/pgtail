using System.Globalization;
using System.Text;

namespace Pgtail.Repl;

/// <summary>
/// The REPL's command history, kept in a file between sessions.
/// </summary>
/// <remarks>
/// The file keeps each entry under a <c># time</c> comment with every line prefixed by <c>+</c>, the format the
/// Python release wrote, so history carries over. Empty lines and repeats of the previous entry are not recorded.
/// </remarks>
/// <param name="path">The history file, or null to keep history for this session only.</param>
internal sealed class ReplHistory(string? path)
{
    private readonly List<string> _entries = [];
    private int _index;
    private string _draft = "";

    /// <summary>
    /// The entries, oldest first.
    /// </summary>
    public IReadOnlyList<string> Entries => _entries;

    /// <summary>
    /// Reads the history file, if there is one.
    /// </summary>
    public void Load()
    {
        _entries.Clear();
        if (path is null || !File.Exists(path))
        {
            ResetNavigation();
            return;
        }

        var current = new List<string>();
        foreach (string line in File.ReadLines(path, Encoding.UTF8))
        {
            if (line.StartsWith('+'))
            {
                current.Add(line[1..]);
                continue;
            }

            if (current.Count > 0)
            {
                _entries.Add(string.Join('\n', current));
                current.Clear();
            }
        }

        if (current.Count > 0)
        {
            _entries.Add(string.Join('\n', current));
        }

        ResetNavigation();
    }

    /// <summary>
    /// Records a submitted line and returns to the newest position.
    /// </summary>
    /// <param name="line">The line.</param>
    public void Add(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        if (line.Length > 0 && (_entries.Count == 0 || _entries[^1] != line))
        {
            _entries.Add(line);
            Append(line);
        }

        ResetNavigation();
    }

    /// <summary>
    /// Moves to the previous entry, remembering the line being edited when leaving it.
    /// </summary>
    /// <param name="current">The text being edited.</param>
    /// <returns>The entry to show, or null at the oldest entry.</returns>
    public string? Previous(string current)
    {
        if (_index == 0)
        {
            return null;
        }

        if (_index == _entries.Count)
        {
            _draft = current;
        }

        _index--;
        return _entries[_index];
    }

    /// <summary>
    /// Moves to the next entry, or back to the line being edited after the newest.
    /// </summary>
    /// <returns>The text to show, or null when already at the line being edited.</returns>
    public string? Next()
    {
        if (_index >= _entries.Count)
        {
            return null;
        }

        _index++;
        return _index == _entries.Count ? _draft : _entries[_index];
    }

    /// <summary>
    /// Returns to the newest position without recording anything.
    /// </summary>
    public void ResetNavigation()
    {
        _index = _entries.Count;
        _draft = "";
    }

    private void Append(string line)
    {
        if (path is null)
        {
            return;
        }

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            var builder = new StringBuilder();
            builder.Append('\n').Append("# ")
                .Append(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.ffffff", CultureInfo.InvariantCulture)).Append('\n');
            foreach (string part in line.Split('\n'))
            {
                builder.Append('+').Append(part).Append('\n');
            }

            File.AppendAllText(path, builder.ToString(), new UTF8Encoding(false));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // History is a convenience; a read-only or full disk must not interrupt the session.
        }
    }
}
