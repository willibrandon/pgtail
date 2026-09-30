using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Pgtail.Notifications;

/// <summary>
/// Minimal WinRT and COM plumbing: activation, strings, interface queries, and vtable calls.
/// </summary>
[SupportedOSPlatform("windows")]
internal static unsafe partial class WinRt
{
    private const int SOk = 0;
    private const int SFalse = 1;
    private const int RpcEChangedMode = unchecked((int)0x80010106);
    private const int RoInitMultithreaded = 1;

    [ThreadStatic]
    private static bool s_initialized;

    /// <summary>
    /// Initializes the Windows Runtime on this thread in the multithreaded apartment, once.
    /// </summary>
    /// <remarks>
    /// A thread already in another apartment is accepted as it is.
    /// </remarks>
    /// <exception cref="WinRtException">Initialization failed.</exception>
    public static void EnsureInitialized()
    {
        if (s_initialized)
        {
            return;
        }

        int result = RoInitialize(RoInitMultithreaded);
        if (result is not (SOk or SFalse or RpcEChangedMode))
        {
            throw new WinRtException("RoInitialize failed", result);
        }

        s_initialized = true;
    }

    /// <summary>
    /// Gets a class's activation factory as the given interface.
    /// </summary>
    /// <param name="className">The runtime class name.</param>
    /// <param name="iid">The factory interface.</param>
    /// <returns>The factory; release it when done.</returns>
    public static nint GetActivationFactory(string className, Guid iid)
    {
        nint name = CreateString(className);
        try
        {
            Check(RoGetActivationFactory(name, &iid, out nint factory), $"RoGetActivationFactory({className})");
            return factory;
        }
        finally
        {
            _ = WindowsDeleteString(name);
        }
    }

    /// <summary>
    /// Creates an instance of a class with its default constructor.
    /// </summary>
    /// <param name="className">The runtime class name.</param>
    /// <returns>The instance's <c>IInspectable</c>; release it when done.</returns>
    public static nint ActivateInstance(string className)
    {
        nint name = CreateString(className);
        try
        {
            Check(RoActivateInstance(name, out nint instance), $"RoActivateInstance({className})");
            return instance;
        }
        finally
        {
            _ = WindowsDeleteString(name);
        }
    }

    /// <summary>
    /// Creates a Windows Runtime string.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The <c>HSTRING</c>; delete it with <see cref="DeleteString"/>.</returns>
    public static nint CreateString(string text)
    {
        Check(WindowsCreateString(text, (uint)text.Length, out nint value), "WindowsCreateString");
        return value;
    }

    /// <summary>
    /// Deletes a Windows Runtime string.
    /// </summary>
    /// <param name="value">The <c>HSTRING</c>.</param>
    public static void DeleteString(nint value) => _ = WindowsDeleteString(value);

    /// <summary>
    /// Asks an object for another of its interfaces.
    /// </summary>
    /// <param name="instance">The object.</param>
    /// <param name="iid">The interface.</param>
    /// <returns>The interface pointer; release it when done.</returns>
    public static nint QueryInterface(nint instance, Guid iid)
    {
        nint result;
        var function = (delegate* unmanaged[Stdcall]<nint, Guid*, nint*, int>)VTable(instance)[0];
        Check(function(instance, &iid, &result), "QueryInterface");
        return result;
    }

    /// <summary>
    /// Releases an interface pointer; zero is ignored.
    /// </summary>
    /// <param name="instance">The pointer.</param>
    public static void Release(nint instance)
    {
        if (instance != 0)
        {
            var function = (delegate* unmanaged[Stdcall]<nint, uint>)VTable(instance)[2];
            _ = function(instance);
        }
    }

    /// <summary>
    /// The vtable of an interface pointer.
    /// </summary>
    /// <param name="instance">The pointer.</param>
    /// <returns>The vtable.</returns>
    public static nint* VTable(nint instance) => *(nint**)instance;

    /// <summary>
    /// Throws for a failed <c>HRESULT</c>.
    /// </summary>
    /// <param name="result">The result.</param>
    /// <param name="operation">What was attempted.</param>
    /// <exception cref="WinRtException">The result is a failure.</exception>
    public static void Check(int result, string operation)
    {
        if (result < 0)
        {
            throw new WinRtException($"{operation} failed: 0x{result:X8}", result);
        }
    }

    [LibraryImport("combase.dll")]
    private static partial int RoInitialize(int initType);

    [LibraryImport("combase.dll", StringMarshalling = StringMarshalling.Utf16)]
    private static partial int WindowsCreateString(string sourceString, uint length, out nint value);

    [LibraryImport("combase.dll")]
    private static partial int WindowsDeleteString(nint value);

    [LibraryImport("combase.dll")]
    private static partial int RoGetActivationFactory(nint activatableClassId, Guid* iid, out nint factory);

    [LibraryImport("combase.dll")]
    private static partial int RoActivateInstance(nint activatableClassId, out nint instance);
}
