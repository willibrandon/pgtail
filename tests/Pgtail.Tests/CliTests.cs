using Hex1b.Automation;
using Hex1b.Input;

namespace Pgtail.Tests;

/// <summary>
/// The pgtail executable in a pseudo-terminal: its command line, the REPL on a real terminal, and tail mode.
/// </summary>
[TestClass]
public sealed class CliTests
{
    /// <summary>
    /// Supplies cancellation for the terminal.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// --version prints the version and exits cleanly.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Version_PrintsVersionAndExitsZero()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "--version");
        await pgtail.Automator.WaitUntilAsync(screen => screen.FindPattern(@"pgtail \d+\.\d+\.\d+").Count == 1, description: "the version");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// --help lists the commands.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Help_ListsCommands()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "--help");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Usage: pgtail [OPTIONS] COMMAND [ARGS]...")
                && screen.ContainsText("list-instances") && screen.ContainsText("enable-logging"),
            description: "usage and commands");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// An unknown command prints usage and an error, and exits with 2.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task UnknownCommand_PrintsErrorAndExitsTwo()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "bogus");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Try 'pgtail --help' for help.") && screen.ContainsText("Error: No such command 'bogus'."),
            description: "usage error");
        Assert.AreEqual(2, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// list-instances shows an instance found through <c>PGDATA</c>.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ListInstances_WithPgdata_ShowsInstance()
    {
        using var environment = new TestEnvironment();
        var (data, _) = DataDirectories.Create(environment.Root, "17", 5498);
        environment.Set("PGDATA", data);
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "list-instances");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("instance(s):") && screen.ContainsText("5498") && screen.ContainsText("17"),
            description: "the PGDATA instance");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// config --path prints where the configuration file lives.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ConfigPath_PrintsConfigFile()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "config", "--path");
        await pgtail.Automator.WaitUntilTextAsync(environment.Paths.ConfigFile);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// Shell completion offers the tail command's options.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Complete_TailOptions_ListsFlags()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "__complete", "bash", "--", "tail", "--s");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("--since") && screen.ContainsText("--stream") && screen.ContainsText("--stdin")
                && !screen.ContainsText("--file"),
            description: "matching tail options");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// tail --stream prints entries to the terminal and keeps following until Ctrl+C.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStream_File_PrintsEntriesUntilCtrlC()
    {
        using var environment = new TestEnvironment();
        var log = Path.Combine(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4100, "ERROR",
            "duplicate key value violates unique constraint"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken, "tail", "--file", log,
            "--since", "1h", "--stream");
        await pgtail.Automator.WaitUntilTextAsync("duplicate key value violates unique constraint");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 4101, "LOG", "a line written while streaming"));
        await pgtail.Automator.WaitUntilTextAsync("a line written while streaming");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// Piped input streams through the filters, and piped output holds only entries.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStdinStream_PipedLog_PrintsEntries()
    {
        using var environment = new TestEnvironment();
        var log = Path.Combine(environment.Root, "piped.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 4200, "WARNING", "piped warning line"),
            LogFiles.Text(DateTime.UtcNow, 4201, "LOG", "piped log line"));
        var reader = OperatingSystem.IsWindows() ? "type" : "cat";
        await using var shell = PgtailProcess.Shell(environment, $"{reader} \"{log}\" | {{pgtail}} tail --stdin --stream",
            TestContext.CancellationToken);
        await shell.Automator.WaitUntilAsync(
            screen => screen.ContainsText("piped warning line") && screen.ContainsText("piped log line")
                && !screen.ContainsText("Detected format"),
            description: "both piped entries and nothing else");
        Assert.AreEqual(0, await shell.WaitForExitAsync());
    }

    /// <summary>
    /// With <c>NO_COLOR</c>, streamed entries have no colors.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStream_NoColor_PrintsWithoutColors()
    {
        using var environment = new TestEnvironment(new Dictionary<string, string?> { ["NO_COLOR"] = "1" });
        var log = Path.Combine(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4300, "ERROR", "uncolored failure"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken, "tail", "--file", log,
            "--since", "1h", "--stream");
        await pgtail.Automator.WaitUntilTextAsync("uncolored failure");
        using var screen = pgtail.Automator.CreateSnapshot();
        Assert.IsFalse(screen.HasForegroundColor(), "no text should be colored");
    }

    /// <summary>
    /// Full screen tail mode starts on the alternate screen, and q exits cleanly.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Tail_FullScreen_QuitExitsZero()
    {
        using var environment = new TestEnvironment();
        var log = Path.Combine(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4400, "LOG", "full screen entry"));
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken, "tail", "--file", log, "--since", "1h");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.InAlternateScreen && screen.ContainsText("full screen entry") && screen.ContainsText("FOLLOW"),
            description: "tail mode on the alternate screen");
        await pgtail.Automator.TabAsync(TestContext.CancellationToken);
        await pgtail.Automator.TypeAsync("q", TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// The REPL starts with its banner and prompt, and quit exits cleanly.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_Quit_ExitsZero()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("pgtail - PostgreSQL log tailer") && screen.ContainsText("pgtail>"),
            description: "banner and prompt");
        await pgtail.Automator.TypeAsync("quit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// A ! command runs in the shell on the real terminal, then the prompt returns.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_BangCommand_RunsInShell()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("!echo shell-output-$((6*7))", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        var expected = OperatingSystem.IsWindows() ? "shell-output-$((6*7))" : "shell-output-42";
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText(expected) && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the shell's output and a new prompt");
    }

    /// <summary>
    /// clear clears the real terminal and shows the prompt at the top.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_Clear_ClearsScreen()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail - PostgreSQL log tailer");
        await pgtail.Automator.TypeAsync("clear", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => !screen.ContainsText("pgtail - PostgreSQL log tailer") && screen.GetLineTrimmed(0) == "pgtail>",
            description: "a cleared screen with the prompt on top");
    }

    /// <summary>
    /// Tail mode from the REPL takes the alternate screen and gives the prompt back on q.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_TailThenQuit_ReturnsToPrompt()
    {
        using var environment = new TestEnvironment();
        var log = Path.Combine(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4500, "LOG", "entry seen from the repl"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync($"tail --file {log} --since 1h", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.InAlternateScreen && screen.ContainsText("entry seen from the repl"),
            description: "tail mode");
        await pgtail.Automator.TabAsync(TestContext.CancellationToken);
        await pgtail.Automator.TypeAsync("q", TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => !screen.InAlternateScreen && ReplHarness.PromptLine(screen) == "pgtail>"
                && screen.ContainsText($"pgtail> tail --file {log} --since 1h"),
            description: "the prompt again below the tail command");
        await pgtail.Automator.TypeAsync("quit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// config edit opens the built-in editor, and closing it returns to the prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_ConfigEdit_OpensEditorAndCloses()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("config edit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.InAlternateScreen && screen.ContainsText("config.toml"),
            description: "the editor on the alternate screen");
        await pgtail.Automator.EscapeAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => !screen.InAlternateScreen && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the prompt again");
    }

    /// <summary>
    /// connections --watch streams events on the real terminal until Ctrl+C, then sums up and gives the prompt back.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Repl_ConnectionsWatch_StreamsUntilCtrlC()
    {
        using var environment = new TestEnvironment();
        var (data, log) = DataDirectories.Create(environment.Root, "17", 5496);
        environment.Set("PGDATA", data);
        await using var pgtail = PgtailProcess.Start(environment, 200, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");

        // Tailing the instance by its data directory makes it the one watched, whatever else runs on the machine.
        await pgtail.Automator.TypeAsync($"tail {data} --stream", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Press Ctrl+C to stop");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Paused. Use 'stop' to stop tailing.");
        await pgtail.Automator.TypeAsync("connections --watch", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("[+] connect  [-] disconnect  [!] failed");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 900, "LOG",
            "connection authorized: user=alice database=orders application_name=psql"));
        await pgtail.Automator.WaitUntilTextAsync("alice@orders (psql)");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Exited watch mode. 1 events seen.")
                && ReplHarness.PromptLine(screen).StartsWith("paused [", StringComparison.Ordinal),
            description: "the summary and the prompt again");
    }
}
