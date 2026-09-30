using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace Pgtail.Analyzers;

/// <summary>
/// Asks for a using directive where a System type is written out in full although its short name would mean the same type.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class QualifiedNameAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.s_nameIsQualified);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxNodeAction(AnalyzeName, SyntaxKind.QualifiedName, SyntaxKind.SimpleMemberAccessExpression,
            SyntaxKind.QualifiedCref);
    }

    private static void AnalyzeName(SyntaxNodeAnalysisContext context)
    {
        SyntaxNode node = context.Node;
        if (!StartsAtSystem(node) || node.Ancestors().Any(ancestor => ancestor is UsingDirectiveSyntax))
        {
            return;
        }

        (SyntaxNode Left, SyntaxNode Written) parts = node switch
        {
            QualifiedNameSyntax qualified => (qualified.Left, qualified.Right),
            MemberAccessExpressionSyntax access => (access.Expression, access.Name),
            _ => (((QualifiedCrefSyntax)node).Container, ((QualifiedCrefSyntax)node).Member),
        };

        (SyntaxNode? left, SyntaxNode? written) = parts;
        SemanticModel model = context.SemanticModel;
        ISymbol? symbol = model.GetSymbolInfo(node, context.CancellationToken).Symbol;

        // An attribute's name binds to the constructor it calls rather than to the type.
        if (symbol is IMethodSymbol { MethodKind: MethodKind.Constructor } constructor && node.Parent is AttributeSyntax)
        {
            symbol = constructor.ContainingType;
        }

        if (symbol is not INamedTypeSymbol type || model.GetSymbolInfo(left, context.CancellationToken).Symbol is not INamespaceSymbol)
        {
            return;
        }

        INamespaceSymbol root = type.ContainingNamespace;
        while (root.ContainingNamespace is { IsGlobalNamespace: false } outer)
        {
            root = outer;
        }

        if (root.Name != "System")
        {
            return;
        }

        // The full name stays where the short one already means something else, such as a Mono.Cecil type or a member.
        // An attribute is looked up under both of its names, because "Flags" is written for FlagsAttribute.
        SyntaxNode simple = written is NameMemberCrefSyntax member ? member.Name : written;
        string spelled = simple is SimpleNameSyntax { Identifier.ValueText: var text } ? text : type.Name;
        foreach (string? candidate in new[] { type.Name, spelled }.Distinct())
        {
            if (model.LookupSymbols(node.SpanStart, name: candidate).Any(other => IsRival(other, type)))
            {
                return;
            }
        }

        context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_nameIsQualified, node.GetLocation(),
            type.ContainingNamespace.ToDisplayString(), written.ToString()));
    }

    // A type with another number of type arguments, as IList<T> beside IList, does not compete for the short name.
    private static bool IsRival(ISymbol other, INamedTypeSymbol type) =>
        (other is not INamedTypeSymbol named || named.Arity == type.Arity)
        && !SymbolEqualityComparer.Default.Equals(other.OriginalDefinition, type.OriginalDefinition);

    // The name is read from its tokens, so a line break or a comment inside it changes nothing.
    private static bool StartsAtSystem(SyntaxNode node)
    {
        while (true)
        {
            switch (node)
            {
                case QualifiedNameSyntax qualified:
                    node = qualified.Left;
                    break;
                case MemberAccessExpressionSyntax access:
                    node = access.Expression;
                    break;
                case QualifiedCrefSyntax cref:
                    node = cref.Container;
                    break;
                case AliasQualifiedNameSyntax alias:
                    return alias.Alias.Identifier.IsKind(SyntaxKind.GlobalKeyword) && alias.Name.Identifier.ValueText == "System";
                case IdentifierNameSyntax identifier:
                    return identifier.Identifier.ValueText == "System";
                default:
                    return false;
            }
        }
    }
}
