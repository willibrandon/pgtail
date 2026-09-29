#!/usr/bin/env -S dotnet --
#:property TargetFramework=net10.0

using System.Diagnostics;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;
using System.Xml.Linq;

// Publishes pgtail with Native AOT for one runtime, checks the executable, then packs and checks its tool package.
// Usage: dotnet run --file scripts/Publish-NativeAot.cs -- --rid linux-x64 [--package-version 1.2.3] [--output dir]
var options = ParseOptions(args);
if (options is null)
{
    Console.Error.WriteLine("usage: Publish-NativeAot.cs --rid RID [--package-version VERSION] [--output DIRECTORY]");
    return 2;
}

var (rid, version, output) = options.Value;
if (rid != CurrentRid())
{
    Console.Error.WriteLine($"{rid} must be published and checked on a matching machine; this one is {CurrentRid()}.");
    return 1;
}

var repo = FindRepository();
var artifacts = Path.GetFullPath(Path.Join(output, rid), repo);
var publishDirectory = Path.Join(artifacts, "publish");
var packagesDirectory = Path.Join(artifacts, "packages");
var project = Path.Join(repo, "src", "Pgtail", "Pgtail.csproj");
var executableName = OperatingSystem.IsWindows() ? "pgtail.exe" : "pgtail";
if (Directory.Exists(artifacts))
{
    Directory.Delete(artifacts, recursive: true);
}

if (await RunAsync(repo, "dotnet", ["publish", project, "-c", "Release", "-r", rid, "-o", publishDirectory,
    $"-p:Version={version}", "--nologo"]) != 0)
{
    return 1;
}

var published = Directory.GetFiles(publishDirectory, "*", SearchOption.AllDirectories)
    .Select(path => Path.GetRelativePath(publishDirectory, path)).ToArray();
if (published is not [var only] || only != executableName)
{
    Console.Error.WriteLine($"expected only {executableName} in the publish directory, found: {string.Join(", ", published)}");
    return 1;
}

var executable = Path.Join(publishDirectory, executableName);
if (!await SmokeAsync(executable, version))
{
    return 1;
}

if (await RunAsync(repo, "dotnet", ["pack", project, "-c", "Release", "-r", rid, "-o", packagesDirectory,
    $"-p:Version={version}", $"-p:PackageVersion={version}", "--nologo"]) != 0)
{
    return 1;
}

var package = Path.Join(packagesDirectory, $"pgtail.{rid}.{version}.nupkg");
if (!File.Exists(package))
{
    Console.Error.WriteLine($"expected {package} after packing");
    return 1;
}

var unpacked = Directory.CreateTempSubdirectory("pgtail-package-").FullName;
try
{
    ZipFile.ExtractToDirectory(package, unpacked);
    var settings = Directory.GetFiles(unpacked, "DotnetToolSettings.xml", SearchOption.AllDirectories).Single();
    var entryPoint = XDocument.Load(settings).Descendants("Command").Single().Attribute("EntryPoint")!.Value;
    var packaged = Path.Join(Path.GetDirectoryName(settings)!, entryPoint);
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
    var version = "0.0.0";
    var output = "artifacts/native-aot";
    for (var index = 0; index < arguments.Length; index++)
    {
        var value = index + 1 < arguments.Length ? arguments[index + 1] : null;
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
    var os = OperatingSystem.IsWindows() ? "win" : OperatingSystem.IsMacOS() ? "osx" : "linux";
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
    using var process = Process.Start(info)!;
    await process.WaitForExitAsync();
    return process.ExitCode;
}

// Runs the executable the way users and scripts do, in a private home so nothing on the machine is read or written,
// with the update check off so nothing reaches the network.
static async Task<bool> SmokeAsync(string executable, string version)
{
    var home = Directory.CreateTempSubdirectory("pgtail-smoke-").FullName;
    try
    {
        var config = Path.Join(home, "config", "pgtail", "config.toml");
        var data = Path.Join(home, "pgdata");
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

        var log = """
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

        foreach (var (arguments, input, expected) in checks)
        {
            var info = new ProcessStartInfo(executable, arguments)
            {
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
            };

            foreach (var (name, value) in environment)
            {
                info.Environment[name] = value;
            }

            using var process = Process.Start(info)!;
            if (input is not null)
            {
                await process.StandardInput.WriteAsync(input);
            }

            process.StandardInput.Close();
            var stdout = process.StandardOutput.ReadToEndAsync();
            var stderr = process.StandardError.ReadToEndAsync();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            await process.WaitForExitAsync(timeout.Token);
            var text = await stdout;
            var command = "pgtail " + string.Join(' ', arguments);
            if (process.ExitCode != 0 || expected.Any(part => !text.Contains(part, StringComparison.Ordinal)))
            {
                Console.Error.WriteLine($"{command} failed with exit code {process.ExitCode}");
                Console.Error.WriteLine(text);
                Console.Error.WriteLine(await stderr);
                return false;
            }

            Console.WriteLine($"checked: {command}");
        }

        return true;
    }
    finally
    {
        Directory.Delete(home, recursive: true);
    }
}
