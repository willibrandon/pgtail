# Feature Specification: pgtail Distribution

**Feature Branch**: `019-distribution`
**Created**: 2026-01-01
**Status**: Draft
**Input**: User description: "Cross-platform installation methods without PyPI dependency"

## Clarifications

### Session 2026-01-01

- Q: Should Linux ARM64 binary be included? → A: Yes, include Linux ARM64 binary in initial release
- Q: How do you want to create releases? → A: Git command in terminal (tag push triggers workflow)
- Q: Homebrew/winget formula updates? → A: Automatic (workflow updates formula/manifest and opens PRs)
- Q: Initial version number? → A: v0.1.0
- Q: Release notes? → A: Auto-generate from commits
- Q: Should pgtail check for updates? → A: Both startup notification and explicit --check-update command; detect install method and show appropriate upgrade command

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Python User Installs via pip/pipx/uv from GitHub (Priority: P1)

A developer with Python 3.10+ wants to install pgtail quickly using their preferred Python package manager. They run a single command to install directly from the GitHub repository without waiting for PyPI publication.

**Why this priority**: Python developers are the primary audience. pip/pipx/uv are the most common installation methods and require no additional infrastructure beyond the existing repository.

**Independent Test**: Can be fully tested by running `pip install git+https://github.com/willibrandon/pgtail.git` on a fresh Python environment and verifying `pgtail --version` works.

**Acceptance Scenarios**:

1. **Given** a system with Python 3.10+ and pip installed, **When** the user runs `pip install git+https://github.com/willibrandon/pgtail.git`, **Then** pgtail is installed and the `pgtail` command is available in PATH
2. **Given** a system with pipx installed, **When** the user runs `pipx install git+https://github.com/willibrandon/pgtail.git`, **Then** pgtail is installed in an isolated environment and available globally
3. **Given** a system with uv installed, **When** the user runs `uv pip install git+https://github.com/willibrandon/pgtail.git`, **Then** pgtail is installed
4. **Given** a specific version tag exists (e.g., v0.1.0), **When** the user runs `pip install git+https://github.com/willibrandon/pgtail.git@v0.1.0`, **Then** that specific version is installed
5. **Given** pgtail is installed via pipx, **When** the user runs `pipx upgrade pgtail`, **Then** pgtail is updated to the latest version from GitHub
6. **Given** uv is installed, **When** the user runs `uvx --from git+https://github.com/willibrandon/pgtail.git pgtail`, **Then** pgtail runs directly without permanent installation

---

### User Story 2 - User Downloads Pre-built Binary (Priority: P2)

A user without Python installed wants to use pgtail. They download a pre-built standalone executable for their platform from GitHub Releases and run it immediately.

**Why this priority**: Binary downloads enable adoption by non-Python users and are the foundation for package manager integrations (Homebrew, winget).

**Independent Test**: Can be fully tested by downloading the binary for the current platform, making it executable, and running `./pgtail --version`.

**Acceptance Scenarios**:

1. **Given** a GitHub Release exists, **When** a macOS Apple Silicon user downloads `pgtail-macos-arm64`, **Then** the binary runs natively on M1/M2/M3 Macs
2. **Given** a GitHub Release exists, **When** a macOS Intel user downloads `pgtail-macos-x86_64`, **Then** the binary runs on Intel Macs
3. **Given** a GitHub Release exists, **When** a Linux x86_64 user downloads `pgtail-linux-x86_64`, **Then** the binary runs on standard Linux distributions
4. **Given** a GitHub Release exists, **When** a Linux ARM64 user downloads `pgtail-linux-arm64`, **Then** the binary runs on ARM64 Linux systems (Raspberry Pi 4/5, AWS Graviton, Oracle Ampere)
5. **Given** a GitHub Release exists, **When** a Windows user downloads `pgtail-windows-x86_64.exe`, **Then** the executable runs on Windows 10/11
6. **Given** a new release tag is pushed, **When** GitHub Actions runs, **Then** binaries for all five platforms are automatically built and attached to the release
7. **Given** a binary is downloaded, **When** the user runs it without any Python installation, **Then** it executes successfully with all features working

