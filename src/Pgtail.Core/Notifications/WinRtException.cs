using System.Runtime.InteropServices;

namespace Pgtail.Notifications;

/// <summary>
/// A Windows Runtime call that failed, with its result code.
/// </summary>
/// <param name="message">What failed.</param>
/// <param name="result">The result code.</param>
public sealed class WinRtException(string message, int result) : COMException(message, result);
