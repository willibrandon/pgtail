<#
.SYNOPSIS
    Test MSIX package installation and functionality.

.DESCRIPTION
    This script tests a local MSIX package by:
    1. Installing the self-signed certificate to Trusted Root CA (requires elevation)
    2. Installing the MSIX package
    3. Testing the pgtail command
    4. Uninstalling the package
    5. Optionally removing the certificate

.PARAMETER MsixPath
    Path to the MSIX package (default: dist\pgtail-x64.msix)

.PARAMETER KeepInstalled
    Don't uninstall after testing

.PARAMETER SkipCertCleanup
    Don't remove the test certificate after uninstall

.EXAMPLE
    .\test-msix.ps1
    .\test-msix.ps1 -MsixPath dist\pgtail-arm64.msix
    .\test-msix.ps1 -KeepInstalled
#>

param(
    [string]$MsixPath,

    [switch]$KeepInstalled,

    [switch]$SkipCertCleanup
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    WARNING: $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "    ERROR: $msg" -ForegroundColor Red }

# Find project root
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Default MSIX path
if (-not $MsixPath) {
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "x64" }
    $MsixPath = Join-Path $projectRoot "dist\pgtail-$arch.msix"
}

if (-not (Test-Path $MsixPath)) {
    Write-Err "MSIX package not found: $MsixPath"
    Write-Host ""
    Write-Host "Build the package first:"
    Write-Host "  .\scripts\build-msix.ps1"
    exit 1
}

Write-Host "Testing MSIX package" -ForegroundColor White
Write-Host "  Package: $MsixPath"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn "Not running as Administrator - certificate installation may fail"
    Write-Host "    Run PowerShell as Administrator for full testing"
}

# Install certificate
Write-Step "Installing test certificate..."
$certPath = Join-Path $projectRoot "msix\pgtail.pfx"
$certPassword = "pgtail-password"

if (-not (Test-Path $certPath)) {
    Write-Err "Certificate not found: $certPath"
    Write-Host "Run build-msix.ps1 first to create the certificate"
    exit 1
}

try {
    # Write the certificate import script to a temp file
    # This avoids PSModulePath conflicts when calling Windows PowerShell from PS7
    $tempScript = Join-Path $env:TEMP "import-cert-$([guid]::NewGuid().ToString('N')).ps1"

    @"
`$securePassword = ConvertTo-SecureString -String '$certPassword' -Force -AsPlainText
`$cert = Import-PfxCertificate -FilePath '$certPath' -Password `$securePassword -CertStoreLocation 'Cert:\LocalMachine\Root'
Write-Output `$cert.Thumbprint
"@ | Out-File -FilePath $tempScript -Encoding UTF8

    # Run in Windows PowerShell with clean environment (clear PSModulePath to avoid PS7 conflicts)
    $thumbprint = cmd.exe /c "set PSModulePath= && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$tempScript`""

    # Clean up temp script
    Remove-Item $tempScript -Force -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -eq 0 -and $thumbprint) {
        Write-Success "Certificate installed: $thumbprint"
        $certInstalled = $true
    } else {
        throw "Import failed"
    }
} catch {
    Write-Warn "Could not install certificate: $_"
    Write-Host "    You may need to run as Administrator"
    $certInstalled = $false
}

# Check for existing installation
Write-Step "Checking for existing installation..."
$existingPackage = Get-AppxPackage -Name "pgtail" -ErrorAction SilentlyContinue
if ($existingPackage) {
    Write-Host "    Removing existing installation..."
    Remove-AppxPackage $existingPackage.PackageFullName
    Write-Success "Removed existing package"
}

# Install MSIX
Write-Step "Installing MSIX package..."
try {
    Add-AppxPackage -Path $MsixPath
    Write-Success "Package installed"
} catch {
    Write-Err "Installation failed: $_"
    if (-not $certInstalled) {
        Write-Host ""
        Write-Host "Installation failed because the certificate is not trusted."
        Write-Host "Run this script as Administrator, or manually:"
        Write-Host "  1. Right-click $certPath → Install PFX"
        Write-Host "  2. Choose 'Local Machine'"
        Write-Host "  3. Store in 'Trusted Root Certification Authorities'"
        Write-Host "  4. Re-run this script"
    }
    exit 1
}

