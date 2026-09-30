namespace Pgtail.Tests;

/// <summary>
/// The interactive REPL, driven through a headless terminal.
/// </summary>
[TestClass]
public sealed class ReplTests
{
    /// <summary>
    /// Supplies cancellation for the terminal.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// Starting shows the banner, the prompt, and the toolbar.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Start_ShowsBannerPromptAndToolbar()
    {
        using var environment = new TestEnvironment();
        await using ReplHarness repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("pgtail - PostgreSQL log tailer");
        await repl.Automator.WaitUntilTextAsync("Type 'help' for available commands, 'quit' to exit.");
        await repl.Automator.WaitUntilTextAsync("Theme: dark");
    }

    /// <summary>
    /// A command's output appears above the next prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Help_PrintsCommandReference()
    {
        using var environment = new TestEnvironment();
        await using ReplHarness repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("help", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("Ctrl+D    Exit pgtail");
        await repl.Automator.WaitUntilTextAsync("pgtail>");
    }
}
