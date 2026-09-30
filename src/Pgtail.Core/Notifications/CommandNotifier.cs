using System.ComponentModel;
using System.Diagnostics;

namespace Pgtail.Notifications;

/// <summary>
/// Runs a notification program and waits up to five seconds for it to succeed.
/// </summary>
internal static class CommandNotifier
{
    private static readonly TimeSpan s_timeout = TimeSpan.FromSeconds(5);

    /// <summary>
    /// Runs a program with arguments and no console interaction.
    /// </summary>
    /// <param name="program">The program path.</param>
    /// <param name="arguments">The arguments.</param>
    /// <returns>True when it exited with status 0 in time.</returns>
    public static bool Run(string program, IReadOnlyList<string> arguments)
    {
        var start = new ProcessStartInfo(program)
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };

        foreach (string argument in arguments)
        {
            start.ArgumentList.Add(argument);
        }

        try
        {
            using var process = Process.Start(start);
            if (process is null)
            {
                return false;
            }

            process.StandardInput.Close();
            Task<string> output = process.StandardOutput.ReadToEndAsync();
            Task<string> error = process.StandardError.ReadToEndAsync();
            if (!process.WaitForExit(s_timeout))
            {
                process.Kill(entireProcessTree: true);
                return false;
            }

            Task.WaitAll(output, error);
            return process.ExitCode == 0;
        }
        catch (Exception exception) when (exception is InvalidOperationException or Win32Exception)
        {
            return false;
        }
    }
}