---

### User Story 3 - macOS/Linux User Installs via Homebrew (Priority: P3)

A macOS or Linux user prefers to manage software through Homebrew. They run `brew install willibrandon/tap/pgtail` to install pgtail with automatic updates.

**Why this priority**: Homebrew is the dominant package manager on macOS. Integration requires the Homebrew tap repository and formula, which builds on the binary releases.

**Independent Test**: Can be fully tested by running `brew install willibrandon/tap/pgtail` on a Mac and verifying the command works.

**Acceptance Scenarios**:

1. **Given** the homebrew-tap repository exists with a valid formula, **When** a macOS user runs `brew install willibrandon/tap/pgtail`, **Then** pgtail is installed and available as `pgtail` command
2. **Given** pgtail is installed via Homebrew, **When** the user runs `brew upgrade pgtail`, **Then** the latest version is installed
3. **Given** a new release is published, **When** the Homebrew formula is updated, **Then** users receive the update via `brew upgrade`
4. **Given** a Linux user with Homebrew (Linuxbrew), **When** they run `brew install willibrandon/tap/pgtail`, **Then** pgtail is installed for Linux
5. **Given** the formula exists, **When** a user runs `brew info willibrandon/tap/pgtail`, **Then** they see version, description, and homepage information

---

### User Story 4 - Windows User Installs via winget (Priority: P4)

A Windows user prefers to install software through winget (Windows Package Manager). They run `winget install willibrandon.pgtail` for a streamlined installation experience.

**Why this priority**: winget is Microsoft's official package manager for Windows. Integration requires submitting a manifest to the winget-pkgs repository.

**Independent Test**: Can be fully tested by running `winget install willibrandon.pgtail` on Windows 10/11 and verifying the command works.

**Acceptance Scenarios**:

1. **Given** the winget manifest is accepted in microsoft/winget-pkgs, **When** a Windows user runs `winget install willibrandon.pgtail`, **Then** pgtail is installed
2. **Given** pgtail is installed via winget, **When** the user runs `winget upgrade willibrandon.pgtail`, **Then** the latest version is installed
3. **Given** the manifest exists, **When** a user runs `winget show willibrandon.pgtail`, **Then** they see package information
4. **Given** a new release is published, **When** the winget manifest is updated, **Then** users can upgrade to the new version

---

### User Story 5 - User Checks for Updates (Priority: P5)

A pgtail user wants to know if a newer version is available. They receive automatic notifications on startup and can explicitly check on demand. The upgrade command shown matches how they installed pgtail.

**Why this priority**: Keeps users informed of updates across all installation methods without manual GitHub checking.

**Independent Test**: Can be fully tested by running an older version and verifying the correct upgrade command is shown for the installation method.

**Acceptance Scenarios**:

1. **Given** a newer version exists and 24+ hours since last check, **When** pgtail starts, **Then** a one-line notification shows the new version and correct upgrade command for the install method
2. **Given** pgtail was installed via pip, **When** an update notification appears, **Then** it shows `pip install --upgrade git+https://github.com/willibrandon/pgtail.git`
3. **Given** pgtail was installed via pipx, **When** an update notification appears, **Then** it shows `pipx upgrade pgtail`
4. **Given** pgtail was installed via Homebrew, **When** an update notification appears, **Then** it shows `brew upgrade pgtail`
5. **Given** pgtail was installed via winget, **When** an update notification appears, **Then** it shows `winget upgrade willibrandon.pgtail`
6. **Given** pgtail was installed as a binary, **When** an update notification appears, **Then** it shows the GitHub Releases download URL
7. **Given** any install method, **When** user runs `pgtail --check-update`, **Then** current and latest versions are displayed with the correct upgrade command
8. **Given** pgtail is offline or GitHub API unavailable, **When** an update check occurs, **Then** pgtail continues normally without error

---

### Edge Cases

- What happens when a user tries to install on Python < 3.10?
  - pip/pipx/uv MUST fail with a clear error message indicating Python 3.10+ is required
