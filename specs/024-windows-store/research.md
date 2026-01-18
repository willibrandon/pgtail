# Research: Windows Store Distribution

**Feature**: 024-windows-store
**Date**: 2026-01-18

## 1. ARM64 Windows Build Strategy

### Decision
Build native ARM64 executables using GitHub Actions `windows-11-arm` runner.

### Rationale
- **Native performance**: ARM64 users get native binaries without emulation overhead
- **GitHub Actions support**: `windows-11-arm` runners available for public repositories
- **Nuitka ARM64 support**: Nuitka supports ARM64 Windows builds on native ARM64 runners
- **MSIX bundle**: Both architectures bundled for automatic platform selection

### Implementation
```yaml
build-windows-arm64:
  runs-on: windows-11-arm
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Build with Nuitka
      run: |
        uv run nuitka --mode=standalone ...
```

### Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|--------------|
| x64 only with emulation | Simpler build | Performance overhead, not native | User experience degraded |
| Cross-compilation from x64 | Single runner | Nuitka doesn't support cross-compile | Not supported |

## 2. MSIX Package Format

### Decision
Use MSIX Bundle (.msixbundle) format for Store submission.

### Rationale
- **Single upload**: Bundle multiple architectures into one file for simpler Store submission
- **Automatic selection**: Windows downloads only the user's architecture
- **Partner Center requirement**: Preferred format for multi-arch apps
- **Smaller user downloads**: ARM64 users don't download x64 package

### Implementation
```powershell
# Create individual MSIX packages
makeappx pack /d msix-stage-x64 /p pgtail-x64.msix /nv
makeappx pack /d msix-stage-arm64 /p pgtail-arm64.msix /nv  # Future

# Bundle them (x64 only initially)
makeappx bundle /d packages/ /p pgtail.msixbundle /bv 0.5.0.0
```

### Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|--------------|
| Separate MSIX uploads | Simpler build | More complex submission, can't revert to bundle later | Less maintainable |
| MSIX only (no bundle) | Simplest | Can't add architectures later without bundle | Limits future ARM64 native support |

## 3. Partner Center API Authentication

### Decision
Use Azure AD client credentials flow with service principal.

### Rationale
- **Official method**: Microsoft's documented approach for automated submissions
- **Token-based**: No interactive login required in CI/CD
- **Scoped permissions**: Limit to submission operations only

### Implementation
```powershell
# Get access token
$body = @{
    grant_type = "client_credentials"
    client_id = $env:STORE_CLIENT_ID
    client_secret = $env:STORE_CLIENT_SECRET
    resource = "https://manage.devcenter.microsoft.com"
}
$response = Invoke-RestMethod -Method Post `
    -Uri "https://login.microsoftonline.com/$env:STORE_TENANT_ID/oauth2/token" `
    -Body $body
$token = $response.access_token
```

### Required Secrets
| Secret | Source | Purpose |
|--------|--------|---------|
| `STORE_CLIENT_ID` | Azure AD app registration | Application (client) ID |
| `STORE_CLIENT_SECRET` | Azure AD app secrets | Client secret value |
| `STORE_TENANT_ID` | Azure AD | Directory (tenant) ID |
| `STORE_APP_ID` | Partner Center | App ID from Partner Center |

## 4. Store Submission Workflow

### Decision
Implement 7-step submission process with retry logic and status polling.

### Rationale
- **API requirements**: Partner Center API requires specific workflow order
- **Reliability**: Network failures handled with exponential backoff
- **Visibility**: Status polling provides workflow feedback

### Implementation Flow
1. Get OAuth access token
2. Check for and delete pending submissions
3. Create new submission (get `fileUploadUrl`)
4. Update submission metadata (package info)
5. Create ZIP containing MSIXBUNDLE
6. Upload ZIP to Azure Blob Storage via SAS URL
7. Commit submission and poll status

### Retry Strategy
```powershell
$maxRetries = 3
$delays = @(30, 60, 120)  # Exponential backoff

for ($i = 0; $i -lt $maxRetries; $i++) {
    try {
        Invoke-RestMethod -Method Put -Uri $fileUploadUrl -InFile submission.zip
        break
    } catch {
        if ($i -eq $maxRetries - 1) { throw }
        Start-Sleep -Seconds $delays[$i]
    }
}
```

## 5. AppExecutionAlias for CLI

### Decision
Use `windows.appExecutionAlias` extension with `desktop4:Subsystem="console"`.

### Rationale
- **PATH-less invocation**: Users type `pgtail` without manual PATH configuration
- **Store CLI standard**: Same mechanism used by `winget.exe` and other Store CLI tools
- **Console subsystem**: Enables proper stdin/stdout handling

### Implementation
```xml
<Extensions>
  <uap5:Extension Category="windows.appExecutionAlias"
      Executable="pgtail\pgtail.exe"
      EntryPoint="Windows.FullTrustApplication">
    <uap5:AppExecutionAlias desktop4:Subsystem="console">
      <uap5:ExecutionAlias Alias="pgtail.exe" />
    </uap5:AppExecutionAlias>
  </uap5:Extension>
</Extensions>
```

### Creates
- Stub at `%LOCALAPPDATA%\Microsoft\WindowsApps\pgtail.exe`
- WindowsApps folder already in PATH on Windows 10+

## 6. Logo Asset Generation

### Decision
Use ImageMagick to generate PNG assets from pgtail.ico.

### Rationale
- **Existing source**: pgtail.ico already exists in art/
- **CLI-friendly**: ImageMagick available on GitHub Actions runners
- **Consistent branding**: All assets derived from same source

### Required Assets
| File | Size | Usage |
|------|------|-------|
| StoreLogo.png | 50x50 | Store listing |
| Square44x44Logo.png | 44x44 | Taskbar, App list |
| Square150x150Logo.png | 150x150 | Start menu tile |
| Wide310x150Logo.png | 310x150 | Wide Start tile |

### Generation Commands
```powershell
# ImageMagick is preinstalled on both windows-latest (7.1.2-10) and windows-11-arm (7.1.2-0)
magick art/pgtail.ico[0] -resize 50x50 msix/Assets/StoreLogo.png
magick art/pgtail.ico[0] -resize 44x44 msix/Assets/Square44x44Logo.png
magick art/pgtail.ico[0] -resize 150x150 msix/Assets/Square150x150Logo.png
magick art/pgtail.ico[0] -resize 310x150! msix/Assets/Wide310x150Logo.png
```

## 7. Version Format Conversion

### Decision
Append `.0` to semantic version for MSIX format.

### Rationale
- **MSIX requirement**: Version must be X.Y.Z.0 (fourth segment reserved for Store)
- **Prerelease handling**: Strip prerelease suffix (e.g., `-rc1`) for MSIX version

### Implementation
```powershell
$fullVersion = "${{ github.ref_name }}" -replace '^v', ''  # "0.5.0" or "0.5.0-rc1"
$msixVersion = ($fullVersion -replace '-.*$', '') + ".0"   # "0.5.0.0"
```

## Summary

All research items have clear implementation paths:
- ARM64 builds: Native via `windows-11-arm` runner
- Package format: MSIX bundle containing x64 and ARM64 packages
- Store submission: Partner Center API with Azure AD authentication
- CLI invocation: AppExecutionAlias with console subsystem
- Assets: Generated from pgtail.ico using ImageMagick
- Version format: Append `.0` to semantic version
