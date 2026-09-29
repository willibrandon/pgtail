using System.Runtime.CompilerServices;

namespace Pgtail.Tests;

/// <summary>
/// Gives the thread pool enough threads for terminal tests running in parallel.
/// </summary>
/// <remarks>
/// Each Hex1b terminal runs input and output pumps on the thread pool, and a REPL test can run two terminals. Without
/// a higher minimum the pool adds threads about once a second, and parallel tests time out waiting for their screens,
/// as Hex1b's own test suite notes.
/// </remarks>
internal static class TestThreadPoolSetup
{
    /// <summary>
    /// Raises the thread pool's minimum before any test runs.
    /// </summary>
    [ModuleInitializer]
    internal static void Initialize() => ThreadPool.SetMinThreads(64, 64);
}
