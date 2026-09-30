#!/usr/bin/env -S dotnet --
#:property TargetFramework=net10.0
#:package Hex1b

using System.Diagnostics;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;
using System.Xml.Linq;
using Hex1b;
using Hex1b.Automation;

// Publishes pgtail with Native AOT for one runtime, checks the executable, then packs and checks its tool package.
// Usage: dotnet run --file scripts/Publish-NativeAot.cs -- --rid linux-x64 [--package-version 1.2.3] [--output dir]
(string Rid, string Version, string Output)? options = ParseOptions(args);
if (options is null)
{
    Console.Error.WriteLine("usage: Publish-NativeAot.cs --rid RID [--package-version VERSION] [--output DIRECTORY]");
    return 2;
}

(string rid, string version, string output) = options.Value;
if (rid != CurrentRid())
{
    Console.Error.WriteLine($"{rid} must be published and checked on a matching machine; this one is {CurrentRid()}.");
    return 1;
}

string repo = FindRepository();
string artifacts = Path.GetFullPath(Path.Join(output, rid), repo);
string publishDirectory = Path.Join(artifacts, "publish");
string packagesDirectory = Path.Join(artifacts, "packages");
string project = Path.Join(repo, "src", "Pgtail", "Pgtail.csproj");
string executableName = OperatingSystem.IsWindows() ? "pgtail.exe" : "pgtail";
if (Directory.Exists(artifacts))
{
    Directory.Delete(artifacts, recursive: true);
}

if (await RunAsync(repo, "dotnet", ["publish", project, "-c", "Release", "-r", rid, "-o", publishDirectory,
    $"-p:Version={version}", "--nologo"]) != 0)
{
    return 1;
}

// Hex1b's console driver on Linux and macOS calls its native helper, which must sit beside the executable. On Windows,
// Hex1b also ships programs for hosting a pseudo-terminal, which pgtail never starts; the project removes them, since
// package validation runs every program an installer puts down and they exit with an error on their own.
var published = Directory.GetFiles(publishDirectory, "*", SearchOption.AllDirectories)
    .Select(path => Path.GetRelativePath(publishDirectory, path)).ToHashSet();
string[] required = OperatingSystem.IsWindows() ? [executableName]
    : OperatingSystem.IsMacOS() ? [executableName, "libhex1binterop.dylib"] : [executableName, "libhex1binterop.so"];
if (required.Any(file => !published.Contains(file))
    || published.Any(file => file.EndsWith(".dbg", StringComparison.Ordinal) || file.EndsWith(".xml", StringComparison.Ordinal)))
{
    Console.Error.WriteLine($"expected {string.Join(", ", required)} and no symbols or documentation, found: "
        + string.Join(", ", published));
    return 1;
}

if (UnexpectedPrograms(publishDirectory, executableName) is { Count: > 0 } extra)
{
    Console.Error.WriteLine("only pgtail may be published as a program, found: " + string.Join(", ", extra));
    return 1;
}

string executable = Path.Join(publishDirectory, executableName);
if (!await SmokeAsync(executable, version))
{
    return 1;
}

if (await RunAsync(repo, "dotnet", ["pack", project, "-c", "Release", "-r", rid, "-o", packagesDirectory,
    $"-p:Version={version}", $"-p:PackageVersion={version}", "--nologo"]) != 0)
{
    return 1;
}

string package = Path.Join(packagesDirectory, $"pgtail.{rid}.{version}.nupkg");
if (!File.Exists(package))
{
    Console.Error.WriteLine($"expected {package} after packing");
    return 1;
}

string unpacked = Directory.CreateTempSubdirectory("pgtail-package-").FullName;
try
{
    ZipFile.ExtractToDirectory(package, unpacked);
    if (UnexpectedPrograms(unpacked, executableName) is { Count: > 0 } packed)
    {
        Console.Error.WriteLine("only pgtail may be packed as a program, found: " + string.Join(", ", packed));
        return 1;
    }

    string settings = Directory.GetFiles(unpacked, "DotnetToolSettings.xml", SearchOption.AllDirectories).Single();
    string entryPoint = XDocument.Load(settings).Descendants("Command").Single().Attribute("EntryPoint")!.Value;
    string packaged = Path.Join(Path.GetDirectoryName(settings)!, entryPoint);
    if (!OperatingSystem.IsWindows())
    {
        File.SetUnixFileMode(packaged, File.GetUnixFileMode(packaged) | UnixFileMode.UserExecute);
    }

    if (!await SmokeAsync(packaged, version))
    {
        return 1;
    }
}
finally
{
    Directory.Delete(unpacked, recursive: true);
}

Console.WriteLine($"published, packed, and checked pgtail {version} for {rid}");
return 0;

