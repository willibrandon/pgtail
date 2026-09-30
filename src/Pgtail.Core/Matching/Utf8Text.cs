using System.Buffers;
using System.Text;

namespace Pgtail.Matching;

/// <summary>
/// A string encoded once as UTF-8 for byte-oriented matching, with byte offsets mapped back to character offsets.
/// </summary>
/// <remarks>
/// ASCII text maps byte offsets to character offsets directly; other text builds its offset table on first use.
/// Dispose the instance to return its buffer.
/// </remarks>
public sealed class Utf8Text : IDisposable
{
    private readonly byte[] _buffer;
    private int[]? _charOffsets;

    /// <summary>
    /// Encodes a string.
    /// </summary>
    /// <param name="text">The string.</param>
    public Utf8Text(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        Text = text;
        _buffer = ArrayPool<byte>.Shared.Rent(Math.Max(1, Encoding.UTF8.GetMaxByteCount(text.Length)));
        Length = Encoding.UTF8.GetBytes(text, _buffer);
        IsAscii = Length == text.Length;
    }

    /// <summary>
    /// The string.
    /// </summary>
    public string Text { get; }

    /// <summary>
    /// The number of UTF-8 bytes.
    /// </summary>
    public int Length { get; }

    /// <summary>
    /// Whether every character is ASCII, so byte and character offsets agree.
    /// </summary>
    public bool IsAscii { get; }

    /// <summary>
    /// The UTF-8 bytes.
    /// </summary>
    public ReadOnlySpan<byte> Bytes => _buffer.AsSpan(0, Length);

    /// <summary>
    /// The character offset of a byte offset; an offset inside a multi-byte sequence maps to its character.
    /// </summary>
    /// <param name="byteOffset">The byte offset.</param>
    /// <returns>The character offset.</returns>
    public int ToCharOffset(int byteOffset)
    {
        if (IsAscii)
        {
            return byteOffset;
        }

        _charOffsets ??= BuildOffsets();
        return _charOffsets[Math.Clamp(byteOffset, 0, Length)];
    }

    /// <inheritdoc />
    public void Dispose() => ArrayPool<byte>.Shared.Return(_buffer);

    private int[] BuildOffsets()
    {
        int[] offsets = new int[Length + 1];
        int bytePosition = 0;
        for (int i = 0; i < Text.Length; i++)
        {
            char c = Text[i];
            int width;
            int characters = 1;
            if (char.IsHighSurrogate(c) && i + 1 < Text.Length && char.IsLowSurrogate(Text[i + 1]))
            {
                width = 4;
                characters = 2;
            }
            else
            {
                width = c < 0x80 ? 1 : c < 0x800 ? 2 : 3;
            }

            for (int b = 0; b < width && bytePosition + b < offsets.Length; b++)
            {
                offsets[bytePosition + b] = i;
            }

            bytePosition += width;
            i += characters - 1;
        }

        offsets[Length] = Text.Length;
        return offsets;
    }
}
