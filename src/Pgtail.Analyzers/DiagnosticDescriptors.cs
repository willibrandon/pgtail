using Microsoft.CodeAnalysis;

namespace Pgtail.Analyzers;

/// <summary>
/// The layout rules this repository enforces beyond those the .NET SDK provides.
/// </summary>
internal static class DiagnosticDescriptors
{
    /// <summary>
    /// A block, type, namespace, or switch is never written on one line, and each of its braces stands alone on its line.
    /// </summary>
    internal static readonly DiagnosticDescriptor BlockIsNotExpanded = new(
        id: "PGTAIL0001",
        title: "A block's braces stand on their own lines",
        messageFormat: "Put this block's braces on their own lines",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A parameter list that does not fit on one line gives every parameter a line of its own.
    /// </summary>
    internal static readonly DiagnosticDescriptor ParametersAreNotStacked = new(
        id: "PGTAIL0002",
        title: "Parameters that wrap are stacked one to a line",
        messageFormat: "Put parameter '{0}' on its own line, because this parameter list spans more than one line",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A System type is named through a using directive unless its short name would mean something else where it is written.
    /// </summary>
    internal static readonly DiagnosticDescriptor NameIsQualified = new(
        id: "PGTAIL0004",
        title: "A System type is imported instead of written out in full",
        messageFormat: "Import '{0}' with a using directive and write '{1}'",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A closing brace is followed by a blank line before the comment or member that comes next.
    /// </summary>
    internal static readonly DiagnosticDescriptor BlankLineAfterBrace = new(
        id: "PGTAIL0005",
        title: "A line that begins with a closing brace is followed by a blank line",
        messageFormat: "Leave a blank line after the closing brace above",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A public or internal type or member carries XML documentation.
    /// </summary>
    internal static readonly DiagnosticDescriptor MemberIsNotDocumented = new(
        id: "PGTAIL0007",
        title: "A public or internal type or member is documented",
        messageFormat: "Document '{0}' with a triple slash XML comment",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A documentation summary takes the opening tag, one line of text, and the closing tag.
    /// </summary>
    internal static readonly DiagnosticDescriptor SummaryIsNotThreeLines = new(
        id: "PGTAIL0006",
        title: "A summary takes exactly three lines",
        messageFormat: "Write this summary as three lines: the opening tag, one line of text, and the closing tag",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);

    /// <summary>
    /// A line stays within the max_line_length set in the editor configuration.
    /// </summary>
    internal static readonly DiagnosticDescriptor LineIsTooLong = new(
        id: "PGTAIL0003",
        title: "A line fits within max_line_length",
        messageFormat: "This line is {0} characters long; the limit is {1}",
        category: "Pgtail.Layout",
        defaultSeverity: DiagnosticSeverity.Error,
        isEnabledByDefault: true);
}
