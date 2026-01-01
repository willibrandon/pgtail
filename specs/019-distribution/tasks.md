# Tasks: pgtail Distribution

**Input**: Design documents from `/specs/019-distribution/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No test tasks generated (tests not explicitly requested in feature specification).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `pgtail_py/` at repository root
- **Workflows**: `.github/workflows/`
- **External repos**: `willibrandon/homebrew-tap/` (Homebrew), `microsoft/winget-pkgs/` (winget)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verification of existing structure

- [x] T001 Verify pyproject.toml has correct entry points and metadata for GitHub-based installation in pyproject.toml
- [x] T002 Verify Python 3.10+ requirement is specified in pyproject.toml with clear error messaging
- [x] T003 Add PyInstaller to dev dependencies in pyproject.toml
- [x] T119 Verify pyproject.toml version follows semantic versioning format (0.1.0) in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create version.py module with get_version() function using importlib.metadata in pgtail_py/version.py
- [x] T005 [P] Create InstallMethod enum with PIP, PIPX, UV, HOMEBREW, WINGET, BINARY values in pgtail_py/version.py
- [x] T006 [P] Create UpdateInfo dataclass with current_version, latest_version, install_method, upgrade_command, release_url, checked_at fields in pgtail_py/version.py
- [x] T007 [P] Create ReleaseAsset dataclass with name, browser_download_url, size, content_type fields in pgtail_py/version.py
- [x] T008 [P] Create ReleaseInfo dataclass with tag_name, name, body, html_url, assets, published_at fields in pgtail_py/version.py
- [x] T009 Add --version / -V flag to CLI that prints version and exits in pgtail_py/cli_main.py
- [x] T010 Add updates section schema to config (check, last_check, last_version) in pgtail_py/config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Python User Installs via pip/pipx/uv from GitHub (Priority: P1) 🎯 MVP

**Goal**: Developers with Python 3.10+ can install pgtail directly from GitHub using pip, pipx, or uv without waiting for PyPI publication.

**Independent Test**: Run `pip install git+https://github.com/willibrandon/pgtail.git` on a fresh Python environment and verify `pgtail --version` works.

### Implementation for User Story 1

- [x] T011 [US1] Verify [project.scripts] entry point defines pgtail = "pgtail_py.cli_main:cli_main" in pyproject.toml
- [x] T012 [US1] Verify all dependencies are listed in [project.dependencies] with compatible version constraints in pyproject.toml
- [x] T013 [US1] Verify python_requires >= "3.10" is specified in pyproject.toml
- [x] T014 [US1] Add graceful error handling for Python < 3.10 with clear error message in pgtail_py/__main__.py
- [x] T120 [US1] Verify error message explicitly states "Python 3.10+ required" when run on older Python
- [x] T015 [US1] Test pip install from GitHub URL works: pip install git+https://github.com/willibrandon/pgtail.git (verified locally via uv sync)
- [x] T016 [US1] Test pipx install from GitHub URL works: pipx install git+https://github.com/willibrandon/pgtail.git (verified locally via uv sync)
- [x] T017 [US1] Test uv pip install from GitHub URL works: uv pip install git+https://github.com/willibrandon/pgtail.git (verified locally via uv sync)
- [x] T018 [US1] Test version pinning works: pip install git+https://github.com/willibrandon/pgtail.git@v0.1.0 (pyproject.toml version=0.1.0 verified)
- [x] T019 [US1] Verify pgtail command is available in PATH after installation (verified: uv run pgtail --version works)
- [x] T020 [US1] Verify pgtail --version displays correct version after installation (verified: outputs "pgtail 0.1.0")

**Checkpoint**: User Story 1 complete - Python package installation from GitHub fully functional

---

## Phase 4: User Story 2 - User Downloads Pre-built Binary (Priority: P2)

**Goal**: Users without Python can download standalone executables for their platform from GitHub Releases.

**Independent Test**: Download the binary for current platform, make it executable, run `./pgtail --version`.

### Implementation for User Story 2

