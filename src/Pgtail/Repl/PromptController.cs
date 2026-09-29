using System.Runtime.CompilerServices;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Commands;

namespace Pgtail.Repl;

/// <summary>
/// Handles the REPL prompt's keys: completion, history, shell mode, and submitting.
/// </summary>
/// <remarks>
/// Completions appear while typing, as in the Python release. Tab inserts a lone completion or the part all
/// completions share, then cycles through them; Up and Down move through the menu while it shows and through history
/// otherwise; Escape closes the menu or leaves shell mode; <c>!</c> on an empty line enters shell mode.
/// </remarks>
/// <param name="state">The prompt state.</param>
/// <param name="catalog">The commands to complete.</param>
/// <param name="host">The command host, for completion.</param>
/// <param name="shellMode">Reads and sets shell mode.</param>
internal sealed class PromptController(PromptState state, CommandCatalog catalog, ICommandHost host, StrongBox<bool> shellMode)
{
    /// <summary>
    /// The prompt state.
    /// </summary>
    public PromptState State { get; } = state;

    /// <summary>
    /// Whether the next line runs as a shell command.
    /// </summary>
    public bool ShellMode
    {
        get => shellMode.Value;
        set => shellMode.Value = value;
    }

    /// <summary>
    /// Called when the prompt ends.
    /// </summary>
    public Action<PromptResult>? Ended { get; set; }

    /// <summary>
    /// Called after a key changes what is shown.
    /// </summary>
    public Action? Changed { get; set; }

    /// <summary>
    /// Recomputes completions after the user edits the line, entering shell mode for <c>!</c> on an empty line.
    /// </summary>
    public void TextChanged()
    {
        var version = State.Editor.Document.Version;
        if (version == State.SeenVersion)
        {
            return;
        }

        State.SeenVersion = version;
        State.History.ResetNavigation();
        if (!ShellMode && State.Text == "!")
        {
            State.SetText("");
            ShellMode = true;
        }

        if (ShellMode)
        {
            State.HideCompletions();
            return;
        }

        var (start, items) = Complete();
        var partial = State.Text[start..Math.Min(State.Caret, State.Text.Length)];
        if (items is [var only] && only.Text.Equals(partial, StringComparison.OrdinalIgnoreCase))
        {
            items = [];
        }

        State.ShowCompletions(start, items);
    }

    /// <summary>
    /// Adds the prompt's key bindings to the editor's.
    /// </summary>
    /// <param name="bindings">The editor's bindings.</param>
    public void Bind(InputBindingsBuilder bindings)
    {
        ArgumentNullException.ThrowIfNull(bindings);
        bindings.Remove(EditorWidget.InsertNewline);
        bindings.Remove(EditorWidget.InsertTab);
        bindings.Remove(EditorWidget.AddCursorAtNextMatch);
        bindings.Remove(EditorWidget.MoveUp);
        bindings.Remove(EditorWidget.MoveDown);
        bindings.Remove(Hex1bKey.Escape);
        bindings.Key(Hex1bKey.Enter).Action(_ => End(PromptOutcome.Submitted), "Run the command");
        bindings.Key(Hex1bKey.Tab).Action(_ => Tab(), "Complete");
        bindings.Shift().Key(Hex1bKey.Tab).Action(_ => Update(() => State.MoveSelection(-1)), "Previous completion");
        bindings.Key(Hex1bKey.UpArrow).Action(_ => Update(Up), "Previous completion or history entry");
        bindings.Key(Hex1bKey.DownArrow).Action(_ => Update(Down), "Next completion or history entry");
        bindings.Key(Hex1bKey.Escape).Action(_ => Update(Escape), "Close completions or leave shell mode");
        bindings.Ctrl().Key(Hex1bKey.C).Action(_ => End(PromptOutcome.Interrupted), "Abandon the line");
        bindings.Ctrl().Key(Hex1bKey.D).Action(_ => CtrlD(), "Leave on an empty line, else delete");
        bindings.Ctrl().Key(Hex1bKey.L).Action(_ => End(PromptOutcome.ClearScreen), "Clear the screen");
        bindings.Key(Hex1bKey.Backspace).Action(_ => Update(Backspace), "Delete back, or leave shell mode");
    }

    private (int Start, List<CompletionItem> Items) Complete()
    {
        var caret = Math.Min(State.Caret, State.Text.Length);
        return catalog.Complete(State.Text[..caret], host, CompletionStyle.Menu);
    }

    private void Tab()
    {
        if (ShellMode)
        {
            return;
        }

        if (State.MenuVisible)
        {
            Update(() => State.MoveSelection(1));
            return;
        }

        var (start, items) = Complete();
        Update(() =>
        {
            switch (items.Count)
            {
                case 0:
                    return;
                case 1:
                    State.ShowCompletions(start, items);
                    State.Accept(items[0]);
                    return;
            }

            var partial = State.Text[start..Math.Min(State.Caret, State.Text.Length)];
            var common = CommonPrefix(items.Select(item => item.Text));
            State.ShowCompletions(start, items);
            if (common.Length > partial.Length)
            {
                State.Replace(start, start + partial.Length, common);
            }
        });
    }

    private void Up()
    {
        if (State.MenuVisible)
        {
            State.MoveSelection(-1);
        }
        else if (State.History.Previous(State.Text) is { } previous)
        {
            State.SetText(previous);
        }
    }

    private void Down()
    {
        if (State.MenuVisible)
        {
            State.MoveSelection(1);
        }
        else if (State.History.Next() is { } next)
        {
            State.SetText(next);
        }
    }

    private void Escape()
    {
        if (State.MenuVisible)
        {
            State.HideCompletions();
        }
        else if (ShellMode)
        {
            ShellMode = false;
        }
    }

    private void Backspace()
    {
        if (State.Text.Length == 0)
        {
            ShellMode = false;
            return;
        }

        State.Editor.DeleteBackward();
        TextChanged();
    }

    private void CtrlD()
    {
        if (State.Text.Length == 0)
        {
            End(PromptOutcome.EndOfInput);
            return;
        }

        Update(() =>
        {
            State.Editor.DeleteForward();
            TextChanged();
        });
    }

    private void End(PromptOutcome outcome)
    {
        State.HideCompletions();
        Ended?.Invoke(new PromptResult(outcome, State.Text, ShellMode));
    }

    private void Update(Action action)
    {
        action();
        Changed?.Invoke();
    }

    private static string CommonPrefix(IEnumerable<string> values)
    {
        string? prefix = null;
        foreach (var value in values)
        {
            if (prefix is null)
            {
                prefix = value;
                continue;
            }

            var length = 0;
            while (length < prefix.Length && length < value.Length
                && char.ToLowerInvariant(prefix[length]) == char.ToLowerInvariant(value[length]))
            {
                length++;
            }

            prefix = prefix[..length];
        }

        return prefix ?? "";
    }
}
