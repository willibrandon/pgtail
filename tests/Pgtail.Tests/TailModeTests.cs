using Hex1b.Automation;

namespace Pgtail.Tests;

/// <summary>
/// Full screen tail mode, entered from the REPL.
/// </summary>
[TestClass]
public sealed class TailModeTests
{
    /// <summary>
    /// Supplies cancellation for the terminal.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// Leaving tail mode with q returns to the REPL prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailFile_Quit_ReturnsToPrompt()
    {
        using var environment = new TestEnvironment();
        string log = Path.Combine(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 100, "LOG", "database system is ready to accept connections"));
        // Wide enough for the command on one line, with the long temp directories of macOS and Windows.
        await using ReplHarness repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, width: 160);
        await repl.RunAsync($"tail --file {log}", TestContext.CancellationToken);
        Hex1bTerminalAutomator screen = await repl.WaitForScreenAsync();
        await screen.WaitUntilTextAsync("FOLLOW");
        await screen.TypeAsync("q", TestContext.CancellationToken);
        await screen.WaitUntilAsync(snapshot => TailHarness.Input(snapshot) == "tail> q", description: "q typed at the prompt");
        await screen.EnterAsync(TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(snapshot => snapshot.ContainsText($"pgtail> tail --file {log}")
            && ReplHarness.Toolbar(snapshot).Contains("Theme: dark", StringComparison.Ordinal));
    }
}
