using Hex1b;
using Hex1b.Automation;
using Hex1b.Input;

namespace Pgtail.Tests;

/// <summary>
/// Confirms that the prototype renders through a headless Hex1b terminal.
/// </summary>
[TestClass]
public sealed class PrototypeTests
{
    /// <summary>
    /// Supplies cancellation for the terminal run.
    /// </summary>
    public TestContext TestContext { get; set; } = null!;

    /// <summary>
    /// The prototype draws its surface row and accepts a prediction with the right arrow.
    /// </summary>
    /// <returns>A task that completes when the check has run.</returns>
    [TestMethod]
    public async Task Prototype_TypesPrefix_AcceptsPrediction()
    {
        var ct = TestContext.CancellationToken;
        await using var terminal = Hex1bTerminal.CreateBuilder()
            .WithHex1bApp(ctx => ctx.VStack(v =>
            [
                v.Text("header"),
                v.TextBox().Predict((text, _) => Task.FromResult<string?>(text == "lev" ? "el" : null)),
            ]))
            .WithHeadless()
            .WithDimensions(60, 10)
            .Build();

        var run = terminal.RunAsync(ct);
        var auto = new Hex1bTerminalAutomator(terminal, defaultTimeout: TimeSpan.FromSeconds(10));
        await auto.WaitUntilTextAsync("header");
        await auto.TypeAsync("lev", ct: ct);
        await auto.WaitUntilTextAsync("level");
        await auto.RightAsync(ct: ct);
        await auto.TypeAsync(" x", ct: ct);
        await auto.WaitUntilTextAsync("level x");
        await auto.Ctrl().KeyAsync(Hex1bKey.C, ct: ct);
        await run.WaitAsync(TimeSpan.FromSeconds(10), ct);
    }
}