- What happens when a binary is run on an incompatible architecture?
  - The OS provides an appropriate error (e.g., "cannot execute binary file")
- What happens when the GitHub repository is private or inaccessible?
  - pip/pipx/uv fail with authentication error; binary downloads return 404
- What happens when Homebrew tap doesn't exist yet?
  - `brew install` fails with "tap not found" error
- What happens when winget manifest is not yet approved?
  - `winget install` fails with "package not found" error
- What happens when downloading a binary over slow/interrupted connection?
  - curl/wget resumes or retries appropriately (standard behavior)
- What happens when the user runs an outdated binary?
  - Binary continues to work; no automatic updates (user must re-download)
- What happens when PyInstaller fails to build for a platform?
  - GitHub Actions workflow fails; release is blocked until fixed
- What happens when code signing is required (macOS Gatekeeper)?
  - Unsigned binaries require user to allow in System Preferences; README documents this workaround
- What happens when Windows SmartScreen blocks the executable?
  - User must click "More info" then "Run anyway"; README documents this workaround
- What happens when update check runs while offline?
  - Check fails silently; pgtail continues normal operation
- What happens when GitHub API rate limit is exceeded?
  - Check fails silently; pgtail continues normal operation
- What happens when user has disabled update checks?
  - Startup check skipped; `--check-update` still works explicitly
- What happens when install method cannot be detected?
  - Falls back to showing GitHub Releases URL
- What happens when running a development/unreleased version?
  - Compares against latest release; notifies if release is newer

## Requirements *(mandatory)*

### Functional Requirements

**Python Package Installation (pip/pipx/uv)**

- **FR-001**: Repository MUST include a valid `pyproject.toml` with proper entry points for the `pgtail` command
- **FR-002**: Repository MUST be installable via `pip install git+https://github.com/willibrandon/pgtail.git`
- **FR-003**: Repository MUST be installable via `pipx install git+https://github.com/willibrandon/pgtail.git`
- **FR-004**: Repository MUST be installable via `uv pip install git+https://github.com/willibrandon/pgtail.git`
- **FR-005**: Repository MUST support version pinning via git tags (e.g., `@v0.1.0`)
- **FR-006**: The `pgtail` command MUST be available in PATH after installation
- **FR-007**: Installation MUST fail gracefully with clear error on Python < 3.10

**Binary Releases**

- **FR-008**: GitHub Actions workflow MUST trigger on version tag push (e.g., `git tag v0.1.0 && git push --tags`) and automatically create a GitHub Release with attached binaries and auto-generated release notes from commits since the previous tag
- **FR-009**: Binaries MUST be built for macOS Apple Silicon (arm64)
- **FR-010**: Binaries MUST be built for macOS Intel (x86_64)
- **FR-011**: Binaries MUST be built for Linux x86_64
- **FR-011a**: Binaries MUST be built for Linux ARM64
- **FR-012**: Binaries MUST be built for Windows x86_64
- **FR-013**: Binaries MUST be attached to the GitHub Release automatically
- **FR-014**: Binaries MUST work without Python installed on the target system
- **FR-015**: Binaries MUST include all dependencies bundled via PyInstaller
- **FR-016**: Binary naming MUST follow the pattern: `pgtail-{os}-{arch}[.exe]`

**Homebrew Integration**

- **FR-017**: A `willibrandon/homebrew-tap` repository MUST be created
- **FR-018**: The tap MUST contain a formula for pgtail
- **FR-019**: The formula MUST download the appropriate binary for the user's platform
- **FR-020**: The formula MUST include proper metadata (version, description, homepage, license)
- **FR-021**: The formula MUST support both macOS architectures (arm64, x86_64)
- **FR-022**: The formula MUST support Linux x86_64 and Linux ARM64 via Linuxbrew
- **FR-022a**: Release workflow MUST automatically update the Homebrew formula with new version and SHA256 checksums

**winget Integration**

- **FR-023**: A winget manifest MUST be created following microsoft/winget-pkgs format
- **FR-024**: The manifest MUST point to the Windows binary in GitHub Releases
- **FR-025**: The manifest MUST include proper metadata (version, description, publisher, license)
- **FR-026**: Release workflow MUST automatically generate updated winget manifest and open a PR to microsoft/winget-pkgs

