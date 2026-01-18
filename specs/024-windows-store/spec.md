# Feature Specification: Windows Store Distribution

**Feature Branch**: `024-windows-store`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "Windows Store Distribution - Add MSIX package build and Microsoft Store submission automation to provide free code signing, automatic updates, and eliminate SmartScreen warnings for Windows users"

## Clarifications

### Session 2026-01-18

- Q: How should maintainer be notified when Store submission fails certification? → A: Rely on Partner Center's built-in email notifications (no additional notification mechanism required)
- Q: What should the maximum retry behavior be for network timeouts during upload? → A: 3 retries with exponential backoff (30s, 60s, 120s delays)
- Q: Should ARM64 architecture be supported in addition to x64? → A: Yes, include ARM64 in scope (build both x64 and ARM64 MSIX packages)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Windows User Installs pgtail from Microsoft Store (Priority: P1)

A Windows user discovers pgtail and wants to install it with confidence. Currently, unsigned executables trigger SmartScreen warnings ("Windows protected your PC") that alarm users and block enterprise deployments. By distributing through the Microsoft Store, users can install pgtail without security warnings because Microsoft signs the package with their trusted certificate.

**Why this priority**: This is the primary user-facing benefit. SmartScreen warnings are the main friction point preventing adoption on Windows. Microsoft Store distribution eliminates this barrier entirely.

**Independent Test**: Can be fully tested by installing pgtail from Microsoft Store and verifying the `pgtail` command works in any terminal (PowerShell, Command Prompt, Windows Terminal).

**Acceptance Scenarios**:

1. **Given** a Windows 10/11 user opens Microsoft Store, **When** they search for "pgtail" and click Install, **Then** the app installs without SmartScreen warnings and shows "Verified publisher"
2. **Given** pgtail is installed from Store, **When** user opens any terminal and types `pgtail`, **Then** the command executes correctly via AppExecutionAlias
3. **Given** pgtail is installed from Store, **When** user wants to uninstall, **Then** they can remove it through Settings → Apps like any modern Windows app

---

### User Story 2 - Automatic Updates for Store Users (Priority: P1)

Windows users who install pgtail from the Microsoft Store receive automatic updates when new versions are released. Users don't need to manually check for updates or download new installers.

**Why this priority**: Automatic updates ensure users always have the latest features and security fixes. This is a major benefit of Store distribution that differentiates it from manual installation methods.

**Independent Test**: Can be tested by releasing a new version and verifying Store users receive the update automatically within Microsoft's update cycle.

**Acceptance Scenarios**:

1. **Given** a new pgtail version is published to the Store, **When** the user's system checks for updates (automatic), **Then** pgtail updates silently in the background
2. **Given** pgtail is installed from Store, **When** user pauses Store updates, **Then** pgtail respects the user's preference (up to 5-week pause limit)
3. **Given** an update is available, **When** the update completes, **Then** the next `pgtail` command invocation uses the new version

---

### User Story 3 - Release Automation Publishes to Store (Priority: P2)

When a maintainer creates a new release tag (v*), the CI/CD pipeline automatically builds an MSIX package and submits it to the Microsoft Store for certification. This reduces manual effort and ensures consistent releases across all distribution channels.

**Why this priority**: Automation is essential for sustainable maintenance. Manual Store submissions would create friction and risk inconsistent releases between GitHub and Store.

**Independent Test**: Can be tested by pushing a version tag and verifying the Store submission workflow completes successfully (enters certification queue).

**Acceptance Scenarios**:

1. **Given** a maintainer pushes a `v*` tag to GitHub, **When** the release workflow runs, **Then** an MSIX package is built and uploaded as a release artifact
2. **Given** the MSIX is built, **When** the `update-store` workflow job runs, **Then** it authenticates with Partner Center API and creates a new submission
3. **Given** a submission is created, **When** the package is uploaded and committed, **Then** the submission enters Microsoft's certification queue
4. **Given** certification succeeds, **When** the update is approved, **Then** the new version becomes available in the Store

---

### User Story 4 - Maintainer Initial Store Setup (Priority: P3)

A maintainer performs one-time setup to enable Store distribution. This includes registering as a Microsoft developer (free via storedeveloper.microsoft.com), reserving the "pgtail" app name, creating Azure AD credentials for API access, and configuring GitHub secrets.

**Why this priority**: This is a prerequisite for automation but only needs to be done once. The complexity is front-loaded but the ongoing benefit is zero-maintenance releases.

**Independent Test**: Can be tested by completing registration, reserving the app name, and verifying Partner Center shows the reserved app.

**Acceptance Scenarios**:

1. **Given** maintainer visits storedeveloper.microsoft.com, **When** they complete identity verification, **Then** they have a free Microsoft developer account (no $19 fee in flighted markets)
2. **Given** maintainer has a developer account, **When** they reserve "pgtail", **Then** Partner Center provides Package Identity Name and Publisher CN values
3. **Given** Azure AD app is created, **When** it's linked to Partner Center with Developer role, **Then** GitHub Actions can authenticate via client credentials
4. **Given** GitHub secrets are configured, **When** a test submission is attempted, **Then** the API accepts the authentication and creates a submission

---

### Edge Cases

