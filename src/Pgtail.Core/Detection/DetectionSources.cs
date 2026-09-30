namespace Pgtail.Detection;

/// <summary>
/// Names of detection sources.
/// </summary>
public static class DetectionSources
{
    /// <summary>
    /// The short name shown in instance lists: <c>process</c>, <c>pgrx</c>, <c>pgdata</c>, or <c>known</c>.
    /// </summary>
    /// <param name="source">The source.</param>
    /// <returns>The name.</returns>
    public static string ToName(this DetectionSource source) => source switch
    {
        DetectionSource.Process => "process",
        DetectionSource.Pgrx => "pgrx",
        DetectionSource.Pgdata => "pgdata",
        _ => "known",
    };
}
