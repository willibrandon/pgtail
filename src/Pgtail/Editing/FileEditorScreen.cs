using System.Text;
using Hex1b;
using Hex1b.Documents;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Commands;

namespace Pgtail.Editing;

/// <summary>
/// The built-in full screen editor for configuration and theme files.
/// </summary>
/// <remarks>
/// Ctrl+S checks the text and saves it when it is valid; problems are listed at the bottom instead. Escape or Ctrl+Q
/// closes the editor; with unsaved changes the first press warns and a second press discards them.
/// </remarks>
internal sealed class FileEditorScreen
{
    private readonly EditRequest _request;
    private readonly EditorState _editor;
    private readonly TomlDecorationProvider _decorations = new();
    private long _savedVersion;
    private bool _discardArmed;
    private string _status;

    /// <summary>
    /// Loads the file, or the request's initial text when it does not exist.
    /// </summary>
    /// <param name="request">The file to edit.</param>
    public FileEditorScreen(EditRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        _request = request;
        var text = File.Exists(request.Path) ? File.ReadAllText(request.Path, Encoding.UTF8) : request.InitialText;
        _editor = new EditorState(new Hex1bDocument(text));
        _savedVersion = _editor.Document.Version;
        _status = File.Exists(request.Path) ? "" : "New file";
    }

    /// <summary>
    /// Whether the file was saved at least once.
    /// </summary>
    public bool Saved { get; private set; }

    /// <summary>
    /// Builds the screen.
    /// </summary>
    /// <param name="context">The root context.</param>
    /// <param name="close">Closes the editor.</param>
    /// <returns>The widget tree.</returns>
    public Hex1bWidget Build(RootContext context, Action close)
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(close);
        var dirty = _editor.Document.Version != _savedVersion;
        var title = $" {_request.Title}{(dirty ? " [modified]" : "")}";
        return context.VStack(v =>
        [
            v.InfoBar(b => [b.Section(title), b.Section("Ctrl+S save · Esc close")]),
            v.Editor(_editor)
                .LineNumbers()
                .Decorations(_decorations)
                .OnTextChanged(_ => _discardArmed = false)
                .InputBindings(b =>
                {
                    b.Ctrl().Key(Hex1bKey.S).Action(_ => Save(), "Save");
                    b.Remove(Hex1bKey.Escape);
                    b.Key(Hex1bKey.Escape).Action(_ => Close(close), "Close");
                    b.Ctrl().Key(Hex1bKey.Q).Action(_ => Close(close), "Close");
                })
                .Fill(),
            v.InfoBar(b => [b.Section(_status.Length == 0 ? " " : " " + _status)], invertColors: false),
        ]);
    }

    /// <summary>
    /// Puts the caret in the editor.
    /// </summary>
    /// <param name="app">The app.</param>
    public static void Focus(Hex1bApp app)
    {
        ArgumentNullException.ThrowIfNull(app);
        app.RequestFocus(node => node is EditorNode);
    }

    private void Save()
    {
        var text = _editor.Document.GetText();
        var problems = _request.Validate(text);
        if (problems.Count > 0)
        {
            _status = "Not saved: " + string.Join("; ", problems);
            return;
        }

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(_request.Path)!);
            File.WriteAllText(_request.Path, text, new UTF8Encoding(false));
            _savedVersion = _editor.Document.Version;
            Saved = true;
            _status = $"Saved {_request.Path}";
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            _status = $"Not saved: {exception.Message}";
        }
    }

    private void Close(Action close)
    {
        if (_editor.Document.Version != _savedVersion && !_discardArmed)
        {
            _discardArmed = true;
            _status = "Unsaved changes. Ctrl+S to save, Esc again to discard.";
            return;
        }

        close();
    }
}
