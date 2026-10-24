using System.Text;

namespace Pgtail.Detection;

/// <summary>
/// Reads PostgreSQL configuration files, with the files they include, as the server reads them.
/// </summary>
/// <remarks>
/// A line holds a name, an optional <c>=</c>, and a value: a word, a number, or a string in single quotes, where
/// <c>''</c> is a quote and a backslash starts an escape. <c>#</c> starts a comment. <c>include</c>,
/// <c>include_if_exists</c>, and <c>include_dir</c> read other files at the place of the line, and a directory gives its
/// <c>.conf</c> files in name order. A relative path starts from the directory of the file that names it. A line the
/// server would refuse is skipped, as is a file that cannot be read.
/// </remarks>
public static class ConfigFileParser
{
    // CONF_FILE_MAX_DEPTH in guc.h, which also stops a file that includes itself through others.
    private const int MaxDepth = 10;

    /// <summary>
    /// Reads a configuration file and every file it includes.
    /// </summary>
    /// <param name="path">The file.</param>
    /// <returns>Every setting in the order the server reads them, so a later one replaces an earlier one.</returns>
    public static List<ConfigSetting> Read(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var settings = new List<ConfigSetting>();
        Read(Path.GetFullPath(path), 0, settings);
        return settings;
    }

    /// <summary>
    /// Reads the name and the value from one line of a configuration file.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <returns>The name and the value, or null for a blank line, a comment, or a line the server would refuse.</returns>
    public static (string Name, string Value)? ParseLine(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        int i = SkipSpace(line, 0);
        if (i == line.Length || line[i] == '#' || !IsLetter(line[i]))
        {
            return null;
        }

        int start = i;
        i = SkipWord(line, i);
        if (i + 1 < line.Length && line[i] == '.' && IsLetter(line[i + 1]))
        {
            i = SkipWord(line, i + 1);
        }

        string name = line[start..i];
        i = SkipSpace(line, i);
        if (i < line.Length && line[i] == '=')
        {
            i = SkipSpace(line, i + 1);
        }

        string? value;
        if (i < line.Length && line[i] == '\'')
        {
            value = Quoted(line, ref i);
        }
        else
        {
            start = i;
            while (i < line.Length && !char.IsWhiteSpace(line[i]) && line[i] is not ('#' or '\'' or '=' or '"'))
            {
                i++;
            }

            value = i > start ? line[start..i] : null;
        }

        i = SkipSpace(line, i);
        return value is not null && (i == line.Length || line[i] == '#') ? (name, value) : null;
    }

    private static void Read(string path, int depth, List<ConfigSetting> settings)
    {
        if (depth > MaxDepth)
        {
            return;
        }

        string content;
        try
        {
            content = File.ReadAllText(path);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return;
        }

        string[] lines = content.Split('\n');
        for (int number = 1; number <= lines.Length; number++)
        {
            if (ParseLine(lines[number - 1]) is not (string name, string value))
            {
                continue;
            }

            if (name.Equals("include", StringComparison.OrdinalIgnoreCase)
                || name.Equals("include_if_exists", StringComparison.OrdinalIgnoreCase))
            {
                string included = PostgresPath.Include(value, path);
                if (included != path)
                {
                    Read(included, depth + 1, settings);
                }
            }
            else if (name.Equals("include_dir", StringComparison.OrdinalIgnoreCase))
            {
                foreach (string file in ConfFiles(PostgresPath.Include(value, path)))
                {
                    Read(file, depth + 1, settings);
                }
            }
            else
            {
                settings.Add(new ConfigSetting(name, value, path, number));
            }
        }
    }

    // The files an include_dir line reads: names that end in .conf and do not start with a dot, sorted by name.
    private static List<string> ConfFiles(string directory)
    {
        try
        {
            return [.. Directory.EnumerateFiles(directory)
                .Where(file => Path.GetFileName(file) is { Length: >= 6 } name && name[0] != '.'
                    && name.EndsWith(".conf", StringComparison.Ordinal))
                .Order(StringComparer.Ordinal)];
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return [];
        }
    }

    // A string in single quotes from the quote at i, with '' and backslash escapes undone, as DeescapeQuotedString does,
    // or null when the line ends before the closing quote.
    private static string? Quoted(string line, ref int i)
    {
        var value = new StringBuilder();
        i++;
        while (i < line.Length)
        {
            char c = line[i];
            if (c == '\'')
            {
                if (i + 1 < line.Length && line[i + 1] == '\'')
                {
                    value.Append('\'');
                    i += 2;
                    continue;
                }

                i++;
                return value.ToString();
            }

            if (c == '\\')
            {
                if (i + 1 == line.Length)
                {
                    return null;
                }

                i = Escape(line, i + 1, value);
                continue;
            }

            value.Append(c);
            i++;
        }

        return null;
    }

    // The character after a backslash at i: a letter for a control character, up to three octal digits, or itself.
    private static int Escape(string line, int i, StringBuilder value)
    {
        char c = line[i];
        if (c is >= '0' and <= '7')
        {
            int code = 0;
            int end = i;
            while (end < line.Length && end - i < 3 && line[end] is >= '0' and <= '7')
            {
                code = (code << 3) + (line[end] - '0');
                end++;
            }

            value.Append((char)(code & 0xFF));
            return end;
        }

        char escaped = c switch
        {
            'b' => '\b',
            'f' => '\f',
            'n' => '\n',
            'r' => '\r',
            't' => '\t',
            _ => c,
        };

        value.Append(escaped);
        return i + 1;
    }

    private static int SkipSpace(string line, int i)
    {
        while (i < line.Length && line[i] is ' ' or '\t' or '\r')
        {
            i++;
        }

        return i;
    }

    private static int SkipWord(string line, int i)
    {
        while (i < line.Length && (IsLetter(line[i]) || char.IsAsciiDigit(line[i])))
        {
            i++;
        }

        return i;
    }

    // A letter in a setting's name: an ASCII letter, an underscore, or any character beyond ASCII.
    private static bool IsLetter(char c) => char.IsAsciiLetter(c) || c == '_' || c >= '\u0080';
}
