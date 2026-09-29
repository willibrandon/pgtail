using System.Globalization;
using System.Text;
using Pgtail.Commands;
using Pgtail.Sessions;

namespace Pgtail.Cli;

/// <summary>
/// Shell completion for bash, zsh, fish, and PowerShell: the scripts, their installation, and the answers they ask for.
/// </summary>
/// <remarks>
/// Each script calls <c>pgtail __complete SHELL -- WORDS</c>, which prints one candidate per line as
/// <c>value&lt;TAB&gt;description</c>.
/// </remarks>
internal static class ShellCompletion
{
    private static readonly string[] Shells = ["bash", "zsh", "fish", "pwsh"];

    private static readonly (string Name, string Description)[] GlobalOptions =
    [
        ("--version", "Show version and exit."),
        ("--check-update", "Check for updates and exit."),
        ("--install-completion", "Install completion for the current shell."),
        ("--show-completion", "Show completion for the current shell."),
        ("--help", "Show this message and exit."),
    ];

    /// <summary>
    /// Runs <c>--show-completion</c>, <c>--install-completion</c>, or <c>__complete</c>.
    /// </summary>
    /// <param name="arguments">The parsed command line.</param>
    /// <returns>The exit code.</returns>
    public static int Run(CliArguments arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        if (arguments.Command == CliCommand.Complete)
        {
            foreach (var (value, description) in Candidates(arguments.Words))
            {
                Console.Out.WriteLine(description.Length > 0 ? $"{value}\t{description}" : value);
            }

            return 0;
        }

        var shell = arguments.Shell ?? DetectShell();
        if (shell is null || !Shells.Contains(shell))
        {
            Console.Error.WriteLine($"Shell {shell ?? "(unknown)"} is not supported. Use one of: {string.Join(", ", Shells)}");
            return 1;
        }

        if (arguments.Command == CliCommand.ShowCompletion)
        {
            Console.Out.Write(Script(shell));
            return 0;
        }

        var path = Install(shell);
        Console.Out.WriteLine($"{shell} completion installed in {path}");
        Console.Out.WriteLine("Completion will take effect once you restart the terminal");
        return 0;
    }

    /// <summary>
    /// The completion script for a shell.
    /// </summary>
    /// <param name="shell">The shell.</param>
    /// <returns>The script.</returns>
    public static string Script(string shell) => shell switch
    {
        "bash" => """
            _pgtail_completion() {
                local IFS=$'\n'
                COMPREPLY=($(pgtail __complete bash -- "${COMP_WORDS[@]:1:COMP_CWORD}" 2>/dev/null | cut -f1))
                return 0
            }
            complete -o default -F _pgtail_completion pgtail

            """,
        "zsh" => """
            #compdef pgtail
            _pgtail_completion() {
                local -a completions
                local line
                for line in "${(@f)$(pgtail __complete zsh -- "${(@)words[2,CURRENT]}" 2>/dev/null)}"; do
                    [[ -z "$line" ]] && continue
                    completions+=("${${line%%$'\t'*}//:/\\:}:${line#*$'\t'}")
                done
                _describe 'pgtail' completions
            }
            compdef _pgtail_completion pgtail

            """,
        "fish" => """
            function __pgtail_complete
                set -l tokens (commandline -opc) (commandline -ct)
                pgtail __complete fish -- $tokens[2..-1] 2>/dev/null
            end
            complete -c pgtail -f -a '(__pgtail_complete)'

            """,
        _ => """
            Register-ArgumentCompleter -Native -CommandName pgtail -ScriptBlock {
                param($wordToComplete, $commandAst, $cursorPosition)
                $words = @($commandAst.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.ToString() })
                if ($wordToComplete -eq '') { $words += '' }
                pgtail __complete pwsh -- @words 2>$null | ForEach-Object {
                    $parts = $_ -split "`t", 2
                    $description = if ($parts.Count -gt 1) { $parts[1] } else { $parts[0] }
                    [System.Management.Automation.CompletionResult]::new($parts[0], $parts[0], 'ParameterValue', $description)
                }
            }

            """,
    };

