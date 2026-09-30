using Pgtail.Configuration;
using Pgtail.Detection;
using Pgtail.Sessions;

namespace Pgtail.Tests;

/// <summary>
/// A private home, configuration, and data directory for one test, removed when the test ends.
/// </summary>
internal sealed class TestEnvironment : IDisposable
{
    private readonly Dictionary<string, string?> _variables;

    /// <summary>
    /// Creates the directories and an environment that points at them.
    /// </summary>
    /// <param name="variables">More environment variables, such as <c>PGDATA</c>.</param>
    public TestEnvironment(IReadOnlyDictionary<string, string?>? variables = null)
    {
        // pgtail shows paths with links followed, as on macOS, where the temp directory is under /var, a link to /private/var.
        Root = PathResolver.Resolve(Path.Combine(Path.GetTempPath(), "pgtail-tests", Guid.NewGuid().ToString("N")));
        Home = Path.Combine(Root, "home");
        Directory.CreateDirectory(Home);
        _variables = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["HOME"] = Home,
            ["XDG_CONFIG_HOME"] = Path.Combine(Home, ".config"),
            ["XDG_DATA_HOME"] = Path.Combine(Home, ".local", "share"),
            ["APPDATA"] = Path.Combine(Home, "AppData", "Roaming"),
            ["LOCALAPPDATA"] = Path.Combine(Home, "AppData", "Local"),
            ["PATH"] = Environment.GetEnvironmentVariable("PATH"),
        };

        if (variables is not null)
        {
            foreach ((string name, string? value) in variables)
            {
                _variables[name] = value;
            }
        }

        Paths = PgtailPaths.ForCurrentUser(Get);
    }

    /// <summary>
    /// The directory everything for the test lives under.
    /// </summary>
    public string Root { get; }

    /// <summary>
    /// The test's home directory.
    /// </summary>
    public string Home { get; }

    /// <summary>
    /// Where pgtail keeps configuration and data for the test.
    /// </summary>
    public PgtailPaths Paths { get; }

    /// <summary>
    /// Reads a variable of the test's environment.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>The value, or null.</returns>
    public string? Get(string name) => _variables.GetValueOrDefault(name);

    /// <summary>
    /// Sets a variable of the test's environment.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <param name="value">The value.</param>
    public void Set(string name, string? value) => _variables[name] = value;

    /// <summary>
    /// A session that uses the test's directories and environment and the machine's real processes.
    /// </summary>
    /// <returns>The session.</returns>
    public PgtailSession CreateSession() => new(Get, Home, Paths, ProcessTable.List);

    /// <summary>
    /// The environment variables for a child process.
    /// </summary>
    /// <returns>The variables that have values.</returns>
    public Dictionary<string, string> ProcessVariables() =>
        _variables.Where(pair => pair.Value is not null).ToDictionary(pair => pair.Key, pair => pair.Value!, StringComparer.Ordinal);

    /// <inheritdoc/>
    public void Dispose()
    {
        try
        {
            Directory.Delete(Root, recursive: true);
        }
        catch (IOException)
        {
            // A process may still hold a file briefly; the temp directory is cleaned eventually.
        }
    }
}
