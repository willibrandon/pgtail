using Hex1b.Automation;
using Hex1b.Input;
using Pgtail.Repl;

namespace Pgtail.Tests;

/// <summary>
/// REPL commands and prompt keys, driven through a headless terminal.
/// </summary>
[TestClass]
public sealed class ReplCommandTests
{
    /// <summary>
    /// Supplies cancellation for the terminal.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// An unknown command says so and points to help.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task UnknownCommand_PrintsHelpHint()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("bogus", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Unknown command: bogus") && snapshot.ContainsText("Type 'help' for available commands."),
            description: "unknown command message");
    }

    /// <summary>
    /// Setting levels confirms them and shows them in the toolbar.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Levels_ErrorWarning_ShowsFilterInToolbar()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("levels error warning", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Filter set: ERROR WARNING")
                && ReplHarness.Toolbar(snapshot).Contains("levels:ERROR,WARNING", StringComparison.Ordinal),
            description: "level filter confirmed and in the toolbar");
    }

    /// <summary>
    /// An unknown level is rejected with the valid names.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Levels_UnknownLevel_ListsValidLevels()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("levels loud", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Unknown level(s): loud") && snapshot.ContainsText("Valid levels:"),
            description: "unknown level message");
    }

    /// <summary>
    /// A regex filter is case-insensitive by default, as the toolbar shows.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Filter_Pattern_ShowsCaseInsensitiveFilterInToolbar()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("filter /deadlock/", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Filter set: /deadlock/")
                && ReplHarness.Toolbar(snapshot).Contains("filter:/deadlock/i", StringComparison.Ordinal),
            description: "regex filter confirmed and in the toolbar");
    }

    /// <summary>
    /// A relative time filter shows the time it starts from.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Since_FiveMinutes_ShowsStartTimeInToolbar()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("since 5m", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Showing logs since ")
                && ReplHarness.Toolbar(snapshot).Contains("since ", StringComparison.Ordinal),
            description: "time filter confirmed and in the toolbar");
    }

    /// <summary>
    /// Slow query thresholds are confirmed with their colors.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Slow_Thresholds_ShowsEachThreshold()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("slow 50 200 900", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Slow query highlighting enabled")
                && snapshot.ContainsText("> 50ms")
                && snapshot.ContainsText("> 200ms")
                && snapshot.ContainsText("> 900ms"),
            description: "slow query thresholds");
    }

    /// <summary>
    /// Setting a value confirms it and saves it to the configuration file.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Set_SlowWarn_SavesConfigurationFile()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("set slow.warn 250", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("slow.warn = 250") && snapshot.ContainsText("Saved to"),
            description: "setting confirmed");
        var text = await File.ReadAllTextAsync(environment.Paths.ConfigFile, TestContext.CancellationToken);
        Assert.Contains("[slow]", text);
        Assert.Contains("warn = 250", text);
    }

    /// <summary>
    /// An invalid value is rejected and nothing is saved.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Set_InvalidValue_IsRejected()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("set slow.warn -5", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("must be a positive integer");
        Assert.IsFalse(File.Exists(environment.Paths.ConfigFile));
    }

    /// <summary>
    /// Switching theme updates the toolbar and saves the choice.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Theme_Monokai_UpdatesToolbarAndSaves()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("theme monokai", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.Toolbar(snapshot).Contains("Theme: monokai", StringComparison.Ordinal),
            description: "toolbar shows the new theme");
        var text = await File.ReadAllTextAsync(environment.Paths.ConfigFile, TestContext.CancellationToken);
        Assert.Contains("name = \"monokai\"", text);
    }

    /// <summary>
    /// Typing a command prefix shows the matching commands with their descriptions.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Typing_CommandPrefix_ShowsCompletionMenu()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.TypeAsync("th", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("theme") && snapshot.ContainsText("Switch color theme"),
            description: "completion menu for 'th'");
    }

    /// <summary>
    /// Tab completes a lone matching command.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Tab_LoneCompletion_CompletesCommand()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.TypeAsync("hig", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("highlight");
        await repl.Automator.TabAsync(TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("pgtail> highlight ");
        await repl.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.PromptLine(snapshot) == "pgtail>",
            description: "a fresh prompt after Ctrl+C");
    }

    /// <summary>
    /// Completion offers a command's subcommands after its name.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Typing_CommandAndSpace_ShowsSubcommands()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.TypeAsync("notify ", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("on") && snapshot.ContainsText("off") && snapshot.ContainsText("quiet"),
            description: "notify subcommands");
    }

    /// <summary>
    /// Up recalls the previous command, and history is saved to disk.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task UpArrow_AfterCommand_RecallsIt()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("display", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("Display: compact, Output: text");
        await repl.Automator.UpAsync(TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.PromptLine(snapshot) == "pgtail> display",
            description: "the previous command recalled");
        var history = await File.ReadAllTextAsync(environment.Paths.HistoryFile, TestContext.CancellationToken);
        Assert.Contains("+display", history);
    }

    /// <summary>
    /// History from an earlier session is available after a restart.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task UpArrow_AfterRestart_RecallsEarlierSession()
    {
        using var environment = new TestEnvironment();
        await using (var first = await ReplHarness.StartAsync(environment, TestContext.CancellationToken))
        {
            await first.RunAsync("output", TestContext.CancellationToken);
            await first.Automator.WaitUntilTextAsync("Output format: text");
        }

        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.UpAsync(TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.PromptLine(snapshot) == "pgtail> output",
            description: "the command from the earlier session");
    }

    /// <summary>
    /// Ctrl+C abandons the line and shows a fresh prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task CtrlC_WithText_AbandonsLine()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.TypeAsync("levels error", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("pgtail> levels error");
        await repl.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.PromptLine(snapshot) == "pgtail>"
                && !ReplHarness.Toolbar(snapshot).Contains("levels:", StringComparison.Ordinal),
            description: "a fresh prompt with no filter set");
    }

    /// <summary>
    /// Ctrl+D on an empty line says goodbye and ends the REPL.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task CtrlD_OnEmptyLine_Exits()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.Ctrl().KeyAsync(Hex1bKey.D, TestContext.CancellationToken);
        _ = await repl.WaitForRequestAsync(ReplRequestKind.Exit);
        await repl.Automator.WaitUntilTextAsync("Goodbye!");
    }

    /// <summary>
    /// quit says goodbye and ends the REPL.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Quit_SaysGoodbyeAndExits()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("quit", TestContext.CancellationToken);
        _ = await repl.WaitForRequestAsync(ReplRequestKind.Exit);
        await repl.Automator.WaitUntilTextAsync("Goodbye!");
    }

    /// <summary>
    /// A command starting with ! asks for the real terminal to run it in the shell.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Bang_WithCommand_RequestsShell()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("!echo hello", TestContext.CancellationToken);
        var request = await repl.WaitForRequestAsync(ReplRequestKind.Shell);
        Assert.AreEqual("echo hello", request.Command);
    }

    /// <summary>
    /// ! on an empty line enters shell mode, and Escape leaves it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Bang_OnEmptyLine_EntersShellMode()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.Automator.TypeAsync("!", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.Toolbar(snapshot).Contains("SHELL", StringComparison.Ordinal)
                && ReplHarness.PromptLine(snapshot) == "!",
            description: "shell mode prompt and toolbar");
        await repl.Automator.EscapeAsync(TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => ReplHarness.Toolbar(snapshot).Contains("Theme: dark", StringComparison.Ordinal)
                && ReplHarness.PromptLine(snapshot) == "pgtail>",
            description: "normal prompt and toolbar");
    }

    /// <summary>
    /// clear asks for the real terminal to clear the screen.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Clear_RequestsClearScreen()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("clear", TestContext.CancellationToken);
        _ = await repl.WaitForRequestAsync(ReplRequestKind.ClearScreen);
        await repl.Automator.WaitUntilTextAsync("pgtail>");
    }

    /// <summary>
    /// list shows an instance found through <c>PGDATA</c> with its version, port, and log.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task List_WithPgdata_ShowsInstance()
    {
        using var environment = new TestEnvironment();
        var (data, _) = DataDirectories.Create(environment.Root, "16", 5499);
        environment.Set("PGDATA", data);
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, width: 140);
        await repl.RunAsync("list", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("VERSION") && snapshot.ContainsText("5499") && snapshot.ContainsText("pgdata"),
            description: "instance table with the PGDATA instance");
    }

    /// <summary>
    /// Tailing a file that does not exist says so and stays at the prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Tail_MissingFile_PrintsError()
    {
        using var environment = new TestEnvironment();
        var missing = Path.Combine(environment.Root, "missing.log");
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, width: 160);
        await repl.RunAsync($"tail --file {missing}", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync($"File not found: {missing}");
    }

    /// <summary>
    /// errors, stats, and connections explain that nothing has been collected yet.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Statistics_BeforeTailing_ExplainNoData()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, height: 40);
        await repl.RunAsync("errors", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("No errors recorded in this session.");
        await repl.RunAsync("stats", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("No query duration data collected yet.");
        await repl.RunAsync("connections", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("No connection data available.");
    }

    /// <summary>
    /// notify on its own reports the notification status and platform.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Notify_Status_ShowsDisabled()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("notify", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("Notifications: disabled") && snapshot.ContainsText("Platform:"),
            description: "notification status");
    }

    /// <summary>
    /// Turning notifications on for levels saves them to the configuration file.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task NotifyOn_Levels_SavesConfiguration()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken);
        await repl.RunAsync("notify on error fatal", TestContext.CancellationToken);
        await repl.Automator.WaitUntilTextAsync("Notifications enabled");
        var text = await File.ReadAllTextAsync(environment.Paths.ConfigFile, TestContext.CancellationToken);
        Assert.Contains("[notifications]", text);
        Assert.Contains("enabled = true", text);
        Assert.Contains("\"ERROR\"", text);
    }

    /// <summary>
    /// config prints the effective configuration as TOML.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Config_Show_PrintsToml()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, height: 60);
        await repl.RunAsync("config", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("[slow]") && snapshot.ContainsText("[theme]"),
            description: "configuration sections");
    }

    /// <summary>
    /// theme list names the built-in themes and marks the current one.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ThemeList_ShowsBuiltInThemes()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, height: 40);
        await repl.RunAsync("theme list", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("dark") && snapshot.ContainsText("monokai") && snapshot.ContainsText("solarized-dark"),
            description: "built-in themes");
    }

    /// <summary>
    /// highlight list shows the built-in highlighters by category.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task HighlightList_ShowsBuiltInHighlighters()
    {
        using var environment = new TestEnvironment();
        await using var repl = await ReplHarness.StartAsync(environment, TestContext.CancellationToken, height: 60);
        await repl.RunAsync("highlight list", TestContext.CancellationToken);
        await repl.Automator.WaitUntilAsync(
            snapshot => snapshot.ContainsText("timestamp") && snapshot.ContainsText("sqlstate") && snapshot.ContainsText("duration"),
            description: "built-in highlighters");
    }
}
