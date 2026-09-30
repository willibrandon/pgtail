using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Text;

namespace Pgtail.Analyzers;

/// <summary>
/// Requires each brace of a block, type, namespace, or switch to stand alone on its line, a lambda body included.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class ExpandedBlockAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.s_blockIsNotExpanded);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxNodeAction(AnalyzeBlock, SyntaxKind.Block, SyntaxKind.SwitchStatement, SyntaxKind.NamespaceDeclaration,
            SyntaxKind.ClassDeclaration, SyntaxKind.StructDeclaration, SyntaxKind.InterfaceDeclaration, SyntaxKind.EnumDeclaration,
            SyntaxKind.RecordDeclaration, SyntaxKind.RecordStructDeclaration, SyntaxKind.ExtensionBlockDeclaration,
            SyntaxKind.AccessorList, SyntaxKind.SwitchExpression,
            SyntaxKind.ObjectInitializerExpression, SyntaxKind.CollectionInitializerExpression, SyntaxKind.ArrayInitializerExpression,
            SyntaxKind.ComplexElementInitializerExpression, SyntaxKind.WithInitializerExpression,
            SyntaxKind.AnonymousObjectCreationExpression, SyntaxKind.PropertyPatternClause);
    }

    private static void AnalyzeBlock(SyntaxNodeAnalysisContext context)
    {
        SyntaxToken open;
        SyntaxToken close;
        switch (context.Node)
        {
            case BlockSyntax block:
                open = block.OpenBraceToken;
                close = block.CloseBraceToken;
                break;
            case SwitchStatementSyntax choice:
                open = choice.OpenBraceToken;
                close = choice.CloseBraceToken;
                break;
            case NamespaceDeclarationSyntax space:
                open = space.OpenBraceToken;
                close = space.CloseBraceToken;
                break;
            case ExtensionBlockDeclarationSyntax extension:
                open = extension.OpenBraceToken;
                close = extension.CloseBraceToken;
                break;
            case BaseTypeDeclarationSyntax type:
                open = type.OpenBraceToken;
                close = type.CloseBraceToken;
                break;
            default:
                // Braces that hold no statements read as one phrase on one line, as "{ get; set; }", "new() { Name = name }",
                // and "kind switch { 0 => a, _ => b }" do. Once they take more than one line they are laid out like a body.
                (open, close) = context.Node switch
                {
                    AccessorListSyntax accessors => (accessors.OpenBraceToken, accessors.CloseBraceToken),
                    SwitchExpressionSyntax choice => (choice.OpenBraceToken, choice.CloseBraceToken),
                    InitializerExpressionSyntax initializer => (initializer.OpenBraceToken, initializer.CloseBraceToken),
                    AnonymousObjectCreationExpressionSyntax anonymous => (anonymous.OpenBraceToken, anonymous.CloseBraceToken),
                    PropertyPatternClauseSyntax pattern => (pattern.OpenBraceToken, pattern.CloseBraceToken),
                    _ => default,
                };

                if (SharesLine(open, close))
                {
                    return;
                }

                break;
        }

        // A record or type declared with a semicolon has no braces to place.
        if (open.IsKind(SyntaxKind.None) || open.IsMissing)
        {
            return;
        }

        if (SharesLine(open.GetPreviousToken(), open) || SharesLine(open, open.GetNextToken())
            || SharesLine(close.GetPreviousToken(), close) || ContinuesWithCode(close)
            || HasCommentBeside(open) || HasCommentBeside(close))
        {
            context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.s_blockIsNotExpanded, open.GetLocation()));
        }
    }

    // Only what completes the expression around a block may follow its brace, as in "});". The "while" of a "do" and a member
    // access that carries the expression on, as in ".ToList()", take the next line.
    private static bool ContinuesWithCode(SyntaxToken close)
    {
        SyntaxToken next = close.GetNextToken();
        if (!SharesLine(close, next))
        {
            return false;
        }

        switch (next.Kind())
        {
            case SyntaxKind.CloseParenToken:
            case SyntaxKind.CloseBracketToken:
            case SyntaxKind.SemicolonToken:
            case SyntaxKind.CommaToken:
                return StartsAnotherStatement(close);
            case SyntaxKind.EqualsToken:
                // A property's initializer can only follow its accessors, and the next member still takes a line of its own.
                return next.Parent is not EqualsValueClauseSyntax { Parent: PropertyDeclarationSyntax } || StartsAnotherStatement(close);
            default:
                return true;
        }
    }

    // The rest of the line may finish the statement, as "}, token).ConfigureAwait(false);" does, which is how such a call
    // is written everywhere. A statement or member that starts after it, as in "}); Next();", is code beside the brace.
    private static bool StartsAnotherStatement(SyntaxToken close)
    {
        for (SyntaxToken token = close.GetNextToken(); SharesLine(close, token); token = token.GetNextToken())
        {
            if (token.IsKind(SyntaxKind.SemicolonToken) && SharesLine(token, token.GetNextToken()))
            {
                return true;
            }
        }

        return false;
    }

    // A comment is trivia, so the neighbouring tokens do not show it. One written after "});" hangs on the last token of that line.
    private static bool HasCommentBeside(SyntaxToken brace)
    {
        SyntaxTree tree = brace.SyntaxTree!;
        int line = tree.GetLineSpan(brace.Span).StartLinePosition.Line;
        for (SyntaxToken token = brace; SharesLine(brace, token); token = token.GetNextToken())
        {
            foreach (SyntaxTrivia trivia in token.LeadingTrivia.Concat(token.TrailingTrivia))
            {
                if (IsComment(trivia) && Touches(tree, trivia, line))
                {
                    return true;
                }
            }
        }

        return false;
    }

    // Whatever is neither blank space nor a directive is a comment of some kind, documentation comments included.
    private static bool IsComment(SyntaxTrivia trivia) =>
        !trivia.IsKind(SyntaxKind.WhitespaceTrivia) && !trivia.IsKind(SyntaxKind.EndOfLineTrivia) && !trivia.IsDirective;

    // A documentation comment's span runs to the start of the next line, which is not a line it is written on.
    private static bool Touches(SyntaxTree tree, SyntaxTrivia trivia, int line)
    {
        FileLinePositionSpan span = tree.GetLineSpan(trivia.Span);
        LinePosition end = span.EndLinePosition;
        int last = end.Character == 0 && end.Line > span.StartLinePosition.Line ? end.Line - 1 : end.Line;
        return span.StartLinePosition.Line == line || last == line;
    }

    private static bool SharesLine(SyntaxToken first, SyntaxToken second)
    {
        if (first.IsKind(SyntaxKind.None) || second.IsKind(SyntaxKind.None))
        {
            return false;
        }

        SyntaxTree tree = first.SyntaxTree!;
        return tree.GetLineSpan(first.Span).EndLinePosition.Line == tree.GetLineSpan(second.Span).StartLinePosition.Line;
    }
}
