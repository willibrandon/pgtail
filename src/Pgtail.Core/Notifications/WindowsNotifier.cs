using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Pgtail.Notifications;

/// <summary>
/// Shows Windows toast notifications through the Windows Runtime toast API, called directly over COM.
/// </summary>
/// <remarks>
/// After five failures in a row, sending pauses for a minute; access denied or an unregistered class stops it for good.
/// </remarks>
[SupportedOSPlatform("windows")]
public sealed unsafe class WindowsNotifier : INotifier
{
    private const int FailureThreshold = 5;
    private const int AccessDenied = unchecked((int)0x80070005);
    private const int ClassNotRegistered = unchecked((int)0x80040154);
    private static readonly TimeSpan Cooldown = TimeSpan.FromSeconds(60);
    private static readonly Guid IidToastNotificationManagerStatics = new("50AC103F-D235-4598-BBEF-98FE4D1A3AD4");
    private static readonly Guid IidToastNotificationFactory = new("04124B20-82C6-4229-B109-FD9ED4662B53");
    private static readonly Guid IidToastNotification2 = new("9DFB9FD1-143A-490E-90BF-B9FBA7132DE7");
    private static readonly Guid IidToastNotification4 = new("15154935-28EA-4727-88E9-C58680E2D118");
    private static readonly Guid IidXmlDocument = new("F7F3A506-1E87-42D6-BCFB-B8C809FA5494");
    private static readonly Guid IidXmlDocumentIo = new("6CD0E74E-EE65-4489-9EBF-CA43E87BA637");
    private static readonly Guid IidPropertyValueStatics = new("629BDBC8-D932-4FF4-96B9-8D96C5C1E858");
    private static readonly Guid IidReferenceOfDateTime = new("5541D8A7-497C-5AA4-86FC-7713ADBF2A2C");
    private readonly Lock _gate = new();
    private readonly nint _toastNotifier;
    private readonly nint _toastFactory;
    private readonly nint _propertyValues;
    private bool _available = true;
    private int _failures;
    private DateTime? _pausedUntil;

    private WindowsNotifier(nint toastNotifier, nint toastFactory, nint propertyValues)
    {
        _toastNotifier = toastNotifier;
        _toastFactory = toastFactory;
        _propertyValues = propertyValues;
    }

    /// <inheritdoc/>
    public bool IsAvailable => _available;

    /// <inheritdoc/>
    public string PlatformInfo => _available ? "Windows (WinRT Toast)" : "Windows (WinRT unavailable)";

    /// <summary>
    /// Registers the Start menu shortcut and connects to the toast API.
    /// </summary>
    /// <param name="environment">Reads environment variables.</param>
    /// <returns>The notifier, or null when toasts cannot be shown.</returns>
    public static WindowsNotifier? TryCreate(Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(environment);
        nint manager = 0;
        nint toastNotifier = 0;
        try
        {
            WinRt.EnsureInitialized();
            if (!StartMenuShortcut.Ensure(environment))
            {
                return null;
            }

            manager = WinRt.GetActivationFactory("Windows.UI.Notifications.ToastNotificationManager", IidToastNotificationManagerStatics);
            var id = WinRt.CreateString(StartMenuShortcut.AppUserModelId);
            try
            {
                var create = (delegate* unmanaged[Stdcall]<nint, nint, nint*, int>)WinRt.VTable(manager)[7];
                WinRt.Check(create(manager, id, &toastNotifier), "CreateToastNotifierWithId");
            }
            finally
            {
                WinRt.DeleteString(id);
            }

            var factory = WinRt.GetActivationFactory("Windows.UI.Notifications.ToastNotification", IidToastNotificationFactory);
            var values = WinRt.GetActivationFactory("Windows.Foundation.PropertyValue", IidPropertyValueStatics);
            return new WindowsNotifier(toastNotifier, factory, values);
        }
        catch (Exception exception) when (exception is COMException or DllNotFoundException or EntryPointNotFoundException)
        {
            WinRt.Release(toastNotifier);
            return null;
        }
        finally
        {
            WinRt.Release(manager);
        }
    }

    /// <inheritdoc/>
    public bool Send(Notification notification)
    {
        ArgumentNullException.ThrowIfNull(notification);
        lock (_gate)
        {
            if (!_available)
            {
                return false;
            }

            if (_pausedUntil is { } until)
            {
                if (DateTime.UtcNow < until)
                {
                    return false;
                }

                _pausedUntil = null;
                _failures = 0;
            }

            try
            {
                WinRt.EnsureInitialized();
                Show(notification);
                _failures = 0;
                return true;
            }
            catch (COMException exception)
            {
                if (exception.HResult is AccessDenied or ClassNotRegistered)
                {
                    _available = false;
                    return false;
                }

                if (++_failures >= FailureThreshold)
                {
                    _pausedUntil = DateTime.UtcNow + Cooldown;
                }

                return false;
            }
        }
    }

