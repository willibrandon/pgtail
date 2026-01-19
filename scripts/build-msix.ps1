<#
.SYNOPSIS
    Build MSIX package locally for testing.

.DESCRIPTION
    This script builds a local MSIX package for pgtail. It:
    1. Checks for required tools (Windows SDK, ImageMagick)
    2. Optionally generates a self-signed certificate
    3. Builds pgtail with Nuitka
    4. Creates and optionally signs the MSIX package

.PARAMETER Architecture
    Target architecture: x64 or arm64 (default: current architecture)

.PARAMETER Version
    Version number for the package (default: read from pyproject.toml)

.PARAMETER SkipBuild
    Skip Nuitka build, use existing build output

.PARAMETER Unsigned
    Create unsigned package (requires Developer Mode for installation)

.EXAMPLE
    .\build-msix.ps1
    .\build-msix.ps1 -Unsigned
    .\build-msix.ps1 -Architecture arm64
    .\build-msix.ps1 -Version 0.5.0.0 -SkipBuild
#>

param(
    [ValidateSet("x64", "arm64")]
    [string]$Architecture = $(if ([System.Environment]::Is64BitOperatingSystem) {
        if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "x64" }
    } else { "x64" }),

    [string]$Version,

    [switch]$SkipBuild,

    [switch]$Unsigned
)

$ErrorActionPreference = "Stop"

# In PowerShell 7.3+, native commands can trigger terminating errors on stderr output.
# Disable this for OpenSSL which outputs progress to stderr.
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

# Read version from pyproject.toml if not specified
if (-not $Version) {
    $pyprojectPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        $content = Get-Content $pyprojectPath -Raw
        if ($content -match 'version\s*=\s*"([^"]+)"') {
            $semver = $Matches[1]
            # Convert semver (X.Y.Z) to MSIX format (X.Y.Z.0)
            $Version = "$semver.0"
        }
    }
    if (-not $Version) {
        $Version = "0.0.1.0"
        Write-Host "Warning: Could not read version from pyproject.toml, using default $Version" -ForegroundColor Yellow
    }
}

# Colors for output
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    WARNING: $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "    ERROR: $msg" -ForegroundColor Red }

# Find project root
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

Write-Host "Building pgtail MSIX package" -ForegroundColor White
Write-Host "  Architecture: $Architecture"
Write-Host "  Version: $Version"
Write-Host "  Unsigned: $Unsigned"
Write-Host "  Project root: $projectRoot"

# Check for Windows SDK
Write-Step "Checking for Windows SDK..."
$makeAppx = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
            Sort-Object { [version]($_.Directory.Parent.Name) } -Descending |
            Select-Object -First 1

if (-not $makeAppx) {
    Write-Err "Windows SDK not found"
    Write-Host ""
    Write-Host "Install Windows SDK with:"
    Write-Host "  winget install Microsoft.WindowsSDK.10.0.26100"
    Write-Host ""
    exit 1
}
Write-Success "Found MakeAppx: $($makeAppx.FullName)"

$signTool = Join-Path $makeAppx.Directory "signtool.exe"
if (-not (Test-Path $signTool)) {
    Write-Err "SignTool not found at $signTool"
    exit 1
}
Write-Success "Found SignTool: $signTool"

# Check for ImageMagick
Write-Step "Checking for ImageMagick..."
$magick = Get-Command magick -ErrorAction SilentlyContinue
if (-not $magick) {
    # Try common install location
    $magickPath = Get-ChildItem "C:\Program Files\ImageMagick-*\magick.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($magickPath) {
        $magick = $magickPath.FullName
    }
}

if (-not $magick) {
    Write-Err "ImageMagick not found"
    Write-Host ""
    Write-Host "Install ImageMagick with:"
    Write-Host "  winget install ImageMagick.ImageMagick"
    Write-Host ""
    exit 1
}
Write-Success "Found ImageMagick: $magick"

# Generate logo assets if not present
Write-Step "Generating logo assets..."
$assetsDir = Join-Path $projectRoot "msix\Assets"
if (-not (Test-Path $assetsDir)) {
    New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null
}

$icoPath = Join-Path $projectRoot "art\pgtail.ico"
if (-not (Test-Path $icoPath)) {
    Write-Err "Source icon not found: $icoPath"
    exit 1
}

$assets = @(
    @{ Name = "StoreLogo.png"; Size = "50x50" },
    @{ Name = "Square44x44Logo.png"; Size = "44x44" },
    @{ Name = "Square150x150Logo.png"; Size = "150x150" },
    @{ Name = "Wide310x150Logo.png"; Size = "150x150"; Extent = "310x150" }
)

foreach ($asset in $assets) {
    $outPath = Join-Path $assetsDir $asset.Name
    if ($asset.Extent) {
        & $magick "$icoPath[0]" -resize $asset.Size -gravity center -background transparent -extent $asset.Extent $outPath
    } else {
        & $magick "$icoPath[0]" -resize $asset.Size $outPath
    }
    Write-Success "Generated $($asset.Name)"
}

