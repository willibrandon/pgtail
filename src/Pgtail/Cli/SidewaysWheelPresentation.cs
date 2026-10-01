using System.Buffers;
using System.Globalization;
using System.Text;
using Hex1b;

namespace Pgtail.Cli;

/// <summary>
/// The console, with the mouse's sideways wheel reported as the wheel turned with Shift held.
/// </summary>
/// <remarks>
/// A trackpad's sideways swipe, or a tilted wheel, reaches a terminal application as wheel buttons 6 and 7, codes 66
/// and 67 in an SGR mouse report. pgtail's screens scroll sideways on the wheel with Shift, so each sideways report is
/// rewritten as one: left as Shift with the wheel up, right as Shift with the wheel down. A report split between two
/// reads is held until the rest of it arrives.
/// </remarks>
internal sealed class SidewaysWheelPresentation : IHex1bTerminalPresentationAdapter
{
    // The longest SGR mouse report: ESC [ < button ; column ; row M, with numbers far wider than any terminal's.
    private const int LongestReport = 32;
    private const int ShiftBit = 4;
    private static ReadOnlySpan<byte> ReportStart => "\e[<"u8;
    private readonly ConsolePresentationAdapter _inner = new(enableMouse: true);
    private byte[] _held = [];

    /// <inheritdoc />
    public int Width => _inner.Width;

    /// <inheritdoc />
    public int Height => _inner.Height;

    /// <inheritdoc />
    public TerminalCapabilities Capabilities => _inner.Capabilities;

    /// <inheritdoc />
    public bool AnswersProtocolQueriesDirectly => _inner.AnswersProtocolQueriesDirectly;

    /// <inheritdoc />
    public event Action<int, int>? Resized
    {
        add => _inner.Resized += value;
        remove => _inner.Resized -= value;
    }

    /// <inheritdoc />
    public event Action? Disconnected
    {
        add => _inner.Disconnected += value;
        remove => _inner.Disconnected -= value;
    }

    /// <inheritdoc />
    public ValueTask WriteOutputAsync(ReadOnlyMemory<byte> data, CancellationToken ct = default) => _inner.WriteOutputAsync(data, ct);

    /// <inheritdoc />
    public async ValueTask<ReadOnlyMemory<byte>> ReadInputAsync(CancellationToken ct = default)
    {
        while (true)
        {
            ReadOnlyMemory<byte> data = await _inner.ReadInputAsync(ct);
            if (data.IsEmpty)
            {
                // The console has closed; what was held is passed on as it came.
                byte[] rest = _held;
                _held = [];
                return rest.Length > 0 ? rest : data;
            }

            ReadOnlyMemory<byte> input = data;
            if (_held.Length > 0)
            {
                byte[] joined = [.. _held, .. data.Span];
                input = joined;
            }

            byte[]? translated = Translate(input.Span, out int held);
            _held = input.Span[(input.Length - held)..].ToArray();
            ReadOnlyMemory<byte> ready = translated ?? input[..(input.Length - held)];
            if (!ready.IsEmpty)
            {
                return ready;
            }
        }
    }

    /// <inheritdoc />
    public void InvalidatePresentation() => ((IHex1bTerminalPresentationAdapter)_inner).InvalidatePresentation();

    /// <inheritdoc />
    public ValueTask FlushAsync(CancellationToken ct = default) => _inner.FlushAsync(ct);

    /// <inheritdoc />
    public ValueTask EnterRawModeAsync(CancellationToken ct = default) => _inner.EnterRawModeAsync(ct);

    /// <inheritdoc />
    public ValueTask ExitRawModeAsync(CancellationToken ct = default) => _inner.ExitRawModeAsync(ct);

    /// <inheritdoc />
    public (int Row, int Column) GetCursorPosition() => _inner.GetCursorPosition();

    /// <inheritdoc />
    public ValueTask DisposeAsync() => _inner.DisposeAsync();

    /// <summary>
    /// Rewrites the sideways wheel reports in console input as reports of the wheel with Shift held.
    /// </summary>
    /// <param name="input">The input.</param>
    /// <param name="held">
    /// The number of bytes at the end of the input that start a mouse report without finishing it, to be read again
    /// with what follows.
    /// </param>
    /// <returns>The input before the held bytes, rewritten; null when nothing in it was rewritten.</returns>
    internal static byte[]? Translate(ReadOnlySpan<byte> input, out int held)
    {
        held = 0;
        ArrayBufferWriter<byte>? output = null;
        int copied = 0;
        int searched = 0;
        while (input[searched..].IndexOf(ReportStart) is int found and >= 0)
        {
            int start = searched + found;
            int end = ReportEnd(input, start);
            if (end < 0)
            {
                held = input.Length - start;
                break;
            }

            searched = end + 1;
            if (end == start || Sideways(input[start..searched]) is not { } report)
            {
                continue;
            }

            output ??= new ArrayBufferWriter<byte>(input.Length);
            output.Write(input[copied..start]);
            output.Write(report);
            copied = searched;
        }

        if (output is null)
        {
            return null;
        }

        output.Write(input[copied..(input.Length - held)]);
        return output.WrittenSpan.ToArray();
    }

    /// <summary>
    /// Finds the end of the mouse report starting at an index.
    /// </summary>
    /// <param name="input">The input.</param>
    /// <param name="start">Where the report starts.</param>
    /// <returns>
    /// The index of the report's final byte; the start itself when the bytes there are not a report, so they are passed
    /// on; or -1 when the input ends inside the report.
    /// </returns>
    private static int ReportEnd(ReadOnlySpan<byte> input, int start)
    {
        for (int index = start + ReportStart.Length; index < input.Length; index++)
        {
            byte current = input[index];
            if (current is (byte)'M' or (byte)'m')
            {
                return index;
            }

            if (current is not ((>= (byte)'0' and <= (byte)'9') or (byte)';') || index - start >= LongestReport)
            {
                return start;
            }
        }

        return input.Length - start >= LongestReport ? start : -1;
    }

    /// <summary>
    /// A sideways wheel report rewritten as the wheel with Shift held.
    /// </summary>
    /// <param name="report">A whole mouse report.</param>
    /// <returns>The rewritten report, or null for any other report.</returns>
    private static byte[]? Sideways(ReadOnlySpan<byte> report)
    {
        ReadOnlySpan<byte> fields = report[ReportStart.Length..^1];
        int separator = fields.IndexOf((byte)';');
        if (separator <= 0 || !int.TryParse(fields[..separator], NumberStyles.None, CultureInfo.InvariantCulture, out int button))
        {
            return null;
        }

        // Bits 2 to 5 carry Shift, Alt, Control, and motion; the rest name the button, 66 and 67 the sideways wheel.
        if ((button & ~0b11_1100) is not (66 or 67))
        {
            return null;
        }

        int wheel = (button & ~0b11) | (button & 1) | ShiftBit;
        byte[] code = Encoding.ASCII.GetBytes(wheel.ToString(CultureInfo.InvariantCulture));
        return [.. ReportStart, .. code, .. fields[separator..], report[^1]];
    }
}
