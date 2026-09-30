using Pgtail.Parsing;
using Pgtail.Styling;

namespace Pgtail.Display;

/// <summary>
/// The fixed styles of tail mode's entry lines.
/// </summary>
public static class TailStyles
{
    private static readonly TextStyle s_panic = StyleParser.Parse("bold white on red");
    private static readonly TextStyle s_fatal = StyleParser.Parse("bold red reverse");
    private static readonly TextStyle s_error = StyleParser.Parse("bold red");
    private static readonly TextStyle s_warning = StyleParser.Parse("yellow");
    private static readonly TextStyle s_notice = StyleParser.Parse("cyan");
    private static readonly TextStyle s_log = StyleParser.Parse("green");
    private static readonly TextStyle s_info = StyleParser.Parse("blue");

    /// <summary>
    /// Timestamps and process IDs.
    /// </summary>
    public static TextStyle Dim { get; } = StyleParser.Parse("dim");

    /// <summary>
    /// The source file of an entry when several files are tailed.
    /// </summary>
    public static TextStyle SourceFile { get; } = StyleParser.Parse("magenta");

    /// <summary>
    /// The SQLSTATE code.
    /// </summary>
    public static TextStyle SqlState { get; } = StyleParser.Parse("cyan");

    /// <summary>
    /// The style of a level name.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <returns>The style.</returns>
    public static TextStyle Level(LogLevel level) => level switch
    {
        LogLevel.Panic => s_panic,
        LogLevel.Fatal => s_fatal,
        LogLevel.Error => s_error,
        LogLevel.Warning => s_warning,
        LogLevel.Notice => s_notice,
        LogLevel.Log => s_log,
        LogLevel.Info => s_info,
        _ => Dim,
    };
}