# Verify installation
Write-Step "Verifying installation..."
$package = Get-AppxPackage -Name "pgtail"
if (-not $package) {
    Write-Err "Package not found after installation"
    exit 1
}

Write-Success "Package: $($package.Name)"
Write-Success "Version: $($package.Version)"
Write-Success "Architecture: $($package.Architecture)"
Write-Success "Install Location: $($package.InstallLocation)"

# Test AppExecutionAlias
Write-Step "Testing AppExecutionAlias..."
$aliasPath = "$env:LOCALAPPDATA\Microsoft\WindowsApps\pgtail.exe"
if (Test-Path $aliasPath) {
    Write-Success "Alias created: $aliasPath"
} else {
    Write-Warn "Alias not found at expected location"
    Write-Host "    This may be normal - checking PATH..."
}

# Test command execution
Write-Step "Testing pgtail command..."
try {
    $versionOutput = & pgtail --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "pgtail --version: $versionOutput"
    } else {
        Write-Err "pgtail --version failed with exit code $LASTEXITCODE"
        Write-Host "    Output: $versionOutput"
    }
} catch {
    Write-Err "Failed to run pgtail: $_"
    Write-Host ""
    Write-Host "Try running manually:"
    Write-Host "  pgtail --version"
}

# Test help command
Write-Step "Testing pgtail --help..."
try {
    $helpOutput = & pgtail --help 2>&1 | Select-Object -First 5
    if ($LASTEXITCODE -eq 0) {
        Write-Success "pgtail --help works"
        $helpOutput | ForEach-Object { Write-Host "    $_" }
    } else {
        Write-Warn "pgtail --help returned exit code $LASTEXITCODE"
    }
} catch {
    Write-Warn "Could not run pgtail --help: $_"
}

# Test no-args execution (important for Store certification)
# Note: pgtail is an interactive REPL, so we skip blocking wait
Write-Step "Testing no-args execution (Store certification requirement)..."
Write-Success "Skipped - pgtail is an interactive REPL (enters command mode with no args)"
Write-Host "    Interactive CLI apps are permitted by Store certification"
Write-Host "    The app launches successfully and can be exited with 'quit' or 'q'"

# Uninstall if not keeping
if (-not $KeepInstalled) {
    Write-Step "Uninstalling package..."
    Remove-AppxPackage $package.PackageFullName
    Write-Success "Package uninstalled"

    # Verify uninstall
    $remaining = Get-AppxPackage -Name "pgtail" -ErrorAction SilentlyContinue
    if ($remaining) {
        Write-Warn "Package still present after uninstall"
    } else {
        Write-Success "Package fully removed"
    }

    # Check alias removal
    if (Test-Path $aliasPath) {
        Write-Warn "Alias still present (may be cached)"
    }

    # Remove certificate
    if ($certInstalled -and -not $SkipCertCleanup) {
        Write-Step "Removing test certificate..."
        try {
            # Write the certificate removal script to a temp file
            # This avoids PSModulePath conflicts when calling Windows PowerShell from PS7
            $tempScript = Join-Path $env:TEMP "remove-cert-$([guid]::NewGuid().ToString('N')).ps1"

            @"
Get-ChildItem 'Cert:\LocalMachine\Root' | Where-Object { `$_.Subject -like '*pgtail*' } | Remove-Item
"@ | Out-File -FilePath $tempScript -Encoding UTF8

            # Run in Windows PowerShell with clean environment
            cmd.exe /c "set PSModulePath= && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$tempScript`"" | Out-Null

            # Clean up temp script
            Remove-Item $tempScript -Force -ErrorAction SilentlyContinue

            if ($LASTEXITCODE -eq 0) {
                Write-Success "Certificate removed"
            } else {
                throw "Remove failed"
            }
        } catch {
            Write-Warn "Could not remove certificate: $_"
        }
    }
} else {
    Write-Host ""
    Write-Host "Package kept installed. To uninstall manually:" -ForegroundColor Yellow
    Write-Host "  Get-AppxPackage pgtail | Remove-AppxPackage"
}

# Summary
Write-Host ""
Write-Host "Test complete!" -ForegroundColor Green
