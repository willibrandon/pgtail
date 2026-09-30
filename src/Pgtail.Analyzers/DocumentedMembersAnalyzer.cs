using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace Pgtail.Analyzers;

/// <summary>
/// Asks for XML documentation on every public or internal type and member, which the compiler checks for public ones only.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class DocumentedMembersAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.s_memberIsNotDocumented);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSymbolAction(AnalyzeSymbol, SymbolKind.NamedType, SymbolKind.Method, SymbolKind.Property, SymbolKind.Field,
            SymbolKind.Event);
    }

    private static void AnalyzeSymbol(SymbolAnalysisContext context)
    {
        ISymbol symbol = context.Symbol;
        if (symbol.IsImplicitlyDeclared || !IsVisible(symbol) || !IsWritten(symbol))
        {
            return;
        }

        // A partial type is documented once, on whichever part carries the comment, and the symbol sees all of its parts.
        // The comment is a triple slash one: a "/** */" block also yields XML, and the convention does not take it.
        string? xml = symbol.GetDocumentationCommentXml(cancellationToken: context.CancellationToken);
        if (string.IsNullOrWhiteSpace(xml) || !symbol.DeclaringSyntaxReferences.Any(reference => HasTripleSlash(reference.GetSyntax())))
        {
            context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_memberIsNotDocumented, symbol.Locations[0], symbol.Name));
        }
    }

    // A field or an event is declared by its variable, and the comment stands on the declaration around it.
    private static bool HasTripleSlash(SyntaxNode node)
    {
        SyntaxNode owner = node is VariableDeclaratorSyntax { Parent.Parent: { } declaration } ? declaration : node;
        return owner.GetLeadingTrivia().Any(trivia => trivia.IsKind(SyntaxKind.SingleLineDocumentationCommentTrivia));
    }

    // Public or internal all the way out: a member is no more visible than the types that hold it.
    private static bool IsVisible(ISymbol symbol)
    {
        for (ISymbol? current = symbol; current is not null and not INamespaceSymbol; current = current.ContainingSymbol)
        {
            if (current.DeclaredAccessibility is not (Accessibility.Public or Accessibility.Internal or Accessibility.ProtectedOrInternal))
            {
                return false;
            }
        }

        return true;
    }

    // Accessors, a record's positional members, a primary constructor, and the class the compiler makes around top-level
    // statements have no declaration of their own to document.
    private static bool IsWritten(ISymbol symbol)
    {
        var declarations = symbol.DeclaringSyntaxReferences.Select(reference => reference.GetSyntax()).ToList();
        if (symbol is INamedTypeSymbol)
        {
            return declarations.Any(node => node is not CompilationUnitSyntax);
        }

        if (symbol is IMethodSymbol method && method.MethodKind is not (MethodKind.Ordinary or MethodKind.Constructor
            or MethodKind.UserDefinedOperator or MethodKind.Conversion or MethodKind.StaticConstructor))
        {
            return false;
        }

        return declarations.Any(node => node is not (TypeDeclarationSyntax or ParameterSyntax or CompilationUnitSyntax));
    }
}
