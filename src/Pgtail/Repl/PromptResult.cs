namespace Pgtail.Repl;

/// <summary>
/// The line the prompt ended with, and how it ended.
/// </summary>
/// <param name="Outcome">How it ended.</param>
/// <param name="Text">The line as it stood.</param>
/// <param name="Shell">True when the line was typed in shell mode.</param>
internal sealed record PromptResult(PromptOutcome Outcome, string Text, bool Shell);