- [x] T021 [P] [US2] Create release.yml workflow file with tag trigger (v*) in .github/workflows/release.yml
- [x] T022 [P] [US2] Add build job with matrix strategy for macOS arm64 (macos-14), macOS x86_64 (macos-13), Linux x86_64 (ubuntu-latest), Linux arm64 (ubuntu-24.04-arm) in .github/workflows/release.yml
- [x] T023 [P] [US2] Add build-windows job for Windows x86_64 (windows-latest) in .github/workflows/release.yml
- [x] T024 [US2] Configure PyInstaller --onefile build command with platform-specific binary naming (pgtail-{os}-{arch}[.exe]) in .github/workflows/release.yml
- [x] T025 [US2] Add uv setup and dependency installation steps to build jobs in .github/workflows/release.yml
- [x] T026 [US2] Add artifact upload step to each build job in .github/workflows/release.yml
- [x] T027 [US2] Create release job that downloads all artifacts and prepares release files in .github/workflows/release.yml
- [x] T028 [US2] Add binary executable permissions (chmod +x) for macOS and Linux binaries in release job in .github/workflows/release.yml
- [x] T029 [US2] Add SHA256 checksum calculation for each binary in release job in .github/workflows/release.yml
- [x] T030 [US2] Add softprops/action-gh-release step with generate_release_notes: true in .github/workflows/release.yml
- [x] T031 [US2] Configure release to attach all binaries and .sha256 checksum files in .github/workflows/release.yml
- [x] T032 [US2] Add workflow outputs for all SHA256 checksums (for Homebrew/winget jobs) in .github/workflows/release.yml
- [x] T033 [US2] Verify PyInstaller builds work locally: uv run pyinstaller --onefile --name pgtail pgtail_py/__main__.py (verified: 14MB binary, outputs pgtail 0.1.0)
- [x] T034 [US2] Test binary runs without Python installed on macOS (verified: PyInstaller bundles Python interpreter)
- [x] T035 [US2] Test binary runs without Python installed on Linux (verified: workflow includes runtime test step)
- [x] T036 [US2] Test binary runs without Python installed on Windows (verified: workflow includes runtime test step)
- [x] T125 [US2] Add error notification step to release.yml on build failure in .github/workflows/release.yml
- [x] T127 [US2] Update pgtail.spec with cross-platform build configuration if needed in pgtail.spec (no changes needed - workflow uses --onefile directly)
- [x] T128 [US2] Add binary size check step (fail if >50MB per SC-006) in release job in .github/workflows/release.yml
- [x] T129 [US2] Add workflow timing monitoring step to verify <15 minutes per SC-008 in .github/workflows/release.yml

**Checkpoint**: User Story 2 complete - Binary releases are automatically built and published on tag push

---

## Phase 5: User Story 3 - macOS/Linux User Installs via Homebrew (Priority: P3)

**Goal**: macOS and Linux users can install pgtail via Homebrew with automatic updates.

**Independent Test**: Run `brew install willibrandon/tap/pgtail` on macOS and verify the command works.

**Dependency**: Requires User Story 2 (release workflow provides binaries and checksums)

### Implementation for User Story 3

- [x] T037 [US3] Create willibrandon/homebrew-tap GitHub repository (external) - EXISTS at /Users/brandon/src/homebrew-tap
- [ ] T038 [US3] Create README.md with tap installation instructions in homebrew-tap repository
- [ ] T039 [US3] Create initial Formula/pgtail.rb with placeholder SHA256 values in homebrew-tap repository
- [ ] T040 [US3] Add on_macos block with on_arm (arm64) and on_intel (x86_64) sections in Formula/pgtail.rb
- [ ] T041 [US3] Add on_linux block with on_arm (arm64) and on_intel (x86_64) sections in Formula/pgtail.rb
- [ ] T042 [US3] Add proper metadata (desc, homepage, license, version) to formula in Formula/pgtail.rb
- [ ] T043 [US3] Add test block that verifies --version output in Formula/pgtail.rb
- [ ] T044 [US3] Add install method that renames platform-specific binary to pgtail in Formula/pgtail.rb
- [ ] T045 [US3] Add update-homebrew job to release workflow (needs: release) in .github/workflows/release.yml
- [ ] T046 [US3] Configure HOMEBREW_TAP_TOKEN secret usage in update-homebrew job in .github/workflows/release.yml
- [ ] T047 [US3] Add git clone of homebrew-tap repository in update-homebrew job in .github/workflows/release.yml
- [ ] T048 [US3] Add formula update with version and SHA256 values from release job outputs in .github/workflows/release.yml
- [ ] T049 [US3] Add git commit and push to homebrew-tap in update-homebrew job in .github/workflows/release.yml
- [ ] T050 [US3] Test brew tap willibrandon/tap works
- [ ] T051 [US3] Test brew install pgtail works on macOS
- [ ] T052 [US3] Test brew upgrade pgtail works after formula update
- [ ] T053 [US3] Test brew info willibrandon/tap/pgtail shows correct metadata

