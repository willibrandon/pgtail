using Pgtail.Filtering;
using Pgtail.Parsing;

namespace Pgtail.Tail;

/// <summary>
/// The filters tail mode started with, which <c>clear</c> returns to.
/// </summary>
/// <param name="Levels">The levels shown, or null for all.</param>
/// <param name="Regex">The regular expression filters.</param>
/// <param name="Time">The time filter.</param>
internal sealed record FilterAnchor(HashSet<LogLevel>? Levels, RegexFilterState Regex, TimeFilter Time);
