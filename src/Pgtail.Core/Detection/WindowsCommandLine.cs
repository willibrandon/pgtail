using System.Text;

namespace Pgtail.Detection;

/// <summary>
/// Splits a Windows command line into arguments the way programs receive them.
/// </summary>
public static class WindowsCommandLine
{
    /// <summary>
    /// Splits a command line.
    /// </summary>
    /// <remarks>
    /// The program name ends at the first space or tab, or at its closing quote. In later arguments, 2n backslashes
    /// before a quote become n backslashes and the quote toggles quoting, 2n+1 backslashes before a quote become n
    /// backslashes and a literal quote, and other backslashes are literal.
    /// </remarks>
    /// <param name="commandLine">The command line.</param>
    /// <returns>The arguments.</returns>
    public static IReadOnlyList<string> Split(string commandLine)
    {
        ArgumentNullException.ThrowIfNull(commandLine);
        var arguments = new List<string>();
        var i = 0;
        if (commandLine.Length == 0)
        {
            return arguments;
        }

        var program = new StringBuilder();
        if (commandLine[0] == '"')
        {
            i = 1;
            while (i < commandLine.Length && commandLine[i] != '"')
            {
                program.Append(commandLine[i++]);
            }

            i++;
        }
        else
        {
            while (i < commandLine.Length && commandLine[i] is not (' ' or '\t'))
            {
                program.Append(commandLine[i++]);
            }
        }

        arguments.Add(program.ToString());
        while (true)
        {
            while (i < commandLine.Length && commandLine[i] is ' ' or '\t')
            {
                i++;
            }

            if (i >= commandLine.Length)
            {
                return arguments;
            }

            var argument = new StringBuilder();
            var quoted = false;
            while (i < commandLine.Length && (quoted || commandLine[i] is not (' ' or '\t')))
            {
                var backslashes = 0;
                while (i < commandLine.Length && commandLine[i] == '\\')
                {
                    backslashes++;
                    i++;
                }

                if (i < commandLine.Length && commandLine[i] == '"')
                {
                    argument.Append('\\', backslashes / 2);
                    if (backslashes % 2 == 1)
                    {
                        argument.Append('"');
                    }
                    else if (quoted && i + 1 < commandLine.Length && commandLine[i + 1] == '"')
                    {
                        argument.Append('"');
                        i++;
                    }
                    else
                    {
                        quoted = !quoted;
                    }

                    i++;
                }
                else
                {
                    argument.Append('\\', backslashes);
                    if (i < commandLine.Length && (quoted || commandLine[i] is not (' ' or '\t')))
                    {
                        argument.Append(commandLine[i++]);
                    }
                }
            }

            arguments.Add(argument.ToString());
        }
    }
}
