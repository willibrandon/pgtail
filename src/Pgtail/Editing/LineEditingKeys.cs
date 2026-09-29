using Hex1b.Input;

namespace Pgtail.Editing;

/// <summary>
/// The line editing keys of a shell prompt, for the REPL prompt and tail mode's command input.
/// </summary>
/// <remarks>
/// These are the keys prompt_toolkit and readline give a prompt: Ctrl+A and Ctrl+E move to the start and end, Ctrl+B and
/// Ctrl+F by a character, Alt+B and Alt+F by a word, Ctrl+K and Ctrl+U cut to the end and start of the line, Ctrl+W
/// cuts the word before the caret, Alt+D the word after it, and Ctrl+Y pastes the last cut text.
/// </remarks>
/// <param name="line">The line.</param>
/// <param name="changed">Called after a key changes the text, for an owner that does not watch the text itself.</param>
internal sealed class LineEditingKeys(IEditableLine line, Action? changed = null)
{
    private string _cut = "";

    /// <summary>
    /// Replaces the input's own bindings for these keys.
    /// </summary>
    /// <param name="bindings">The input's bindings.</param>
    public void Bind(InputBindingsBuilder bindings)
    {
        ArgumentNullException.ThrowIfNull(bindings);
        foreach (var key in new[] { Hex1bKey.A, Hex1bKey.E, Hex1bKey.B, Hex1bKey.F, Hex1bKey.K, Hex1bKey.U, Hex1bKey.W, Hex1bKey.Y })
        {
            bindings.Remove(key, Hex1bModifiers.Control);
        }

        bindings.Remove(Hex1bKey.B, Hex1bModifiers.Alt);
        bindings.Remove(Hex1bKey.F, Hex1bModifiers.Alt);
        bindings.Remove(Hex1bKey.D, Hex1bModifiers.Alt);
        bindings.Ctrl().Key(Hex1bKey.A).Action(_ => line.Caret = 0, "Go to the start of the line");
        bindings.Ctrl().Key(Hex1bKey.E).Action(_ => line.Caret = line.Text.Length, "Go to the end of the line");
        bindings.Ctrl().Key(Hex1bKey.B).Action(_ => line.Caret = Math.Max(0, Caret - 1), "Back a character");
        bindings.Ctrl().Key(Hex1bKey.F).Action(_ => line.Caret = Math.Min(line.Text.Length, Caret + 1), "Forward a character");
        bindings.Alt().Key(Hex1bKey.B).Action(_ => line.Caret = WordStartBefore(Caret), "Back a word");
        bindings.Alt().Key(Hex1bKey.F).Action(_ => line.Caret = WordEndAfter(Caret), "Forward a word");
        bindings.Ctrl().Key(Hex1bKey.K).Action(_ => Cut(Caret, line.Text.Length), "Cut to the end of the line");
        bindings.Ctrl().Key(Hex1bKey.U).Action(_ => Cut(0, Caret), "Cut to the start of the line");
        bindings.Ctrl().Key(Hex1bKey.W).Action(_ => Cut(SpaceWordStartBefore(Caret), Caret), "Cut the word before the caret");
        bindings.Alt().Key(Hex1bKey.D).Action(_ => Cut(Caret, WordEndAfter(Caret)), "Cut the word after the caret");
        bindings.Ctrl().Key(Hex1bKey.Y).Action(_ => Paste(), "Paste the last cut text");
    }

    private int Caret => Math.Clamp(line.Caret, 0, line.Text.Length);

    private void Cut(int start, int end)
    {
        if (end <= start)
        {
            return;
        }

        _cut = line.Text[start..end];
        line.Replace(start, end, "");
        changed?.Invoke();
    }

    private void Paste()
    {
        if (_cut.Length > 0)
        {
            line.Replace(Caret, Caret, _cut);
            changed?.Invoke();
        }
    }

    // As readline's Ctrl+W: back over spaces, then over the word before them.
    private int SpaceWordStartBefore(int caret)
    {
        var text = line.Text;
        var start = caret;
        while (start > 0 && char.IsWhiteSpace(text[start - 1]))
        {
            start--;
        }

        while (start > 0 && !char.IsWhiteSpace(text[start - 1]))
        {
            start--;
        }

        return start;
    }

    // As readline's Alt+B: back over anything else, then over letters and digits.
    private int WordStartBefore(int caret)
    {
        var text = line.Text;
        var start = caret;
        while (start > 0 && !char.IsLetterOrDigit(text[start - 1]))
        {
            start--;
        }

        while (start > 0 && char.IsLetterOrDigit(text[start - 1]))
        {
            start--;
        }

        return start;
    }

    // As readline's Alt+F and Alt+D: forward over anything else, then over letters and digits.
    private int WordEndAfter(int caret)
    {
        var text = line.Text;
        var end = caret;
        while (end < text.Length && !char.IsLetterOrDigit(text[end]))
        {
            end++;
        }

        while (end < text.Length && char.IsLetterOrDigit(text[end]))
        {
            end++;
        }

        return end;
    }
}
