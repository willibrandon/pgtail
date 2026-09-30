using System.ComponentModel;
using System.Diagnostics;

namespace Pgtail.Cli;

/// <summary>
/// Runs <c>!command</c> lines in the user's shell with the terminal attached.
/// </summary>
internal static class ShellRunner
{
    /// <summary>
    /// Runs a command line and waits for it, keeping Ctrl+C for the command rather than pgtail.
    /// </summary>
    /// <remarks>
    /// Unix runs it with <c>sh -c</c>. Windows runs it with PowerShell when pgtail was started from PowerShell and
    /// with <c>cmd /c</c> otherwise.
    /// </remarks>
    /// <param name="command">The command line.</param>
    /// <param name="error">Receives a message when the shell cannot be started.</param>
    public static void Run(string command, Action<string> error)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(error);
        ProcessStartInfo start = OperatingSystem.IsWindows() ? WindowsShell(command)
            : new ProcessStartInfo("/bin/sh") { ArgumentList = { "-c", command } };
        start.UseShellExecute = false;
        ConsoleCancelEventHandler ignore = (_, e) => e.Cancel = true;
        Console.CancelKeyPress += ignore;
        try
        {
            using var process = Process.Start(start);
            process?.WaitForExit();
        }
        catch (Win32Exception exception)
        {
            error($"Shell error: {exception.Message}");
        }
        finally
        {
            Console.CancelKeyPress -= ignore;
        }
    }

    private static ProcessStartInfo WindowsShell(string command)
    {
        if (StartedFromPowerShell())
        {
            return new ProcessStartInfo("powershell") { ArgumentList = { "-NoProfile", "-Command", command } };
        }

        // cmd reads its command line itself instead of by the C runtime's rules, which escape quotes with backslashes,
        // so the command goes in as typed; with /s, cmd runs what is between the first and last quotes, as Node.js runs
        // shell commands.
        return new ProcessStartInfo(Environment.GetEnvironmentVariable("ComSpec") ?? "cmd.exe", $"/d /s /c \"{command}\"");
    }

    private static bool StartedFromPowerShell()
    {
        string? shell = Environment.GetEnvironmentVariable("PSModulePath");
        return shell is not null && Environment.GetEnvironmentVariable("PROMPT") is null;
    }
}
