using System.ComponentModel;
using System.Diagnostics;
using System.Text;
using Hex1b;

namespace Pgtail.Tail;

/// <summary>
/// Copies text to the clipboard through the terminal (OSC 52) and through the platform's clipboard command.
/// </summary>
/// <remarks>
/// OSC 52 reaches the clipboard of the machine the terminal runs on, even over SSH, in terminals that support it. The
/// platform command (<c>pbcopy</c>, <c>wl-copy</c>, <c>xclip</c>, <c>xsel</c>, or <c>clip.exe</c>) covers
/// terminals that do not.
/// </remarks>
internal static class TailClipboard
{
    /// <summary>
    /// Copies text both ways.
    /// </summary>
    /// <param name="app">The running app, which writes the OSC 52 sequence, or null.</param>
    /// <param name="text">The text.</param>
    public static void Copy(Hex1bApp? app, string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (text.Length == 0)
        {
            return;
        }

        app?.CopyToClipboard(text);
        _ = Task.Run(() => CopyWithCommand(text));
    }

    /// <summary>
    /// Runs the first platform clipboard command that accepts the text on its standard input.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>True when a command accepted it.</returns>
    public static bool CopyWithCommand(string text)
    {
        foreach (var (program, arguments) in Commands())
        {
            try
            {
                var start = new ProcessStartInfo(program)
                {
                    RedirectStandardInput = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    StandardInputEncoding = OperatingSystem.IsWindows() ? Encoding.Unicode : new UTF8Encoding(false),
                };

                foreach (var argument in arguments)
                {
                    start.ArgumentList.Add(argument);
                }

                using var process = Process.Start(start);
                if (process is null)
                {
                    continue;
                }

                process.StandardInput.Write(text);
                process.StandardInput.Close();
                if (process.WaitForExit(TimeSpan.FromSeconds(3)) && process.ExitCode == 0)
                {
                    return true;
                }
            }
            catch (Exception exception) when (exception is Win32Exception or InvalidOperationException or IOException)
            {
                // The command is missing or failed; try the next one.
            }
        }

        return false;
    }

    private static IEnumerable<(string Program, string[] Arguments)> Commands()
    {
        if (OperatingSystem.IsMacOS())
        {
            yield return ("pbcopy", []);
        }
        else if (OperatingSystem.IsWindows())
        {
            yield return ("clip.exe", []);
        }
        else
        {
            yield return ("wl-copy", []);
            yield return ("xclip", ["-selection", "clipboard"]);
            yield return ("xsel", ["--clipboard", "--input"]);
        }
    }
}
