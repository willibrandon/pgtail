namespace Pgtail.Updates;

/// <summary>
/// How pgtail was installed, which decides the upgrade command to suggest.
/// </summary>
public enum InstallMethod
{
    /// <summary>
    /// A .NET global or local tool.
    /// </summary>
    DotnetTool,

    /// <summary>
    /// Homebrew.
    /// </summary>
    Homebrew,

    /// <summary>
    /// The Windows Package Manager.
    /// </summary>
    Winget,

    /// <summary>
    /// Scoop.
    /// </summary>
    Scoop,

    /// <summary>
    /// A binary downloaded from GitHub releases, or the MSI installer.
    /// </summary>
    Binary,
}
