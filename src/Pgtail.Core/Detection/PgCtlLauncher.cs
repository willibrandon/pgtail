namespace Pgtail.Detection;

/// <summary>
/// A server that <c>pg_ctl</c> starts and stops, with no tool that manages it.
/// </summary>
/// <param name="DataDirectory">The data directory.</param>
public sealed record PgCtlLauncher(string DataDirectory) : ServerLauncher
{
    /// <inheritdoc/>
    public override string Name => "pg_ctl";

    /// <inheritdoc/>
    public override string? OutputFile => null;

    /// <inheritdoc/>
    public override IReadOnlyList<string> RestartCommands(bool running) =>
        [$"pg_ctl {(running ? "restart" : "start")} -D {Argument(DataDirectory)}"];
}
