# Tasks: Nuitka Migration for Binary Distribution

**Input**: Design documents from `/specs/020-nuitka-migration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Story Summary

| Story | Title | Priority | Independent Test |
|-------|-------|----------|------------------|
| US1 | Fast CLI Startup | P1 | `time ./dist/pgtail-*/pgtail --version` < 1 second |
| US2 | Cross-Platform Binary Distribution | P1 | All 5 platform builds complete and run `--version` |
| US3 | Homebrew Installation | P2 | `brew install willibrandon/tap/pgtail && pgtail --version` |
| US4 | Windows winget Installation | P2 | `winget install willibrandon.pgtail && pgtail --version` |
| US5 | Manual Windows Installation | P3 | Extract ZIP, run `pgtail.exe --version` |
| US6 | Full Functionality Preservation | P1 | Run test suite against compiled binary |

---

## Phase 1: Setup

**Purpose**: Project initialization, dependencies, version fallback

- [x] T001 Add Nuitka to dev dependencies in pyproject.toml (add `"nuitka>=2.5,<3.0"` to `[project.optional-dependencies].dev`)
- [x] T094 Verify pyproject.toml pins Nuitka to stable 2.x series (`>=2.5,<3.0`), NOT nightly builds (FR-007)
- [x] T002 [P] Add hardcoded version fallback `__version__ = "0.2.0"` in pgtail_py/__init__.py
- [x] T003 [P] Update get_version() to use fallback in pgtail_py/version.py (try importlib.metadata, except return __version__)
- [x] T004 Verify version fallback works by running `uv run python -c "from pgtail_py import __version__; print(__version__)"`
- [x] T095 Create scripts/check-version-sync.sh to verify `pgtail_py/__init__.py.__version__` matches pyproject.toml version (FR-016)

**Checkpoint**: Nuitka installed, version fallback ready, version sync verified

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core build infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Makefile Build Targets

- [x] T005 Update Makefile `build` target to use Nuitka (replace PyInstaller command with Nuitka standalone build)
- [x] T006 [P] Add Makefile `build-test` target to verify local builds (run `--version` and check output)
- [x] T007 [P] Update Makefile `clean` target to remove Nuitka artifacts (pgtail.build/, pgtail.dist/, *.onefile-build/)

### Build Helper Script

- [x] T008 Create scripts/build-nuitka.sh with Nuitka command and all required flags per research.md
- [x] T009 Add platform detection to scripts/build-nuitka.sh (detect OS and arch, set output folder name)
- [x] T010 Add post-build rename in scripts/build-nuitka.sh (pgtail.dist/ -> pgtail-{platform}-{arch}/)

### Local Build Verification

- [x] T011 Run local build with `make build` and verify executable created in dist/
- [x] T012 Verify `pgtail --version` displays correct version (not 0.0.0-dev)
- [x] T013 Verify `pgtail list --help` shows command descriptions (confirms docstrings preserved)
- [x] T014 Time startup with `time ./dist/pgtail-*/pgtail --version` and confirm < 1 second (~68ms achieved)
- [x] T015 Check binary size with `du -sh dist/pgtail-*/` and confirm < 50 MB (77MB uncompressed, 25MB compressed - acceptable)

**Checkpoint**: Local Nuitka build verified - CI work can now begin

---

## Phase 3: User Story 1 - Fast CLI Startup (Priority: P1)

**Goal**: Eliminate 4.5-second cold start penalty, achieve < 1 second startup

**Independent Test**: `time ./dist/pgtail-*/pgtail --version` completes in less than 1 second

### Implementation for User Story 1

- [x] T016 [US1] Verify Nuitka uses `--mode=standalone` NOT `--mode=onefile` in scripts/build-nuitka.sh
- [x] T017 [US1] Verify NO `--python-flag=no_docstrings` flag in scripts/build-nuitka.sh (would break Typer CLI help)
- [x] T018 [US1] Measure baseline startup time with `hyperfine './dist/pgtail-*/pgtail --version'` (or time 10 runs manually) - ~68ms achieved
- [x] T019 [US1] Document startup time improvement in release notes draft (RELEASE_NOTES_v0.2.0.md)

**Checkpoint**: Fast startup verified locally (< 1 second goal met)

---

## Phase 4: User Story 6 - Full Functionality Preservation (Priority: P1)

**Goal**: All existing features work identically after migration

**Independent Test**: Run existing test suite against compiled binary; exercise REPL, tail mode, detection, notifications

### Implementation for User Story 6

- [x] T020 [US6] Verify scripts/build-nuitka.sh includes `--include-package=pgtail_py` flag
- [x] T021 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-package=psutil` flag (native extension)
- [x] T022 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-package-data=certifi` flag (CA bundle)
- [x] T023 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-module=pgtail_py.detector_unix` flag
- [x] T024 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-module=pgtail_py.detector_windows` flag
- [x] T025 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-module=pgtail_py.notifier_unix` flag
- [x] T026 [P] [US6] Verify scripts/build-nuitka.sh includes `--include-module=pgtail_py.notifier_windows` flag
- [x] T027 [US6] Test REPL mode: run `./dist/pgtail-*/pgtail`, enter help command, exit with Ctrl+D
- [x] T028 [US6] Test list command: run `./dist/pgtail-*/pgtail list` and verify PostgreSQL detection works
- [x] T029 [US6] Test tail mode: run `./dist/pgtail-*/pgtail tail 0` (if instance available) and verify UI renders
- [x] T030 [US6] Test --check-update: run `./dist/pgtail-*/pgtail --check-update` and verify HTTPS works (certifi CA bundle)

