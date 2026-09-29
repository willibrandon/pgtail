using System.Reflection;

namespace Pgtail.Cli;

/// <summary>
/// The running version of pgtail.
/// </summary>
internal static class PgtailVersion
{
    /// <summary>
    /// The version, such as <c>0.6.1</c>, without build metadata.
    /// </summary>
    public static string Current { get; } = Read();

    private static string Read()
    {
        var informational = typeof(PgtailVersion)
            .Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
        return informational is null ? "0.0.0-dev" : informational.Split('+')[0];
    }
}
