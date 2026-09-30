using System.Collections.Generic;
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
        ImmutableArray.Create(DiagnosticDescriptors.s_parametersAreNotStacked);

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
        SyntaxNode list = context.Node;
        List<SyntaxNode> parameters = list switch
        {
            FunctionPointerParameterListSyntax pointer => [.. pointer.Parameters.Cast<SyntaxNode>()],
            TypeParameterListSyntax types => [.. types.Parameters.Cast<SyntaxNode>()],
            _ => [.. ((BaseParameterListSyntax)list).Parameters.Cast<SyntaxNode>()],
        };

        if (parameters.Count == 0)
        {
            return;
        }

        SyntaxTree tree = list.SyntaxTree;
        FileLinePositionSpan span = tree.GetLineSpan(list.Span);
        if (span.StartLinePosition.Line == span.EndLinePosition.Line)
        {
            return;
        }

        foreach (SyntaxNode? parameter in parameters)
        {
            SyntaxToken first = parameter.GetFirstToken();
            SyntaxToken previous = first.GetPreviousToken();
            bool startsItsLine = tree.GetLineSpan(previous.Span).EndLinePosition.Line
                != tree.GetLineSpan(first.Span).StartLinePosition.Line;
            if (!startsItsLine)
            {
                string name = parameter switch
                {
                    ParameterSyntax named => named.Identifier.ValueText,
                    TypeParameterSyntax generic => generic.Identifier.ValueText,
                    _ => parameter.ToString(),
                };

                context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_parametersAreNotStacked, parameter.GetLocation(), name));
            }
        }
    }
}
