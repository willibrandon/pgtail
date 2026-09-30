using System.Globalization;
using Hex1b.Automation;
using Hex1b.Input;
using Hex1b.Theming;

namespace Pgtail.Tests;

/// <summary>
/// Tail mode's log, keys, mouse, commands, and status bar, driven through a headless terminal.
/// </summary>
[TestClass]
public sealed class TailScreenTests
{
    private static readonly Hex1bColor SelectionBackground = Hex1bColor.FromRgb(38, 79, 120);

    /// <summary>
    /// Supplies cancellation for the terminal.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// The screen shows the key hints, the entries, and the counts in the status bar.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Start_ExistingEntries_ShowsLogAndStatus()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "database system is ready to accept connections"),
            ("ERROR", "relation \"users\" does not exist"), ("WARNING", "checkpoints are occurring too frequently"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("q Quit")
                && screen.ContainsText("relation \"users\" does not exist")
                && TailHarness.Status(screen).Contains("E:1 W:1 | 3 lines", StringComparison.Ordinal)
                && TailHarness.Status(screen).Contains("postgresql.log", StringComparison.Ordinal),
            description: "header, entries, and status");
    }

    /// <summary>
    /// Lines written after the screen opens appear at the bottom while following.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task AppendedLines_WhileFollowing_AppearAtBottom()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(0, 40).Select(i => ("LOG", $"existing line {i}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.LogRows(screen)[^1].EndsWith("existing line 39",
            StringComparison.Ordinal),
            description: "the last existing line at the bottom");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 200, "ERROR", "a new error arrived"));
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.LogRows(screen)[^1].EndsWith("a new error arrived", StringComparison.Ordinal)
                && TailHarness.Status(screen).StartsWith("FOLLOW | E:1 W:0 | 41 lines", StringComparison.Ordinal),
            description: "the new line at the bottom and counted");
    }

    /// <summary>
    /// Moving up highlights a row and stops following until f.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task K_MovesCursorUp_HighlightsRowAndPauses()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(0, 30).Select(i => ("LOG", $"line number {i}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("line number 29");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("k", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal)
                && RowOf(screen, "line number 28") is { } row
                && screen.GetCell(40, row).Background is { } background && background.R == 38 && background.G == 79,
            description: "the row above the last highlighted and the status paused");
        await tail.Automator.TypeAsync("f", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).StartsWith("FOLLOW", StringComparison.Ordinal)
                && !screen.HasBackgroundColor(SelectionBackground),
            description: "following again with nothing highlighted");
    }

    /// <summary>
    /// g jumps to the first entry.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task G_JumpsToTop()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(0, 60).Select(i => ("LOG", $"entry {i:D2}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("entry 59");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("g", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.LogRows(screen)[0].EndsWith("entry 00", StringComparison.Ordinal) && !screen.ContainsText("entry 59"),
            description: "the first entry at the top");
        await tail.Automator.TypeAsync("G", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.LogRows(screen)[^1].EndsWith("entry 59", StringComparison.Ordinal)
                && TailHarness.Status(screen).StartsWith("FOLLOW", StringComparison.Ordinal),
            description: "back at the last entry and following");
    }

    /// <summary>
    /// Keys typed faster than the screen reads them each take effect.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TypedKeys_ArrivingTogether_EachMoveTheCursor()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(0, 30).Select(i => ("LOG", $"row {i:D2}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("row 29");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.SequenceAsync(builder => builder.Type("kkkk"), "four ups at once", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => RowOf(screen, "row 25") is { } row && screen.GetCell(40, row).Background is { R: 38, G: 79 },
            description: "the cursor four rows up");
    }

    /// <summary>
    /// Pausing keeps new entries out of the log and counts them; following shows them.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task P_ThenNewEntries_CountsThemUntilFollow()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "before pausing"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("before pausing");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("p", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal),
            description: "paused");
        LogFiles.Append(log, LogFiles.Text(DateTime.UtcNow, 300, "LOG", "while paused one"),
            LogFiles.Text(DateTime.UtcNow, 301, "LOG", "while paused two"));
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).StartsWith("PAUSED +2 new", StringComparison.Ordinal)
                && !screen.ContainsText("while paused"),
            description: "two new entries counted but not shown");
        await tail.Automator.TypeAsync("f", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("while paused one") && screen.ContainsText("while paused two")
                && TailHarness.Status(screen).StartsWith("FOLLOW", StringComparison.Ordinal),
            description: "the paused entries shown after following");
    }

    /// <summary>
    /// The level command redraws the log with only the chosen levels.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task LevelCommand_Error_ShowsOnlyErrors()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "routine message"), ("ERROR", "first failure"), ("LOG", "another routine"),
            ("ERROR", "second failure"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("second failure");
        await tail.RunAsync("level error", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("first failure") && screen.ContainsText("second failure")
                && !screen.ContainsText("routine")
                && TailHarness.Status(screen).Contains("levels:ERROR", StringComparison.Ordinal),
            description: "only errors, and the level in the status bar");
    }

    /// <summary>
    /// Lines with Debian and Ubuntu's <c>log_line_prefix</c>, <c>'%m [%p] %q%u@%d '</c>, filter by level like any other.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task DebianPrefix_LevelCommand_KeepsErrorWithStatement()
    {
        using var environment = new TestEnvironment();
        var path = Path.Combine(environment.Root, "logs", "postgresql-18-main.log");
        var time = DateTime.UtcNow.AddMinutes(-5).ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture);
        LogFiles.Append(path,
            $"{time} UTC [4200] [unknown]@[unknown] LOG:  connection received: host=::1 port=50000",
            $"{time} UTC [4200] alice@orders ERROR:  division by zero",
            $"{time} UTC [4200] alice@orders STATEMENT:  select 1/0",
            $"{time} UTC [17] LOG:  checkpoint starting: time");
        await using var tail = await TailHarness.StartAsync(environment, path, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("LOG    : connection received: host=::1 port=50000")
                && TailHarness.Status(screen).Contains("E:1 W:0 | 4 lines", StringComparison.Ordinal),
            description: "the entries read with their levels");
        await tail.RunAsync("level error", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.LogRows(screen).Where(row => row.Length > 0).ToList() is [var error, var statement]
                && error.EndsWith("[4200 ] ERROR  : division by zero", StringComparison.Ordinal)
                && statement == "STATEMENT:  select 1/0",
            description: "the error with its statement, and nothing else");
    }

    /// <summary>
    /// An error's DETAIL and STATEMENT lines stay with it: a level filter keeps them, and they count as one error.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task LevelCommand_ErrorWithDetail_KeepsContinuationLines()
    {
        using var environment = new TestEnvironment();
        var path = Path.Combine(environment.Root, "logs", "postgresql.log");
        var time = DateTime.UtcNow.AddMinutes(-5);
        LogFiles.Append(path,
            LogFiles.Text(time, 2001, "ERROR", "duplicate key value violates unique constraint \"t_pkey\""),
            LogFiles.Text(time, 2001, "DETAIL", "Key (id)=(1) already exists."),
            LogFiles.Text(time, 2001, "STATEMENT", "insert into t values (1)"),
            LogFiles.Text(time.AddSeconds(1), 2002, "LOG", "checkpoint starting: time"));
        await using var tail = await TailHarness.StartAsync(environment, path, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("checkpoint starting")
                && TailHarness.Status(screen).Contains("E:1 W:0 | 4 lines", StringComparison.Ordinal),
            description: "one error with its two continuation lines, and one other entry");
        await tail.RunAsync("level error", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.LogRows(screen).Where(row => row.Length > 0).ToList() is [var error, var detail, var statement]
                && error.EndsWith("ERROR  : duplicate key value violates unique constraint \"t_pkey\"", StringComparison.Ordinal)
                && detail == "DETAIL:  Key (id)=(1) already exists."
                && statement == "STATEMENT:  insert into t values (1)"
                && !screen.ContainsText("checkpoint starting"),
            description: "the error with its detail and statement, and nothing else");
    }

    /// <summary>
    /// A regex filter keeps matching entries, and clear brings the rest back.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task FilterCommand_ThenClear_RestoresEntries()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "connection authorized: user=alice"), ("LOG", "checkpoint starting: time"),
            ("LOG", "connection authorized: user=bob"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("user=bob");
        await tail.RunAsync("filter /connection/", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("user=alice") && screen.ContainsText("user=bob") && !screen.ContainsText("checkpoint starting"),
            description: "only matching entries");
        await tail.RunAsync("clear", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("checkpoint starting") && screen.ContainsText("user=alice"),
            description: "every entry again");
    }

    /// <summary>
    /// An unknown command is reported in the log.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task UnknownCommand_ShowsError()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("bogus", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("✗ Unknown command: bogus. Type 'help' for commands.");
    }

    /// <summary>
    /// A command name typed partly shows the rest as a suggestion, and Right accepts it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Input_PartialCommand_SuggestsRest()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TypeAsync("conn", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> connections",
            description: "the suggestion completing the command");
        await tail.Automator.RightAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync(" --history", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> connections --history",
            description: "the accepted suggestion with more typed");
    }

    /// <summary>
    /// The terminal's cursor stays just after the typed text, and the suggestion follows it in the same place each key.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Input_Suggestion_FollowsTheCursor()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        foreach (var (typed, shown) in new[] { ("t", "tail> theme"), ("th", "tail> theme"), ("the", "tail> theme") })
        {
            await tail.Automator.TypeAsync(typed[^1..], TestContext.CancellationToken);
            await tail.Automator.WaitUntilAsync(
                screen => TailHarness.Input(screen) == shown && TailHarness.InputCursor(screen) == "tail> ".Length + typed.Length,
                description: $"the cursor after '{typed}' with the rest of theme after it");
        }
    }

    /// <summary>
    /// The shell's line keys work in the input: Ctrl+W, Ctrl+A, Ctrl+E, Ctrl+U, and Ctrl+Y.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Input_LineKeys_EditTheLine()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TypeAsync("level error ", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen).StartsWith("tail> level error", StringComparison.Ordinal),
            description: "the line typed");
        // As in readline, the space before the cut word stays; at the end of the line the first level is suggested after it.
        await tail.Automator.Ctrl().KeyAsync(Hex1bKey.W, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Input(screen) == "tail> level debug" && TailHarness.InputCursor(screen) == "tail> level ".Length,
            description: "the last word cut, with the suggestion after the caret");
        await tail.Automator.Ctrl().KeyAsync(Hex1bKey.A, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Input(screen) == "tail> level" && TailHarness.InputCursor(screen) == "tail> ".Length,
            description: "the cursor at the start, with no suggestion");
        await tail.Automator.Ctrl().KeyAsync(Hex1bKey.E, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.InputCursor(screen) == "tail> level ".Length,
            description: "the cursor at the end");
        await tail.Automator.Ctrl().KeyAsync(Hex1bKey.U, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail>", description: "the line cut");
        await tail.Automator.Ctrl().KeyAsync(Hex1bKey.Y, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> level debug", description: "the cut text pasted");
    }

    /// <summary>
    /// The input keeps the focus after a command, so Up there recalls it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Input_UpArrow_RecallsPreviousCommand()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("ERROR", "a failure"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("errors", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => screen.ContainsText("Error Statistics") && TailHarness.Input(screen) == "tail>",
            description: "the output and an empty input");
        await tail.Automator.UpAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> errors",
            description: "the previous command");
    }

    /// <summary>
    /// Commands typed one after another each reach the input, since running one keeps the input focused.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Input_AfterCommand_TakesTheNextCommand()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("ERROR", "a failure"), ("LOG", "routine"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TypeAsync("level error", TestContext.CancellationToken);
        await tail.Automator.EnterAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).Contains("levels:ERROR", StringComparison.Ordinal)
            && TailHarness.Input(screen) == "tail>", description: "the filter applied and an empty input");
        await tail.Automator.TypeAsync("level all", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> level all",
            description: "the next command typed in the input");
        await tail.Automator.EnterAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).Contains("levels:ALL", StringComparison.Ordinal),
            description: "the second command run");
    }

    /// <summary>
    /// levels works in tail mode as at the REPL prompt, as another name for level.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Levels_IsLevelInTailMode()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("ERROR", "a failure"), ("LOG", "routine"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("levels error", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).Contains("levels:ERROR", StringComparison.Ordinal) && !screen.ContainsText("routine"),
            description: "the level filter set");
    }

    /// <summary>
    /// Text typed on the log that is not one of its keys goes to the input.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Log_TypedCommand_GoesToTheInput()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.EscapeAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("since 5m", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> since 5m",
            description: "the command in the input");
    }

    /// <summary>
    /// help writes its text into the log, where the end shows at once and the rest is a scroll up away.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Help_WritesIntoLog()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TypeAsync("help", TestContext.CancellationToken);
        await tail.Automator.EnterAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("stop/exit/q  Exit tail mode") && TailHarness.Input(screen) == "tail>"
                && TailHarness.Status(screen).Contains("| 1 lines |", StringComparison.Ordinal),
            description: "the end of the help in the log, with only the entry counted");
        await tail.Automator.PageUpAsync(TestContext.CancellationToken);
        await tail.Automator.PageUpAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Navigation");
    }

    /// <summary>
    /// ? opens the key help, and Escape closes it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task QuestionMark_ShowsHelp_EscapeCloses()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken, height: 50);
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("?", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("pgtail Keybindings") && screen.ContainsText("Press Escape, q, or ? to close"),
            description: "the help overlay");
        await tail.Automator.EscapeAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilNoTextAsync("pgtail Keybindings");
        await tail.Automator.TypeAsync("k", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal)
            || screen.HasBackgroundColor(SelectionBackground),
            description: "keys reach the log after closing help");
    }

    /// <summary>
    /// Visual line mode selects rows and y copies them.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task VisualLineMode_Yank_CopiesSelectedRows()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "first"), ("LOG", "second"), ("LOG", "third"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("third");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("k", TestContext.CancellationToken);
        await tail.Automator.TypeAsync("V", TestContext.CancellationToken);
        await tail.Automator.TypeAsync("j", TestContext.CancellationToken);
        var rows = TailHarness.LogRows(tail.Automator.CreateSnapshot());
        var expected = rows.First(row => row.EndsWith("second", StringComparison.Ordinal)).Length
            + 1 + rows.First(row => row.EndsWith("third", StringComparison.Ordinal)).Length;
        await tail.Automator.TypeAsync("y", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync($"Copied {expected} characters");
    }

    /// <summary>
    /// Clicking a row selects it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Click_OnRow_SelectsIt()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "alpha"), ("LOG", "bravo"), ("LOG", "charlie"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("charlie");
        var row = RowOf(tail.Automator.CreateSnapshot(), "alpha")!.Value;
        await tail.Automator.ClickAtAsync(10, row, ct: TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.GetCell(60, row).Background is { R: 38, G: 79, B: 120 }
                && screen.GetCell(60, row + 1).Background is not { R: 38, G: 79 },
            description: "the clicked row highlighted");
    }

    /// <summary>
    /// A time filter's whole range loads: the newest lines first, then the older ones, and the status counts every line.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task TimeFilter_LongLog_LoadsWholeRangeAndCountsIt()
    {
        using var environment = new TestEnvironment();
        var count = Tail.TailScreen.BacklogLines + 12_345;
        var log = WriteLog(environment, [.. Enumerable.Range(1, count).Select(i => ("LOG", $"entry {i:D6}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).Contains($"| {count.ToString("N0", CultureInfo.InvariantCulture)} lines |",
                    StringComparison.Ordinal)
                && screen.ContainsText($"entry {count:D6}"),
            description: "every line counted, the newest on screen");
        await tail.Automator.EscapeAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("g", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("entry 000001");
    }

    /// <summary>
    /// Pressing the scrollbar jumps to that point of the log, and dragging it to the bottom follows again.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Scrollbar_PressAndDrag_Scrolls()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(1, 100).Select(i => ("LOG", $"entry {i:D3}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("entry 100");
        var scrollbar = tail.Automator.CreateSnapshot().Width - 1;
        await tail.Automator.ClickAtAsync(scrollbar, 2, ct: TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("entry 001") && TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal),
            description: "the first entries, paused");
        await tail.Automator.DragAsync(scrollbar, 2, scrollbar, 20, ct: TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("entry 100") && TailHarness.Status(screen).StartsWith("FOLLOW", StringComparison.Ordinal),
            description: "the newest entries, following");
    }

    /// <summary>
    /// The input's block cursor blinks while the input has focus and stays on while the log has it.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task InputCursor_BlinksWhenFocused_SolidOtherwise()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.InputCursor(screen) == "tail> ".Length, description: "the cursor on");
        await tail.Automator.WaitUntilAsync(screen => TailHarness.InputCursor(screen) is null, description: "the cursor blinking off");
        await tail.Automator.WaitUntilAsync(screen => TailHarness.InputCursor(screen) is not null, description: "the cursor back on");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.InputCursor(screen) is not null,
            description: "the cursor with the log focused");
        for (var sample = 0; sample < 6; sample++)
        {
            await Task.Delay(Tail.TailInput.BlinkInterval / 2, TestContext.CancellationToken);
            using var screen = tail.Automator.CreateSnapshot();
            Assert.AreEqual("tail> ".Length, TailHarness.InputCursor(screen), "the cursor stays on while the log has focus");
        }
    }

    /// <summary>
    /// Dragging across text selects exactly that text.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Drag_AcrossText_SelectsIt()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "alpha bravo charlie"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("alpha bravo charlie");
        using (var screen = tail.Automator.CreateSnapshot())
        {
            var row = RowOf(screen, "alpha")!.Value;
            var start = screen.GetLineTrimmed(row).IndexOf("bravo", StringComparison.Ordinal);
            await tail.Automator.DragAsync(start, row, start + 4, row, ct: TestContext.CancellationToken);
            await tail.Automator.WaitUntilAsync(
                current => current.GetCell(start, row).Background is { R: 38, G: 79 }
                    && current.GetCell(start + 4, row).Background is { R: 38, G: 79 }
                    && current.GetCell(start - 1, row).Background is not { R: 38, G: 79 }
                    && current.GetCell(start + 6, row).Background is not { R: 38, G: 79 },
                description: "just 'bravo' selected");
        }
    }

    /// <summary>
    /// Scrolling the mouse wheel up leaves the end and pauses.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task MouseWheelUp_ScrollsBackAndPauses()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, [.. Enumerable.Range(0, 60).Select(i => ("LOG", $"wheel {i:D2}"))]);
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("wheel 59");
        await tail.Automator.MouseMoveToAsync(20, 10, TestContext.CancellationToken);
        await tail.Automator.ScrollUpAsync(2, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => !screen.ContainsText("wheel 59") && TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal),
            description: "scrolled back and paused");
    }

    /// <summary>
    /// Levels are drawn in their colors and attributes: errors bold.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ErrorLevel_IsDrawnBoldAndColored()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("ERROR", "something failed"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("something failed");
        using var screen = tail.Automator.CreateSnapshot();
        var row = RowOf(screen, "something failed")!.Value;
        var column = screen.GetLineTrimmed(row).IndexOf("ERROR", StringComparison.Ordinal);
        var cell = screen.GetCell(column, row);
        Assert.IsTrue(cell.IsBold, "ERROR should be bold");
        Assert.IsNotNull(cell.Foreground, "ERROR should be colored");
    }

    /// <summary>
    /// With <c>NO_COLOR</c> the log keeps attributes but has no colors.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task NoColor_DrawsAttributesWithoutColors()
    {
        using var environment = new TestEnvironment(new Dictionary<string, string?> { ["NO_COLOR"] = "1" });
        var log = WriteLog(environment, ("ERROR", "something failed"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("something failed");
        using var screen = tail.Automator.CreateSnapshot();
        var row = RowOf(screen, "something failed")!.Value;
        var line = screen.GetLineTrimmed(row);
        var column = line.IndexOf("ERROR", StringComparison.Ordinal);
        Assert.IsTrue(screen.GetCell(column, row).IsBold, "ERROR should stay bold");
        for (var x = 0; x < line.Length; x++)
        {
            Assert.IsNull(screen.GetCell(x, row).Foreground, $"column {x} should have no color");
        }
    }

    /// <summary>
    /// A row longer than the view scrolls sideways when the cursor moves to its end.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Dollar_OnLongRow_ScrollsToItsEnd()
    {
        using var environment = new TestEnvironment();
        var columns = string.Join(", ", Enumerable.Range(0, 30).Select(i => $"column_{i}"));
        var log = WriteLog(environment, ("LOG", $"statement: SELECT {columns} FROM wide_table END_OF_ROW"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("statement: SELECT column_0");
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("k", TestContext.CancellationToken);
        await tail.Automator.TypeAsync("$", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("END_OF_ROW") && !screen.ContainsText("statement: SELECT"),
            description: "the end of the row in view");
        await tail.Automator.TypeAsync("0", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("statement: SELECT column_0") && !screen.ContainsText("END_OF_ROW"),
            description: "the start of the row in view");
    }

    /// <summary>
    /// export writes the shown entries to a file.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ExportCommand_WritesShownEntries()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "keep this one"), ("ERROR", "and this error"));
        var output = Path.Combine(environment.Root, "exported.log");
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken, width: 160);
        await tail.Automator.WaitUntilTextAsync("and this error");
        await tail.RunAsync($"export {output}", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Exported 2 entries");
        var text = await File.ReadAllTextAsync(output, TestContext.CancellationToken);
        Assert.Contains("keep this one", text);
        Assert.Contains("and this error", text);
    }

    /// <summary>
    /// A time written in a named zone shows as written, and JSON export keeps its offset.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ZoneWrittenInLog_ShowsTimeAsWrittenAndExportsOffset()
    {
        using var environment = new TestEnvironment();
        var path = Path.Combine(environment.Root, "logs", "postgresql.log");
        var written = DateTime.UtcNow.AddHours(-7).AddMinutes(-5);
        var stamp = written.ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture);
        LogFiles.Append(path, $"{stamp} PDT [3001] ERROR:  relation \"missing_table\" does not exist");
        var output = Path.Combine(environment.Root, "exported.json");
        await using var tail = await TailHarness.StartAsync(environment, path, TestContext.CancellationToken, width: 160);
        await tail.Automator.WaitUntilTextAsync($"{stamp[11..]} [3001 ] ERROR  : relation \"missing_table\" does not exist");
        await tail.RunAsync($"export --format json {output}", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Exported 1 entries");
        var json = await File.ReadAllTextAsync(output, TestContext.CancellationToken);
        Assert.Contains($"\"timestamp\": \"{stamp.Replace(' ', 'T')}000-07:00\"", json);
    }

    /// <summary>
    /// Tailing a server's file shows the version and port the server logged at startup.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ServerStartupLines_ShowVersionAndPortInStatus()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment,
            ("LOG", "starting PostgreSQL 17.2 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 14.2.1, 64-bit"),
            ("LOG", "listening on IPv4 address \"127.0.0.1\", port 5544"),
            ("LOG", "database system is ready to accept connections"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).EndsWith("| PG17.2:5544", StringComparison.Ordinal),
            description: "the logged version and port");
    }

    /// <summary>
    /// slow colors the queries slower than its threshold in the log, the whole message in one slow query color.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task SlowCommand_ColorsSlowQueries()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "duration: 850.000 ms  statement: SELECT count(*) FROM orders WHERE id = 42"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken, width: 120);
        await tail.Automator.WaitUntilTextAsync("SELECT count(*) FROM orders");
        await tail.RunAsync("slow 200", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => TailHarness.Status(screen).Contains("slow:>200ms", StringComparison.Ordinal)
                && RowOf(screen, "SELECT count(*)") is { } row
                && screen.GetLineTrimmed(row).IndexOf("duration", StringComparison.Ordinal) is var first and > 0
                && screen.GetCell(first, row) is { IsBold: true, Foreground: { } color }
                && screen.GetCell(screen.GetLineTrimmed(row).Length - 1, row) is { IsBold: true, Foreground: { } last }
                && last.Equals(color),
            description: "the whole message in the slow query color");
    }

    /// <summary>
    /// help lists the commands, help keys the keys, and help with a command, or the command with help, its usage.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task HelpCommands_ShowCommandsKeysAndUsage()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken, height: 60);
        await tail.RunAsync("help", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("help keys    Show keybinding reference") && screen.ContainsText("stop/exit/q  Exit tail mode"),
            description: "the command list");
        await tail.RunAsync("help keys", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Escape / q       Close help");
        await tail.RunAsync("help level", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Usage: level <level>[+|-] [level2...]") && screen.ContainsText("Aliases: e=error"),
            description: "the level command's usage");
        await tail.RunAsync("filter ?", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Usage: filter");
    }

    /// <summary>
    /// The pause and follow commands switch the status like the p and f keys.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task PauseAndFollowCommands_SwitchStatus()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("pause", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).StartsWith("PAUSED", StringComparison.Ordinal),
            description: "paused");
        await tail.RunAsync("follow", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Status(screen).StartsWith("FOLLOW", StringComparison.Ordinal),
            description: "following");
    }

    /// <summary>
    /// theme, set, and notify work from tail mode, and set saves the configuration.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task ThemeSetNotifyCommands_Work()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("theme monokai", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("✓ Switched to theme monokai");
        await tail.RunAsync("set slow.warn 50", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(
            screen => screen.ContainsText("Set slow.warn = 50")
                && TailHarness.Status(screen).Contains("slow:>50ms", StringComparison.Ordinal),
            description: "the setting applied");
        await tail.RunAsync("notify", TestContext.CancellationToken);
        await tail.Automator.WaitUntilTextAsync("Notifications: disabled");
        var config = await File.ReadAllTextAsync(environment.Paths.ConfigFile, TestContext.CancellationToken);
        Assert.Contains("warn = 50", config);
        Assert.Contains("name = \"monokai\"", config);
    }

    /// <summary>
    /// The stop command leaves tail mode.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task StopCommand_LeavesTailMode()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.RunAsync("stop", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(_ => tail.Stopped, description: "tail mode stopped");
    }

    /// <summary>
    /// q typed at the prompt is text, like any other key, until Enter runs it as the q command.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Q_AtPrompt_IsTextUntilEnter()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TypeAsync("q", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(screen => TailHarness.Input(screen) == "tail> q" && !tail.Stopped,
            description: "q in the prompt, tail mode still running");
        await tail.Automator.EnterAsync(TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(_ => tail.Stopped, description: "tail mode stopped by the q command");
    }

    /// <summary>
    /// q in the log leaves tail mode.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Q_InLog_LeavesTailMode()
    {
        using var environment = new TestEnvironment();
        var log = WriteLog(environment, ("LOG", "hello"));
        await using var tail = await TailHarness.StartAsync(environment, log, TestContext.CancellationToken);
        await tail.Automator.TabAsync(TestContext.CancellationToken);
        await tail.Automator.TypeAsync("q", TestContext.CancellationToken);
        await tail.Automator.WaitUntilAsync(_ => tail.Stopped, description: "tail mode stopped");
    }

    private static string WriteLog(TestEnvironment environment, params (string Level, string Message)[] entries)
    {
        var path = Path.Combine(environment.Root, "logs", "postgresql.log");
        var start = DateTime.UtcNow.AddMinutes(-10);
        LogFiles.Append(path, entries.Select((entry, index) => LogFiles.Text(start.AddSeconds(index), 1000
            + index, entry.Level, entry.Message)));
        return path;
    }

    private static int? RowOf(Hex1bTerminalSnapshot screen, string text)
    {
        for (var row = 0; row < screen.Height; row++)
        {
            if (screen.GetLineTrimmed(row).Contains(text, StringComparison.Ordinal))
            {
                return row;
            }
        }

        return null;
    }
}
