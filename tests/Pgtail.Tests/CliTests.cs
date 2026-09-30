using System.Globalization;
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
    public async Task VersionPrintsVersionAndExitsZero()
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
    public async Task HelpListsCommands()
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
    public async Task UnknownCommandPrintsErrorAndExitsTwo()
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
    public async Task ListInstancesWithPgdataShowsInstance()
    {
        using var environment = new TestEnvironment();
        (string? data, string _) = DataDirectories.Create(environment.Root, "17", 5498);
        environment.Set("PGDATA", data);
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "list-instances");
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("instance(s):") && screen.ContainsText("5498") && screen.ContainsText("17"),
            description: "the PGDATA instance");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// config --path prints the platform's place for settings: Application Support, APPDATA, or XDG_CONFIG_HOME.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ConfigPathPrintsPlatformConfigFile()
    {
        using var environment = new TestEnvironment();
        string expected = OperatingSystem.IsMacOS()
            ? Path.Join(environment.Home, "Library", "Application Support", "pgtail", "config.toml")
            : OperatingSystem.IsWindows()
                ? Path.Join(environment.Home, "AppData", "Roaming", "pgtail", "config.toml")
                : Path.Join(environment.Home, ".config", "pgtail", "config.toml");
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "config", "--path");
        await pgtail.Automator.WaitUntilTextAsync(expected);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// list-instances finds a data directory where the platform keeps one for the user.
    /// </summary>
    /// <remarks>
    /// On Windows that is <c>%LOCALAPPDATA%\PostgreSQL\data</c>; elsewhere Postgres.app's
    /// <c>~/Library/Application Support/Postgres/var-&lt;version&gt;</c>, which is looked for on every Unix system.
    /// </remarks>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ListInstancesUserKnownLocationShowsInstance()
    {
        using var environment = new TestEnvironment();
        string data = OperatingSystem.IsWindows()
            ? Path.Join(environment.Home, "AppData", "Local", "PostgreSQL", "data")
            : Path.Join(environment.Home, "Library", "Application Support", "Postgres", "var-16");
        DataDirectories.CreateAt(data, "16", 5493);
        await using var pgtail = PgtailProcess.Run(environment, TestContext.CancellationToken, "list-instances");
        await pgtail.Automator.WaitUntilAsync(
            screen => Enumerable.Range(0, screen.Height).Select(screen.GetLineTrimmed)
                .Any(line => line.Contains("5493", StringComparison.Ordinal) && line.EndsWith("known", StringComparison.Ordinal)),
            description: "the instance found in the known location");
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// Shell completion offers the tail command's options.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task CompleteTailOptionsListsFlags()
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
    public async Task TailStreamFilePrintsEntriesUntilCtrlC()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
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
    /// The full display names the user and database Debian and Ubuntu's <c>log_line_prefix</c> writes.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplDisplayFullDebianPrefixShowsUserAndDatabase()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql-18-main.log");
        string time = DateTime.UtcNow.AddMinutes(-1).ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture);
        LogFiles.Append(log,
            $"{time} UTC [4200] alice@orders ERROR:  division by zero",
            $"{time} UTC [4200] alice@orders STATEMENT:  select 1/0");
        await using var pgtail = PgtailProcess.Start(environment, 120, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("display full", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Display mode: full");
        await pgtail.Automator.TypeAsync($"tail --file {log} --since 1h --stream", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("ERROR  : division by zero") && screen.ContainsText("STATEMENT:  select 1/0")
                && screen.ContainsText("Database: orders") && screen.ContainsText("User: alice"),
            description: "the error with its statement, database, and user");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("paused [postgresql-18-main.log]>");
        await pgtail.Automator.TypeAsync("stop", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => ReplHarness.PromptLine(screen) == "pgtail>", description: "the prompt");
        await pgtail.Automator.TypeAsync("quit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
    }

    /// <summary>
    /// Piped input streams through the filters, and piped output holds only entries.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStdinStreamPipedLogPrintsEntries()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "piped.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 4200, "WARNING", "piped warning line"),
            LogFiles.Text(DateTime.UtcNow, 4201, "LOG", "piped log line"));
        string reader = OperatingSystem.IsWindows() ? "type" : "cat";
        await using var shell = PgtailProcess.Shell(environment, $"{reader} \"{log}\" | {{pgtail}} tail --stdin --stream",
            TestContext.CancellationToken);
        await shell.Automator.WaitUntilAsync(
            screen => screen.ContainsText("piped warning line") && screen.ContainsText("piped log line")
                && !screen.ContainsText("Detected format"),
            description: "both piped entries and nothing else");
        Assert.AreEqual(0, await shell.WaitForExitAsync());
    }

    /// <summary>
    /// Piped input split between an error and its statement keeps the statement with the error.
    /// </summary>
    /// <remarks>
    /// Input is read 64 KiB at a time, and the pipe is full before pgtail first reads it, so the first read ends right
    /// after the error.
    /// </remarks>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStdinStreamErrorAtReadBoundaryKeepsItsStatement()
    {
        using var environment = new TestEnvironment();
        string log = LogFiles.ErrorAtBoundary(Path.Join(environment.Root, "piped.log"), 64 * 1024);
        string output = Path.Join(environment.Root, "output.txt");
        string reader = OperatingSystem.IsWindows() ? "type" : "cat";
        await using var shell = PgtailProcess.Shell(environment,
            $"{reader} \"{log}\" | {{pgtail}} tail --stdin --stream > \"{output}\"", TestContext.CancellationToken);
        Assert.AreEqual(0, await shell.WaitForExitAsync());
        string[] lines = File.ReadAllLines(output);
        int error = Array.FindIndex(lines, line => line.EndsWith("ERROR  : relation \"nope\" does not exist", StringComparison.Ordinal));
        Assert.IsGreaterThanOrEqualTo(0, error, "the error is written");
        Assert.AreEqual("STATEMENT:  select * from nope", lines[error + 1]);
        Assert.EndsWith("LOG    : checkpoint starting: time", lines[error + 2]);
    }

    /// <summary>
    /// With <c>NO_COLOR</c>, streamed entries have no colors.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStreamNoColorPrintsWithoutColors()
    {
        using var environment = new TestEnvironment(new Dictionary<string, string?> { ["NO_COLOR"] = "1" });
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4300, "ERROR", "uncolored failure"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken, "tail", "--file", log,
            "--since", "1h", "--stream");
        await pgtail.Automator.WaitUntilTextAsync("uncolored failure");
        using Hex1bTerminalSnapshot screen = pgtail.Automator.CreateSnapshot();
        Assert.IsFalse(screen.HasForegroundColor(), "no text should be colored");
    }

    /// <summary>
    /// Full screen tail mode starts on the alternate screen, and q exits cleanly.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailFullScreenQuitExitsZero()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
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
    public async Task ReplQuitExitsZero()
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
    public async Task ReplBangCommandRunsInShell()
    {
        using var environment = new TestEnvironment();
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("!echo shell-output-$((6*7))", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        string expected = OperatingSystem.IsWindows() ? "shell-output-$((6*7))" : "shell-output-42";
        await pgtail.Automator.WaitUntilAsync(
            screen => ReplHarness.LineAfter(screen, "echo shell-output") is { } output
                && output.StartsWith(expected, StringComparison.Ordinal) && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the shell's output at the start of the next line, and a new prompt");
    }

    /// <summary>
    /// A shell command keeps its quotes, so a quoted path with a space reaches the command whole.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplBangCommandKeepsQuotes()
    {
        using var environment = new TestEnvironment();
        File.WriteAllText(Path.Join(environment.Root, "two words.txt"), "quoted-file-contents\n");
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync(OperatingSystem.IsWindows() ? "!type \"two words.txt\"" : "!cat \"two words.txt\"",
            TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => ReplHarness.LineAfter(screen, "two words.txt") == "quoted-file-contents"
                && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the file's contents on the next line, and a new prompt");
    }

    /// <summary>
    /// Shell commands run one after another each keep their command line above their output, with nothing between.
    /// </summary>
    /// <remarks>
    /// On Windows, pgtail started from PowerShell runs them with PowerShell and otherwise with cmd, so both run here.
    /// </remarks>
    /// <param name="fromPowerShell">Whether pgtail looks started from PowerShell.</param>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    [DataRow(false)]
    [DataRow(true)]
    public async Task ReplBangCommandsInARowKeepCommandAndOutputTogether(bool fromPowerShell)
    {
        using var environment = new TestEnvironment();
        if (fromPowerShell && OperatingSystem.IsWindows())
        {
            environment.Set("PSModulePath", Environment.GetEnvironmentVariable("PSModulePath"));
        }

        await using var pgtail = PgtailProcess.Start(environment, 100, 16, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        foreach (string? word in new[] { "first", "second", "third" })
        {
            await pgtail.Automator.TypeAsync($"!echo {word}", TestContext.CancellationToken);
            await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
            await pgtail.Automator.WaitUntilAsync(
                screen => ReplHarness.LineAfter(screen, $"echo {word}") == word && ReplHarness.PromptLine(screen) == "pgtail>",
                description: $"{word} under its command, and a new prompt");
        }

        using Hex1bTerminalSnapshot final = pgtail.Automator.CreateSnapshot();
        var rows = Enumerable.Range(0, final.Height).Select(final.GetLineTrimmed).ToList();
        int start = rows.FindIndex(row => row.EndsWith("echo first", StringComparison.Ordinal));
        // A command line reads "! echo first", or "pgtail> !echo first" when Enter came before the prompt redrew.
        string[] expected = ["echo first", "first", "echo second", "second", "echo third", "third", "pgtail>"];
        IEnumerable<string> shown = rows.Skip(start).Take(expected.Length).Select(row => row.Contains("echo", StringComparison.Ordinal)
            ? row[row.IndexOf("echo", StringComparison.Ordinal)..]
            : row);
        Assert.AreSequenceEqual(expected, shown, string.Join("\n", rows));
    }

    /// <summary>
    /// Text pasted at the REPL prompt goes into the line at the caret, its line breaks as spaces.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplPasteGoesIntoTheLine()
    {
        using var environment = new TestEnvironment();
        await using PgtailProcess pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("levels ", TestContext.CancellationToken);
        await pgtail.PasteAsync("error\nwarning\n", TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => ReplHarness.PromptLine(screen) == "pgtail> levels error warning",
            description: "the pasted text on the line");
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Filter set: ERROR WARNING");
    }

    /// <summary>
    /// Text pasted in tail mode goes into the command input, wherever the focus is.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailPasteGoesIntoTheInput()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4800, "LOG", "an entry to tail"));
        await using PgtailProcess pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken, "tail", "--file", log,
            "--since", "1h");
        await pgtail.Automator.WaitUntilTextAsync("an entry to tail");
        await pgtail.PasteAsync("level error", TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> level error",
            description: "the pasted text in the input");
    }

    /// <summary>
    /// Ctrl+C stops a stream that still has a long backlog to print.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TailStreamWithBacklogStopsAtCtrlC()
    {
        using var environment = new TestEnvironment();
        const int count = 400_000;
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
        DateTime start = DateTime.UtcNow.AddMinutes(-30);
        LogFiles.Append(log, Enumerable.Range(1, count).Select(i => LogFiles.Text(start.AddMilliseconds(i), 4700, "LOG", $"entry {i:D6}")));
        await using PgtailProcess pgtail = PgtailProcess.Start(environment, 100, 30, TestContext.CancellationToken, "tail", "--file", log,
            "--since", "1h", "--stream");
        await pgtail.Automator.WaitUntilTextAsync("LOG    : entry 0");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        Assert.AreEqual(0, await pgtail.WaitForExitAsync());
        using Hex1bTerminalSnapshot screen = pgtail.Automator.CreateSnapshot();
        Assert.IsFalse(screen.ContainsText($"entry {count:D6}"), "the stream stopped before the end of the backlog");
    }

    /// <summary>
    /// stats counts each duration logged in milliseconds or seconds, in any case, and skips a label with no duration.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplStatsCountsDurationsInEitherUnit()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
        DateTime time = DateTime.UtcNow.AddMinutes(-1);
        LogFiles.Append(log,
            LogFiles.Text(time, 4600, "LOG", "duration: 250.000 ms  statement: select 1"),
            LogFiles.Text(time, 4601, "LOG", "DURATION: 3 MS  statement: select 2"),
            LogFiles.Text(time, 4602, "LOG", "duration: 1.5 s  statement: select pg_sleep(1.5)"),
            LogFiles.Text(time, 4603, "LOG", "duration: unknown, then duration: 7ms  statement: select 3"),
            LogFiles.Text(time, 4604, "LOG", "duration: 12 min  statement: select 4"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 40, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync($"tail --file {log} --since 1h --stream", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("select 4");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("paused [postgresql.log]>");
        await pgtail.Automator.TypeAsync("stop", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => ReplHarness.PromptLine(screen) == "pgtail>", description: "the prompt");
        await pgtail.Automator.TypeAsync("stats", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Queries:  4") && screen.ContainsText("Average:  440.0ms")
                && screen.ContainsText("max:    1500.0ms"),
            description: "four durations: 250 ms, 3 ms, 1.5 s, and 7 ms");
    }

    /// <summary>
    /// clear clears the real terminal and shows the prompt at the top.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplClearClearsScreen()
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
    public async Task ReplTailThenQuitReturnsToPrompt()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
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
    /// Tail mode opened from the REPL asks the terminal to report the mouse, so clicks and the scrollbar reach it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplTailModeReportsMouse()
    {
        using var environment = new TestEnvironment();
        string log = Path.Join(environment.Root, "logs", "postgresql.log");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow.AddMinutes(-1), 4600, "LOG", "entry with the mouse on"));
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync($"tail --file {log} --since 1h", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.InAlternateScreen && screen.ContainsText("entry with the mouse on")
                && screen.MouseProtocolAnyEnabled && screen.MouseEncodingSgrEnabled,
            description: "tail mode with mouse reporting on");
    }

    /// <summary>
    /// config edit opens the built-in editor, and closing it returns to the prompt.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplConfigEditOpensEditorAndCloses()
    {
        using var environment = new TestEnvironment();
        // Wide enough for the title's path, which is long under a test's temp directory on Windows.
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken);
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
    /// Edits undone back to the saved text leave nothing unsaved, so Escape closes the editor at once.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplConfigEditUndoneEditClosesWithoutWarning()
    {
        using var environment = new TestEnvironment();
        // Wide enough for the title's path, which is long under a test's temp directory on Windows.
        await using var pgtail = PgtailProcess.Start(environment, 160, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");
        await pgtail.Automator.TypeAsync("config edit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => screen.InAlternateScreen && screen.ContainsText("config.toml"),
            description: "the editor");
        await pgtail.Automator.TypeAsync("x", TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("[modified]");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.Z, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilNoTextAsync("[modified]");
        await pgtail.Automator.EscapeAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => !screen.InAlternateScreen && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the prompt, with no unsaved changes to discard");
    }

    /// <summary>
    /// A misspelled setting is reported at startup, and the editor saves the file only once it is spelled right.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplConfigEditUnknownSettingNotSavedUntilFixed()
    {
        using var environment = new TestEnvironment();
        Directory.CreateDirectory(Path.GetDirectoryName(environment.Paths.ConfigFile)!);
        await File.WriteAllTextAsync(environment.Paths.ConfigFile, "[slow]\nwarning = 250\n\n[updates]\ncheck = false\n",
            TestContext.CancellationToken);
        await using var pgtail = PgtailProcess.Start(environment, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Unknown setting slow.warning, ignored.") && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the warning at startup");
        await pgtail.Automator.TypeAsync("config edit", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => screen.InAlternateScreen && screen.ContainsText("warning = 250"),
            description: "the editor");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.S, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Not saved: Unknown setting slow.warning");
        await pgtail.Automator.DownAsync(TestContext.CancellationToken);
        for (int i = 0; i < "warning".Length; i++)
        {
            await pgtail.Automator.DeleteAsync(TestContext.CancellationToken);
        }

        await pgtail.Automator.WaitUntilAsync(screen => screen.ContainsText(" = 250") && !screen.ContainsText("warning = 250"),
            description: "the misspelled name deleted");

        await pgtail.Automator.TypeAsync("warn", TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("warn = 250");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.S, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Saved config.toml");
        await pgtail.Automator.EscapeAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(screen => !screen.InAlternateScreen && ReplHarness.PromptLine(screen) == "pgtail>",
            description: "the prompt again");
        await pgtail.Automator.TypeAsync("slow", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Warning (yellow):      > 250ms");
    }

    /// <summary>
    /// connections --watch streams events on the real terminal until Ctrl+C, then sums up and gives the prompt back.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ReplConnectionsWatchStreamsUntilCtrlC()
    {
        using var environment = new TestEnvironment();
        (string? data, string? log) = DataDirectories.Create(environment.Root, "17", 5496);
        environment.Set("PGDATA", data);
        await using var pgtail = PgtailProcess.Start(environment, 200, 30, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("pgtail>");

        // Tailing the instance by its data directory makes it the one watched, whatever else runs on the machine.
        await pgtail.Automator.TypeAsync($"tail {data} --stream", TestContext.CancellationToken);
        await pgtail.Automator.EnterAsync(TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilTextAsync("Press Ctrl+C to stop");
        await pgtail.Automator.Ctrl().KeyAsync(Hex1bKey.C, TestContext.CancellationToken);
        await pgtail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Paused. Use 'stop' to stop tailing.")
                && ReplHarness.PromptLine(screen).StartsWith("paused [", StringComparison.Ordinal),
            description: "the paused prompt");
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