- **Store submission fails certification**: Workflow reports failure status; Partner Center sends email notification to registered developer; maintainer reviews certification report and addresses issues before resubmitting
- **Pending submission exists**: Workflow deletes any pending submission before creating new one to avoid conflicts
- **Azure AD credentials expire**: Client secret expires after configured period; maintainer must rotate secret and update GitHub secrets
- **Package Identity values mismatch**: MSIX build fails validation if manifest doesn't match Partner Center identity; workflow substitutes correct values from environment
- **Store name "pgtail" unavailable**: Maintainer chooses alternative name (e.g., "pgtail-postgresql") and updates all references
- **User has both Store and winget installations**: AppExecutionAlias and PATH entries may conflict; Store version takes precedence in WindowsApps PATH position
- **Network timeout during upload**: Workflow retries up to 3 times with exponential backoff (30s, 60s, 120s delays); fails workflow after final attempt with clear error message
- **Version format mismatch**: MSIX requires X.Y.Z.0 format; workflow automatically appends .0 to semantic version

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Build pipeline MUST produce an MSIX package containing the Nuitka-built pgtail executable and all dependencies
- **FR-002**: MSIX package MUST include AppxManifest.xml with AppExecutionAlias for `pgtail.exe` so users can invoke `pgtail` from any terminal
- **FR-003**: MSIX manifest MUST specify `desktop4:Subsystem="console"` to enable proper stdin/stdout handling for the CLI application
- **FR-004**: MSIX package MUST include required logo assets (44x44, 50x50, 150x150, 310x150 PNG files) derived from the existing pgtail.ico
- **FR-005**: MSIX version format MUST be X.Y.Z.0 (fourth segment reserved for Store) derived from the release tag version
- **FR-006**: MSIX package MUST be unsigned when built; Microsoft signs it during Store certification
- **FR-007**: Release workflow MUST upload MSIX package as a GitHub Release artifact alongside existing ZIP and MSI
- **FR-008**: Release workflow MUST include an `update-store` job that authenticates with Partner Center API using Azure AD client credentials
- **FR-009**: Store submission workflow MUST delete any pending submissions before creating a new one
- **FR-010**: Store submission workflow MUST upload the MSIX package in a ZIP container to Azure Blob Storage via the provided SAS URL
- **FR-011**: Store submission workflow MUST poll submission status until it leaves `CommitStarted` state
- **FR-012**: Store submission workflow MUST fail the workflow if submission status is not `PreProcessing` or `Certification` after commit
- **FR-013**: MSIX package MUST target Windows 10 version 1809 (build 17763) as minimum supported version
- **FR-014**: MSIX packages MUST be produced for both x64 and ARM64 processor architectures
- **FR-015**: MSIX package MUST declare `runFullTrust` capability for unrestricted file system and process access
- **FR-016**: Build pipeline MUST produce ARM64 Windows executable via Nuitka using windows-11-arm runner
- **FR-017**: Store submission MUST include both x64 and ARM64 packages in an MSIX bundle so Windows automatically installs the correct architecture

### Key Entities

- **MSIX Package**: Container format for Windows Store distribution; contains manifest, assets, and application files in a signed archive
- **AppxManifest.xml**: XML configuration declaring package identity, capabilities, visual elements, and entry points including AppExecutionAlias
- **Partner Center**: Microsoft's developer portal for managing Store apps, submissions, and analytics
- **Azure AD Application**: Service principal used by GitHub Actions to authenticate with Partner Center API for automated submissions
- **Store Submission**: A version of the app uploaded for certification; includes package files, listing metadata, and pricing information
- **AppExecutionAlias**: Windows mechanism that creates executable stubs in WindowsApps folder, enabling CLI tools to be invoked by name from any terminal

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can install pgtail from Microsoft Store without encountering SmartScreen warnings
- **SC-002**: Users can invoke `pgtail` command from any terminal (PowerShell, Command Prompt, Windows Terminal) after Store installation
- **SC-003**: Store users receive automatic updates when new versions are published, without manual intervention
- **SC-004**: Release workflow successfully builds and uploads MSIX package for every version tag
- **SC-005**: Store submission automation successfully creates submissions and enters certification queue without manual intervention
- **SC-006**: Total distribution cost remains $0 (free developer registration, no code signing certificate purchase required)
- **SC-007**: MSIX package size for each architecture is comparable to current Windows build output (target: under 35MB each for x64 and ARM64)
- **SC-008**: Store certification approval rate is 100% after initial setup (no recurring certification failures)

## Assumptions

- Maintainer can register at storedeveloper.microsoft.com to obtain free developer account (requires flighted market or potential fee in non-flighted regions)
- App name "pgtail" is available for reservation in Partner Center
- Partner Center API remains stable and continues to support automated submissions
- GitHub Actions windows-latest runners include Windows SDK with MakeAppx.exe
- GitHub Actions windows-11-arm runners are available for ARM64 Windows builds (public repos)
- Azure AD client credentials grant access to Partner Center API when properly configured
- Store certification process accepts CLI tools with runFullTrust capability
- Users have Microsoft Store enabled on their Windows installations (enterprise policies may block Store access)

## Dependencies

- Existing Nuitka build pipeline produces valid Windows x64 executable (to be extended for ARM64)
- Existing release.yml workflow structure supports adding new jobs
- pgtail.ico exists in art/ directory for asset generation
- GitHub repository has access to create secrets for Azure AD credentials
- Nuitka supports ARM64 Windows builds on windows-11-arm runner