    private void Show(Notification notification)
    {
        nint inspectable = 0;
        nint document = 0;
        nint documentIo = 0;
        nint toast = 0;
        try
        {
            inspectable = WinRt.ActivateInstance("Windows.Data.Xml.Dom.XmlDocument");
            documentIo = WinRt.QueryInterface(inspectable, IidXmlDocumentIo);
            var xml = WinRt.CreateString(ToastXml.Build(notification));
            try
            {
                var load = (delegate* unmanaged[Stdcall]<nint, nint, int>)WinRt.VTable(documentIo)[6];
                WinRt.Check(load(documentIo, xml), "IXmlDocumentIO.LoadXml");
            }
            finally
            {
                WinRt.DeleteString(xml);
            }

            document = WinRt.QueryInterface(inspectable, IidXmlDocument);
            var create = (delegate* unmanaged[Stdcall]<nint, nint, nint*, int>)WinRt.VTable(_toastFactory)[6];
            WinRt.Check(create(_toastFactory, document, &toast), "CreateToastNotification");
            if (ToastXml.Expiry(notification.Severity) is { } lifetime)
            {
                SetExpiration(toast, DateTime.UtcNow + lifetime);
            }

            if (notification.Tag is { } tag)
            {
                SetTag(toast, tag.Length > 16 ? tag[..16] : tag);
            }

            if (notification.Severity is NotificationSeverity.Error or NotificationSeverity.Critical)
            {
                SetHighPriority(toast);
            }

            var show = (delegate* unmanaged[Stdcall]<nint, nint, int>)WinRt.VTable(_toastNotifier)[6];
            WinRt.Check(show(_toastNotifier, toast), "IToastNotifier.Show");
        }
        finally
        {
            WinRt.Release(toast);
            WinRt.Release(document);
            WinRt.Release(documentIo);
            WinRt.Release(inspectable);
        }
    }

    private void SetExpiration(nint toast, DateTime expiresUtc)
    {
        nint value = 0;
        nint reference = 0;
        try
        {
            // A Windows.Foundation.DateTime counts 100 ns ticks from 1601, as a FILETIME does.
            var ticks = expiresUtc.ToFileTimeUtc();
            var createDateTime = (delegate* unmanaged[Stdcall]<nint, long, nint*, int>)WinRt.VTable(_propertyValues)[21];
            WinRt.Check(createDateTime(_propertyValues, ticks, &value), "IPropertyValueStatics.CreateDateTime");
            reference = WinRt.QueryInterface(value, IidReferenceOfDateTime);
            var put = (delegate* unmanaged[Stdcall]<nint, nint, int>)WinRt.VTable(toast)[7];
            WinRt.Check(put(toast, reference), "IToastNotification.put_ExpirationTime");
        }
        finally
        {
            WinRt.Release(reference);
            WinRt.Release(value);
        }
    }

    private static void SetTag(nint toast, string tag)
    {
        var second = WinRt.QueryInterface(toast, IidToastNotification2);
        try
        {
            PutString(second, 6, tag, "IToastNotification2.put_Tag");
            PutString(second, 8, "pgtail", "IToastNotification2.put_Group");
        }
        finally
        {
            WinRt.Release(second);
        }
    }

    private static void SetHighPriority(nint toast)
    {
        nint fourth;
        try
        {
            fourth = WinRt.QueryInterface(toast, IidToastNotification4);
        }
        catch (COMException)
        {
            // Windows before the Creators Update has no toast priority.
            return;
        }

        try
        {
            var put = (delegate* unmanaged[Stdcall]<nint, int, int>)WinRt.VTable(fourth)[9];
            WinRt.Check(put(fourth, 1), "IToastNotification4.put_Priority");
        }
        finally
        {
            WinRt.Release(fourth);
        }
    }

    private static void PutString(nint instance, int slot, string text, string operation)
    {
        var value = WinRt.CreateString(text);
        try
        {
            var put = (delegate* unmanaged[Stdcall]<nint, nint, int>)WinRt.VTable(instance)[slot];
            WinRt.Check(put(instance, value), operation);
        }
        finally
        {
            WinRt.DeleteString(value);
        }
    }
}
