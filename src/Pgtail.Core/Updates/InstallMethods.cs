namespace Pgtail.Updates;

/// <summary>
/// Detects how pgtail was installed from where its executable lives.
/// </summary>
public static class InstallMethods
{
    /// <summary>
    /// The GitHub releases page.
    /// </summary>
    public const string ReleasesPage = "https://github.com/willibrandon/pgtail/releases";

    /// <summary>
    /// Classifies an executable path.
    /// </summary>
    /// <param name="executable">The executable's full path.</param>
    /// <param name="environment">Reads environment variables, for <c>LOCALAPPDATA</c>.</param>
    /// <returns>The install method; a path that matches no package manager is a downloaded binary.</returns>
    public static InstallMethod Detect(string executable, Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(executable);
        ArgumentNullException.ThrowIfNull(environment);
        var normalized = executable.Replace('\\', '/').ToLowerInvariant();
        if (normalized.Contains("/.dotnet/tools/", StringComparison.Ordinal)
            || normalized.Contains("/.store/pgtail/", StringComparison.Ordinal))
        {
            return InstallMethod.DotnetTool;
        }

        if (normalized.StartsWith("/opt/homebrew", StringComparison.Ordinal)
            || normalized.StartsWith("/usr/local/cellar", StringComparison.Ordinal)
            || normalized.StartsWith("/home/linuxbrew", StringComparison.Ordinal))
        {
            return InstallMethod.Homebrew;
        }

        var localAppData = environment("LOCALAPPDATA")?.Replace('\\', '/').ToLowerInvariant();
        if (normalized.Contains("/microsoft/winget/", StringComparison.Ordinal)
            || (localAppData is { Length: > 0 }
                && normalized.StartsWith(localAppData + "/microsoft/winget/packages", StringComparison.Ordinal)))
        {
            return InstallMethod.Winget;
        }

        return normalized.Contains("/scoop/apps/pgtail/", StringComparison.Ordinal) ? InstallMethod.Scoop : InstallMethod.Binary;
    }

    /// <summary>
    /// The command, or the page, that upgrades an installation.
    /// </summary>
    /// <param name="method">The install method.</param>
    /// <returns>The command or URL.</returns>
    public static string UpgradeCommand(InstallMethod method) => method switch
    {
        InstallMethod.DotnetTool => "dotnet tool update -g pgtail",
        InstallMethod.Homebrew => "brew upgrade pgtail",
        InstallMethod.Winget => "winget upgrade willibrandon.pgtail",
        InstallMethod.Scoop => "scoop update pgtail",
        _ => ReleasesPage,
    };
}