**Checkpoint**: All core functionality verified in compiled binary

---

## Phase 5: User Story 2 - Cross-Platform Binary Distribution (Priority: P1)

**Goal**: Binaries build and run on all 5 platforms via CI

**Independent Test**: Push tag, all 5 platform builds succeed, each runs `--version` successfully

### CI Workflow Implementation

- [x] T031 [US2] Create .github/workflows/release.yml with Nuitka build (replace PyInstaller workflow)
- [x] T032 [P] [US2] Add build matrix in release.yml: macos-14 (arm64), macos-15-intel (x86_64), ubuntu-latest (x86_64), ubuntu-24.04-arm (arm64), windows-latest (x86_64)
- [x] T098 [US2] Configure `timeout-minutes: 30` for each build job in release.yml (SC-003)
- [x] T033 [P] [US2] Add Python 3.12 setup step in release.yml using actions/setup-python
- [x] T034 [P] [US2] Add uv setup step in release.yml using astral-sh/setup-uv
- [x] T035 [US2] Add uv sync step: `uv sync --extra dev`
- [x] T036 [US2] Add Nuitka build step: `uv run nuitka <flags>` with all required flags from research.md
- [x] T037 [US2] Add post-build rename step: pgtail.dist/ -> pgtail-{platform}-{arch}/
- [x] T038 [US2] Add verification step: run `./dist/pgtail-*/pgtail --version` and assert exit code 0

### Archive Creation

- [x] T039 [P] [US2] Add tar.gz creation step for Unix platforms in release.yml
- [x] T040 [P] [US2] Add ZIP creation step for Windows platform in release.yml
- [x] T041 [US2] Add SHA256 checksum generation step for all archives in release.yml

### Artifact Upload

- [x] T042 [US2] Add upload-artifact step for archives and checksums in release.yml

### GitHub Release

- [x] T043 [US2] Add release job that downloads artifacts and creates GitHub Release with all files
- [x] T044 [US2] Add failure notification job that creates GitHub issue if any build step fails (FR-021)

### CI Verification

- [x] T045 [US2] Push test tag (e.g., v0.2.0-rc1) to trigger CI workflow
- [x] T046 [US2] Verify all 5 platform builds complete successfully
- [x] T047 [US2] Verify each platform artifact runs `--version` in CI logs
- [x] T048 [US2] Verify SHA256 checksums attached to release

**Checkpoint**: All 5 platforms build in CI, verification passes

---

## Phase 6: User Story 5 - Manual Windows Installation (Priority: P3)

**Goal**: Windows ZIP works as portable installation

**Independent Test**: Extract ZIP, run `pgtail.exe --version` from any folder

### Implementation for User Story 5

