namespace Pgtail.Commands;

/// <summary>
/// Runs a command.
/// </summary>
/// <param name="invocation">The command as typed and where it runs.</param>
/// <returns>A task that completes when the command has finished.</returns>
internal delegate Task CommandHandler(CommandInvocation invocation);
