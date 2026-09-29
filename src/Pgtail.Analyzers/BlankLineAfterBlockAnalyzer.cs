using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace Pgtail.Analyzers;

/// <summary>
/// Requires a blank line after a line that begins with a closing brace, where the SDK's rule is silent on it.
/// </summary>
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class BlankLineAfterBlockAnalyzer : DiagnosticAnalyzer
{
    /// <inheritdoc />
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } =
        ImmutableArray.Create(DiagnosticDescriptors.BlankLineAfterBrace);

    /// <inheritdoc />
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxTreeAction(AnalyzeComments);
        context.RegisterSyntaxNodeAction(AnalyzeSequence, SyntaxKind.Block, SyntaxKind.SwitchStatement, SyntaxKind.SwitchSection,
            SyntaxKind.CompilationUnit, SyntaxKind.NamespaceDeclaration, SyntaxKind.FileScopedNamespaceDeclaration,
            SyntaxKind.ClassDeclaration, SyntaxKind.StructDeclaration, SyntaxKind.InterfaceDeclaration,
            SyntaxKind.RecordDeclaration, SyntaxKind.RecordStructDeclaration, SyntaxKind.ExtensionBlockDeclaration,
            SyntaxKind.AccessorList);
    }

    // A comment is held to the rule wherever it follows a closing brace line: between statements, members, accessors, or
    // switch sections, before an "else", "catch", "finally", or "while", and at the end of a body or the file. Reading
    // the tokens covers them all, because no list of syntax nodes names every place a comment can stand.
    private static void AnalyzeComments(SyntaxTreeAnalysisContext context)
    {
        foreach (var token in context.Tree.GetRoot(context.CancellationToken).DescendantTokens())
        {
            // The brace that closes a hole in an interpolated string is text, not layout.
            if (!token.IsKind(SyntaxKind.CloseBraceToken) || token.Parent is InterpolationSyntax
                || SharesLine(token.GetPreviousToken(), token))
            {
                continue;
            }

            // Closing punctuation wrapped onto the next line still belongs to the brace, as in "}" and then ");".
            var last = LastOnLine(token);
            while (true)
            {
                var next = last.GetNextToken(includeZeroWidth: true);
                if (IsCrowded(next, out var comment) && comment is { } found)
                {
                    context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.BlankLineAfterBrace, found.GetLocation()));
                }

                if (!IsCloser(next) || StartLineOf(next) != LineOf(last) + 1 || !ClosesOnly(next, LastOnLine(next)))
                {
                    break;
                }

                // A comment beside that punctuation has no blank line above it either.
                last = LastOnLine(next);
                foreach (var trivia in last.TrailingTrivia.Where(trivia => !IsLayout(trivia)))
                {
                    context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.BlankLineAfterBrace, trivia.GetLocation()));
                }
            }
        }
    }

    private static void AnalyzeSequence(SyntaxNodeAnalysisContext context)
    {
        IReadOnlyList<SyntaxNode> items = context.Node switch
        {
            BlockSyntax block => block.Statements,
            SwitchStatementSyntax choice => choice.Sections,
            SwitchSectionSyntax section => section.Statements,
            CompilationUnitSyntax unit => unit.Members,
            BaseNamespaceDeclarationSyntax space => space.Members,
            AccessorListSyntax accessors => accessors.Accessors,
            ExtensionBlockDeclarationSyntax extension => extension.Members,
            TypeDeclarationSyntax type => type.Members,
            _ => [],
        };

        for (var index = 0; index + 1 < items.Count; index++)
        {
            if (!EndsOnBraceLine(items[index]))
            {
                continue;
            }

            // The SDK's rule already reports a statement placed right under a block, so that one case is left to it.
            var last = items[index].GetLastToken();
            var next = items[index + 1];
            if (last.IsKind(SyntaxKind.CloseBraceToken) && IsStatement(items[index]) && IsStatement(next))
            {
                continue;
            }

            // A comment under the brace is the other pass's to report.
            var first = next.GetFirstToken();
            if (StartLineOf(first) != LineOf(last) && IsCrowded(first, out var comment) && comment is null)
            {
                context.ReportDiagnostic(Diagnostic.Create(DiagnosticDescriptors.BlankLineAfterBrace, first.GetLocation()));
            }
        }
    }

    private static bool IsStatement(SyntaxNode node) => node is StatementSyntax or GlobalStatementSyntax;

    // A body, a lambda, or an initializer can end a statement or member on a line that begins with its closing brace. Lines
    // that hold nothing but the closing punctuation around that brace, such as ");", count as part of it.
    private static bool EndsOnBraceLine(SyntaxNode node)
    {
        var token = node.GetLastToken();
        if (node.SyntaxTree.GetLineSpan(node.Span).StartLinePosition.Line == LineOf(token))
        {
            return false;
        }

        while (true)
        {
            var first = FirstOnLine(token);
            if (first.IsKind(SyntaxKind.CloseBraceToken))
            {
                return true;
            }

            var above = first.GetPreviousToken();
            if (!ClosesOnly(first, token) || first.SpanStart <= node.SpanStart || LineOf(above) + 1 != StartLineOf(first))
            {
                return false;
            }

            token = above;
        }
    }

    private static SyntaxToken FirstOnLine(SyntaxToken token)
    {
        while (SharesLine(token.GetPreviousToken(), token))
        {
            token = token.GetPreviousToken();
        }

        return token;
    }

    // A token that runs over several lines, as the text of a raw string does, ends the line it starts on.
    private static SyntaxToken LastOnLine(SyntaxToken token)
    {
        while (SharesLine(token, token.GetNextToken()) && StartLineOf(token.GetNextToken()) == LineOf(token.GetNextToken()))
        {
            token = token.GetNextToken();
        }

        return token;
    }

    private static bool ClosesOnly(SyntaxToken first, SyntaxToken last)
    {
        for (var token = first; ; token = token.GetNextToken())
        {
            if (!IsCloser(token))
            {
                return false;
            }

            if (token == last)
            {
                return true;
            }
        }
    }

    private static bool IsCloser(SyntaxToken token) =>
        token.IsKind(SyntaxKind.CloseParenToken) || token.IsKind(SyntaxKind.CloseBracketToken)
        || token.IsKind(SyntaxKind.SemicolonToken) || token.IsKind(SyntaxKind.CommaToken);

    // Whether no blank line stands between the brace line and what follows it, which is a comment or else the token itself.
    // A directive is passed over: "#endif" under a brace puts no space between the brace and the code after it.
    private static bool IsCrowded(SyntaxToken next, out SyntaxTrivia? comment)
    {
        comment = null;
        var lineIsEmpty = true;
        foreach (var trivia in next.LeadingTrivia)
        {
            if (trivia.IsKind(SyntaxKind.WhitespaceTrivia))
            {
                continue;
            }

            if (trivia.IsKind(SyntaxKind.EndOfLineTrivia))
            {
                if (lineIsEmpty)
                {
                    return false;
                }

                lineIsEmpty = true;
                continue;
            }

            // A directive, and the text a false "#if" disables, end their own lines.
            if (trivia.IsDirective || trivia.IsKind(SyntaxKind.DisabledTextTrivia))
            {
                lineIsEmpty = true;
                continue;
            }

            comment = trivia;
            return true;
        }

        return true;
    }

    private static bool IsLayout(SyntaxTrivia trivia) =>
        trivia.IsKind(SyntaxKind.WhitespaceTrivia) || trivia.IsKind(SyntaxKind.EndOfLineTrivia) || trivia.IsDirective;

    private static int LineOf(SyntaxToken token) => token.SyntaxTree!.GetLineSpan(token.Span).EndLinePosition.Line;

    private static int StartLineOf(SyntaxToken token) => token.SyntaxTree!.GetLineSpan(token.Span).StartLinePosition.Line;

    private static bool SharesLine(SyntaxToken first, SyntaxToken second)
    {
        if (first.IsKind(SyntaxKind.None) || second.IsKind(SyntaxKind.None))
        {
            return false;
        }

        var tree = first.SyntaxTree!;
        return tree.GetLineSpan(first.Span).EndLinePosition.Line == tree.GetLineSpan(second.Span).StartLinePosition.Line;
    }
}