static (string Rid, string Version, string Output)? ParseOptions(string[] arguments)
{
    string? rid = null;
    string version = "0.0.0";
    string output = "artifacts/native-aot";
    for (int index = 0; index < arguments.Length; index++)
    {
        string? value = index + 1 < arguments.Length ? arguments[index + 1] : null;
        switch (arguments[index])
        {
            case "--rid" when value is not null:
                rid = value;
                index++;
                break;
            case "--package-version" when value is not null:
                version = value.TrimStart('v');
                index++;
                break;
            case "--output" when value is not null:
                output = value;
                index++;
                break;
            default:
                return null;
        }
    }

    return rid is null ? null : (rid, version, output);
}

static string CurrentRid()
{
    string os = OperatingSystem.IsWindows() ? "win" : OperatingSystem.IsMacOS() ? "osx" : "linux";
    return $"{os}-{RuntimeInformation.OSArchitecture.ToString().ToLowerInvariant()}";
}

static string FindRepository()
{
    for (var directory = new DirectoryInfo(Environment.CurrentDirectory); directory is not null; directory = directory.Parent)
    {
        if (File.Exists(Path.Join(directory.FullName, "Pgtail.slnx")))
        {
            return directory.FullName;
        }
    }

    throw new InvalidOperationException("run this from inside the pgtail repository");
}

static async Task<int> RunAsync(string directory, string fileName, IEnumerable<string> arguments)
{
    var info = new ProcessStartInfo(fileName, arguments) { WorkingDirectory = directory };
    using Process process = Process.Start(info)!;
    await process.WaitForExitAsync();
    return process.ExitCode;
}

// Runs the executable the way users and scripts do, in a private home so nothing on the machine is read or written,
// with the update check off so nothing reaches the network.
static async Task<bool> SmokeAsync(string executable, string version)
{
    string home = Directory.CreateTempSubdirectory("pgtail-smoke-").FullName;
    try
    {
        string config = Path.Join(home, "config", "pgtail", "config.toml");
        string data = Path.Join(home, "pgdata");
        Directory.CreateDirectory(Path.GetDirectoryName(config)!);
        Directory.CreateDirectory(Path.Join(data, "log"));
        await File.WriteAllTextAsync(config, "[updates]\ncheck = false\n");
        await File.WriteAllTextAsync(Path.Join(data, "PG_VERSION"), "17\n");
        await File.WriteAllTextAsync(Path.Join(data, "postgresql.conf"), "port = 5497\nlogging_collector = on\n");
        var environment = new Dictionary<string, string>
        {
            ["HOME"] = home,
            ["USERPROFILE"] = home,
            ["XDG_CONFIG_HOME"] = Path.Join(home, "config"),
            ["XDG_DATA_HOME"] = Path.Join(home, "data"),
            ["APPDATA"] = Path.Join(home, "config"),
            ["LOCALAPPDATA"] = Path.Join(home, "data"),
            ["PGDATA"] = data,
        };

        string log = """
            2026-09-29 10:15:01.123 UTC [4242] LOG:  database system is ready to accept connections
            2026-09-29 10:15:02.456 UTC [4243] ERROR:  duplicate key value violates unique constraint "users_pkey"
            2026-09-29 10:15:03.789 UTC [4244] LOG:  duration: 1234.567 ms  statement: SELECT * FROM orders WHERE id = 42

            """;

        (string[] Arguments, string? Input, string[] Expected)[] checks =
        [
            (["--version"], null, [$"pgtail {version}"]),
            (["--help"], null, ["Usage: pgtail", "list-instances"]),
            (["config", "--path"], null, ["config.toml"]),
            (["list-instances"], null, ["5497", "17"]),
            (["__complete", "bash", "--", "tail", "--s"], null, ["--since", "--stream"]),
            (["tail", "--stdin", "--stream"], log, ["ready to accept connections", "users_pkey", "1234.567 ms"]),
        ];

        foreach ((string[] arguments, string? input, string[] expected) in checks)
        {
            var info = new ProcessStartInfo(executable, arguments)
            {
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
            };

            foreach ((string name, string value) in environment)
            {
                info.Environment[name] = value;
            }

            using Process process = Process.Start(info)!;
            if (input is not null)
            {
                await process.StandardInput.WriteAsync(input);
            }

            process.StandardInput.Close();
            Task<string> stdout = process.StandardOutput.ReadToEndAsync();
            Task<string> stderr = process.StandardError.ReadToEndAsync();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            await process.WaitForExitAsync(timeout.Token);
            string text = await stdout;
            string command = "pgtail " + string.Join(' ', arguments);
            if (process.ExitCode != 0 || expected.Any(part => !text.Contains(part, StringComparison.Ordinal)))
            {
                Console.Error.WriteLine($"{command} failed with exit code {process.ExitCode}");
                Console.Error.WriteLine(text);
                Console.Error.WriteLine(await stderr);
                return false;
            }

            Console.WriteLine($"checked: {command}");
        }

        // A terminal names itself in the environment; without a name, pgtail alone in a Windows console leaves.
        var terminal = new Dictionary<string, string>(environment) { ["TERM"] = "xterm-256color" };
        return await InteractiveAsync(executable, terminal)
            && await RedirectedAsync(executable, environment)
            && (!OperatingSystem.IsWindows() || await WithoutConsoleAsync(executable, environment));
    }
    finally
    {
        Directory.Delete(home, recursive: true);
    }
}

