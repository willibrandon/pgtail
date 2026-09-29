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
        var builder = Hex1bTerminal.CreateBuilder();
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
    /// Makes the next cursor position query ask the terminal.
    /// </summary>
    /// <remarks>
    /// .NET caches the cursor position and moves it along with the text written through <see cref="Console"/>, but Hex1b
    /// writes to the terminal directly, so after a terminal has run the cached row is stale and the next prompt would
    /// start above the output. Writing an escape sequence through <see cref="Console"/> makes .NET drop the cache; the
    /// sequence written resets text attributes and changes nothing on the screen.
    /// </remarks>
    public static void ForgetCursorPosition()
    {
        Console.Out.Write("\e[0m");
        Console.Out.Flush();
    }
}
