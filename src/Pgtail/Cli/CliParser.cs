using System.Globalization;
namespace Pgtail.Cli;

/// <summary>
/// Parses pgtail's command line.
/// </summary>
internal static class CliParser
{
    /// <summary>
    /// The commands, with their aliases.
    /// </summary>
    public static IReadOnlyList<(string Name, string Description)> Commands { get; } =
    [
        ("list-instances", "List detected PostgreSQL instances."),
        ("tail", "Tail logs for a PostgreSQL instance or arbitrary log file(s)."),
        ("config", "Show or manage configuration."),
        ("enable-logging", "Enable logging_collector for an instance."),
    ];

    /// <summary>
    /// Parses arguments.
    /// </summary>
    /// <param name="args">The arguments.</param>
    /// <returns>The parsed command line.</returns>
    /// <exception cref="CliParseException">The arguments are not valid.</exception>
    public static CliArguments Parse(IReadOnlyList<string> args)
    {
        ArgumentNullException.ThrowIfNull(args);
        var index = 0;
        while (index < args.Count)
        {
            var argument = args[index];
            switch (argument)
            {
                case "--version" or "-V":
                    return new CliArguments { Command = CliCommand.Version };
                case "--check-update":
                    return new CliArguments { Command = CliCommand.CheckUpdate };
                case "--help" or "-h":
                    return new CliArguments { Command = CliCommand.Help };
                case "--show-completion" or "--install-completion":
                    var shell = index + 1 < args.Count && !args[index + 1].StartsWith('-') ? args[index + 1] : null;
                    return new CliArguments
                    {
                        Command = argument == "--show-completion" ? CliCommand.ShowCompletion : CliCommand.InstallCompletion,
                        Shell = shell,
                    };

                case "__complete":
                    return new CliArguments
                    {
                        Command = CliCommand.Complete,
                        Shell = index + 1 < args.Count ? args[index + 1] : null,
                        Words = [.. args.Skip(index + 2).SkipWhile(word => word == "--")],
                    };

                case var option when option.StartsWith('-'):
                    throw new CliParseException($"No such option: {option}", null);
                default:
                    return ParseCommand(argument, [.. args.Skip(index + 1)]);
            }
        }

        return new CliArguments();
    }

    private static CliArguments ParseCommand(string name, List<string> args)
    {
        if (args.Contains("--help") || args.Contains("-h"))
        {
            return new CliArguments { Command = CliCommand.Help, HelpFor = Canonical(name) ?? throw NoSuchCommand(name) };
        }

        return Canonical(name) switch
        {
            "list-instances" => ParseList(args),
            "tail" => ParseTail(args),
            "config" => ParseConfig(args),
            "enable-logging" => ParseEnableLogging(args),
            _ => throw NoSuchCommand(name),
        };
    }

    private static string? Canonical(string name) => name switch
    {
        "list-instances" or "list" => "list-instances",
        "tail" or "config" or "enable-logging" => name,
        _ => null,
    };

    private static CliParseException NoSuchCommand(string name) => new($"No such command '{name}'.", null);

    private static CliArguments ParseList(List<string> args)
    {
        var verbose = false;
        foreach (var argument in args)
        {
            verbose = argument is "--verbose" or "-v" ? true : throw Unexpected(argument, "list-instances");
        }

        return new CliArguments { Command = CliCommand.ListInstances, Verbose = verbose };
    }

    private static CliArguments ParseTail(List<string> args)
    {
        var files = new List<string>();
        var (stdin, stream) = (false, false);
        string? since = null;
        string? instance = null;
        for (var i = 0; i < args.Count; i++)
        {
            var argument = args[i];
            switch (argument)
            {
                case "--file" or "-f":
                    files.Add(Value(args, ref i, argument, "tail"));
                    break;
                case var option when option.StartsWith("--file=", StringComparison.Ordinal):
                    files.Add(option["--file=".Length..]);
                    break;
                case "--since" or "-s":
                    since = Value(args, ref i, argument, "tail");
                    break;
                case var option when option.StartsWith("--since=", StringComparison.Ordinal):
                    since = option["--since=".Length..];
                    break;
                case "--stdin":
                    stdin = true;
                    break;
                case "--stream":
                    stream = true;
                    break;
                case var option when option.StartsWith('-') && option.Length > 1:
                    throw new CliParseException($"No such option: {option}", "tail");
                default:
                    if (instance is not null)
                    {
                        throw new CliParseException($"Got unexpected extra argument ({argument})", "tail");
                    }

                    if (!int.TryParse(argument, NumberStyles.None, CultureInfo.InvariantCulture, out _))
                    {
                        throw new CliParseException($"Invalid value for '[INSTANCE_ID]': '{argument}' is not a valid integer.", "tail");
                    }

                    instance = argument;
                    break;
            }
        }

        return new CliArguments
        {
            Command = CliCommand.Tail,
            Files = files,
            Stdin = stdin,
            Since = since,
            Stream = stream,
            Instance = instance,
        };
    }

    private static CliArguments ParseConfig(List<string> args)
    {
        var (path, edit, reset) = (false, false, false);
        foreach (var argument in args)
        {
            switch (argument)
            {
                case "--path" or "-p":
                    path = true;
                    break;
                case "--edit" or "-e":
                    edit = true;
                    break;
                case "--reset":
                    reset = true;
                    break;
                default:
                    throw Unexpected(argument, "config");
            }
        }

        return new CliArguments { Command = CliCommand.Config, ConfigPath = path, ConfigEdit = edit, ConfigReset = reset };
    }

    private static CliArguments ParseEnableLogging(List<string> args)
    {
        if (args.Count == 0)
        {
            throw new CliParseException("Missing argument 'INSTANCE'.", "enable-logging");
        }

        if (args.Count > 1)
        {
            throw new CliParseException($"Got unexpected extra argument ({args[1]})", "enable-logging");
        }

        return args[0].StartsWith('-')
            ? throw new CliParseException($"No such option: {args[0]}", "enable-logging")
            : new CliArguments { Command = CliCommand.EnableLogging, Instance = args[0] };
    }

    private static string Value(List<string> args, ref int index, string option, string command)
    {
        if (index + 1 >= args.Count)
        {
            throw new CliParseException($"Option '{option}' requires an argument.", command);
        }

        index++;
        return args[index];
    }

    private static CliParseException Unexpected(string argument, string command) => argument.StartsWith('-')
        ? new CliParseException($"No such option: {argument}", command)
        : new CliParseException($"Got unexpected extra argument ({argument})", command);
}