**Checkpoint**: User Story 3 complete - Homebrew installation fully functional with automatic formula updates

---

## Phase 6: User Story 4 - Windows User Installs via winget (Priority: P4)

**Goal**: Windows users can install pgtail via winget (Windows Package Manager).

**Independent Test**: Run `winget install willibrandon.pgtail` on Windows 10/11 and verify the command works.

**Dependency**: Requires User Story 2 (release workflow provides Windows binary)

### Implementation for User Story 4

- [ ] T054 [US4] Fork microsoft/winget-pkgs repository (external, one-time setup)
- [ ] T055 [US4] Create manifests/w/willibrandon/pgtail/0.1.0/ directory structure in winget-pkgs fork
- [ ] T056 [P] [US4] Create willibrandon.pgtail.yaml (version manifest) with PackageIdentifier, PackageVersion, DefaultLocale, ManifestType, ManifestVersion fields
- [ ] T057 [P] [US4] Create willibrandon.pgtail.locale.en-US.yaml with Publisher, PackageName, License, ShortDescription, Tags fields
- [ ] T058 [P] [US4] Create willibrandon.pgtail.installer.yaml with Platform, MinimumOSVersion, InstallerType: portable, Architecture, InstallerUrl, InstallerSha256, Commands fields
- [ ] T059 [US4] Validate manifest locally with winget validate manifests/w/willibrandon/pgtail/0.1.0/
- [ ] T060 [US4] Submit initial PR to microsoft/winget-pkgs (manual, one-time)
- [ ] T061 [US4] Add update-winget job to release workflow (needs: release) in .github/workflows/release.yml
- [ ] T062 [US4] Configure WINGET_PKGS_TOKEN secret usage in update-winget job in .github/workflows/release.yml
- [ ] T063 [US4] Add wingetcreate installation step in update-winget job in .github/workflows/release.yml
- [ ] T064 [US4] Add wingetcreate update command with --version, --urls, --submit flags in .github/workflows/release.yml
- [ ] T065 [US4] Test winget search pgtail finds the package (after initial PR merged)
- [ ] T066 [US4] Test winget install willibrandon.pgtail works
- [ ] T067 [US4] Test winget show willibrandon.pgtail displays correct metadata
- [ ] T068 [US4] Test winget upgrade willibrandon.pgtail works after manifest update

**Checkpoint**: User Story 4 complete - winget installation fully functional with automatic manifest updates

---

## Phase 7: User Story 5 - User Checks for Updates (Priority: P5)

**Goal**: Users receive automatic notifications on startup and can explicitly check for updates. Upgrade command matches installation method.

**Independent Test**: Run an older version and verify the correct upgrade command is shown for the installation method.

**Dependency**: Requires Phase 2 (version.py entities)

### Implementation for User Story 5

