# Feature Specification: Nuitka Migration for Binary Distribution

**Feature Branch**: `020-nuitka-migration`
**Created**: 2026-01-01
**Status**: Draft
**Input**: Migrate from PyInstaller to Nuitka for binary distribution to eliminate cold start penalty

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast CLI Startup (Priority: P1)

As a pgtail user, I want the binary to start instantly so that quick operations like `--version`, `--check-update`, and `list` feel responsive like native CLI tools.

**Why this priority**: The primary motivation for this migration is the 4.5-second cold start penalty. Every invocation suffers this delay, making the tool feel sluggish for simple operations.

**Independent Test**: Can be fully tested by timing `pgtail --version` and verifying it completes in under 1 second, delivering immediate user value by eliminating the startup delay.

**Acceptance Scenarios**:

1. **Given** the pgtail binary is installed, **When** user runs `pgtail --version`, **Then** the version displays in less than 1 second
2. **Given** the pgtail binary is installed, **When** user runs `pgtail --check-update`, **Then** the update check completes without noticeable startup delay
3. **Given** the pgtail binary is installed, **When** user runs `pgtail list`, **Then** PostgreSQL instances are listed promptly
4. **Given** the pgtail binary is installed, **When** user runs `pgtail list --help`, **Then** CLI help text displays correctly with all command descriptions

---

### User Story 2 - Cross-Platform Binary Distribution (Priority: P1)

As a distribution maintainer, I want binaries that work reliably on all supported platforms so that users can install pgtail regardless of their operating system.

**Why this priority**: Binary distribution is the primary delivery mechanism. All 5 platforms must build and function correctly for the release to be viable.

**Independent Test**: Can be fully tested by building binaries on each platform, verifying they execute correctly, and running basic functionality tests.

**Acceptance Scenarios**:

1. **Given** CI builds for macOS ARM64, **When** build completes, **Then** the binary runs `--version` successfully
2. **Given** CI builds for macOS x86_64, **When** build completes, **Then** the binary runs `--version` successfully
3. **Given** CI builds for Linux x86_64, **When** build completes, **Then** the binary runs `--version` successfully
4. **Given** CI builds for Linux ARM64, **When** build completes, **Then** the binary runs `--version` successfully
5. **Given** CI builds for Windows x86_64, **When** build completes, **Then** the binary runs `--version` successfully

---

### User Story 3 - Homebrew Installation (Priority: P2)

As a macOS/Linux user, I want to install pgtail via Homebrew so that I can manage it alongside my other development tools.

**Why this priority**: Homebrew is the primary distribution channel for macOS users. Formula must adapt to the new archive-based distribution format.

**Independent Test**: Can be fully tested by running `brew install willibrandon/tap/pgtail` and verifying the executable works correctly.

**Acceptance Scenarios**:

1. **Given** pgtail is released with Nuitka binaries, **When** user runs `brew install willibrandon/tap/pgtail`, **Then** the formula installs the correct platform binary
2. **Given** pgtail is installed via Homebrew, **When** user runs `pgtail --version`, **Then** the correct version displays
3. **Given** a new pgtail version is released, **When** Homebrew formula is updated, **Then** users can upgrade seamlessly

---

### User Story 4 - Windows winget Installation (Priority: P2)

As a Windows user, I want to install pgtail via winget so that I can use standard Windows package management.

**Why this priority**: winget is the standard Windows package manager. An MSI installer is required for proper winget integration.

**Independent Test**: Can be fully tested by running `winget install willibrandon.pgtail` and verifying the executable works.

**Acceptance Scenarios**:

1. **Given** pgtail MSI is published to winget, **When** user runs `winget install willibrandon.pgtail`, **Then** pgtail installs to Program Files and adds to PATH
2. **Given** pgtail is installed via winget, **When** user runs `pgtail --version`, **Then** the correct version displays
3. **Given** a newer version is available, **When** user runs `winget upgrade pgtail`, **Then** the upgrade completes cleanly

---

### User Story 5 - Manual Windows Installation (Priority: P3)

As a Windows user without admin rights, I want a portable ZIP distribution so that I can use pgtail without administrative installation.

**Why this priority**: Some users cannot run MSI installers. A ZIP archive provides a portable alternative.

**Independent Test**: Can be fully tested by extracting the ZIP and running the executable directly.

**Acceptance Scenarios**:

