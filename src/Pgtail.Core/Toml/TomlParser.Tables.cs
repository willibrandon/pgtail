namespace Pgtail.Toml;

/// <summary>
/// Keys, tables, and the rules that keep every key and table defined once.
/// </summary>
internal sealed partial class TomlParser
{
    private List<string> ParseKey()
    {
        var parts = new List<string> { ParseSimpleKey() };
        while (true)
        {
            int save = _position;
            SkipWhitespace();
            if (AtEnd || Current != '.')
            {
                _position = save;
                return parts;
            }

            _position++;
            SkipWhitespace();
            parts.Add(ParseSimpleKey());
        }
    }

    private string ParseSimpleKey()
    {
        if (AtEnd)
        {
            throw Error("Expected a key");
        }

        if (Current == '"')
        {
            if (_text.AsSpan(_position).StartsWith("\"\"\""))
            {
                throw Error("Multi-line strings are not allowed as keys");
            }

            return ParseBasicString();
        }

        if (Current == '\'')
        {
            if (_text.AsSpan(_position).StartsWith("'''"))
            {
                throw Error("Multi-line strings are not allowed as keys");
            }

            return ParseLiteralString();
        }

        int start = _position;
        while (!AtEnd && IsBareKeyCharacter(Current))
        {
            _position++;
        }

        if (_position == start)
        {
            throw Error(AtEnd || Current is '\n' or '\r' ? "Expected a key" : $"Unexpected '{Current}' where a key was expected");
        }

        return _text[start.._position];
    }

    private static bool IsBareKeyCharacter(char c) => c is (>= 'A' and <= 'Z') or (>= 'a' and <= 'z') or (>= '0' and <= '9') or '_' or '-';

    private void Insert(TomlTable table, List<string> key, object value, int keyStart)
    {
        TomlTable target = table;
        for (int i = 0; i < key.Count - 1; i++)
        {
            if (target.TryGetValue(key[i], out object? existing))
            {
                if (existing is not TomlTable { Kind: TomlTableKind.Dotted } dotted)
                {
                    throw Error($"Cannot add to '{string.Join('.', key.Take(i + 1))}' with a dotted key: it is already defined",
                        keyStart);
                }

                target = dotted;
            }
            else
            {
                var created = new TomlTable(TomlTableKind.Dotted);
                target.Add(key[i], created);
                target = created;
            }
        }

        if (target.ContainsKey(key[^1]))
        {
            throw Error($"Duplicate key '{string.Join('.', key)}'", keyStart);
        }

        target.Add(key[^1], value);
    }

    private TomlTable Descend(List<string> path, int count, int lineStart)
    {
        TomlTable table = _root;
        for (int i = 0; i < count; i++)
        {
            if (!table.TryGetValue(path[i], out object? existing))
            {
                var created = new TomlTable(TomlTableKind.Implicit);
                table.Add(path[i], created);
                table = created;
                continue;
            }

            table = existing switch
            {
                TomlTable { Kind: TomlTableKind.Inline } => throw Error(
                    $"Cannot extend the inline table '{string.Join('.', path.Take(i + 1))}'", lineStart),
                TomlTable nested => nested,
                TomlArray { IsTableArray: true } array => (TomlTable)array[^1],
                _ => throw Error($"'{string.Join('.', path.Take(i + 1))}' is already defined as a value", lineStart),
            };
        }

        return table;
    }

    private TomlTable OpenTable(List<string> path, int lineStart)
    {
        TomlTable parent = Descend(path, path.Count - 1, lineStart);
        string name = path[^1];
        if (!parent.TryGetValue(name, out object? existing))
        {
            var created = new TomlTable(TomlTableKind.Header);
            parent.Add(name, created);
            return created;
        }

        if (existing is TomlTable { Kind: TomlTableKind.Implicit } implicitTable)
        {
            implicitTable.Kind = TomlTableKind.Header;
            return implicitTable;
        }

        throw Error($"Table '{string.Join('.', path)}' is already defined", lineStart);
    }

    private TomlTable OpenArrayTable(List<string> path, int lineStart)
    {
        TomlTable parent = Descend(path, path.Count - 1, lineStart);
        string name = path[^1];
        var element = new TomlTable(TomlTableKind.ArrayElement);
        if (!parent.TryGetValue(name, out object? existing))
        {
            var array = new TomlArray(isTableArray: true);
            array.Add(element);
            parent.Add(name, array);
            return element;
        }

        if (existing is TomlArray { IsTableArray: true } tables)
        {
            tables.Add(element);
            return element;
        }

        throw Error($"'{string.Join('.', path)}' is already defined and is not an array of tables", lineStart);
    }
}
