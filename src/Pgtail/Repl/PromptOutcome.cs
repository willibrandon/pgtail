namespace Pgtail.Repl;

/// <summary>
/// How the prompt ended.
/// </summary>
internal enum PromptOutcome
{
    /// <summary>
    /// Enter submitted the line.
    /// </summary>
    Submitted,

    /// <summary>
    /// Ctrl+C abandoned the line.
    /// </summary>
    Interrupted,

    /// <summary>
    /// Ctrl+D on an empty line asked to leave.
    /// </summary>
    EndOfInput,

    /// <summary>
    /// Ctrl+L asked to clear the screen.
    /// </summary>
    ClearScreen,
}