1. **Given** user downloads the Windows ZIP, **When** they extract and run `pgtail.exe --version`, **Then** the version displays correctly
2. **Given** the ZIP is extracted to any folder, **When** user adds the folder to PATH, **Then** pgtail is accessible from any terminal

---

### User Story 6 - Full Functionality Preservation (Priority: P1)

As a pgtail user, I want all existing features to work identically after the migration so that my workflows are not disrupted.

**Why this priority**: The migration must not break any existing functionality. All features must work as before.

**Independent Test**: Can be fully tested by running the existing test suite against the compiled binary and exercising all major features.

**Acceptance Scenarios**:

1. **Given** a Nuitka-compiled binary, **When** user enters REPL mode, **Then** all commands work as expected
2. **Given** a Nuitka-compiled binary, **When** user enters tail mode, **Then** log tailing functions correctly with all filters
3. **Given** a Nuitka-compiled binary, **When** user runs PostgreSQL detection, **Then** instances are found via all detection methods
4. **Given** a Nuitka-compiled binary, **When** user triggers desktop notifications, **Then** notifications appear on the appropriate platform

---

### Edge Cases

- What happens when the binary is run from a read-only filesystem? The system displays a clear error message without crashing.
- How does the system handle missing CA certificates for update checks? The system fails gracefully with a clear SSL/certificate error message.
- What happens on platforms with unusual architectures not in the build matrix? The system provides a clear "unsupported platform" message or users compile from source.
- How does the system behave when run under Rosetta 2 on Apple Silicon? The x86_64 binary works correctly via Rosetta emulation.
- What happens if the user moves the binary without its dependency folder? The system fails with a clear error about missing dependencies.
- How does version display work when package metadata is unavailable? The system falls back to hardcoded `__version__` value.
- What happens when antivirus software quarantines dependencies? The system provides troubleshooting guidance in documentation (Windows-specific concern).
- How does the build handle psutil's native extensions on each platform? The build explicitly includes psutil with all platform-specific native extensions.

## Requirements *(mandatory)*

### Functional Requirements

**Build System**:

- **FR-001**: Build system MUST produce standalone executables using Nuitka's `--mode=standalone`
- **FR-002**: Build system MUST NOT use `--mode=onefile` (would reintroduce extraction overhead)
- **FR-003**: Build system MUST include all pgtail_py modules explicitly to handle conditional imports
- **FR-004**: Build system MUST include psutil package with platform-specific native extensions
- **FR-005**: Build system MUST include certifi CA bundle for HTTPS operations
- **FR-006**: Build system MUST NOT strip docstrings (Typer uses them for CLI help)
- **FR-007**: Build system MUST pin Nuitka version to stable 2.x series (not nightly builds)

**Artifacts**:

