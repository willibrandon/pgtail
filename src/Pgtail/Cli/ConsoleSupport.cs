using System.Runtime.InteropServices;

namespace Pgtail.Cli;

/// <summary>
/// Console details that differ by platform.
/// </summary>
/// <remarks>
/// Escape sequence support, the processes attached to the console, and reattaching the keyboard after piped input.
/// </remarks>
internal static partial class ConsoleSupport
{
    private const int StdInputHandle = -10;
    private const int StdOutputHandle = -11;
    private const uint EnableVirtualTerminalProcessing = 0x0004;
    private const uint GenericRead = 0x80000000;
    private const uint GenericWrite = 0x40000000;
    private const uint FileShareRead = 1;
    private const uint FileShareWrite = 2;
    private const uint OpenExisting = 3;
    private const int ORdwr = 2;

    /// <summary>
    /// Turns on escape sequence processing for standard output on Windows; other platforms always have it.
    /// </summary>
    public static void EnableEscapeSequences()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        var handle = GetStdHandle(StdOutputHandle);
        if (GetConsoleMode(handle, out var mode))
        {
            _ = SetConsoleMode(handle, mode | EnableVirtualTerminalProcessing);
        }
    }

    /// <summary>
    /// Whether pgtail is the only process attached to its console on Windows.
    /// </summary>
    /// <remarks>
    /// That happens when it is started by a double click, <c>Start-Process</c>, or package validation, so there is
    /// no one to type at the prompt.
    /// </remarks>
    /// <returns>True when no shell shares the console.</returns>
    public static bool IsAloneInConsole()
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        var processes = new uint[16];
        return GetConsoleProcessList(processes, (uint)processes.Length) == 1;
    }

    /// <summary>
    /// Points standard input at the terminal again after piped input was read, so keys reach the tail view.
    /// </summary>
    /// <returns>True when the terminal could be opened.</returns>
    public static bool ReattachKeyboard()
    {
        if (OperatingSystem.IsWindows())
        {
            var console = CreateFileW("CONIN$", GenericRead | GenericWrite, FileShareRead | FileShareWrite, 0, OpenExisting, 0, 0);
            return console != -1 && SetStdHandle(StdInputHandle, console);
        }

        var terminal = open("/dev/tty", ORdwr);
        if (terminal < 0)
        {
            return false;
        }

        var result = dup2(terminal, 0);
        _ = close(terminal);
        return result >= 0;
    }

    [LibraryImport("kernel32.dll", SetLastError = true)]
    private static partial nint GetStdHandle(int handle);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool GetConsoleMode(nint handle, out uint mode);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool SetConsoleMode(nint handle, uint mode);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    private static partial uint GetConsoleProcessList([Out] uint[] processes, uint count);

    [LibraryImport("kernel32.dll", SetLastError = true, StringMarshalling = StringMarshalling.Utf16)]
    private static partial nint CreateFileW(string name, uint access, uint share, nint security, uint disposition, uint flags,
        nint template);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool SetStdHandle(int handle, nint value);

    [LibraryImport("libc", SetLastError = true, StringMarshalling = StringMarshalling.Utf8)]
    private static partial int open(string path, int flags);

    [LibraryImport("libc", SetLastError = true)]
    private static partial int dup2(int oldDescriptor, int newDescriptor);

    [LibraryImport("libc", SetLastError = true)]
    private static partial int close(int descriptor);
}
