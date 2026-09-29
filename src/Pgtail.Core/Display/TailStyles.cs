using Pgtail.Parsing;
using Pgtail.Styling;

namespace Pgtail.Display;

/// <summary>
/// The fixed styles of tail mode's entry lines.
/// </summary>
public static class TailStyles
{
    private static readonly TextStyle Panic = StyleParser.Parse("bold white on red");
    private static readonly TextStyle Fatal = StyleParser.Parse("bold red reverse");
    private static readonly TextStyle Error = StyleParser.Parse("bold red");
    private static readonly TextStyle Warning = StyleParser.Parse("yellow");
    private static readonly TextStyle Notice = StyleParser.Parse("cyan");
    private static readonly TextStyle Log = StyleParser.Parse("green");
    private static readonly TextStyle Info = StyleParser.Parse("blue");

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
        LogLevel.Panic => Panic,
        LogLevel.Fatal => Fatal,
        LogLevel.Error => Error,
        LogLevel.Warning => Warning,
        LogLevel.Notice => Notice,
        LogLevel.Log => Log,
        LogLevel.Info => Info,
        _ => Dim,
    };
}
