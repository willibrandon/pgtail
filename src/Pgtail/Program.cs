using Hex1b;
using Hex1b.Surfaces;
using Hex1b.Theming;
using Hex1b.Widgets;

await using var terminal = Hex1bTerminal.CreateBuilder()
    .WithHex1bApp(ctx => ctx.VStack(v =>
    [
        v.Text("pgtail prototype " + string.Join(' ', args)),
        v.Separator(),
        v.Interactable(i => i.Surface(s =>
        [
            s.Layer(surface =>
            {
                var text = "surface row";
                for (var x = 0; x < text.Length && x < surface.Width; x++)
                {
                    surface[x, 0] = SurfaceCells.Char(text[x], Hex1bColor.Green, null, CellAttributes.Bold);
                }
            }),
        ])).Fill(),
        v.Separator(),
        v.TextBox().Predict((text, _) => Task.FromResult<string?>(text == "lev" ? "el" : null)),
        v.InfoBar(b => [b.Section("FOLLOW"), b.Section("E:0 W:0")]),
    ]))
    .Build();
return await terminal.RunAsync();
