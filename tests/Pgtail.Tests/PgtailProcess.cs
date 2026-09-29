using System.Diagnostics;
using System.Runtime.InteropServices;
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

        _terminal = workload(Hex1bTerminal.CreateBuilder())
            .WithHeadless()
            .WithDimensions(width, height)
            .Build();
        _stop = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        Exited = _terminal.RunAsync(_stop.Token);
        Automator = new Hex1bTerminalAutomator(_terminal, defaultTimeout: TimeSpan.FromSeconds(20));
    }

    /// <summary>
    /// The built executable.
    /// </summary>
    public static string Executable { get; } = Path.Combine(AppContext.BaseDirectory, OperatingSystem.IsWindows() ? "pgtail.exe"
        : "pgtail");

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
        new(environment, builder => builder.WithProcess(StartInfo(environment, Executable, arguments)), 160, 40, cancellationToken);

    /// <summary>
    /// Runs a command line through the platform shell with its output piped to the terminal, for pipes into pgtail.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="commandLine">The command line; <c>{pgtail}</c> in it runs the built executable.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <returns>The running shell.</returns>
    public static PgtailProcess Shell(TestEnvironment environment, string commandLine, CancellationToken cancellationToken)
    {
        var command = commandLine.Replace("{pgtail}", $"\"{Executable}\"", StringComparison.Ordinal);
        var info = OperatingSystem.IsWindows()
            ? StartInfo(environment, "cmd.exe", ["/d", "/c", command])
            : StartInfo(environment, "/bin/sh", ["-c", command]);
        return new(environment, builder => builder.WithProcess(info), 160, 40, cancellationToken);
    }

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

    private static ProcessStartInfo StartInfo(TestEnvironment environment, string fileName, IEnumerable<string> arguments)
    {
        var info = new ProcessStartInfo(fileName, arguments) { WorkingDirectory = environment.Root };
        info.Environment.Clear();
        foreach (var (name, value) in Variables(environment))
        {
            info.Environment[name] = value;
        }

        return info;
    }

    private static Dictionary<string, string> Variables(TestEnvironment environment)
    {
        var variables = environment.ProcessVariables();
        variables["TERM"] = "xterm-256color";
        variables["DOTNET_ROOT"] = Path.GetFullPath(Path.Combine(RuntimeEnvironment.GetRuntimeDirectory(), "..", "..", ".."));
        variables["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1";
        if (OperatingSystem.IsWindows())
        {
            foreach (var name in new[] { "SystemRoot", "SystemDrive", "ComSpec", "PATHEXT", "TEMP", "TMP", "WINDIR" })
            {
                if (Environment.GetEnvironmentVariable(name) is { } value)
                {
                    variables[name] = value;
                }
            }

            variables["USERPROFILE"] = environment.Home;
        }

        return variables;
    }
}
