# Tasks: Windows Store Distribution

**Input**: Design documents from `/specs/024-windows-store/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/partner-center-api.md, quickstart.md

**Tests**: Not explicitly requested - test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create MSIX directory structure and generate logo assets

- [ ] T001 Create `msix/` directory structure per plan.md
- [ ] T002 [P] Generate StoreLogo.png (50x50) from art/pgtail.ico using ImageMagick in msix/Assets/StoreLogo.png
- [ ] T003 [P] Generate Square44x44Logo.png (44x44) from art/pgtail.ico in msix/Assets/Square44x44Logo.png
- [ ] T004 [P] Generate Square150x150Logo.png (150x150) from art/pgtail.ico in msix/Assets/Square150x150Logo.png
- [ ] T005 [P] Generate Wide310x150Logo.png (310x150) from art/pgtail.ico in msix/Assets/Wide310x150Logo.png

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create AppxManifest.xml template that all MSIX builds depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create AppxManifest.xml template with Identity placeholders in msix/AppxManifest.xml
- [ ] T007 Add AppExecutionAlias extension with `desktop4:Subsystem="console"` for `pgtail.exe` in msix/AppxManifest.xml
- [ ] T008 Add `runFullTrust` capability declaration in msix/AppxManifest.xml
- [ ] T009 Add logo asset references (StoreLogo, Square44x44Logo, Square150x150Logo, Wide310x150Logo) in msix/AppxManifest.xml
- [ ] T010 Add TargetDeviceFamily for Windows 10 1809 (build 17763) minimum in msix/AppxManifest.xml

**Checkpoint**: Foundation ready - manifest template complete, user story implementation can begin

---

## Phase 3: User Story 1 - Windows User Installs pgtail from Microsoft Store (Priority: P1)

**Goal**: Users can install pgtail from Store without SmartScreen warnings and invoke `pgtail` from any terminal

**Independent Test**: Install pgtail from Microsoft Store and verify `pgtail` command works in PowerShell/cmd/Windows Terminal

### Implementation for User Story 1

- [ ] T011 [US1] Add `build-windows-arm64` job to .github/workflows/release.yml using `windows-11-arm` runner
- [ ] T012 [US1] Configure Nuitka ARM64 build with `--mode=standalone` in build-windows-arm64 job
- [ ] T013 [US1] Add `build-msix` job that depends on both x64 and ARM64 build jobs in .github/workflows/release.yml
- [ ] T014 [US1] Add step to substitute Package Identity Name from `STORE_PACKAGE_NAME` secret into AppxManifest.xml in build-msix job
- [ ] T015 [US1] Add step to substitute Publisher CN from `STORE_PUBLISHER_CN` secret into AppxManifest.xml in build-msix job
- [ ] T016 [US1] Add step to convert semantic version to X.Y.Z.0 format for MSIX in build-msix job
- [ ] T017 [US1] Add step to create msix-stage-x64/ directory with manifest, assets, and Nuitka output in build-msix job
- [ ] T018 [US1] Add step to create msix-stage-arm64/ directory with manifest, assets, and Nuitka output in build-msix job
- [ ] T019 [US1] Add step to run `makeappx pack` for x64 MSIX package in build-msix job
- [ ] T020 [US1] Add step to run `makeappx pack` for ARM64 MSIX package in build-msix job
- [ ] T021 [US1] Add step to run `makeappx bundle` to create pgtail.msixbundle from x64 and ARM64 packages in build-msix job
- [ ] T022 [US1] Add step to upload pgtail.msixbundle as GitHub Release artifact in build-msix job

**Checkpoint**: MSIX bundle builds and uploads on every release tag - ready for manual Store submission

---

## Phase 4: User Story 2 - Automatic Updates for Store Users (Priority: P1)

**Goal**: Store users receive automatic updates when new versions are published

**Independent Test**: Release new version and verify Store users receive update automatically

**Note**: This user story is satisfied by User Story 1 + User Story 3 - Microsoft Store handles automatic updates natively. No additional implementation required beyond building and submitting MSIX packages.

- [ ] T023 [US2] Document automatic update behavior in quickstart.md troubleshooting section

**Checkpoint**: Automatic updates work via native Store functionality

---

## Phase 5: User Story 3 - Release Automation Publishes to Store (Priority: P2)

**Goal**: CI/CD pipeline automatically submits MSIX to Store when maintainer pushes version tag

**Independent Test**: Push version tag and verify Store submission workflow completes successfully

### Implementation for User Story 3

- [ ] T024 [US3] Add `update-store` job that depends on build-msix in .github/workflows/release.yml
- [ ] T025 [US3] Add step to authenticate with Partner Center API using OAuth2 client credentials flow in update-store job
- [ ] T026 [US3] Add step to get application info and check for pending submission in update-store job
- [ ] T027 [US3] Add step to delete pending submission if exists (409 Conflict handling) in update-store job
- [ ] T028 [US3] Add step to create new submission and get fileUploadUrl in update-store job
- [ ] T029 [US3] Add step to update submission with package metadata in update-store job
- [ ] T030 [US3] Add step to create submission.zip containing pgtail.msixbundle in update-store job
- [ ] T031 [US3] Add step to upload submission.zip to Azure Blob Storage via SAS URL with retry logic (3 retries, 30s/60s/120s backoff) in update-store job
- [ ] T032 [US3] Add step to commit submission in update-store job
- [ ] T033 [US3] Add step to poll submission status until it leaves `CommitStarted` state in update-store job
- [ ] T034 [US3] Add step to fail workflow if status is not `PreProcessing` or `Certification` in update-store job
- [ ] T035 [US3] Add workflow output summary with submission ID and status in update-store job

**Checkpoint**: Store submission automation complete - every release tag triggers Store update

---

## Phase 6: User Story 4 - Maintainer Initial Store Setup (Priority: P3)

**Goal**: Maintainer completes one-time setup for Store distribution

**Independent Test**: Complete registration, reserve app name, verify Partner Center shows reserved app

**Note**: Most of this user story is already complete (developer account, app reservation, Azure AD, GitHub secrets). Remaining tasks document and finalize setup.

- [ ] T036 [US4] Update quickstart.md with actual Package Identity Name (`willibrandon.pgtail`) in Phase 4 section
- [ ] T037 [US4] Update quickstart.md with actual Publisher CN (`CN=D5CABD13-9566-41E6-B3CA-A0F512C3FD38`) in Phase 4 section
- [ ] T038 [US4] Update quickstart.md with actual Store App ID (`9NWX1SPCWFNQ`) in Phase 3 section
- [ ] T039 [US4] Document secret rotation schedule in quickstart.md (client secret expiration)
- [ ] T040 [US4] Add GitHub secrets list verification command example in quickstart.md

**Checkpoint**: Setup documentation complete with real values

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finalize implementation and handle edge cases

- [ ] T041 [P] Add workflow timeout of 30 minutes to all Windows Store jobs in .github/workflows/release.yml
- [ ] T042 [P] Add error handling for Package Identity mismatch with clear error message in build-msix job
- [ ] T043 [P] Add version format validation to reject invalid tags gracefully in build-msix job
- [ ] T044 [P] Add MSIX package size check (warn if >35MB) in build-msix job
- [ ] T045 [P] Create scripts/build-msix.ps1 for local MSIX builds (generates self-signed cert, builds package)
- [ ] T046 [P] Add Windows SDK and ImageMagick install check to scripts/build-msix.ps1 with install instructions on failure
- [ ] T047 [P] Create scripts/test-msix.ps1 for local install/test/uninstall cycle
- [ ] T048 [P] Add `make msix` target to Makefile that runs build-msix.ps1
- [ ] T049 Document local MSIX testing workflow in docs/development/msix-testing.md
- [ ] T050 Verify AppExecutionAlias creates `pgtail.exe` stub in WindowsApps (manual local test)
- [ ] T051 Verify MSIX uninstall removes all components cleanly (manual local test)
- [ ] T052 Update CLAUDE.md with Windows Store distribution section documenting workflow jobs
- [ ] T053 [P] Update README.md with Microsoft Store installation option in Installation section
- [ ] T054 [P] Add docs/installation/windows-store.md with Store installation instructions for mkdocs
- [ ] T055 [P] Update docs/installation/index.md to include Windows Store as installation method
- [ ] T056 Commit msix/ directory with AppxManifest.xml and Assets/ to repository

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (needs Assets/) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (needs AppxManifest.xml)
- **User Story 2 (Phase 4)**: Documentation only - can start after Phase 3
- **User Story 3 (Phase 5)**: Depends on Phase 3 (needs build-msix job)
- **User Story 4 (Phase 6)**: Documentation only - can start anytime
- **Polish (Phase 7)**: Depends on Phase 5

### User Story Dependencies

- **User Story 1 (P1)**: Independent - MSIX build capability
- **User Story 2 (P1)**: Trivial - native Store functionality after US1+US3
- **User Story 3 (P2)**: Depends on US1 - needs MSIX bundle to submit
- **User Story 4 (P3)**: Independent - documentation updates

### Within Each User Story

- Workflow jobs ordered by dependency (build → package → submit)
- Each step depends on previous step's output
- Retry logic added before commit step

### Parallel Opportunities

Within Phase 1:
```bash
# All asset generation runs in parallel:
Task: T002 "Generate StoreLogo.png"
Task: T003 "Generate Square44x44Logo.png"
Task: T004 "Generate Square150x150Logo.png"
Task: T005 "Generate Wide310x150Logo.png"
```

Within Phase 7:
```bash
# All polish tasks marked [P] run in parallel:
Task: T041 "Add workflow timeout"
Task: T042 "Add Package Identity error handling"
Task: T043 "Add version format validation"
Task: T044 "Add MSIX size check"
Task: T045 "Create build-msix.ps1"
Task: T046 "Add SDK/ImageMagick check"
Task: T047 "Create test-msix.ps1"
Task: T048 "Add make msix target"
Task: T053 "Update README.md"
Task: T054 "Add Windows Store mkdocs page"
Task: T055 "Update installation index"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (generate assets)
2. Complete Phase 2: Foundational (create manifest)
3. Complete Phase 3: User Story 1 (MSIX build workflow)
4. **STOP and VALIDATE**: Trigger test release, verify MSIX artifact uploads
5. Manual Store submission for first version

### Incremental Delivery

1. Setup + Foundational → Assets and manifest ready
2. User Story 1 → MSIX builds on every release (MVP!)
3. User Story 3 → Automated Store submission
4. User Story 4 → Documentation finalized
5. Polish → Edge cases and validation

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**

This delivers:
- MSIX package builds for x64 and ARM64
- MSIX bundle uploaded as release artifact
- Manual Store submission possible

Automated submission (User Story 3) can follow after first manual Store approval.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All STORE_* secrets already configured in GitHub
- First Store submission must be manual (API can only update existing apps)
- ARM64 builds use `windows-11-arm` runner (public repos only)
- MSIX packages are unsigned - Microsoft signs during certification
