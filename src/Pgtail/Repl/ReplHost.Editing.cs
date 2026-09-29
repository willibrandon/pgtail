using Pgtail.Commands;
using Pgtail.Editing;

namespace Pgtail.Repl;

/// <content>
/// The built-in editor, run as a full screen app between prompts.
/// </content>
internal sealed partial class ReplHost
{
    /// <inheritdoc/>
    public async Task<bool> EditAsync(EditRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var screen = new FileEditorScreen(request);
        await RunScreenAsync((app, options) =>
        {
            options.EnableDefaultCtrlCExit = false;
            FileEditorScreen.Focus(app);
            return context => screen.Build(context, app.RequestStop);
        });

        return screen.Saved;
    }
}
