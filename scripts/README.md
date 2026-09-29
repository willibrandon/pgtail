# Scripts

Repository utilities are .NET file-based apps. They need the .NET 10 SDK; run one with `dotnet run --file`:

```
dotnet run --file scripts/Publish-NativeAot.cs -- --rid linux-x64 --package-version 1.2.3
```

| App | Purpose |
| --- | --- |
| `Publish-NativeAot.cs` | Publishes pgtail with Native AOT for one runtime, runs the executable, packs its runtime-specific tool package, and runs the packaged executable. |

`Publish-NativeAot.cs` must run on a machine of the runtime it publishes for, since it runs what it builds. It writes to
`artifacts/native-aot/<rid>/publish` and `artifacts/native-aot/<rid>/packages`; `--output` changes the base directory.
The checks run pgtail in a private home with the update check turned off, so they read nothing on the machine and reach
nothing on the network.