**Documentation**

- **FR-027**: README MUST document all installation methods with copy-pasteable commands
- **FR-028**: README MUST include a summary table of methods, platforms, and Python requirements
- **FR-029**: README MUST document version installation syntax for pip/pipx/uv
- **FR-030**: README MUST document upgrade commands for each method
- **FR-031**: README MUST document macOS Gatekeeper and Windows SmartScreen workarounds for unsigned binaries

**Version Management**

- **FR-032**: Repository MUST use semantic versioning for release tags (vMAJOR.MINOR.PATCH), starting with v0.1.0
- **FR-033**: Version MUST be defined in a single source (pyproject.toml) and readable at runtime
- **FR-034**: `pgtail --version` MUST display the installed version

**Update Checking**

- **FR-035**: pgtail MUST check for updates on startup by querying GitHub Releases API
- **FR-036**: Startup update check MUST be rate-limited (at most once per 24 hours) to avoid API spam
- **FR-037**: If a newer version exists, pgtail MUST display a one-line notification with the new version and upgrade command
- **FR-038**: Update notification MUST NOT block or delay normal operation
- **FR-039**: `pgtail --check-update` MUST explicitly check for updates (bypassing rate limit) and display current vs latest version
- **FR-040**: Update check MUST fail gracefully (silent) if offline or GitHub API unavailable
- **FR-041**: Update check MUST respect NO_COLOR for notification styling
- **FR-042**: User MUST be able to disable startup update checks via config (`updates.check = false`)
- **FR-043**: pgtail MUST detect its installation method (pip, pipx, uv, Homebrew, winget, binary) and show the correct upgrade command
- **FR-044**: If installation method cannot be detected, pgtail MUST fall back to showing the GitHub Releases URL

### Key Entities

- **Release**: A versioned snapshot (tag) of the codebase with associated binaries
- **Binary Artifact**: Platform-specific standalone executable built by PyInstaller
- **Homebrew Formula**: Ruby file defining how to install pgtail via Homebrew
- **winget Manifest**: YAML files defining the package for Windows Package Manager
- **Tap Repository**: Git repository (willibrandon/homebrew-tap) hosting Homebrew formulae

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can install pgtail via pip/pipx/uv from GitHub in under 60 seconds on a typical internet connection
- **SC-002**: Users can download and run pre-built binaries without Python in under 30 seconds
- **SC-003**: Homebrew users can install pgtail with a single `brew install` command
- **SC-004**: Windows users can install pgtail with a single `winget install` command
- **SC-005**: All five binary platforms (macOS arm64, macOS x86_64, Linux x86_64, Linux arm64, Windows x86_64) are built and released automatically on each tagged release
- **SC-006**: Binary size is under 50MB per platform (reasonable for a Python CLI tool bundled with PyInstaller)
- **SC-007**: 100% of documented installation methods work as described in README
- **SC-008**: Release workflow completes successfully within 15 minutes
- **SC-009**: Users can verify their installed version via `pgtail --version`
- **SC-010**: Upgrade path is documented and functional for all installation methods
- **SC-011**: Users are notified of available updates within 24 hours of running pgtail after a new release
- **SC-012**: Update check adds less than 500ms to startup (non-blocking)
- **SC-013**: `pgtail --check-update` completes in under 2 seconds on typical connection
- **SC-014**: Correct upgrade command is shown for each installation method (pip, pipx, Homebrew, winget, binary)

## Assumptions

- The GitHub repository is public and accessible to all users
- Users have internet access to download from GitHub
- PyInstaller can successfully bundle pgtail and all its dependencies for all target platforms
- GitHub Actions has runners available for all target platforms (macOS, Linux, Windows)
- The `willibrandon` namespace is available on GitHub for the homebrew-tap repository
- winget manifest submission to microsoft/winget-pkgs will be accepted (subject to their review process)
- Users accept unsigned binaries (no code signing certificate for initial release)
- The existing `pyproject.toml` structure is compatible with GitHub-based installation
