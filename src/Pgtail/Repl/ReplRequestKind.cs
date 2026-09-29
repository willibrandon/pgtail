namespace Pgtail.Repl;

/// <summary>
/// What the REPL needs the real terminal for while its prompt loop pauses.
/// </summary>
internal enum ReplRequestKind
{
    /// <summary>
    /// Leave pgtail.
    /// </summary>
    Exit,

    /// <summary>
    /// Clear the screen and scrollback.
    /// </summary>
    ClearScreen,

    /// <summary>
    /// Run a shell command attached to the terminal.
    /// </summary>
    Shell,

    /// <summary>
    /// Stream output to the terminal until Ctrl+C.
    /// </summary>
    Stream,

    /// <summary>
    /// Run a full screen app, such as tail mode or the editor, then continue the command that asked for it.
    /// </summary>
    Screen,
}
