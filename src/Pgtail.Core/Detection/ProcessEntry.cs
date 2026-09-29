namespace Pgtail.Detection;

/// <summary>
/// A running process with its command line.
/// </summary>
/// <param name="Pid">The process ID.</param>
/// <param name="Name">The process name, without an extension on Windows.</param>
/// <param name="Arguments">The command line arguments, starting with the program; empty when they cannot be read.</param>
public sealed record ProcessEntry(int Pid, string Name, IReadOnlyList<string> Arguments);
