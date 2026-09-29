using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace Pgtail.Detection;

/// <summary>
/// Lists running processes with their command lines on Linux, macOS, and Windows.
/// </summary>
public static partial class ProcessTable
{
    private const int CtlKern = 1;
    private const int KernArgMax = 8;
    private const int KernProcArgs2 = 49;
    private const uint ProcessQueryLimitedInformation = 0x1000;
    private const int ProcessCommandLineInformation = 60;

    /// <summary>
    /// Lists every process this user may inspect.
    /// </summary>
    /// <returns>The processes; one that ends while it is being read is left out.</returns>
    public static IReadOnlyList<ProcessEntry> List()
    {
        if (OperatingSystem.IsLinux())
        {
            return ListProc();
        }

        var entries = new List<ProcessEntry>();
        foreach (var process in Process.GetProcesses())
        {
            using (process)
            {
                try
                {
                    var arguments = OperatingSystem.IsWindows() ? WindowsArguments(process.Id)
                        : OperatingSystem.IsMacOS() ? MacArguments(process.Id)
                        : [];
                    entries.Add(new ProcessEntry(process.Id, process.ProcessName, arguments));
                }
                catch (Exception exception) when (exception is InvalidOperationException or Win32Exception)
                {
                    // The process ended while it was being read.
                }
            }
        }

        return entries;
    }

    /// <summary>
    /// The name of a running process.
    /// </summary>
    /// <param name="pid">The process ID.</param>
    /// <returns>The name, or null when no such process runs or it cannot be inspected.</returns>
    public static string? NameOf(int pid)
    {
        if (OperatingSystem.IsLinux())
        {
            return ReadText($"/proc/{pid}/comm")?.Trim();
        }

        try
        {
            using var process = Process.GetProcessById(pid);
            return process.ProcessName;
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException)
        {
            return null;
        }
    }

    private static List<ProcessEntry> ListProc()
    {
        var entries = new List<ProcessEntry>();
        IEnumerable<string> directories;
        try
        {
            directories = Directory.EnumerateDirectories("/proc");
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return entries;
        }

        foreach (var directory in directories)
        {
            if (!int.TryParse(Path.GetFileName(directory), out var pid) || ReadText(Path.Combine(directory, "comm")) is not { } comm)
            {
                continue;
            }

            var commandLine = ReadText(Path.Combine(directory, "cmdline")) ?? "";
            var arguments = commandLine.Split('\0');
            var count = arguments.Length > 0 && arguments[^1].Length == 0 ? arguments.Length - 1 : arguments.Length;
            entries.Add(new ProcessEntry(pid, comm.Trim(), arguments[..count]));
        }

        return entries;
    }

    private static List<string> MacArguments(int pid)
    {
        var maxName = new[] { CtlKern, KernArgMax };
        var maxBuffer = new byte[sizeof(int)];
        nuint maxLength = sizeof(int);
        if (Sysctl(maxName, 2, maxBuffer, ref maxLength, IntPtr.Zero, 0) != 0)
        {
            return [];
        }

        var size = BitConverter.ToInt32(maxBuffer);
        var buffer = new byte[size];
        var length = (nuint)size;
        if (Sysctl([CtlKern, KernProcArgs2, pid], 3, buffer, ref length, IntPtr.Zero, 0) != 0 || length < sizeof(int))
        {
            return [];
        }

        // The buffer holds argc, the executable path, padding, and then argc NUL-terminated arguments.
        var count = BitConverter.ToInt32(buffer, 0);
        var position = sizeof(int);
        var used = (int)length;
        while (position < used && buffer[position] != 0)
        {
            position++;
        }

        while (position < used && buffer[position] == 0)
        {
            position++;
        }

        var arguments = new List<string>();
        while (arguments.Count < count && position < used)
        {
            var end = Array.IndexOf(buffer, (byte)0, position, used - position);
            end = end < 0 ? used : end;
            arguments.Add(Encoding.UTF8.GetString(buffer, position, end - position));
            position = end + 1;
        }

        return arguments;
    }

    private static IReadOnlyList<string> WindowsArguments(int pid)
    {
        var handle = OpenProcess(ProcessQueryLimitedInformation, false, pid);
        if (handle == IntPtr.Zero)
        {
            return [];
        }

        try
        {
            NtQueryInformationProcess(handle, ProcessCommandLineInformation, [], 0, out var required);
            if (required <= 0)
            {
                return [];
            }

            var buffer = new byte[required];
            if (NtQueryInformationProcess(handle, ProcessCommandLineInformation, buffer, buffer.Length, out _) != 0)
            {
                return [];
            }

            // The UNICODE_STRING header is followed directly by the characters it describes.
            var bytes = BitConverter.ToUInt16(buffer, 0);
            var offset = IntPtr.Size == 8 ? 16 : 8;
            if (offset + bytes > buffer.Length)
            {
                return [];
            }

            return WindowsCommandLine.Split(Encoding.Unicode.GetString(buffer, offset, bytes));
        }
        finally
        {
            CloseHandle(handle);
        }
    }

    private static string? ReadText(string path)
    {
        try
        {
            return File.ReadAllText(path);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    [LibraryImport("libc", EntryPoint = "sysctl", SetLastError = true)]
    private static partial int Sysctl(
        int[] name,
        uint nameLength,
        byte[] oldValue,
        ref nuint oldLength,
        IntPtr newValue,
        nuint newLength);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    private static partial IntPtr OpenProcess(uint access, [MarshalAs(UnmanagedType.Bool)] bool inherit, int pid);

    [LibraryImport("kernel32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool CloseHandle(IntPtr handle);

    [LibraryImport("ntdll.dll")]
    private static partial int NtQueryInformationProcess(
        IntPtr handle,
        int informationClass,
        byte[] buffer,
        int length,
        out int returnLength);
}