    /// <summary>
    /// The candidates for the last word of a command line.
    /// </summary>
    /// <param name="words">The words after <c>pgtail</c>; the last one is being typed and may be empty.</param>
    /// <returns>The candidates and their descriptions.</returns>
    public static IEnumerable<(string Value, string Description)> Candidates(IReadOnlyList<string> words)
    {
        ArgumentNullException.ThrowIfNull(words);
        var partial = words.Count > 0 ? words[^1] : "";
        var before = words.Count > 1 ? words.Take(words.Count - 1).ToList() : [];
        IEnumerable<(string Value, string Description)> items;
        if (before is [.., "--install-completion" or "--show-completion"])
        {
            items = Shells.Select(shell => (shell, $"{shell} completion"));
        }
        else if (before.Count == 0)
        {
            items = GlobalOptions.Concat(CliParser.Commands);
        }
        else
        {
            items = before[0] switch
            {
                "tail" => Tail(before, partial),
                "list-instances" or "list" => [("--verbose", "Show detailed instance information."), ("--help",
                    "Show this message and exit.")],
                "config" => [("--path", "Show config file path."), ("--edit", "Open config in the built-in editor."),
                    ("--reset", "Reset to defaults (creates backup)."), ("--help", "Show this message and exit.")],
                "enable-logging" => Instances(),
                _ => [],
            };
        }

        return items.Where(item => item.Value.StartsWith(partial, StringComparison.Ordinal));
    }

    private static IEnumerable<(string Value, string Description)> Tail(List<string> before, string partial)
    {
        if (before[^1] is "--file" or "-f")
        {
            var session = PgtailSession.ForCurrentUser();
            var context = new CompletionContext(session, [], partial, Environment.CurrentDirectory);
            return CompletionSources.Paths(context).Select(item => (item.Text, ""));
        }

        if (before[^1] is "--since" or "-s")
        {
            return [("5m", "Last 5 minutes"), ("30m", "Last 30 minutes"), ("1h", "Last hour"), ("2h", "Last 2 hours"), ("1d", "Last day")];
        }

        IEnumerable<(string, string)> options =
        [
            ("--file", "Path or glob pattern to tail."),
            ("--stdin", "Read log data from stdin pipe."),
            ("--since", "Show entries from time (e.g., 5m, 1h, 14:30)."),
            ("--stream", "Print entries to standard output."),
            ("--help", "Show this message and exit."),
        ];
        return partial.StartsWith('-') ? options : Instances().Concat(options);
    }

    private static IEnumerable<(string Value, string Description)> Instances()
    {
        var session = PgtailSession.ForCurrentUser();
        session.Refresh();
        return session.Instances.Select(instance => (instance.Id.ToString(CultureInfo.InvariantCulture),
            $"PG{instance.Version}:{instance.PortText} ({instance.StatusText})"));
    }

    private static string? DetectShell()
    {
        if (OperatingSystem.IsWindows())
        {
            return "pwsh";
        }

        if (Environment.GetEnvironmentVariable("SHELL") is not { Length: > 0 } shell)
        {
            return null;
        }

        var name = Path.GetFileName(shell);
        return name is "powershell" ? "pwsh" : name;
    }

    private static string Install(string shell)
    {
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var script = Script(shell);
        switch (shell)
        {
            case "bash":
                var bashScript = Path.Combine(home, ".bash_completions", "pgtail.sh");
                Write(bashScript, script);
                AppendOnce(Path.Combine(home, ".bashrc"), $"source {bashScript}");
                return bashScript;
            case "zsh":
                var zshScript = Path.Combine(home, ".zfunc", "_pgtail");
                Write(zshScript, script);
                AppendOnce(Path.Combine(home, ".zshrc"), "fpath+=~/.zfunc");
                AppendOnce(Path.Combine(home, ".zshrc"), "autoload -Uz compinit && compinit");
                return zshScript;
            case "fish":
                var fishScript = Path.Combine(home, ".config", "fish", "completions", "pgtail.fish");
                Write(fishScript, script);
                return fishScript;
            default:
                var profile = OperatingSystem.IsWindows()
                    ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "PowerShell",
                        "Microsoft.PowerShell_profile.ps1")
                    : Path.Combine(home, ".config", "powershell", "Microsoft.PowerShell_profile.ps1");
                if (!File.Exists(profile) || !File.ReadAllText(profile).Contains("-CommandName pgtail", StringComparison.Ordinal))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(profile)!);
                    File.AppendAllText(profile, "\n" + script, new UTF8Encoding(false));
                }

                return profile;
        }
    }

    private static void Write(string path, string text)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, text, new UTF8Encoding(false));
    }

    private static void AppendOnce(string path, string line)
    {
        if (File.Exists(path) && File.ReadLines(path).Any(existing => existing.Trim() == line))
        {
            return;
        }

        File.AppendAllText(path, $"\n{line}\n", new UTF8Encoding(false));
    }
}
