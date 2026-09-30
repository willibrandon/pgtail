using System;
using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Text;

namespace Pgtail.Analyzers;

/// <summary>
/// Holds every documentation summary to three lines: the opening tag, one line of text, and the closing tag.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class SummaryLinesAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.s_summaryIsNotThreeLines);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxTreeAction(AnalyzeTree);
    }

    // Documentation is structured trivia, which a walk of the nodes reaches only when it is asked to descend into trivia.
    private static void AnalyzeTree(SyntaxTreeAnalysisContext context)
    {
        SourceText text = context.Tree.GetText(context.CancellationToken);
        SyntaxNode root = context.Tree.GetRoot(context.CancellationToken);

        // "<summary />" is an element of another kind, and it has no line of text at all.
        foreach (XmlEmptyElementSyntax? empty in root.DescendantNodes(descendIntoTrivia: true).OfType<XmlEmptyElementSyntax>()
            .Where(element => element.Name.LocalName.ValueText == "summary"))
        {
            context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_summaryIsNotThreeLines, empty.GetLocation()));
        }

        foreach (XmlElementSyntax? summary in root.DescendantNodes(descendIntoTrivia: true).OfType<XmlElementSyntax>()
            .Where(element => element.StartTag.Name.LocalName.ValueText == "summary"))
        {
            TextLine first = text.Lines.GetLineFromPosition(summary.StartTag.SpanStart);
            TextLine last = text.Lines.GetLineFromPosition(summary.EndTag.SpanStart);

            // Nothing but the tag stands on the first line and on the last, and one line of text lies between them.
            string afterOpening = text.ToString(TextSpan.FromBounds(summary.StartTag.Span.End, first.End));
            string beforeClosing = text.ToString(TextSpan.FromBounds(last.Start, summary.EndTag.SpanStart));
            string between = last.LineNumber - first.LineNumber == 2 ? text.Lines[first.LineNumber + 1].ToString().Trim() : "";
            if (afterOpening.Trim().Length != 0 || beforeClosing.Trim() != "///" || !between.StartsWith("///", StringComparison.Ordinal)
                || between.Substring(3).Trim().Length == 0)
            {
                context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_summaryIsNotThreeLines, summary.StartTag.GetLocation()));
            }
        }
    }
}
