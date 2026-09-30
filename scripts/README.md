# Scripts

Repository utilities are .NET file-based apps. They need the .NET 10 SDK; run one with `dotnet run --file`:

```
dotnet run --file scripts/Publish-NativeAot.cs -- --rid linux-x64 --package-version 1.2.3
```

| App | Purpose |
| --- | --- |
| `Publish-NativeAot.cs` | Publishes pgtail with Native AOT for one runtime, runs the executable, packs its runtime-specific tool package, and runs the packaged executable. |
| `Verify-CodeQl.cs` | Lists every finding in the CodeQL results under a directory and fails when there is one. |

`Publish-NativeAot.cs` must run on a machine of the runtime it publishes for, since it runs what it builds. It writes to
`artifacts/native-aot/<rid>/publish` and `artifacts/native-aot/<rid>/packages`; `--output` changes the base directory.
The checks run pgtail in a private home with the update check turned off, so they read nothing on the machine and reach
nothing on the network.

GitHub shows CodeQL findings in the Security tab without failing a check. The CodeQL workflow therefore saves its result
file and runs `Verify-CodeQl.cs` on it, so a finding fails the pull request that introduced it:

```
dotnet run --file scripts/Verify-CodeQl.cs -- artifacts/codeql-results
```

The scripts build under the repository's `.editorconfig` and the analyzers in `src/Pgtail.Analyzers`, like every
project, so `dotnet build scripts/<name>.cs` reports what the solution build would. `dotnet format` cannot process a
file-based app, so fix what that build reports by hand. The solution does not include the scripts, so build each of
them after a change to the analyzers or the `.editorconfig`.
