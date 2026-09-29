using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace Pgtail.Analyzers;

/// <summary>
/// Requires a parameter list that spans more than one line to give every parameter a line of its own.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class StackedParametersAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.ParametersAreNotStacked);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxNodeAction(AnalyzeParameters, SyntaxKind.ParameterList, SyntaxKind.BracketedParameterList,
            SyntaxKind.FunctionPointerParameterList, SyntaxKind.TypeParameterList);
    }

    private static void AnalyzeParameters(SyntaxNodeAnalysisContext context)
    {
        var list = context.Node;
        var parameters = list switch
        {
            FunctionPointerParameterListSyntax pointer => pointer.Parameters.Cast<SyntaxNode>().ToList(),
            TypeParameterListSyntax types => types.Parameters.Cast<SyntaxNode>().ToList(),
            _ => ((BaseParameterListSyntax)list).Parameters.Cast<SyntaxNode>().ToList(),
        };

        if (parameters.Count == 0)
        {
            return;
        }

        var tree = list.SyntaxTree;
        var span = tree.GetLineSpan(list.Span);
        if (span.StartLinePosition.Line == span.EndLinePosition.Line)
        {
            return;
        }

        foreach (var parameter in parameters)
        {
            var first = parameter.GetFirstToken();
            var previous = first.GetPreviousToken();
            var startsItsLine = tree.GetLineSpan(previous.Span).EndLinePosition.Line != tree.GetLineSpan(first.Span).StartLinePosition.Line;
            if (!startsItsLine)
            {
                var name = parameter switch
                {
                    ParameterSyntax named => named.Identifier.ValueText,
                    TypeParameterSyntax generic => generic.Identifier.ValueText,
                    _ => parameter.ToString(),
                };

                context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.ParametersAreNotStacked, parameter.GetLocation(), name));
            }
        }
    }
}
