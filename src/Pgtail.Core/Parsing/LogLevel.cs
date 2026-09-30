namespace Pgtail.Parsing;

/// <summary>
/// A PostgreSQL log severity, ordered from the most severe to the least.
/// </summary>
/// <remarks>
/// Lower values are more severe, so a threshold of <see cref="Warning"/> and above covers every value at or below it.
/// </remarks>
public enum LogLevel
{
    /// <summary>
    /// PANIC: the server is going down.
    /// </summary>
    Panic = 0,

    /// <summary>
    /// FATAL: the session is ending.
    /// </summary>
    Fatal = 1,

    /// <summary>
    /// ERROR: the statement failed.
    /// </summary>
    Error = 2,

    /// <summary>
    /// WARNING: something unexpected that did not fail.
    /// </summary>
    Warning = 3,

    /// <summary>
    /// NOTICE: information the client may want.
    /// </summary>
    Notice = 4,

    /// <summary>
    /// LOG: information for administrators.
    /// </summary>
    Log = 5,

    /// <summary>
    /// INFO: information the client asked for.
    /// </summary>
    Info = 6,

    /// <summary>
    /// DEBUG1: the least verbose debugging level.
    /// </summary>
    Debug1 = 7,

    /// <summary>
    /// DEBUG2 debugging output.
    /// </summary>
    Debug2 = 8,

    /// <summary>
    /// DEBUG3 debugging output.
    /// </summary>
    Debug3 = 9,

    /// <summary>
    /// DEBUG4 debugging output.
    /// </summary>
    Debug4 = 10,

    /// <summary>
    /// DEBUG5: the most verbose debugging level.
    /// </summary>
    Debug5 = 11,
}