# Build with Nuitka
if (-not $SkipBuild) {
    Write-Step "Building with Nuitka..."
    $distDir = Join-Path $projectRoot "dist"

    uv run nuitka `
        --mode=standalone `
        --output-dir=$distDir `
        --output-filename=pgtail `
        --windows-icon-from-ico=art/pgtail.ico `
        --include-package=pgtail_py `
        --include-package=psutil `
        --include-package-data=certifi `
        --include-module=pgtail_py.detector_unix `
        --include-module=pgtail_py.detector_windows `
        --include-module=pgtail_py.notifier_unix `
        --include-module=pgtail_py.notifier_windows `
        --nofollow-import-to=psutil.tests `
        --python-flag=no_asserts `
        --python-flag=-m `
        --assume-yes-for-downloads `
        pgtail_py

    if ($LASTEXITCODE -ne 0) {
        Write-Err "Nuitka build failed"
        exit 1
    }

    # Find and rename output
    $nuitkaOutput = Get-ChildItem "$distDir\*.dist" | Select-Object -First 1
    if (-not $nuitkaOutput) {
        Write-Err "Nuitka output directory not found"
        exit 1
    }

    $buildOutput = Join-Path $distDir "pgtail-$Architecture"
    if (Test-Path $buildOutput) {
        Remove-Item -Recurse -Force $buildOutput
    }
    Move-Item $nuitkaOutput.FullName $buildOutput
    Write-Success "Build output: $buildOutput"
} else {
    $buildOutput = Join-Path $projectRoot "dist\pgtail-$Architecture"
    if (-not (Test-Path $buildOutput)) {
        Write-Err "Build output not found: $buildOutput"
        Write-Host "Run without -SkipBuild first"
        exit 1
    }
    Write-Success "Using existing build: $buildOutput"
}

# Certificate setup (only needed for signed packages)
$certPath = $null
$certPassword = $null
$certSubject = $null

if (-not $Unsigned) {
    # Create or load self-signed certificate using OpenSSL
    # OpenSSL is fully non-interactive and works across PowerShell versions
    Write-Step "Setting up code signing certificate..."
    $certPath = Join-Path $projectRoot "msix\pgtail.pfx"
    $certPassword = "pgtail-password"
    # Subject order must match OpenSSL output exactly: C, O, CN
    $certSubject = "C=US, O=pgtail, CN=pgtail"

    if (-not (Test-Path $certPath)) {
        Write-Host "    Creating new self-signed certificate using OpenSSL..."

        # Find OpenSSL (common locations: Git for Windows, standalone install, winget)
        $openssl = Get-Command openssl -ErrorAction SilentlyContinue
        if (-not $openssl) {
            # Check common install locations
            $opensslPaths = @(
                "C:\Program Files\Git\usr\bin\openssl.exe",
                "C:\Program Files\Git\mingw64\bin\openssl.exe",
                "C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
                "C:\OpenSSL-Win64\bin\openssl.exe"
            )
            foreach ($path in $opensslPaths) {
                if (Test-Path $path) {
                    $openssl = $path
                    break
                }
            }
        }

        if (-not $openssl) {
            Write-Err "OpenSSL not found"
            Write-Host ""
            Write-Host "OpenSSL is required for certificate generation. Install via:"
            Write-Host "  - Git for Windows (includes OpenSSL): winget install Git.Git"
            Write-Host "  - Standalone: winget install ShiningLight.OpenSSL"
            Write-Host ""
            exit 1
        }

        $opensslPath = if ($openssl -is [string]) { $openssl } else { $openssl.Source }
        Write-Success "Found OpenSSL: $opensslPath"

        # Create temp directory for intermediate files
        $tempDir = Join-Path $env:TEMP "pgtail-cert-$([guid]::NewGuid().ToString('N'))"
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        $keyPath = Join-Path $tempDir "pgtail.key"
        $cerPath = Join-Path $tempDir "pgtail.cer"
        $configPath = Join-Path $tempDir "openssl.cnf"

        # Create OpenSSL config for code signing certificate
        # EKU 1.3.6.1.5.5.7.3.3 = code signing
        # EKU 1.3.6.1.4.1.311.10.3.13 = lifetime signing (signature valid after cert expires)
        @"
[req]
distinguished_name = req_dn
x509_extensions = v3_ext
prompt = no

[req_dn]
CN = pgtail
O = pgtail
C = US

[v3_ext]
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = codeSigning, 1.3.6.1.4.1.311.10.3.13
"@ | Out-File -FilePath $configPath -Encoding ASCII

        # Generate self-signed certificate (non-interactive, 1 year validity)
        # Use cmd.exe to run OpenSSL to avoid PowerShell treating stderr as errors
        Write-Host "    Generating certificate..."
        cmd.exe /c "`"$opensslPath`" req -x509 -newkey rsa:2048 -keyout `"$keyPath`" -out `"$cerPath`" -days 365 -nodes -config `"$configPath`" 2>nul"

        if (-not (Test-Path $cerPath) -or -not (Test-Path $keyPath)) {
            Write-Err "OpenSSL certificate generation failed"
            Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
            exit 1
        }
        Write-Success "Generated certificate and private key"

        # Convert to PFX format for SignTool
        # Use -legacy flag for OpenSSL 3.0+ compatibility with Windows SignTool
        Write-Host "    Converting to PFX..."
        cmd.exe /c "`"$opensslPath`" pkcs12 -export -legacy -out `"$certPath`" -inkey `"$keyPath`" -in `"$cerPath`" -passout pass:$certPassword 2>nul"

        if (-not (Test-Path $certPath)) {
            Write-Err "OpenSSL PFX export failed"
            Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
            exit 1
        }

        # Clean up temp files
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

        Write-Success "Created certificate: $certPath"
        Write-Warn "This is a self-signed test certificate"
        Write-Host "    To install the package, first import the certificate to Trusted Root CA"
    } else {
        Write-Success "Using existing certificate: $certPath"
    }
} else {
    Write-Step "Skipping certificate setup (unsigned mode)..."
    Write-Success "Package will be unsigned (requires Developer Mode for installation)"
}

