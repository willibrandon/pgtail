using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Pgtail.Notifications;

/// <summary>
/// Creates the Start menu shortcut that registers pgtail's application user model ID, which toasts require.
/// </summary>
[SupportedOSPlatform("windows")]
internal static unsafe partial class StartMenuShortcut
{
    /// <summary>
    /// The application user model ID toasts are shown under.
    /// </summary>
    public const string AppUserModelId = "pgtail.pgtail";

    private const uint ClsctxInprocServer = 1;
    private const ushort VtLpwstr = 31;
    private static readonly Guid ClsidShellLink = new("00021401-0000-0000-C000-000000000046");
    private static readonly Guid IidShellLinkW = new("000214F9-0000-0000-C000-000000000046");
    private static readonly Guid IidPropertyStore = new("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
    private static readonly Guid IidPersistFile = new("0000010B-0000-0000-C000-000000000046");
    private static readonly Guid AppUserModelIdFormat = new("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");

    /// <summary>
    /// Creates the shortcut unless it already exists.
    /// </summary>
    /// <param name="environment">Reads environment variables, for <c>APPDATA</c>.</param>
    /// <returns>True when the shortcut exists afterward.</returns>
    public static bool Ensure(Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(environment);
        var appData = environment("APPDATA");
        if (string.IsNullOrEmpty(appData) || Environment.ProcessPath is not { } executable)
        {
            return false;
        }

        var path = Path.Combine(appData, "Microsoft", "Windows", "Start Menu", "Programs", "pgtail.lnk");
        if (File.Exists(path))
        {
            return true;
        }

        try
        {
            Create(path, executable);
            return true;
        }
        catch (Exception exception) when (exception is COMException or IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static void Create(string path, string executable)
    {
        _ = CoInitializeEx(0, 0);
        nint link = 0;
        nint store = 0;
        nint persist = 0;
        try
        {
            var clsid = ClsidShellLink;
            var iid = IidShellLinkW;
            WinRt.Check(CoCreateInstance(&clsid, 0, ClsctxInprocServer, &iid, out link), "CoCreateInstance(ShellLink)");
            CallString(link, 20, executable, "IShellLinkW.SetPath");
            CallString(link, 7, "pgtail - PostgreSQL log tailer", "IShellLinkW.SetDescription");
            store = WinRt.QueryInterface(link, IidPropertyStore);
            var key = new PropertyKey { FormatId = AppUserModelIdFormat, PropertyId = 5 };
            var id = Marshal.StringToCoTaskMemUni(AppUserModelId);
            try
            {
                var value = new PropVariant { Type = VtLpwstr, Pointer = id };
                var setValue = (delegate* unmanaged[Stdcall]<nint, PropertyKey*, PropVariant*, int>)WinRt.VTable(store)[6];
                WinRt.Check(setValue(store, &key, &value), "IPropertyStore.SetValue");
            }
            finally
            {
                Marshal.FreeCoTaskMem(id);
            }

            var commit = (delegate* unmanaged[Stdcall]<nint, int>)WinRt.VTable(store)[7];
            WinRt.Check(commit(store), "IPropertyStore.Commit");
            persist = WinRt.QueryInterface(link, IidPersistFile);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            fixed (char* file = path)
            {
                var save = (delegate* unmanaged[Stdcall]<nint, char*, int, int>)WinRt.VTable(persist)[6];
                WinRt.Check(save(persist, file, 1), "IPersistFile.Save");
            }
        }
        finally
        {
            WinRt.Release(persist);
            WinRt.Release(store);
            WinRt.Release(link);
        }
    }

    private static void CallString(nint instance, int slot, string text, string operation)
    {
        fixed (char* value = text)
        {
            var function = (delegate* unmanaged[Stdcall]<nint, char*, int>)WinRt.VTable(instance)[slot];
            WinRt.Check(function(instance, value), operation);
        }
    }

    [LibraryImport("ole32.dll")]
    private static partial int CoInitializeEx(nint reserved, uint coInit);

    [LibraryImport("ole32.dll")]
    private static partial int CoCreateInstance(Guid* clsid, nint outer, uint context, Guid* iid, out nint instance);

    [StructLayout(LayoutKind.Sequential)]
    private struct PropertyKey
    {
        public Guid FormatId;
        public uint PropertyId;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PropVariant
    {
        public ushort Type;
        public ushort Reserved1;
        public ushort Reserved2;
        public ushort Reserved3;
        public nint Pointer;
        public nint Padding;
    }
}