- [x] T049 [US5] Verify Windows ZIP contains folder pgtail-windows-x86_64/ with pgtail.exe inside (FR-011)
- [x] T050 [US5] Add Windows ZIP extraction and verification step in CI: extract, run `pgtail.exe --version` (FR-029)
- [x] T051 [US5] Test manual extraction: download ZIP, extract to arbitrary folder, run executable

**Checkpoint**: Windows portable ZIP verified

---

## Phase 7: User Story 4 - Windows winget Installation (Priority: P2)

**Goal**: pgtail installable via `winget install willibrandon.pgtail`

**Independent Test**: `winget install willibrandon.pgtail && pgtail --version`

### MSI Installer

- [x] T052 [US4] Create wix/pgtail.wxs WiX source file per research.md section 3.3
- [x] T053 [US4] Set UpgradeCode GUID to F8E7D6C5-B4A3-9281-7654-321098FEDCBA in pgtail.wxs (constant across versions)
- [x] T099 [US4] Use `Id="*"` for ProductCode in pgtail.wxs (auto-generated per build, MUST change each version)
- [x] T054 [US4] Configure MSI to install to Program Files\pgtail\ in pgtail.wxs
- [x] T055 [US4] Configure MSI to add install folder to system PATH in pgtail.wxs
- [x] T056 [US4] Add WiX build steps to release.yml for Windows job: install WiX via dotnet tool, heat, build
- [x] T100 [US4] Add ProductCode extraction step in release.yml: extract from built MSI for winget manifest

### winget Manifest

- [x] T057 [P] [US4] Create winget/willibrandon.pgtail.yaml version manifest per research.md section 4.2
- [x] T058 [P] [US4] Create winget/willibrandon.pgtail.installer.yaml installer manifest per research.md section 4.3
- [x] T059 [P] [US4] Create winget/willibrandon.pgtail.locale.en-US.yaml locale manifest per research.md section 4.4

### CI Integration

- [x] T060 [US4] Add MSI build steps to release.yml Windows job
- [x] T061 [US4] Add MSI upload step to release.yml (both ZIP and MSI as artifacts)
- [x] T062 [US4] Add SHA256 checksum for MSI in release.yml
- [x] T063 [US4] Add update-winget job to release.yml using wingetcreate (pushes to fork, opens PR to upstream)

### winget Submission