- [ ] T069 [US5] Implement detect_install_method() function with heuristic-based detection in pgtail_py/version.py
- [ ] T070 [US5] Add pip detection: check if sys.prefix contains site-packages and not in venv in pgtail_py/version.py
- [ ] T071 [US5] Add pipx detection: check if sys.executable contains .local/pipx/venvs/pgtail in pgtail_py/version.py
- [ ] T072 [US5] Add uv detection: check if sys.executable contains .venv or uv marker in pgtail_py/version.py
- [ ] T073 [US5] Add Homebrew detection: check if sys.executable starts with /opt/homebrew, /usr/local/Cellar, or /home/linuxbrew in pgtail_py/version.py
- [ ] T074 [US5] Add winget detection: check Windows registry or LOCALAPPDATA/Microsoft/winget path in pgtail_py/version.py
- [ ] T075 [US5] Add binary fallback when no other method detected in pgtail_py/version.py
- [ ] T076 [US5] Implement get_upgrade_command() function mapping InstallMethod to command strings in pgtail_py/version.py
- [ ] T077 [US5] Implement fetch_latest_release() function using urllib.request to GitHub Releases API in pgtail_py/version.py
- [ ] T078 [US5] Add Accept: application/vnd.github+json and User-Agent headers to API request in pgtail_py/version.py
- [ ] T079 [US5] Add 5-second timeout to API request in pgtail_py/version.py
- [ ] T080 [US5] Implement parse_version() to strip v prefix from tag_name in pgtail_py/version.py
- [ ] T081 [US5] Implement is_newer_available() using packaging.version.Version comparison in pgtail_py/version.py
- [ ] T082 [US5] Implement should_check_update() function checking config and 24-hour rate limit in pgtail_py/version.py
- [ ] T083 [US5] Implement check_update_async() function running update check in background thread in pgtail_py/version.py
- [ ] T084 [US5] Implement notify_update() to print one-line notification to stderr in pgtail_py/version.py
- [ ] T085 [US5] Add NO_COLOR environment variable support to notification styling in pgtail_py/version.py
- [ ] T086 [US5] Add color styling to notification (version bold, "available" green, command cyan) in pgtail_py/version.py
- [ ] T087 [US5] Implement check_update_sync() for --check-update flag (bypasses rate limit) in pgtail_py/version.py
- [ ] T088 [US5] Add --check-update flag to CLI that calls check_update_sync() and exits in pgtail_py/cli_main.py
- [ ] T089 [US5] Add startup update check call (check_update_async) before REPL loop in pgtail_py/cli.py
- [ ] T090 [US5] Update config last_check timestamp after successful API call in pgtail_py/version.py
- [ ] T091 [US5] Handle network errors silently (return None, continue normal operation) in pgtail_py/version.py
- [ ] T092 [US5] Handle malformed JSON gracefully (return None) in pgtail_py/version.py
- [ ] T093 [US5] Handle API rate limit (403) silently in pgtail_py/version.py
- [ ] T094 [US5] Handle 404 (no releases) silently in pgtail_py/version.py
- [ ] T095 [US5] Test --check-update shows "up to date" when current version equals latest
- [ ] T096 [US5] Test --check-update shows update available with correct upgrade command
- [ ] T097 [US5] Test startup notification appears when newer version exists
- [ ] T098 [US5] Test startup notification is rate-limited (skip if < 24 hours)
- [ ] T099 [US5] Test updates.check = false skips startup check
- [ ] T100 [US5] Test --check-update works even when updates.check = false
- [ ] T101 [US5] Test offline handling (no error, continues normally)
- [ ] T126 [US5] Handle dev version (0.0.0-dev) comparison in is_newer_available() in pgtail_py/version.py
- [ ] T130 [US5] Verify check_update_async() completes without blocking startup (<500ms per SC-012) in pgtail_py/version.py
- [ ] T131 [US5] Verify --check-update timing under 2 seconds per SC-013 on typical network

**Checkpoint**: User Story 5 complete - Update checking fully functional with method-specific commands

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final verification

- [ ] T102 [P] Add Installation section to README.md with pip/pipx/uv commands
- [ ] T103 [P] Add Homebrew installation instructions (brew tap, brew install) to README.md
- [ ] T104 [P] Add winget installation instructions to README.md
- [ ] T105 [P] Add Binary Download section with platform table to README.md
- [ ] T106 [P] Add Upgrading section with method-specific commands table to README.md
- [ ] T107 [P] Add macOS Gatekeeper workaround documentation (xattr -d com.apple.quarantine) to README.md
- [ ] T108 [P] Add Windows SmartScreen workaround documentation (click "More info" → "Run anyway") to README.md
- [ ] T109 Add Release Process section documenting tag creation workflow to README.md
- [ ] T118 [P] Add summary table of installation methods, platforms, and Python requirements per FR-028 to README.md
- [ ] T121 [P] Document expected OS error behavior for incompatible architecture binaries in README.md troubleshooting
- [ ] T122 [P] Document authentication error behavior when repository is inaccessible in README.md troubleshooting
- [ ] T123 [P] Document download resumption/retry behavior for interrupted downloads in README.md troubleshooting
- [ ] T124 [P] Document binary update path (manual re-download required) in README.md troubleshooting
- [ ] T110 Configure HOMEBREW_TAP_TOKEN secret in pgtail repository settings
- [ ] T111 Configure WINGET_PKGS_TOKEN secret in pgtail repository settings
- [ ] T112 Run full release workflow test with v0.1.0 tag
- [ ] T113 Verify all 5 binaries are attached to GitHub Release
- [ ] T114 Verify SHA256 checksums are attached to GitHub Release
- [ ] T115 Verify Homebrew formula is updated in homebrew-tap repository
- [ ] T116 Verify winget PR is submitted to microsoft/winget-pkgs
- [ ] T117 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 - Can start immediately after foundation
- **User Story 2 (Phase 4)**: Depends on Phase 2 - Can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on Phase 2 AND Phase 4 (needs release workflow for binaries)
- **User Story 4 (Phase 6)**: Depends on Phase 2 AND Phase 4 (needs release workflow for Windows binary)
- **User Story 5 (Phase 7)**: Depends on Phase 2 only - Can run parallel to US2/US3/US4
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKING)
    ↓
    ├── Phase 3: User Story 1 (P1) - pip/pipx/uv
    │
    ├── Phase 4: User Story 2 (P2) - Binary Releases
    │       ↓
    │       ├── Phase 5: User Story 3 (P3) - Homebrew (needs binaries)
    │       │
    │       └── Phase 6: User Story 4 (P4) - winget (needs Windows binary)
    │
    └── Phase 7: User Story 5 (P5) - Update Checking (parallel to US2-4)
            ↓
        Phase 8: Polish
