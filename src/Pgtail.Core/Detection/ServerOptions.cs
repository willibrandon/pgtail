namespace Pgtail.Detection;

/// <summary>
/// Reads the settings on the command line a server last started with, which it keeps in <c>postmaster.opts</c>.
/// </summary>
/// <remarks>
/// The file holds the program, then each argument in double quotes. <c>pg_ctl restart</c> starts the server with the same
/// arguments again. Settings come from <c>-c name=value</c>, <c>--name=value</c>, and the short options that set one
/// setting, such as <c>-p</c> for the port.
/// </remarks>
public static class ServerOptions
{
    // The short options of postgres that take an argument, from the option string in postmaster.c.
    private const string WithArgument = "BCcDdfhkNprStW";

    // The short options that set one setting: to the argument when the value is null, or else to the value.
    private static readonly Dictionary<char, (string Name, string? Value)> s_settings = new()
    {
        ['B'] = ("shared_buffers", null),
        ['E'] = ("log_statement", "all"),
        ['e'] = ("datestyle", "euro"),
        ['F'] = ("fsync", "false"),
        ['h'] = ("listen_addresses", null),
        ['i'] = ("listen_addresses", "*"),
        ['k'] = ("unix_socket_directories", null),
        ['l'] = ("ssl", "true"),
        ['N'] = ("max_connections", null),
        ['O'] = ("allow_system_table_mods", "true"),
        ['P'] = ("ignore_system_indexes", "true"),
        ['p'] = ("port", null),
        ['S'] = ("work_mem", null),
        ['s'] = ("log_statement_stats", "true"),
        ['T'] = ("send_abort_for_crash", "true"),
    };

    /// <summary>
    /// Reads the settings from a data directory's <c>postmaster.opts</c>.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The settings in order, or none when the file is missing or cannot be read.</returns>
    public static IReadOnlyList<ConfigSetting> Read(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        try
        {
            return Settings(Arguments(File.ReadAllText(Path.Join(dataDirectory, "postmaster.opts"))));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return [];
        }
    }

    /// <summary>
    /// Splits the text of <c>postmaster.opts</c> into the arguments after the program.
    /// </summary>
    /// <remarks>
    /// The program is not quoted and can hold spaces, so the arguments start at the first space and double quote.
    /// </remarks>
    /// <param name="content">The file's text.</param>
    /// <returns>The arguments, without their quotes.</returns>
    public static IReadOnlyList<string> Arguments(string content)
    {
        ArgumentNullException.ThrowIfNull(content);
        string line = content.Split('\n')[0].TrimEnd('\r');
        int start = line.IndexOf(" \"", StringComparison.Ordinal);
        if (start < 0 || !line.EndsWith('"'))
        {
            return [];
        }

        string quoted = line[(start + 2)..^1];
        return quoted.Split("\" \"");
    }

    /// <summary>
    /// The settings that server arguments make, in order.
    /// </summary>
    /// <param name="arguments">The arguments after the program.</param>
    /// <returns>The settings, each with no file and line 0.</returns>
    public static IReadOnlyList<ConfigSetting> Settings(IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        var settings = new List<ConfigSetting>();
        for (int i = 0; i < arguments.Count; i++)
        {
            string argument = arguments[i];
            if (argument.Length < 2 || argument[0] != '-')
            {
                continue;
            }

            // A cluster of flags such as -iF, then at most one option that takes the rest, or the next argument.
            for (int j = 1; j < argument.Length; j++)
            {
                char option = argument[j];
                if (option != '-' && !WithArgument.Contains(option, StringComparison.Ordinal))
                {
                    Add(settings, option, null);
                    continue;
                }

                string? value = j + 1 < argument.Length ? argument[(j + 1)..] : i + 1 < arguments.Count ? arguments[++i] : null;
                if (value is null)
                {
                    break;
                }

                if (option is 'c' or '-')
                {
                    AddLong(settings, value);
                }
                else
                {
                    Add(settings, option, value);
                }

                break;
            }
        }

        return settings;
    }

    // -c name=value and --name=value, where a dash in the name stands for an underscore, as ParseLongOption reads them.
    private static void AddLong(List<ConfigSetting> settings, string option)
    {
        int equals = option.IndexOf('=', StringComparison.Ordinal);
        if (equals > 0)
        {
            settings.Add(new ConfigSetting(option[..equals].Replace('-', '_'), option[(equals + 1)..], null, 0));
        }
    }

    private static void Add(List<ConfigSetting> settings, char option, string? argument)
    {
        if (s_settings.TryGetValue(option, out (string Name, string? Value) setting) && (setting.Value ?? argument) is { } value)
        {
            settings.Add(new ConfigSetting(setting.Name, value, null, 0));
        }
    }
}
