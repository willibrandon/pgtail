using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using Hex1b;
using Hex1b.Automation;

namespace Pgtail.Tests;

/// <summary>
/// Runs the built <c>pgtail</c> executable in a terminal.
/// </summary>
/// <remarks>
/// Interactive use runs in a pseudo-terminal; one-shot commands run with their output piped to the terminal, as
/// scripts and shell completion run them. Unless the test wrote a configuration file, one turning off the startup
/// update check is written first, so tests never reach the network.
/// </remarks>
internal sealed class PgtailProcess : IAsyncDisposable
{
    private readonly Hex1bTerminal _terminal;
    private readonly CancellationTokenSource _stop;

    private PgtailProcess(
        TestEnvironment environment,
        Func<Hex1bTerminalBuilder, Hex1bTerminalBuilder> workload,
        int width,
        int height,
        CancellationToken cancellationToken)
    {
        if (!File.Exists(environment.Paths.ConfigFile))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(environment.Paths.ConfigFile)!);
            File.WriteAllText(environment.Paths.ConfigFile, "[updates]\ncheck = false\n");
        }

        _terminal = Record(workload(Hex1bTerminal.CreateBuilder()), environment)
            .WithHeadless()
            .WithDimensions(width, height)
            .Build();
        _stop = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        Exited = _terminal.RunAsync(_stop.Token);
        Automator = new Hex1bTerminalAutomator(_terminal, defaultTimeout: TimeSpan.FromSeconds(20));
    }

    /// <summary>
    /// The executable in pgtail's own build output, beside exactly the files its build put there.
    /// </summary>
    /// <remarks>
    /// The tests' output also holds a copy, but with the tests' own dependencies beside it, which could hide a file
    /// pgtail's build left out. The tests build to <c>tests/Pgtail.Tests/bin/CONFIGURATION/TFM</c> and pgtail to
    /// <c>src/Pgtail/bin/CONFIGURATION/TFM</c>.
    /// </remarks>
    public static string Executable { get; } = FindExecutable();

    /// <summary>
    /// Drives the terminal.
    /// </summary>
    public Hex1bTerminalAutomator Automator { get; }

    /// <summary>
    /// Completes with the process's exit code when it exits.
    /// </summary>
    public Task<int> Exited { get; }

    /// <summary>
    /// Starts pgtail interactively in a pseudo-terminal.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <param name="arguments">The arguments.</param>
    /// <returns>The running process.</returns>
    public static PgtailProcess Start(TestEnvironment environment, CancellationToken cancellationToken, params string[] arguments) =>
        Start(environment, 100, 30, cancellationToken, arguments);

    /// <summary>
    /// Starts pgtail interactively in a pseudo-terminal of a given size.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="width">The terminal width.</param>
    /// <param name="height">The terminal height.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <param name="arguments">The arguments.</param>
    /// <returns>The running process.</returns>
    public static PgtailProcess Start(
        TestEnvironment environment,
        int width,
        int height,
        CancellationToken cancellationToken,
        params string[] arguments) =>
        new(environment, builder => builder.WithPtyProcess(options =>
        {
            options.FileName = Executable;
            options.Arguments = arguments;
            options.WorkingDirectory = environment.Root;
            options.InheritEnvironment = false;
            options.Environment = Variables(environment);
        }), width, height, cancellationToken);

    /// <summary>
    /// Runs a one-shot pgtail command with its output piped to the terminal.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <param name="arguments">The arguments.</param>
    /// <returns>The running process.</returns>
    public static PgtailProcess Run(TestEnvironment environment, CancellationToken cancellationToken, params string[] arguments) =>
        new(environment, builder => builder.WithProcess(StartInfo(environment, new ProcessStartInfo(Executable, arguments))), 160, 40,
            cancellationToken);

    /// <summary>
    /// Runs a command line through the platform shell with its output piped to the terminal, for pipes into pgtail.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="commandLine">The command line; <c>{pgtail}</c> in it runs the built executable.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <returns>The running shell.</returns>
    public static PgtailProcess Shell(TestEnvironment environment, string commandLine, CancellationToken cancellationToken)
    {
        string command = commandLine.Replace("{pgtail}", $"\"{Executable}\"", StringComparison.Ordinal);
        // cmd reads its command line itself instead of by the C runtime's rules, which would escape the quotes around the
        // executable with backslashes; with /s it runs what is between the first and last quotes as written.
        ProcessStartInfo info = OperatingSystem.IsWindows()
            ? StartInfo(environment, new ProcessStartInfo("cmd.exe", $"/d /s /c \"{command}\""))
            : StartInfo(environment, new ProcessStartInfo("/bin/sh", ["-c", command]));
        return new(environment, builder => builder.WithProcess(info), 160, 40, cancellationToken);
    }

    /// <summary>
    /// Pastes text, as a terminal sends it: between the markers of a bracketed paste rather than as keys.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="cancellationToken">Cancels the send.</param>
    /// <returns>A task that completes when the text is sent.</returns>
    public Task PasteAsync(string text, CancellationToken cancellationToken) => SendAsync($"\e[200~{text}\e[201~", cancellationToken);

    /// <summary>
    /// Sends input as the terminal would, such as a mouse report the automator has no step for.
    /// </summary>
    /// <param name="input">The input.</param>
    /// <param name="cancellationToken">Cancels the send.</param>
    /// <returns>A task that completes when the input is sent.</returns>
    public Task SendAsync(string input, CancellationToken cancellationToken) =>
        _terminal.SendInputAsync(Encoding.UTF8.GetBytes(input), cancellationToken);

    /// <summary>
    /// Waits for the process to exit and returns its exit code.
    /// </summary>
    /// <returns>The exit code.</returns>
    public Task<int> WaitForExitAsync() => Exited.WaitAsync(TimeSpan.FromSeconds(20));

    /// <summary>
    /// Stops the terminal and the process, if still running.
    /// </summary>
    /// <returns>A task that completes when the terminal has stopped.</returns>
    public async ValueTask DisposeAsync()
    {
        if (!Exited.IsCompleted)
        {
            await _stop.CancelAsync();
            try
            {
                _ = await Exited.WaitAsync(TimeSpan.FromSeconds(20));
            }
            catch (OperationCanceledException)
            {
                // The test ended before the process did.
            }
        }

        await _terminal.DisposeAsync();
        _stop.Dispose();
    }

    // With PGTAIL_TEST_RECORDINGS set, as CI sets it, each terminal is recorded there in asciinema format, named after
    // the test's directory, so a failure on a platform no one runs locally can be played back.
    private static Hex1bTerminalBuilder Record(Hex1bTerminalBuilder builder, TestEnvironment environment) =>
        Environment.GetEnvironmentVariable("PGTAIL_TEST_RECORDINGS") is { Length: > 0 } directory
            ? builder.WithAsciinemaRecording(Path.Join(Directory.CreateDirectory(directory).FullName,
                Path.GetFileName(environment.Root) + ".cast"))
            : builder;

    private static string FindExecutable()
    {
        var output = new DirectoryInfo(Path.TrimEndingDirectorySeparator(AppContext.BaseDirectory));
        DirectoryInfo configuration = output.Parent!;
        string repository = configuration.Parent!.Parent!.Parent!.Parent!.FullName;
        string executable = Path.Join(repository, "src", "Pgtail", "bin", configuration.Name, output.Name,
            OperatingSystem.IsWindows() ? "pgtail.exe" : "pgtail");
        return File.Exists(executable) ? executable : throw new FileNotFoundException("pgtail has not been built", executable);
    }

    private static ProcessStartInfo StartInfo(TestEnvironment environment, ProcessStartInfo info)
    {
        info.WorkingDirectory = environment.Root;
        info.Environment.Clear();
        foreach ((string name, string value) in Variables(environment))
        {
            info.Environment[name] = value;
        }

        return info;
    }

    private static Dictionary<string, string> Variables(TestEnvironment environment)
    {
        Dictionary<string, string> variables = environment.ProcessVariables();
        variables["TERM"] = "xterm-256color";
        variables["DOTNET_ROOT"] = Path.GetFullPath(Path.Join(RuntimeEnvironment.GetRuntimeDirectory(), "..", "..", ".."));
        variables["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1";
        if (OperatingSystem.IsWindows())
        {
            string[] inherited = ["SystemRoot", "SystemDrive", "ComSpec", "PATHEXT", "TEMP", "TMP", "WINDIR"];
            foreach (string name in inherited.Where(name => Environment.GetEnvironmentVariable(name) is not null))
            {
                variables[name] = Environment.GetEnvironmentVariable(name)!;
            }

            variables["USERPROFILE"] = environment.Home;
        }

        return variables;
    }
}