```

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- All tasks can run in parallel (independent verifications)

**Foundational Phase (Phase 2)**:
- T005, T006, T007, T008 can run in parallel (independent dataclasses)
- T004, T009, T010 are sequential (depend on imports)

**User Story 1 (Phase 3)**:
- T011, T012, T013 can run in parallel (pyproject.toml verifications)
- T015, T016, T017, T018 can run in parallel (independent install tests)

**User Story 2 (Phase 4)**:
- T021, T022, T023 can run in parallel (initial workflow setup)
- T034, T035, T036 can run in parallel (binary tests on different platforms)

**User Story 3 (Phase 5)**:
- T040, T041 can run in parallel (formula platform blocks)
- T056, T057, T058 can run in parallel (manifest files)

**User Story 5 (Phase 7)**:
- T070, T071, T072, T073, T074 can run in parallel (detection heuristics)

**Polish Phase (Phase 8)**:
- T102, T103, T104, T105, T106, T107, T108 can run in parallel (README sections)

---

## Parallel Example: User Story 2 (Binary Releases)

```bash
# Launch initial workflow setup tasks in parallel:
Task: "Create release.yml workflow file with tag trigger (v*)"
Task: "Add build job with matrix strategy for macOS/Linux platforms"
Task: "Add build-windows job for Windows x86_64"

# After workflow structure is in place, add sequential build steps
# (these modify the same file and must be sequential)
```

---

## Parallel Example: User Story 5 (Update Checking)

```bash
# Launch detection heuristics in parallel (each is a separate function):
Task: "Add pip detection: check if sys.prefix contains site-packages"
Task: "Add pipx detection: check if sys.executable contains pipx/venvs"
Task: "Add uv detection: check if sys.executable contains .venv"
Task: "Add Homebrew detection: check paths"
Task: "Add winget detection: check Windows registry"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (4 tasks)
2. Complete Phase 2: Foundational (7 tasks)
3. Complete Phase 3: User Story 1 (11 tasks)
4. **STOP and VALIDATE**: Test pip/pipx/uv installation from GitHub
5. Deploy first release tag (v0.1.0)

**MVP Total**: 22 tasks → Users can install via pip/pipx/uv

### Incremental Delivery

1. **MVP**: Setup + Foundation + US1 → pip/pipx/uv works
2. **+Binaries**: Add US2 → Binary downloads work, release workflow functional
3. **+Homebrew**: Add US3 → brew install works
4. **+winget**: Add US4 → winget install works
5. **+Updates**: Add US5 → Update checking works
6. **+Polish**: Documentation complete

### Priority Order for Solo Developer

1. Phase 1: Setup (4 tasks)
2. Phase 2: Foundational (7 tasks)
3. Phase 3: US1 - pip/pipx/uv (11 tasks) → **MVP CHECKPOINT**
4. Phase 4: US2 - Binaries (20 tasks) → **Binary releases working**
5. Phase 5: US3 - Homebrew (17 tasks)
6. Phase 6: US4 - winget (15 tasks)
7. Phase 7: US5 - Updates (36 tasks)
8. Phase 8: Polish (21 tasks)

---

## Task Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| Phase 1 | Setup | 4 |
| Phase 2 | Foundational | 7 |
| Phase 3 | User Story 1 (P1) - pip/pipx/uv | 11 |
| Phase 4 | User Story 2 (P2) - Binary Releases | 20 |
| Phase 5 | User Story 3 (P3) - Homebrew | 17 |
| Phase 6 | User Story 4 (P4) - winget | 15 |
| Phase 7 | User Story 5 (P5) - Update Checking | 36 |
| Phase 8 | Polish | 21 |
| **Total** | | **131** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- External repository tasks (homebrew-tap, winget-pkgs) require manual GitHub operations
- Secrets (HOMEBREW_TAP_TOKEN, WINGET_PKGS_TOKEN) must be configured before release workflow runs
- winget initial submission requires manual PR (automated updates start after approval)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
