using Pgtail.Styling;

namespace Pgtail.Display;

/// <summary>
/// The labels in front of what is typed at pgtail's prompts, in the colors they are drawn in.
/// </summary>
/// <remarks>
/// The REPL, tail mode, and the documentation's transcripts all take them from here, so they cannot drift apart.
/// </remarks>
public static class PromptLabels
{
    /// <summary>
    /// The label of tail mode's command input, which is drawn in the terminal's own color.
    /// </summary>
    public const string Tail = "tail> ";

    /// <summary>
    /// The REPL's label.
    /// </summary>
    public static StyledText Repl => Markup.Parse("[#00aa00]pgtail[/][#666666]>[/] ");

    /// <summary>
    /// The REPL's label in shell mode, where a line is run by the shell.
    /// </summary>
    public static StyledText Shell => Markup.Parse("[#ff6688]![/] ");

    /// <summary>
    /// The REPL's label while a stream is paused.
    /// </summary>
    /// <param name="stream">What is being streamed: an instance's ID or a file's name.</param>
    /// <returns>The label.</returns>
    public static StyledText Paused(string stream)
    {
        ArgumentNullException.ThrowIfNull(stream);
        return Markup.Parse($"[#ffaa00]paused[/] [#00aaaa]{Markup.Escape($"[{stream}]")}[/][#666666]>[/] ");
    }
}
