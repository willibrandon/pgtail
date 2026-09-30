namespace Pgtail.Toml;

/// <summary>
/// Reads a TOML 1.0 document into tables and records where each top-level statement was written.
/// </summary>
internal sealed partial class TomlParser
{
    private readonly string _text;
    private readonly TomlTable _root = new();
    private readonly List<TomlStatement> _statements = [];
    private int _position;
    private TomlTable _current;
    private List<string> _currentPath = [];

    private TomlParser(string text)
    {
        _text = text;
        _current = _root;
    }

    /// <summary>
    /// Parses a document.
    /// </summary>
    /// <param name="text">The document.</param>
    /// <returns>The root table and the top-level statements.</returns>
    /// <exception cref="TomlException">The document is not valid TOML.</exception>
    public static (TomlTable Root, IReadOnlyList<TomlStatement> Statements) Parse(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var parser = new TomlParser(text);
        parser.ParseDocument();
        return (parser._root, parser._statements);
    }

    private bool AtEnd => _position >= _text.Length;

    private char Current => _text[_position];

    private void ParseDocument()
    {
        if (_text.StartsWith('﻿'))
        {
            _position = 1;
        }

        while (true)
        {
            int lineStart = _position;
            SkipWhitespace();
            if (AtEnd)
            {
                return;
            }

            switch (Current)
            {
                case '#':
                    SkipComment();
                    ExpectLineEnd();
                    break;
                case '\n' or '\r':
                    ExpectLineEnd();
                    break;
                case '[':
                    ParseHeader(lineStart);
                    break;
                default:
                    ParseStatement(lineStart);
                    break;
            }
        }
    }

    private void ParseStatement(int lineStart)
    {
        List<string> key = ParseKey();
        SkipWhitespace();
        Expect('=', "Expected '=' after the key");
        SkipWhitespace();
        int valueStart = _position;
        object value = ParseValue();
        int valueEnd = _position;
        FinishLine();
        Insert(_current, key, value, keyStart: lineStart);
        _statements.Add(new TomlStatement(TomlStatementKind.KeyValue, [.. _currentPath, .. key], [.. _currentPath], lineStart,
            _position, valueStart, valueEnd));
    }

    private void ParseHeader(int lineStart)
    {
        bool isArray = _position + 1 < _text.Length && _text[_position + 1] == '[';
        _position += isArray ? 2 : 1;
        SkipWhitespace();
        List<string> path = ParseKey();
        SkipWhitespace();
        Expect(']', isArray ? "Expected ']]' to close the array of tables header" : "Expected ']' to close the table header");
        if (isArray)
        {
            Expect(']', "Expected ']]' to close the array of tables header");
        }

        FinishLine();
        _current = isArray ? OpenArrayTable(path, lineStart) : OpenTable(path, lineStart);
        _currentPath = path;
        _statements.Add(new TomlStatement(isArray ? TomlStatementKind.ArrayTable : TomlStatementKind.Table, path, path, lineStart,
            _position, _position, _position));
    }

    private void FinishLine()
    {
        SkipWhitespace();
        if (!AtEnd && Current == '#')
        {
            SkipComment();
        }

        ExpectLineEnd();
    }

    private void ExpectLineEnd()
    {
        if (AtEnd)
        {
            return;
        }

        if (Current == '\n')
        {
            _position++;
            return;
        }

        if (Current == '\r' && _position + 1 < _text.Length && _text[_position + 1] == '\n')
        {
            _position += 2;
            return;
        }

        throw Error(Current == '\r' ? "A carriage return must be followed by a line feed" : $"Unexpected '{Current}' after a value");
    }

    private void SkipWhitespace()
    {
        while (!AtEnd && Current is ' ' or '\t')
        {
            _position++;
        }
    }

    private void SkipComment()
    {
        _position++;
        while (!AtEnd && Current != '\n')
        {
            char c = Current;
            if (c == '\r' && _position + 1 < _text.Length && _text[_position + 1] == '\n')
            {
                return;
            }

            if ((c < 0x20 && c != '\t') || c == 0x7F)
            {
                throw Error("Control characters are not allowed in comments");
            }

            _position++;
        }
    }

    private void SkipWhitespaceCommentsAndNewlines()
    {
        while (!AtEnd)
        {
            SkipWhitespace();
            if (AtEnd)
            {
                return;
            }

            if (Current == '#')
            {
                SkipComment();
            }
            else if (Current is '\n' or '\r')
            {
                ExpectLineEnd();
            }
            else
            {
                return;
            }
        }
    }

    private void Expect(char expected, string message)
    {
        if (AtEnd || Current != expected)
        {
            throw Error(message);
        }

        _position++;
    }

    private TomlException Error(string message) => Error(message, _position);

    private TomlException Error(string message, int position)
    {
        int line = 1;
        int column = 1;
        for (int i = 0; i < position && i < _text.Length; i++)
        {
            if (_text[i] == '\n')
            {
                line++;
                column = 1;
            }
            else
            {
                column++;
            }
        }

        return new TomlException(message, line, column);
    }
}
