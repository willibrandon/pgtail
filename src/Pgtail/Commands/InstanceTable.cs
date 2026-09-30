using System.Globalization;
using Pgtail.Detection;

namespace Pgtail.Commands;

/// <summary>
/// Formats detected instances as the table <c>list</c> prints.
/// </summary>
internal static class InstanceTable
{
    /// <summary>
    /// The table, or advice when nothing was found.
    /// </summary>
    /// <param name="instances">The instances.</param>
    /// <param name="home">The home directory, shortened to <c>~</c>.</param>
    /// <returns>The lines.</returns>
    public static IReadOnlyList<string> Format(IReadOnlyList<PostgresInstance> instances, string home)
    {
        ArgumentNullException.ThrowIfNull(instances);
        if (instances.Count == 0)
        {
            return
            [
                "No PostgreSQL instances found.",
                "",
                "Suggestions:",
                "  - Start a PostgreSQL instance",
                "  - Set PGDATA environment variable to your data directory",
                "  - Run 'refresh' after starting PostgreSQL",
                "  - Check ~/.pgrx/ for pgrx development instances",
            ];
        }

        var lines = new List<string> { "  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY" };
        foreach (PostgresInstance instance in instances)
        {
            lines.Add($"  {instance.Id}  {instance.Version,-8} {instance.PortText,-6} {instance.StatusText,-8} "
                + $"{instance.LogStatus,-4} {instance.Source.ToName(),-7} {PathDisplay.Shorten(instance.DataDirectory, home)}");
        }

        return lines;
    }

    /// <summary>
    /// Finds an instance by its ID or its data directory.
    /// </summary>
    /// <param name="instances">The instances.</param>
    /// <param name="argument">The ID or path as typed.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    /// <returns>The instance, or null.</returns>
    public static PostgresInstance? Find(IReadOnlyList<PostgresInstance> instances, string argument, string currentDirectory)
    {
        ArgumentNullException.ThrowIfNull(instances);
        ArgumentNullException.ThrowIfNull(argument);
        if (int.TryParse(argument, NumberStyles.None, CultureInfo.InvariantCulture, out int id))
        {
            return instances.FirstOrDefault(instance => instance.Id == id);
        }

        string path = Path.GetFullPath(argument, currentDirectory).TrimEnd(Path.DirectorySeparatorChar);
        return instances.FirstOrDefault(instance =>
            Path.GetFullPath(instance.DataDirectory).TrimEnd(Path.DirectorySeparatorChar) == path);
    }
}