// Starts the REPL in a pseudo-terminal inside Hex1b's headless terminal, types quit once the prompt shows, and expects a
// clean exit. This puts the console in raw mode and answers the terminal queries a real terminal would, so it fails the
// way a user's terminal would if the executable could not drive the console.
static async Task<bool> InteractiveAsync(string executable, Dictionary<string, string> environment)
{
    await using Hex1bTerminal terminal = Hex1bTerminal.CreateBuilder()
        .WithPtyProcess(options =>
        {
            options.FileName = executable;
            options.Environment = environment;
        })
        .WithHeadless()
        .WithDimensions(100, 30)
        .Build();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(60));
    Task<int> run = terminal.RunAsync(timeout.Token);
    var automator = new Hex1bTerminalAutomator(terminal, defaultTimeout: TimeSpan.FromSeconds(30));
    try
    {
        await automator.WaitUntilTextAsync("pgtail>");
        await automator.TypeAsync("quit");
        await automator.EnterAsync();
        if (await run.WaitAsync(TimeSpan.FromSeconds(30)) == 0)
        {
            Console.WriteLine("checked: pgtail (the REPL in a pseudo-terminal)");
            return true;
        }
    }
    catch (Exception exception) when (exception is Hex1bAutomationException or TimeoutException)
    {
        Console.Error.WriteLine(exception.Message);
    }

    Console.Error.WriteLine("the REPL did not start and leave cleanly in a pseudo-terminal");
    return false;
}

// The programs under a directory other than pgtail itself.
static List<string> UnexpectedPrograms(string directory, string executableName) =>
    [.. Directory.GetFiles(directory, "*.exe", SearchOption.AllDirectories)
        .Where(path => !Path.GetFileName(path).Equals(executableName, StringComparison.OrdinalIgnoreCase))
        .Select(path => Path.GetRelativePath(directory, path))];

// Starts pgtail with no arguments and its input and output redirected, as an installer's check does, and expects it to
// leave at once with status 0 and nothing on its error output.
static async Task<bool> RedirectedAsync(string executable, Dictionary<string, string> environment)
{
    var info = new ProcessStartInfo(executable)
    {
        UseShellExecute = false,
        RedirectStandardInput = true,
        RedirectStandardOutput = true,
        RedirectStandardError = true,
    };

    foreach ((string name, string value) in environment)
    {
        info.Environment[name] = value;
    }

    using Process process = Process.Start(info)!;
    process.StandardInput.Close();
    Task<string> errors = process.StandardError.ReadToEndAsync();
    _ = process.StandardOutput.ReadToEndAsync();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
    try
    {
        await process.WaitForExitAsync(timeout.Token);
    }
    catch (OperationCanceledException)
    {
        process.Kill();
        Console.Error.WriteLine("pgtail with no arguments and no terminal waited instead of leaving");
        return false;
    }

    if (process.ExitCode != 0 || (await errors).Length > 0)
    {
        Console.Error.WriteLine($"pgtail with no arguments and no terminal left with exit code {process.ExitCode}: {await errors}");
        return false;
    }

    Console.WriteLine("checked: pgtail (no arguments and no terminal leaves at once)");
    return true;
}

// Starts the REPL on Windows in a console of its own with no window, as Start-Process or package validation does, and
// expects it to leave at once with status 0 instead of waiting for keys no one will type.
static async Task<bool> WithoutConsoleAsync(string executable, Dictionary<string, string> environment)
{
    var info = new ProcessStartInfo(executable) { UseShellExecute = false, CreateNoWindow = true };
    foreach ((string name, string value) in environment)
    {
        info.Environment[name] = value;
    }

    using Process process = Process.Start(info)!;
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
    try
    {
        await process.WaitForExitAsync(timeout.Token);
    }
    catch (OperationCanceledException)
    {
        process.Kill();
        Console.Error.WriteLine("pgtail without a console waited instead of leaving");
        return false;
    }

    if (process.ExitCode != 0)
    {
        Console.Error.WriteLine($"pgtail without a console left with exit code {process.ExitCode}");
        return false;
    }

    Console.WriteLine("checked: pgtail (the REPL without a console leaves at once)");
    return true;
}
