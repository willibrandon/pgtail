using System.Text;

namespace Pgtail.Styling;

/// <summary>
/// Text made of styled runs, built by appending.
/// </summary>
/// <remarks>
/// Text may hold line breaks; <see cref="SplitLines"/> divides it into lines for display.
/// </remarks>
public sealed class StyledText
{
    private readonly List<StyledSpan> _spans = [];
    private readonly StringBuilder _plain = new();

    /// <summary>
    /// Creates empty text.
    /// </summary>
    public StyledText()
    {
    }

    /// <summary>
    /// Creates text with one run.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="style">Its style.</param>
    public StyledText(string text, TextStyle style = default) => Append(text, style);

    /// <summary>
    /// The runs in order.
    /// </summary>
    public IReadOnlyList<StyledSpan> Spans => _spans;

    /// <summary>
    /// The text without styles.
    /// </summary>
    public string PlainText => _plain.ToString();

    /// <summary>
    /// The number of characters.
    /// </summary>
    public int Length => _plain.Length;

    /// <summary>
    /// Appends a run, merging it with the last run when the style is the same.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="style">Its style.</param>
    /// <returns>This text, for chaining.</returns>
    public StyledText Append(string text, TextStyle style = default)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (text.Length == 0)
        {
            return this;
        }

        if (_spans.Count > 0 && _spans[^1].Style == style)
        {
            _spans[^1] = _spans[^1] with { Text = _spans[^1].Text + text };
        }
        else
        {
            _spans.Add(new StyledSpan(text, style));
        }

        _plain.Append(text);
        return this;
    }

    /// <summary>
    /// Appends every run of other text.
    /// </summary>
    /// <param name="other">The other text.</param>
    /// <returns>This text, for chaining.</returns>
    public StyledText Append(StyledText other)
    {
        ArgumentNullException.ThrowIfNull(other);
        foreach (var span in other._spans)
        {
            Append(span.Text, span.Style);
        }

        return this;
    }

    /// <summary>
    /// Divides the text at line breaks.
    /// </summary>
    /// <returns>One styled text per line.</returns>
    public IReadOnlyList<StyledText> SplitLines()
    {
        var lines = new List<StyledText> { new() };
        foreach (var span in _spans)
        {
            var parts = span.Text.Split('\n');
            for (var i = 0; i < parts.Length; i++)
            {
                if (i > 0)
                {
                    lines.Add(new StyledText());
                }

                lines[^1].Append(parts[i].TrimEnd('\r'), span.Style);
            }
        }

        return lines;
    }

    /// <inheritdoc />
    public override string ToString() => PlainText;
}
