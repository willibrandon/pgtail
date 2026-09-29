using System.Text;

namespace Pgtail.Detection;

/// <summary>
/// Turns on the logging collector in <c>postgresql.conf</c>, keeping the rest of the file as it is.
/// </summary>
public static class LoggingEnabler
{
    /// <summary>
    /// Reads the settings of a <c>postgresql.conf</c>, ignoring comments.
    /// </summary>
    /// <param name="path">The file.</param>
    /// <returns>Each setting's last value, with surrounding quotes removed.</returns>
    public static Dictionary<string, string> ReadSettings(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var settings = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var raw in File.ReadLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#') || !line.Contains('=', StringComparison.Ordinal))
            {
                continue;
            }

            if (line.Contains('#', StringComparison.Ordinal))
            {
                line = line[..line.IndexOf('#', StringComparison.Ordinal)].Trim();
            }

            var separator = line.IndexOf('=', StringComparison.Ordinal);
            if (separator < 0)
            {
                continue;
            }

            var value = line[(separator + 1)..].Trim();
            if (value.Length >= 2 && ((value[0] == '\'' && value[^1] == '\'') || (value[0] == '"' && value[^1] == '"')))
            {
                value = value[1..^1];
            }

            settings[line[..separator].Trim()] = value;
        }

        return settings;
    }

    /// <summary>
    /// Sets values in a <c>postgresql.conf</c>.
    /// </summary>
    /// <remarks>
    /// A setting already present is replaced where it is. A setting present only as a commented-out example gets a
    /// line right after the example. Anything else is appended under a pgtail comment.
    /// </remarks>
    /// <param name="path">The file.</param>
    /// <param name="settings">The settings to write, in order.</param>
    /// <returns>One line per change made.</returns>
    public static IReadOnlyList<string> WriteSettings(string path, IReadOnlyList<KeyValuePair<string, string>> settings)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(settings);
        var changes = new List<string>();
        var remaining = settings.ToList();
        var output = new StringBuilder();
        var content = File.ReadAllText(path);
        foreach (var line in SplitKeepingEndings(content))
        {
            var stripped = line.Trim();
            var indent = line[..(line.Length - line.TrimStart().Length)];
            if (stripped.Contains('=', StringComparison.Ordinal) && !stripped.StartsWith('#'))
            {
                var name = stripped[..stripped.IndexOf('=', StringComparison.Ordinal)].Trim();
                if (Take(remaining, name) is { } value)
                {
                    output.Append($"{indent}{name} = '{value}'\n");
                    changes.Add($"Updated {name} = '{value}'");
                    continue;
                }
            }

            if (stripped.StartsWith('#') && stripped.Contains('=', StringComparison.Ordinal))
            {
                var uncommented = stripped[1..].Trim();
                var name = uncommented[..uncommented.IndexOf('=', StringComparison.Ordinal)].Trim();
                if (Take(remaining, name) is { } value)
                {
                    output.Append(line);
                    if (!line.EndsWith('\n'))
                    {
                        output.Append('\n');
                    }

                    output.Append($"{indent}{name} = '{value}'\n");
                    changes.Add($"Enabled {name} = '{value}'");
                    continue;
                }
            }

            output.Append(line);
        }

        if (remaining.Count > 0)
        {
            output.Append("\n# Logging settings added by pgtail\n");
            foreach (var (name, value) in remaining)
            {
                output.Append($"{name} = '{value}'\n");
                changes.Add($"Added {name} = '{value}'");
            }
        }

        File.WriteAllText(path, output.ToString());
        return changes;
    }

    /// <summary>
    /// Enables logging for a data directory.
    /// </summary>
    /// <remarks>
    /// Sets <c>logging_collector = on</c>, and <c>log_directory = 'log'</c> and
    /// <c>log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'</c> when they are not set, then creates the log directory.
    /// </remarks>
    /// <param name="dataDirectory">The data directory.</param>
    /// <param name="configPath">The instance's <c>postgresql.conf</c>, or null to look for it.</param>
    /// <returns>The outcome.</returns>
    public static ConfigUpdate Enable(string dataDirectory, string? configPath = null)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        var conf = configPath ?? PostgresConf.FindConfFile(dataDirectory);
        if (conf is null || !File.Exists(conf))
        {
            var checkedPaths = new List<string> { Path.Combine(dataDirectory, "postgresql.conf") };
            if (PostgresConf.DebianConfFile(dataDirectory) is { } debian)
            {
                checkedPaths.Add(debian);
            }

            return new ConfigUpdate(false, $"postgresql.conf not found.\n\nChecked:\n  {string.Join("\n  ", checkedPaths)}", []);
        }

        Dictionary<string, string> current;
        try
        {
            current = ReadSettings(conf);
        }
        catch (UnauthorizedAccessException)
        {
            return new ConfigUpdate(false,
                $"Permission denied reading {conf}\n\n{string.Join('\n', PermissionAdvice.ConfPermission(conf))}", []);
        }

        var updates = new List<KeyValuePair<string, string>>();
        if (current.GetValueOrDefault("logging_collector") != "on")
        {
            updates.Add(new("logging_collector", "on"));
        }

        if (!current.ContainsKey("log_directory"))
        {
            updates.Add(new("log_directory", "log"));
        }

        if (!current.ContainsKey("log_filename"))
        {
            updates.Add(new("log_filename", "postgresql-%Y-%m-%d_%H%M%S.log"));
        }

        if (updates.Count == 0)
        {
            return new ConfigUpdate(true, "Logging is already enabled", []);
        }

        List<string> changes;
        try
        {
            changes = [.. WriteSettings(conf, updates)];
        }
        catch (UnauthorizedAccessException)
        {
            return new ConfigUpdate(false,
                $"Permission denied writing to {conf}\n\n{string.Join('\n', PermissionAdvice.ConfPermission(conf))}", []);
        }

        var logDirectory = Path.Combine(dataDirectory,
            updates.FirstOrDefault(update => update.Key == "log_directory").Value ?? current.GetValueOrDefault("log_directory", "log"));
        if (!Directory.Exists(logDirectory))
        {
            try
            {
                Directory.CreateDirectory(logDirectory);
                changes.Add($"Created directory {logDirectory}");
            }
            catch (UnauthorizedAccessException)
            {
                changes.Add($"Note: Could not create {logDirectory} - you may need to create it manually");
            }
        }

        return new ConfigUpdate(true, "Logging enabled successfully", changes);
    }

    private static string? Take(List<KeyValuePair<string, string>> remaining, string name)
    {
        var index = remaining.FindIndex(pair => pair.Key == name);
        if (index < 0)
        {
            return null;
        }

        var value = remaining[index].Value;
        remaining.RemoveAt(index);
        return value;
    }

    private static IEnumerable<string> SplitKeepingEndings(string content)
    {
        var start = 0;
        while (start < content.Length)
        {
            var newline = content.IndexOf('\n', start);
            var end = newline < 0 ? content.Length : newline + 1;
            yield return content[start..end];
            start = end;
        }
    }
}
