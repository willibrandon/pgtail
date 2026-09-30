namespace Pgtail.Detection;

/// <summary>
/// How a PostgreSQL instance was found.
/// </summary>
public enum DetectionSource
{
    /// <summary>
    /// A running postgres process.
    /// </summary>
    Process,

    /// <summary>
    /// A pgrx data directory under <c>~/.pgrx</c>.
    /// </summary>
    Pgrx,

    /// <summary>
    /// The <c>PGDATA</c> environment variable.
    /// </summary>
    Pgdata,

    /// <summary>
    /// A platform default location.
    /// </summary>
    KnownPath,
}
