using System;
using System.Collections.Immutable;
using System.Globalization;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Text;

namespace Pgtail.Analyzers;

/// <summary>
/// Holds every line to the max_line_length the editor configuration sets for its file.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class LineLengthAnalyzer : DiagnosticAnalyzer
{
    private static readonly char[] s_blanks = { ' ', '\t' };

    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.LineIsTooLong);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxTreeAction(AnalyzeTree);
    }

    private static void AnalyzeTree(SyntaxTreeAnalysisContext context)
    {
        var options = context.Options.AnalyzerConfigOptionsProvider.GetOptions(context.Tree);
        if (!options.TryGetValue("max_line_length", out var configured)
            || !int.TryParse(configured, NumberStyles.None, CultureInfo.InvariantCulture, out var limit))
        {
            return;
        }

        foreach (var line in context.Tree.GetText(context.CancellationToken).Lines)
        {
            var length = line.Span.Length;
            if (length <= limit || IsUnbreakable(line))
            {
                continue;
            }

            var overflow = TextSpan.FromBounds(line.Start + limit, line.End);
            context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.LineIsTooLong,
                Location.Create(context.Tree, overflow), length, limit));
        }
    }

    // Only a comment can hold a single word with nowhere to break, such as a link. Code can always be wrapped.
    private static bool IsUnbreakable(TextLine line)
    {
        var text = line.ToString().Trim();
        if (text.StartsWith("///", StringComparison.Ordinal))
        {
            text = text.Substring(3).TrimStart();
        }
        else if (text.StartsWith("//", StringComparison.Ordinal))
        {
            text = text.Substring(2).TrimStart();
        }
        else
        {
            return false;
        }

        return text.IndexOfAny(s_blanks) < 0;
    }
}