# Create MSIX staging directory
Write-Step "Creating MSIX staging directory..."
$stageDir = Join-Path $projectRoot "msix-stage-local"
if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir | Out-Null

# Copy and update manifest
$manifest = Get-Content (Join-Path $projectRoot "msix\AppxManifest.xml") -Raw
$manifest = $manifest -replace 'YOUR_PACKAGE_IDENTITY_NAME', 'pgtail'
$manifest = $manifest -replace 'Version="0\.0\.0\.0"', "Version=`"$Version`""
$manifest = $manifest -replace 'ProcessorArchitecture="PROCESSOR_ARCHITECTURE"', "ProcessorArchitecture=`"$Architecture`""

if ($Unsigned) {
    # For unsigned packages, use a special OID in the Publisher to prevent conflicts with signed packages
    # See: https://learn.microsoft.com/en-us/windows/msix/package/unsigned-package
    $unsignedPublisher = "CN=pgtail-unsigned, OID.2.25.311729368913984317654407730594956997722=1"
    $manifest = $manifest -replace 'YOUR_PUBLISHER_CN', $unsignedPublisher
} else {
    $manifest = $manifest -replace 'YOUR_PUBLISHER_CN', $certSubject
}

Set-Content -Path (Join-Path $stageDir "AppxManifest.xml") -Value $manifest

# Copy assets
Copy-Item -Path $assetsDir -Destination (Join-Path $stageDir "Assets") -Recurse

# Copy build output
Copy-Item -Path $buildOutput -Destination (Join-Path $stageDir "pgtail") -Recurse

Write-Success "Staging directory created"

# Build MSIX package
Write-Step "Building MSIX package..."
$msixPath = Join-Path $projectRoot "dist\pgtail-$Architecture.msix"

& $makeAppx.FullName pack /d $stageDir /p $msixPath /nv /o

if ($LASTEXITCODE -ne 0) {
    Write-Err "MakeAppx failed"
    exit 1
}
Write-Success "Created unsigned MSIX: $msixPath"

# Sign the package (skip for unsigned mode)
if (-not $Unsigned) {
    Write-Step "Signing MSIX package..."
    & $signTool sign /fd SHA256 /a /f $certPath /p $certPassword $msixPath

    if ($LASTEXITCODE -ne 0) {
        Write-Err "SignTool failed"
        exit 1
    }
    Write-Success "Signed MSIX: $msixPath"
} else {
    Write-Step "Skipping signing (unsigned mode)..."
    Write-Success "Created unsigned MSIX: $msixPath"
}

# Cleanup
Remove-Item -Recurse -Force $stageDir

# Summary
Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Package: $msixPath"
Write-Host "Size: $([math]::Round((Get-Item $msixPath).Length / 1MB, 2)) MB"
Write-Host ""

if ($Unsigned) {
    Write-Host "To install (requires Developer Mode):"
    Write-Host "  Add-AppxPackage -Path `"$msixPath`" -AllowUnsigned"
    Write-Host ""
    Write-Host "Note: Developer Mode must be enabled in Windows Settings > Privacy & security > For developers"
} else {
    Write-Host "To install (requires certificate trust):"
    Write-Host "  1. Import $certPath to 'Trusted Root Certification Authorities'"
    Write-Host "  2. Double-click $msixPath or run: Add-AppxPackage $msixPath"
    Write-Host ""
    Write-Host "To test without installing certificate:"
    Write-Host "  .\scripts\test-msix.ps1"
}
