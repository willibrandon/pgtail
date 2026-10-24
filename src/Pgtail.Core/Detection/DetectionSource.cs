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
    /// A pgrx data directory under <c>~/.pgrx</c> or <c>PGRX_HOME</c>.
    /// </summary>
    Pgrx,

    /// <summary>
    /// An ankus development cluster under <c>~/.ankus/clusters</c>.
    /// </summary>
    Ankus,

    /// <summary>
    /// The <c>PGDATA</c> environment variable.
    /// </summary>
    Pgdata,

    /// <summary>
    /// A platform default location.
    /// </summary>
    KnownPath,
}