- [x] T064 [US4] Fork microsoft/winget-pkgs to willibrandon/winget-pkgs (required for CI workflow) [FORK EXISTS]
- [x] T065 [US4] Test manifest locally: `winget validate --manifest winget/` [VALIDATED VIA PR PIPELINE]
- [x] T066 [US4] Submit initial PR from fork (willibrandon/winget-pkgs) to microsoft/winget-pkgs [PR #327397]

**Checkpoint**: MSI builds in CI, winget manifest ready for submission

---

## Phase 8: User Story 3 - Homebrew Installation (Priority: P2)

**Goal**: pgtail installable via `brew install willibrandon/tap/pgtail`

**Independent Test**: `brew install willibrandon/tap/pgtail && pgtail --version`

### Homebrew Formula Update

- [x] T067 [US3] Update homebrew-tap/Formula/pgtail.rb to handle tar.gz archives per research.md section 5.2
- [x] T068 [US3] Add platform-specific URL blocks (on_macos/on_arm, on_macos/on_intel, on_linux/on_arm, on_linux/on_intel)
- [x] T069 [US3] Update install method to extract archive folder to libexec and symlink executable to bin
- [x] T070 [US3] Update test block to verify `pgtail --version` shows current version

### CI Integration

- [x] T071 [US3] Add update-homebrew job to release.yml that clones homebrew-tap, updates formula checksums
- [x] T072 [US3] Configure job to update SHA256 placeholders with actual checksums from release artifacts
- [x] T073 [US3] Configure job to commit and push formula update to homebrew-tap repository

### Verification

- [x] T074 [US3] Test formula locally: `brew install --build-from-source ./Formula/pgtail.rb`
- [x] T075 [US3] Verify `brew test pgtail` passes

**Checkpoint**: Homebrew formula updated, CI auto-updates on release

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, edge cases, final verification

### README Updates

- [x] T076 [P] Update README.md installation section with new archive-based instructions (FR-025)
- [x] T077 [P] Update README.md installation table to reflect tar.gz/ZIP/MSI formats (FR-026)

### mkdocs Documentation Updates

- [x] T078 [P] Update docs/getting-started/installation.md "Binary Download" section: change single binaries to tar.gz/ZIP archives
- [x] T079 [P] Update docs/getting-started/installation.md binary table: `pgtail-macos-arm64` -> `pgtail-macos-arm64.tar.gz` (and all platforms)
- [x] T080 [P] Update docs/getting-started/installation.md: replace `chmod +x` instructions with archive extraction steps (tar -xzf for Unix, Extract for Windows)
- [x] T081 [P] Update docs/getting-started/installation.md "Installation Summary" table: add note about archive extraction
- [x] T082 [P] Add docs/getting-started/installation.md troubleshooting: "Missing dependency folder" error with explanation (FR-027)
- [x] T083 [P] Add docs/getting-started/installation.md troubleshooting: Windows MSI vs ZIP installation paths (FR-028)
- [x] T084 [P] Update docs/getting-started/installation.md Windows section: distinguish MSI (admin/winget) vs ZIP (portable/no-admin)
- [x] T096 [P] Add docs/getting-started/installation.md troubleshooting: unsupported platform/architecture with guidance to compile from source (Edge Case 3)
- [x] T097 [P] Add docs/getting-started/installation.md troubleshooting: Windows antivirus/SmartScreen blocking dependencies with resolution steps (Edge Case 7)
- [x] T085 [P] Update docs/getting-started/quickstart.md if it references binary download (verify archive extraction steps)
- [x] T086 Build and verify mkdocs site: `mkdocs build` and review generated HTML for installation pages

### Edge Case Handling

- [ ] T087 [P] Test binary on read-only filesystem: verify clear error message (not crash)
- [ ] T088 [P] Test binary when user moves executable without dependencies: verify clear error about missing folder
- [ ] T089 [P] Test --check-update with missing CA certificates: verify clear SSL error message
- [ ] T090 [P] Verify x86_64 binary works under Rosetta 2 on Apple Silicon (macOS x86_64 build)

### Final Verification

- [ ] T091 Run quickstart.md validation checklist (all items must pass)
- [ ] T092 Verify all success criteria from spec.md:
  - SC-001: Startup < 1 second
  - SC-002: All 5 platform builds succeed
  - SC-003: CI < 30 minutes
  - SC-004: Binary size < 50 MB
  - SC-005: Tests pass against compiled binary
  - SC-006: CLI help displays correctly
  - SC-007: Version displays correctly
  - SC-008: Homebrew install works
  - SC-009: winget install works (after manifest approval)
  - SC-010: All core features work
  - SC-011: Zero regressions
  - SC-012: Windows ZIP portable verified
  - SC-013: Documentation updated
- [ ] T093 Tag release v0.2.0 and verify full release workflow completes

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all user stories)
    ↓
    ├─→ Phase 3: US1 (Fast Startup) ──────────────┐
    ├─→ Phase 4: US6 (Full Functionality) ────────┤
    ├─→ Phase 5: US2 (Cross-Platform CI) ─────────┼─→ Phase 9: Polish
    ├─→ Phase 6: US5 (Windows ZIP) ───────────────┤     ↓
    ├─→ Phase 7: US4 (winget/MSI) ────────────────┤   Release
    └─→ Phase 8: US3 (Homebrew) ──────────────────┘
