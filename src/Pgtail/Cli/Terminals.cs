using Hex1b;
using Hex1b.Flow;

namespace Pgtail.Cli;

/// <summary>
/// Builds the Hex1b terminals pgtail runs on.
/// </summary>
internal static class Terminals
{
    /// <summary>
    /// A builder for the real terminal, with diagnostics for the <c>hex1b</c> CLI when <c>PGTAIL_DIAGNOSTICS</c> is set.
    /// </summary>
    /// <returns>The builder.</returns>
    public static Hex1bTerminalBuilder Builder()
    {
        Hex1bTerminalBuilder builder = Hex1bTerminal.CreateBuilder();
        return Environment.GetEnvironmentVariable("PGTAIL_DIAGNOSTICS") is { Length: > 0 }
            ? builder.WithDiagnostics("pgtail", forceEnable: true)
            : builder;
    }

    /// <summary>
    /// The REPL flow's options: scrollback-friendly output that reflows on resize, and the mouse for tail mode.
    /// </summary>
    /// <param name="options">The options to set.</param>
    public static void FlowOptions(Hex1bFlowOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        options.UseSoftWrapTombstones = true;
        options.ResizeSettleDelay = TimeSpan.FromMilliseconds(75);
        options.EnableMouse = true;
    }

    /// <summary>
    /// Waits, at the end of a flow, until the terminal has written what the flow printed.
    /// </summary>
    /// <remarks>
    /// A flow's output is queued for the terminal to write, and a terminal whose flow has returned stops without writing
    /// what is still queued. The line a finished prompt leaves behind is queued just before the flow returns, so without
    /// the wait it was sometimes never drawn, and the command's output appeared under a blank row.
    /// </remarks>
    /// <returns>A task that completes when the output has had time to be written.</returns>
    public static Task DrainOutputAsync() => Task.Delay(TimeSpan.FromMilliseconds(50));

    /// <summary>
    /// Waits until a stopped terminal no longer reads the console, before anything else reads it.
    /// </summary>
    /// <remarks>
    /// Hex1b's console input reader checks whether its terminal has stopped between 100 ms waits for input, so for up
    /// to one wait after a terminal stops it can still read what arrives: a shell command's first keys, or the reply to
    /// the next terminal's cursor position query, which then never comes.
    /// </remarks>
    /// <returns>A task that completes when the console is free.</returns>
    public static Task ReleaseConsoleAsync() => Task.Delay(TimeSpan.FromMilliseconds(150));

    /// <summary>
    /// Puts the cursor at the start of a screen row, as after a flow, below everything it printed, and saves it there.
    /// </summary>
    /// <remarks>
    /// A stopped terminal writes the sequence that also leaves an alternate screen, which restores the saved cursor.
    /// A flow never enters one, and Windows' console host, like xterm, still restores: to wherever a cursor was last
    /// saved, such as the line pgtail was started from. Called at the end of a flow, this saves the position the restore
    /// should go to, so the cursor stays put; called again once the terminal has stopped, it corrects a console that
    /// moved anyway, where a shell command's output, a stream, and the next prompt would otherwise start.
    /// </remarks>
    /// <param name="row">The row, counting from 0.</param>
    public static void PlaceCursor(int row)
    {
        Console.Out.Write($"\e[{row + 1};1H\e7");
        Console.Out.Flush();
    }

    /// <summary>
    /// Makes the next cursor position query ask the terminal.
    /// </summary>
    /// <remarks>
    /// On Linux and macOS, .NET caches the cursor position and moves it along with the text written through
    /// <see cref="Console"/>, but Hex1b writes to the terminal directly, so after a terminal has run the cached row is
    /// stale and the next prompt would start above the output. Writing an escape sequence through <see cref="Console"/>
    /// makes .NET drop the cache; the sequence written resets text attributes and changes nothing on the screen. Windows
    /// asks the console every time, so there is nothing to forget.
    /// </remarks>
    public static void ForgetCursorPosition()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        Console.Out.Write("\e[0m");
        Console.Out.Flush();
    }
}
