using System.Text;

namespace Pgtail.Parsing;

/// <summary>
/// Splits one CSV record with the rules of the excel dialect: commas, double quotes, and doubled quotes inside quotes.
/// </summary>
/// <remarks>
/// Parsing is lenient the way PostgreSQL's csvlog readers expect: text after a closing quote joins the field, and a
/// quote left open runs to the end of the line. A bare carriage return or line feed in an unquoted field ends the
/// record, and anything after it makes the record invalid.
/// </remarks>
public static class CsvLine
{
    private enum State
    {
        StartRecord,
        StartField,
        InField,
        InQuotedField,
        QuoteInQuotedField,
        EatNewline,
    }

    /// <summary>
    /// Splits a record into its fields.
    /// </summary>
    /// <param name="line">The record.</param>
    /// <param name="fields">The fields, when the record is valid.</param>
    /// <returns>True when the record is valid; an empty line is not a record.</returns>
    public static bool TrySplit(string line, out List<string> fields)
    {
        ArgumentNullException.ThrowIfNull(line);
        fields = [];
        if (line.Length == 0)
        {
            return false;
        }

        var field = new StringBuilder();
        State state = State.StartRecord;
        foreach (char c in line)
        {
            switch (state)
            {
                case State.StartRecord:
                    if (c is '\n' or '\r')
                    {
                        state = State.EatNewline;
                        break;
                    }

                    state = StartField(c, field, fields);
                    break;
                case State.StartField:
                    state = StartField(c, field, fields);
                    break;
                case State.InField:
                    if (c is '\n' or '\r')
                    {
                        Save(field, fields);
                        state = State.EatNewline;
                    }
                    else if (c == ',')
                    {
                        Save(field, fields);
                        state = State.StartField;
                    }
                    else
                    {
                        field.Append(c);
                    }

                    break;
                case State.InQuotedField:
                    if (c == '"')
                    {
                        state = State.QuoteInQuotedField;
                    }
                    else
                    {
                        field.Append(c);
                    }

                    break;
                case State.QuoteInQuotedField:
                    if (c == '"')
                    {
                        field.Append('"');
                        state = State.InQuotedField;
                    }
                    else if (c == ',')
                    {
                        Save(field, fields);
                        state = State.StartField;
                    }
                    else if (c is '\n' or '\r')
                    {
                        Save(field, fields);
                        state = State.EatNewline;
                    }
                    else
                    {
                        field.Append(c);
                        state = State.InField;
                    }

                    break;
                default:
                    if (c is not ('\n' or '\r'))
                    {
                        // A new line in an unquoted field followed by more text is not a record.
                        fields = [];
                        return false;
                    }

                    break;
            }
        }

        if (state is State.StartField or State.InField or State.InQuotedField or State.QuoteInQuotedField)
        {
            Save(field, fields);
        }

        return true;
    }

    private static State StartField(char c, StringBuilder field, List<string> fields)
    {
        switch (c)
        {
            case '\n' or '\r':
                Save(field, fields);
                return State.EatNewline;
            case '"':
                return State.InQuotedField;
            case ',':
                Save(field, fields);
                return State.StartField;
            default:
                field.Append(c);
                return State.InField;
        }
    }

    private static void Save(StringBuilder field, List<string> fields)
    {
        fields.Add(field.ToString());
        field.Clear();
    }
}