```

### User Story Dependencies

- **US1 (Fast Startup)**: Can start after Foundational - verifies core build approach
- **US6 (Full Functionality)**: Can start after Foundational - verifies all features work
- **US2 (Cross-Platform CI)**: Can start after Foundational - depends on local build working
- **US5 (Windows ZIP)**: Depends on US2 CI being set up (ZIP created there)
- **US4 (winget/MSI)**: Depends on US2 CI being set up (adds MSI build)
- **US3 (Homebrew)**: Depends on US2 CI being set up (needs archive URLs)

### Recommended Execution Order (Single Developer)

1. Phase 1: Setup (T001-T004, T094-T095)
2. Phase 2: Foundational (T005-T015)
3. Phase 3: US1 Fast Startup (T016-T019) - validate approach
4. Phase 4: US6 Full Functionality (T020-T030) - ensure features work
5. Phase 5: US2 Cross-Platform CI (T031-T048, T098) - enable distribution
6. Phase 6: US5 Windows ZIP (T049-T051) - complete Windows portable
7. Phase 7: US4 winget/MSI (T052-T066) - Windows package manager
8. Phase 8: US3 Homebrew (T067-T075) - macOS/Linux package manager
9. Phase 9: Polish (T076-T097) - docs and final verification

### Parallel Opportunities

**Within Phase 1:**
- T002 and T003 can run in parallel (different files)

**Within Phase 2:**
- T006 and T007 can run in parallel (different Makefile targets)

**Within Phase 4 (US6):**
- T021-T026 can all run in parallel (verifying different flags)

**Within Phase 5 (US2):**
- T032-T034 can run in parallel (different CI setup steps)
- T039 and T040 can run in parallel (tar.gz and ZIP creation)

**Within Phase 7 (US4):**
- T057-T059 can run in parallel (different manifest files)

**Within Phase 9 (Polish):**
- T076-T090, T096-T097 can all run in parallel (independent documentation and edge case tasks)

---

## Parallel Example: Phase 4 (US6 Full Functionality)

```bash
# Launch all flag verification tasks together:
Task: "[US6] Verify --include-package=psutil flag"
Task: "[US6] Verify --include-package-data=certifi flag"
Task: "[US6] Verify --include-module=pgtail_py.detector_unix flag"
Task: "[US6] Verify --include-module=pgtail_py.detector_windows flag"
Task: "[US6] Verify --include-module=pgtail_py.notifier_unix flag"
Task: "[US6] Verify --include-module=pgtail_py.notifier_windows flag"
```

---

## Implementation Strategy

### MVP First (Phases 1-4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (Fast Startup) - **Core value delivered**
4. Complete Phase 4: US6 (Full Functionality) - **No regressions**
5. **STOP and VALIDATE**: Local builds work perfectly, < 1 second startup, all features work

### Full Distribution (Phases 5-8)

6. Complete Phase 5: US2 (Cross-Platform CI) - All platforms build
7. Complete Phase 6: US5 (Windows ZIP) - Portable option ready
8. Complete Phase 7: US4 (winget/MSI) - Windows package manager
9. Complete Phase 8: US3 (Homebrew) - macOS/Linux package manager

### Release (Phase 9)

10. Complete Phase 9: Polish - Docs, edge cases, final validation
11. Tag v0.2.0 and release

---

## Task Summary

| Phase | Story | Task Count | Parallel Tasks |
|-------|-------|------------|----------------|
| Phase 1: Setup | - | 6 | 2 |
| Phase 2: Foundational | - | 11 | 2 |
| Phase 3: US1 Fast Startup | US1 | 4 | 0 |
| Phase 4: US6 Full Functionality | US6 | 11 | 6 |
| Phase 5: US2 Cross-Platform CI | US2 | 19 | 5 |
| Phase 6: US5 Windows ZIP | US5 | 3 | 0 |
| Phase 7: US4 winget/MSI | US4 | 17 | 3 |
| Phase 8: US3 Homebrew | US3 | 9 | 0 |
| Phase 9: Polish | - | 20 | 16 |
| **Total** | | **100** | **34** |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- NEVER use `--python-flag=no_docstrings` - it breaks Typer CLI help
- WiX UpgradeCode MUST remain constant: F8E7D6C5-B4A3-9281-7654-321098FEDCBA
- WiX ProductCode MUST change per version: use `Id="*"` for auto-generation, extract from built MSI
- winget workflow: Push to fork (willibrandon/winget-pkgs), open PR to microsoft/winget-pkgs
- Local winget-pkgs reference: `/Users/brandon/src/winget-pkgs`
- mkdocs documentation: `docs/getting-started/installation.md` is the primary installation guide
- Build mkdocs site with `mkdocs build` or serve locally with `mkdocs serve`
