using System.Text;

namespace Pgtail.Tail;

/// <summary>
/// Tail mode's command history: the last 500 commands, one per line in a file.
/// </summary>
/// <remarks>
/// Repeats of the previous command are not recorded. Commands are appended as they run, and the file is rewritten
/// with only the newest entries once it grows past twice that many lines. Lines over 4 KB are skipped when loading.
/// </remarks>
/// <param name="path">The history file, or null to keep history for this session only.</param>
internal sealed class TailHistory(string? path)
{
    /// <summary>
    /// The most commands kept.
    /// </summary>
    public const int MaxEntries = 500;

    private const int MaxLineBytes = 4096;
    private readonly List<string> _entries = [];
    private int _cursor;
    private string? _saved;

    /// <summary>
    /// The commands, oldest first.
    /// </summary>
    public IReadOnlyList<string> Entries => _entries;

    /// <summary>
    /// Reads the history file and compacts it when it has grown too long.
    /// </summary>
    public void Load()
    {
        if (path is null || !File.Exists(path))
        {
            ResetNavigation();
            return;
        }

        try
        {
            string[] lines = File.ReadAllLines(path, Encoding.UTF8);
            _entries.Clear();
            _entries.AddRange(lines.Where(line => line.Length > 0 && Encoding.UTF8.GetByteCount(line) <= MaxLineBytes)
                .TakeLast(MaxEntries));
            if (lines.Length > MaxEntries * 2)
            {
                File.WriteAllLines(path, _entries, new UTF8Encoding(false));
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // History is a convenience; an unreadable file starts it empty.
        }

        ResetNavigation();
    }

    /// <summary>
    /// Records a command and saves it.
    /// </summary>
    /// <param name="command">The command.</param>
    public void Add(string command)
    {
        ArgumentNullException.ThrowIfNull(command);
        if (string.IsNullOrWhiteSpace(command) || (_entries.Count > 0 && _entries[^1] == command))
        {
            ResetNavigation();
            return;
        }

        _entries.Add(command);
        if (_entries.Count > MaxEntries)
        {
            _entries.RemoveRange(0, _entries.Count - MaxEntries);
        }

        ResetNavigation();
        if (path is null)
        {
            return;
        }

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.AppendAllText(path, command + "\n", new UTF8Encoding(false));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // History is a convenience; a read-only disk must not interrupt tailing.
        }
    }

    /// <summary>
    /// Moves to an older command, saving the line being edited the first time.
    /// </summary>
    /// <param name="current">The line being edited.</param>
    /// <returns>The command, or null when there is no history.</returns>
    public string? Back(string current)
    {
        if (_entries.Count == 0)
        {
            return null;
        }

        if (_cursor == _entries.Count && _saved is null)
        {
            _saved = current;
            _cursor = _entries.Count - 1;
        }
        else
        {
            _cursor = Math.Max(0, _cursor - 1);
        }

        return _entries[_cursor];
    }

    /// <summary>
    /// Moves to a newer command, or back to the saved line after the newest.
    /// </summary>
    /// <returns>The text to show, or null when not navigating.</returns>
    public string? Forward()
    {
        if (_cursor == _entries.Count && _saved is null)
        {
            return null;
        }

        _cursor++;
        if (_cursor < _entries.Count)
        {
            return _entries[_cursor];
        }

        string? saved = _saved;
        ResetNavigation();
        return saved ?? "";
    }

    /// <summary>
    /// Stops navigating without changing the line.
    /// </summary>
    public void ResetNavigation()
    {
        _cursor = _entries.Count;
        _saved = null;
    }

    /// <summary>
    /// The newest command that starts with a prefix and is longer than it.
    /// </summary>
    /// <param name="prefix">The prefix, matched with case.</param>
    /// <returns>The command, or null.</returns>
    public string? SearchPrefix(string prefix)
    {
        ArgumentNullException.ThrowIfNull(prefix);
        for (int i = _entries.Count - 1; i >= 0; i--)
        {
            if (_entries[i].StartsWith(prefix, StringComparison.Ordinal) && _entries[i] != prefix)
            {
                return _entries[i];
            }
        }

        return null;
    }
}
