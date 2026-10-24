namespace Pgtail.Detection;

/// <summary>
/// The settings a server reads when it starts, found in the order PostgreSQL reads them.
/// </summary>
/// <remarks>
/// The server reads <c>postgresql.conf</c> with the files it includes, then <c>postgresql.auto.conf</c> in the data
/// directory, which <c>ALTER SYSTEM</c> writes. Options on the server's command line, kept in <c>postmaster.opts</c>,
/// come after every file. Where a setting is set more than once, the last value is the one in effect. The command line
/// can name a <c>config_file</c> other than <c>postgresql.conf</c> in the data directory, as a Debian or Ubuntu cluster
/// does.
/// </remarks>
public sealed class ServerSettings
{
    /// <summary>
    /// The name of the file that <c>ALTER SYSTEM</c> writes, which the server reads after <c>postgresql.conf</c>.
    /// </summary>
    public const string AutoConfFileName = "postgresql.auto.conf";

    private readonly Dictionary<string, ConfigSetting> _settings = new(StringComparer.OrdinalIgnoreCase);

    private ServerSettings(string dataDirectory, string? configFile, IEnumerable<ConfigSetting> settings)
    {
        DataDirectory = dataDirectory;
        ConfigFile = configFile;
        foreach (ConfigSetting setting in settings)
        {
            _settings[setting.Name] = setting;
        }
    }

    /// <summary>
    /// The data directory.
    /// </summary>
    public string DataDirectory { get; }

    /// <summary>
    /// The main configuration file, or null when none was found.
    /// </summary>
    public string? ConfigFile { get; }

    /// <summary>
    /// The file <c>ALTER SYSTEM</c> writes in the data directory.
    /// </summary>
    public string AutoConfFile => Path.Join(DataDirectory, AutoConfFileName);

    /// <summary>
    /// A setting that is in effect, with the place it is set.
    /// </summary>
    /// <param name="name">The setting's name, matched ignoring case.</param>
    /// <returns>The setting, or null when nothing sets it and its default applies.</returns>
    public ConfigSetting? this[string name] => _settings.GetValueOrDefault(name);

    /// <summary>
    /// Reads the settings of a data directory.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The settings.</returns>
    public static ServerSettings Read(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        IReadOnlyList<ConfigSetting> commandLine = ServerOptions.Read(dataDirectory);
        ConfigSetting? named = commandLine.LastOrDefault(setting => setting.Name.Equals("config_file", StringComparison.OrdinalIgnoreCase));
        string? configFile = named is null ? PostgresConf.FindConfFile(dataDirectory) : PostgresPath.Resolve(named.Value, dataDirectory);
        var settings = new List<ConfigSetting>();
        if (configFile is not null)
        {
            settings.AddRange(ConfigFileParser.Read(configFile));
        }

        settings.AddRange(ConfigFileParser.Read(Path.Join(dataDirectory, AutoConfFileName)));
        settings.AddRange(commandLine);
        return new ServerSettings(dataDirectory, configFile, settings);
    }

    /// <summary>
    /// Whether a boolean setting is on.
    /// </summary>
    /// <param name="name">The setting's name.</param>
    /// <returns>True when the setting's value in effect is true; false when it is false or not set.</returns>
    public bool IsOn(string name) => this[name]?.IsOn ?? false;
}