- **FR-008**: System MUST produce tar.gz archives for macOS and Linux platforms
- **FR-009**: System MUST produce ZIP archive for Windows
- **FR-010**: System MUST produce MSI installer for Windows using WiX Toolset
- **FR-011**: Archives MUST contain a folder named `pgtail-{platform}-{arch}/` with the executable inside
- **FR-012**: MSI installer MUST install to `Program Files\pgtail\` and add to system PATH
- **FR-013**: System MUST generate SHA256 checksums for all release artifacts

**Version Detection**:

- **FR-014**: Binary MUST display correct version via `pgtail --version`
- **FR-015**: Version system MUST have hardcoded fallback when importlib.metadata is unavailable
- **FR-016**: Version fallback MUST be synchronized with pyproject.toml version

**CI/CD**:

- **FR-017**: CI workflow MUST build for all 5 platforms: macOS ARM64, macOS x86_64, Linux x86_64, Linux ARM64, Windows x86_64
- **FR-018**: CI workflow MUST verify each build by running `--version` check
- **FR-019**: CI workflow MUST update Homebrew formula with new checksums on release
- **FR-020**: CI workflow MUST submit or update winget manifest on release
- **FR-021**: CI workflow MUST create GitHub issue if any release step fails
- **FR-029**: CI workflow MUST verify Windows ZIP artifact by extracting and running `pgtail.exe --version`

**Local Development**:

- **FR-022**: Makefile `build` target MUST use Nuitka instead of PyInstaller
- **FR-023**: Makefile MUST include `build-test` target to verify local builds
- **FR-024**: Makefile `clean` target MUST remove Nuitka build artifacts

**Documentation**:

- **FR-025**: README MUST be updated with new installation instructions for all platforms (Homebrew tar.gz, winget MSI, Windows ZIP portable, manual Unix tar.gz)
- **FR-026**: README installation table MUST reflect the changed artifact formats (archives instead of single binaries)
- **FR-027**: Documentation MUST include troubleshooting for "missing dependency folder" error (common user mistake with standalone distribution)
- **FR-028**: Windows documentation MUST distinguish between MSI (admin/winget) and ZIP (portable/no-admin) installation paths

### Key Entities

- **Build Artifact**: A distributable package (tar.gz, ZIP, or MSI) containing the compiled executable and dependencies
- **Platform Matrix**: The set of OS/architecture combinations supported (5 total: macOS ARM64, macOS x86_64, Linux x86_64, Linux ARM64, Windows x86_64)
- **Nuitka Configuration**: The set of flags and options controlling compilation behavior
- **Release Workflow**: The CI pipeline that builds, packages, and publishes artifacts

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Binary startup time is less than 1 second for `pgtail --version` (down from 5.1 seconds)
- **SC-002**: All 5 platform builds complete successfully in CI
- **SC-003**: Total CI workflow time is under 30 minutes
- **SC-004**: Binary size is under 50 MB per platform (projected 20-30 MB)
- **SC-005**: All existing tests pass when run against compiled binary
- **SC-006**: CLI help text displays correctly (`pgtail list --help` shows command descriptions)
- **SC-007**: Version displays correctly (`pgtail --version` shows actual version, not 0.0.0-dev)
- **SC-008**: Homebrew installation completes successfully via `brew install willibrandon/tap/pgtail`
- **SC-009**: winget installation completes successfully via `winget install willibrandon.pgtail`
- **SC-010**: All core features work in compiled binary: REPL mode, tail mode, detection, notifications, themes
- **SC-011**: Zero regression in existing functionality compared to PyInstaller builds
- **SC-012**: Windows ZIP portable install verified by extracting and running `pgtail.exe --version` successfully
- **SC-013**: README and documentation updated with new artifact formats and installation instructions

## Scope & Boundaries

### In Scope

- Migrating from PyInstaller to Nuitka for all 5 platforms
- Updating GitHub Actions release workflow
- Updating Homebrew formula for archive-based distribution
- Creating MSI installer for Windows winget distribution
- Adding version fallback for compiled binaries
- Updating Makefile build targets
- Creating build helper scripts
- Updating README with new installation instructions for all platforms
- Updating docs (getting-started, installation guides) to reflect archive-based distribution

### Out of Scope

- Adding new platforms (e.g., Windows ARM64, Linux musl)
- Changing functionality of pgtail itself
- Modifying the REPL or tail mode behavior
- Adding new CLI commands or options
- Performance optimizations beyond startup time

## Assumptions

- GitHub runners have required C compilers pre-installed for Nuitka
- Nuitka 2.x stable series remains compatible with Python 3.12 and project dependencies
- WiX Toolset 5.x is available via `dotnet tool install` on Windows runners
- The winget-pkgs repository accepts MSI installers with the chosen manifest format
- Users installing via Homebrew or winget have standard PATH configuration
- Archive-based distribution is acceptable (folder instead of single executable)
- Build time increase from ~10 min to ~20 min is acceptable for release workflows

## Dependencies

- **Nuitka >= 2.5**: Python-to-C compiler for producing native executables
- **WiX Toolset 5.x**: MSI installer builder for Windows
- **GitHub Actions runners**: Build infrastructure for all 5 platforms
- **homebrew-tap repository**: Target for Homebrew formula updates
- **winget-pkgs repository**: Target for winget manifest submissions (local clone available at `/Users/brandon/src/winget-pkgs` for reference)

## Risks & Mitigations

| Risk                               | Likelihood | Impact | Mitigation                                                                  |
|------------------------------------|------------|--------|-----------------------------------------------------------------------------|
| Textual/Rich compilation issues    | Low        | High   | Use Nuitka >= 2.0 (issues fixed in 1.4.2+); test thoroughly                 |
| psutil native extension problems   | Medium     | High   | Explicit `--include-package=psutil`; test on all platforms                  |
| Build time exceeds CI limits       | Medium     | Medium | Builds run in parallel; increase timeout if needed                          |
| Dynamic imports not detected       | Medium     | High   | Explicit `--include-module` for all conditional imports                     |
| winget PR rejection                | Low        | Medium | Follow manifest format precisely; respond to reviewer feedback              |
| Version shows 0.0.0-dev            | High       | Medium | Add `__version__` fallback before migration                                 |

