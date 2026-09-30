namespace Pgtail.Editing;

/// <summary>
/// A line of text being edited, with a caret, for keys that work the same in every input.
/// </summary>
internal interface IEditableLine
{
    /// <summary>
    /// The text.
    /// </summary>
    string Text { get; }

    /// <summary>
    /// The caret's position, from 0 to the text's length.
    /// </summary>
    int Caret { get; set; }

    /// <summary>
    /// Replaces part of the text and puts the caret after the new text.
    /// </summary>
    /// <param name="start">The first position replaced.</param>
    /// <param name="end">The position after the last one replaced.</param>
    /// <param name="text">The new text.</param>
    void Replace(int start, int end, string text);
}
