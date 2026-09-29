using Pgtail.Commands;
using Pgtail.Tail;
using Pgtail.Tailing;

namespace Pgtail.Repl;

/// <content>
/// Full screen tail mode, run as a full screen app between prompts.
/// </content>
internal sealed partial class ReplHost
{
    private async Task RunTailScreenAsync(TailRequest request)
    {
        Session.Buffer.Clear();
        var source = LogSources.Create(request, Session, CurrentDirectory, StandardInput);
        var screen = new TailScreen(Session, request, source, CurrentDirectory);
        try
        {
            await RunScreenAsync(screen.Configure);
        }
        finally
        {
            await screen.EndAsync();
        }
    }
}
