# Contract: Homebrew Formula

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This contract defines the Homebrew formula structure for pgtail, hosted in the `willibrandon/homebrew-tap` repository.

---

## Repository Structure

```
willibrandon/homebrew-tap/
├── README.md
└── Formula/
    └── pgtail.rb
```

---

## Formula Specification

### File: `Formula/pgtail.rb`

```ruby
class Pgtail < Formula
  desc "PostgreSQL log tailer with auto-detection and color output"
  homepage "https://github.com/willibrandon/pgtail"
  license "MIT"
  version "0.1.0"

  on_macos do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-macos-arm64"
      sha256 "PLACEHOLDER_SHA256_MACOS_ARM64"

      def install
        bin.install "pgtail-macos-arm64" => "pgtail"
      end
    end

    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-macos-x86_64"
      sha256 "PLACEHOLDER_SHA256_MACOS_X86_64"

      def install
        bin.install "pgtail-macos-x86_64" => "pgtail"
      end
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-linux-arm64"
      sha256 "PLACEHOLDER_SHA256_LINUX_ARM64"

      def install
        bin.install "pgtail-linux-arm64" => "pgtail"
      end
    end

    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-linux-x86_64"
      sha256 "PLACEHOLDER_SHA256_LINUX_X86_64"

      def install
        bin.install "pgtail-linux-x86_64" => "pgtail"
      end
    end
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pgtail --version")
  end
end
```

---

## Required Metadata

| Field | Value | Required |
|-------|-------|----------|
| `desc` | "PostgreSQL log tailer with auto-detection and color output" | Yes |
| `homepage` | "https://github.com/willibrandon/pgtail" | Yes |
| `license` | "MIT" | Yes |
| `version` | Semver string (e.g., "0.1.0") | Yes |
| `url` | GitHub Release download URL | Yes (per platform) |
| `sha256` | SHA256 checksum of binary | Yes (per platform) |

---

## Platform Support Matrix

| Platform | Architecture | Binary Name | SHA256 Placeholder |
|----------|--------------|-------------|-------------------|
| macOS | arm64 | `pgtail-macos-arm64` | `PLACEHOLDER_SHA256_MACOS_ARM64` |
| macOS | x86_64 | `pgtail-macos-x86_64` | `PLACEHOLDER_SHA256_MACOS_X86_64` |
| Linux | arm64 | `pgtail-linux-arm64` | `PLACEHOLDER_SHA256_LINUX_ARM64` |
| Linux | x86_64 | `pgtail-linux-x86_64` | `PLACEHOLDER_SHA256_LINUX_X86_64` |

---

## Installation Commands

### End User

```bash
# First time: Add tap
brew tap willibrandon/tap

# Install
brew install pgtail

# Or in one command
brew install willibrandon/tap/pgtail
```

### Upgrade

```bash
brew upgrade pgtail
```

### Uninstall

```bash
brew uninstall pgtail
brew untap willibrandon/tap  # Optional: remove tap
```

---

## Formula Update Process

When a new version is released:

1. **Calculate SHA256 checksums** for each binary:
   ```bash
   sha256sum pgtail-macos-arm64
   sha256sum pgtail-macos-x86_64
   sha256sum pgtail-linux-arm64
   sha256sum pgtail-linux-x86_64
   ```

2. **Update formula** with new version and checksums:
   ```ruby
   version "0.2.0"
   # Update all sha256 values
   ```

3. **Commit and push** to homebrew-tap repository

### Automated Update (Release Workflow)

The release workflow automates this:

```yaml
- name: Update Homebrew Formula
  env:
    HOMEBREW_TAP_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
  run: |
    # Clone tap repo
    git clone https://x-access-token:${HOMEBREW_TAP_TOKEN}@github.com/willibrandon/homebrew-tap.git

    # Update formula with new version and checksums
    python scripts/update_homebrew_formula.py \
      --version ${{ github.ref_name }} \
      --macos-arm64-sha256 ${{ steps.checksums.outputs.macos_arm64 }} \
      --macos-x86_64-sha256 ${{ steps.checksums.outputs.macos_x86_64 }} \
      --linux-arm64-sha256 ${{ steps.checksums.outputs.linux_arm64 }} \
      --linux-x86_64-sha256 ${{ steps.checksums.outputs.linux_x86_64 }}

    # Commit and push
    cd homebrew-tap
    git add Formula/pgtail.rb
    git commit -m "Update pgtail to ${{ github.ref_name }}"
    git push
```

---

## Testing

### Local Formula Testing

```bash
# Audit formula
brew audit --strict --online Formula/pgtail.rb

# Test formula
brew test willibrandon/tap/pgtail

# Install from local formula
brew install --build-from-source Formula/pgtail.rb
```

### Expected Test Output

```bash
$ brew test willibrandon/tap/pgtail
==> Testing willibrandon/tap/pgtail
==> pgtail --version
pgtail 0.1.0
```

---

## README.md Template

```markdown
# Homebrew Tap for pgtail

This tap contains the [pgtail](https://github.com/willibrandon/pgtail) formula.

## Installation

```bash
brew tap willibrandon/tap
brew install pgtail
```

Or directly:

```bash
brew install willibrandon/tap/pgtail
```

## Upgrade

```bash
brew upgrade pgtail
```

## About pgtail

PostgreSQL log tailer with auto-detection and color output. See the [main repository](https://github.com/willibrandon/pgtail) for documentation.

## License

MIT
```

---

## Security Considerations

### SHA256 Verification

- All binaries verified via SHA256 checksum
- Checksums must be updated for each release
- Brew automatically verifies checksum on download

### HTTPS Only

- All URLs use HTTPS
- GitHub Releases provides HTTPS by default

### Token Security

- `HOMEBREW_TAP_TOKEN` secret required for automated updates
- Token needs `repo` scope for push access
- Token stored in GitHub Secrets
