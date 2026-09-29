using System.Collections.Frozen;

namespace Pgtail.Parsing;

/// <summary>
/// Names, abbreviations, and ranges of PostgreSQL log levels.
/// </summary>
public static class LogLevels
{
    private static readonly FrozenDictionary<string, string> Aliases = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["ERR"] = "ERROR",
        ["WARN"] = "WARNING",
        ["INF"] = "INFO",
        ["DBG"] = "DEBUG1",
        ["DEBUG"] = "DEBUG1",
        ["FAT"] = "FATAL",
        ["PAN"] = "PANIC",
        ["NOT"] = "NOTICE",
        ["NTC"] = "NOTICE",
        ["E"] = "ERROR",
        ["W"] = "WARNING",
        ["I"] = "INFO",
        ["L"] = "LOG",
        ["D"] = "DEBUG1",
        ["F"] = "FATAL",
        ["P"] = "PANIC",
        ["N"] = "NOTICE",
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

    private static readonly FrozenDictionary<string, LogLevel> ParserMap = new Dictionary<string, LogLevel>(StringComparer.Ordinal)
    {
        ["PANIC"] = LogLevel.Panic,
        ["FATAL"] = LogLevel.Fatal,
        ["ERROR"] = LogLevel.Error,
        ["WARNING"] = LogLevel.Warning,
        ["NOTICE"] = LogLevel.Notice,
        ["LOG"] = LogLevel.Log,
        ["INFO"] = LogLevel.Info,
        ["DEBUG1"] = LogLevel.Debug1,
        ["DEBUG2"] = LogLevel.Debug2,
        ["DEBUG3"] = LogLevel.Debug3,
        ["DEBUG4"] = LogLevel.Debug4,
        ["DEBUG5"] = LogLevel.Debug5,
        ["DEBUG"] = LogLevel.Debug1,
        ["STATEMENT"] = LogLevel.Log,
        ["DETAIL"] = LogLevel.Log,
        ["HINT"] = LogLevel.Log,
        ["CONTEXT"] = LogLevel.Log,
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

    /// <summary>
    /// Every level, from the most severe to the least.
    /// </summary>
    public static IReadOnlyList<LogLevel> All { get; } = Enum.GetValues<LogLevel>();

    /// <summary>
    /// The upper case names of every level, from the most severe to the least.
    /// </summary>
    public static IReadOnlyList<string> Names { get; } = [.. Enum.GetValues<LogLevel>().Select(level => level.ToName())];

    /// <summary>
    /// The PostgreSQL name of a level, such as <c>ERROR</c> or <c>DEBUG1</c>.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <returns>The upper case name.</returns>
    public static string ToName(this LogLevel level) => level switch
    {
        LogLevel.Panic => "PANIC",
        LogLevel.Fatal => "FATAL",
        LogLevel.Error => "ERROR",
        LogLevel.Warning => "WARNING",
        LogLevel.Notice => "NOTICE",
        LogLevel.Log => "LOG",
        LogLevel.Info => "INFO",
        LogLevel.Debug1 => "DEBUG1",
        LogLevel.Debug2 => "DEBUG2",
        LogLevel.Debug3 => "DEBUG3",
        LogLevel.Debug4 => "DEBUG4",
        LogLevel.Debug5 => "DEBUG5",
        _ => throw new ArgumentOutOfRangeException(nameof(level), level, null),
    };

    /// <summary>
    /// A new set holding every level.
    /// </summary>
    /// <returns>The set.</returns>
    public static HashSet<LogLevel> AllSet() => [.. All];

    /// <summary>
    /// Parses a level name or abbreviation, ignoring case.
    /// </summary>
    /// <param name="name">A name such as <c>error</c>, or an abbreviation such as <c>e</c> or <c>warn</c>.</param>
    /// <returns>The level.</returns>
    /// <exception cref="FormatException">The name is not a level.</exception>
    public static LogLevel Parse(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        if (TryParse(name, out var level))
        {
            return level;
        }

        var abbreviations = string.Join(", ", Aliases.Keys.Order(StringComparer.Ordinal));
        throw new FormatException(
            $"Unknown log level '{name}'. Valid levels: {string.Join(", ", Names)}. Abbreviations: {abbreviations}");
    }

    /// <summary>
    /// Tries to parse a level name or abbreviation, ignoring case.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <param name="level">The level, when the name is one.</param>
    /// <returns>True when the name is a level.</returns>
    public static bool TryParse(string name, out LogLevel level)
    {
        ArgumentNullException.ThrowIfNull(name);
        var upper = name.ToUpperInvariant();
        if (Aliases.TryGetValue(upper, out var canonical))
        {
            upper = canonical;
        }

        foreach (var candidate in All)
        {
            if (candidate.ToName() == upper)
            {
                level = candidate;
                return true;
            }
        }

        level = default;
        return false;
    }

    /// <summary>
    /// Maps a severity written in a log line to a level, falling back to LOG for anything unknown.
    /// </summary>
    /// <remarks>
    /// Continuation labels such as STATEMENT, DETAIL, HINT, and CONTEXT count as LOG, and DEBUG counts as DEBUG1.
    /// </remarks>
    /// <param name="severity">The severity as written, in any case.</param>
    /// <returns>The level.</returns>
    public static LogLevel FromSeverity(string? severity) =>
        severity is not null && ParserMap.TryGetValue(severity.ToUpperInvariant(), out var level) ? level : LogLevel.Log;

    /// <summary>
    /// Every level at least as severe as a threshold.
    /// </summary>
    /// <param name="threshold">The threshold.</param>
    /// <returns>The threshold and every more severe level.</returns>
    public static HashSet<LogLevel> AtOrAbove(LogLevel threshold) => [.. All.Where(level => level <= threshold)];

    /// <summary>
    /// Every level at most as severe as a threshold.
    /// </summary>
    /// <param name="threshold">The threshold.</param>
    /// <returns>The threshold and every less severe level.</returns>
    public static HashSet<LogLevel> AtOrBelow(LogLevel threshold) => [.. All.Where(level => level >= threshold)];

    /// <summary>
    /// Whether an entry at a level passes a level filter.
    /// </summary>
    /// <param name="level">The entry's level.</param>
    /// <param name="active">The levels to show, or null to show every level.</param>
    /// <returns>True when the entry is shown.</returns>
    public static bool ShouldShow(LogLevel level, IReadOnlySet<LogLevel>? active) => active is null || active.Contains(level);

    /// <summary>
    /// Parses level arguments such as <c>ERROR</c>, <c>WARNING+</c>, <c>notice-</c>, or <c>e,w</c> into a set.
    /// </summary>
    /// <remarks>
    /// A trailing <c>+</c> takes the level and everything more severe, a trailing <c>-</c> the level and everything less
    /// severe. A single <c>ALL</c>, or no arguments, clears the filter.
    /// </remarks>
    /// <param name="arguments">The arguments.</param>
    /// <returns>The levels, or null for every level, and the arguments that were not levels.</returns>
    public static (HashSet<LogLevel>? Levels, List<string> Invalid) ParseArguments(IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        var invalid = new List<string>();
        if (arguments.Count == 0 || (arguments.Count == 1 && arguments[0].Equals("ALL", StringComparison.OrdinalIgnoreCase)))
        {
            return (null, invalid);
        }

        var levels = new HashSet<LogLevel>();
        foreach (var argument in arguments)
        {
            var upper = argument.ToUpperInvariant();
            if (upper.EndsWith('+'))
            {
                if (TryParse(upper[..^1], out var level))
                {
                    levels.UnionWith(AtOrAbove(level));
                }
                else
                {
                    invalid.Add(argument);
                }
            }
            else if (upper.EndsWith('-'))
            {
                if (TryParse(upper[..^1], out var level))
                {
                    levels.UnionWith(AtOrBelow(level));
                }
                else
                {
                    invalid.Add(argument);
                }
            }
            else if (TryParse(argument, out var level))
            {
                levels.Add(level);
            }
            else
            {
                invalid.Add(argument);
            }
        }

        return (levels.Count == 0 ? null : levels, invalid);
    }
}
