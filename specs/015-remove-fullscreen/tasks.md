# Tasks: Remove Fullscreen TUI

**Input**: Design documents from `/specs/015-remove-fullscreen/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No new tests required. This is a removal feature - existing tests validate functionality preservation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `pgtail_py/`, `tests/` at repository root
- This is a deletion-focused feature - most tasks remove rather than create

---

## Phase 1: Setup

**Purpose**: No setup required - this is a removal feature on an existing codebase.

> Skip to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational work required - deletions and modifications can proceed directly.

> Skip to Phase 3.

---

## Phase 3: User Story 1 - Clean Codebase Without Fullscreen TUI (Priority: P1) 🎯 MVP

**Goal**: Remove all fullscreen-related source code, commands, and tests from the codebase.

**Independent Test**:
1. `python -c "from pgtail_py import cli"` runs without import errors
2. `grep -r "fullscreen" pgtail_py/ --include="*.py"` returns nothing
3. `make test` passes (after test deletion)

### Implementation for User Story 1

#### Step 1: Delete Fullscreen Source Files

- [X] T001 [P] [US1] Delete fullscreen package file pgtail_py/fullscreen/__init__.py
- [X] T002 [P] [US1] Delete fullscreen app module pgtail_py/fullscreen/app.py
- [X] T003 [P] [US1] Delete fullscreen buffer module pgtail_py/fullscreen/buffer.py
- [X] T004 [P] [US1] Delete fullscreen buffer lexer pgtail_py/fullscreen/buffer_lexer.py
- [X] T005 [P] [US1] Delete fullscreen keybindings pgtail_py/fullscreen/keybindings.py
- [X] T006 [P] [US1] Delete fullscreen layout module pgtail_py/fullscreen/layout.py
- [X] T007 [P] [US1] Delete fullscreen Pygments lexer pgtail_py/fullscreen/lexer.py
- [X] T008 [P] [US1] Delete fullscreen state module pgtail_py/fullscreen/state.py
- [X] T009 [P] [US1] Delete CLI fullscreen handler pgtail_py/cli_fullscreen.py
- [X] T010 [US1] Remove empty pgtail_py/fullscreen/ directory (after T001-T008)

#### Step 2: Delete Fullscreen Test Files

- [X] T011 [P] [US1] Delete test file tests/unit/fullscreen/__init__.py
- [X] T012 [P] [US1] Delete test file tests/unit/fullscreen/test_buffer.py
- [X] T013 [P] [US1] Delete test file tests/unit/fullscreen/test_cli_fullscreen.py
- [X] T014 [P] [US1] Delete test file tests/unit/fullscreen/test_keybindings.py
- [X] T015 [P] [US1] Delete test file tests/unit/fullscreen/test_state.py
- [X] T016 [P] [US1] Delete integration test tests/integration/test_fullscreen.py
- [X] T017 [US1] Remove empty tests/unit/fullscreen/ directory (after T011-T015)

#### Step 3: Update CLI Module

- [X] T018 [US1] Remove import `from pgtail_py.cli_fullscreen import fullscreen_command` in pgtail_py/cli.py
- [X] T019 [US1] Remove import `from pgtail_py.fullscreen import FullscreenState, LogBuffer` in pgtail_py/cli.py
- [X] T020 [US1] Remove `fullscreen_buffer` field from AppState class in pgtail_py/cli.py
- [X] T021 [US1] Remove `fullscreen_state` field from AppState class in pgtail_py/cli.py
- [X] T022 [US1] Remove `get_or_create_buffer()` method from AppState in pgtail_py/cli.py
- [X] T023 [US1] Remove `get_or_create_fullscreen_state()` method from AppState in pgtail_py/cli.py
- [X] T024 [US1] Remove fullscreen docstring references from AppState class in pgtail_py/cli.py
- [X] T025 [US1] Remove fullscreen command handler (`elif cmd in ("fullscreen", "fs"):`) in pgtail_py/cli.py
- [X] T026 [US1] Update pause message to remove fullscreen mention in pgtail_py/cli.py

#### Step 4: Update Commands Module

- [X] T027 [US1] Remove `"fullscreen"` entry from COMMANDS dict in pgtail_py/commands.py
- [X] T028 [US1] Remove `"fs"` entry from COMMANDS dict in pgtail_py/commands.py

**Checkpoint**: At this point, all fullscreen code is removed. Application should start without import errors. Test with:
```bash
python -c "from pgtail_py import cli"
grep -r "fullscreen" pgtail_py/ --include="*.py"
make test
```

---

## Phase 4: User Story 2 - Documentation Reflects Removal (Priority: P2)

**Goal**: Remove all fullscreen references from documentation so users don't see references to non-existent functionality.

**Independent Test**:
1. `grep -i "fullscreen" CLAUDE.md` returns nothing (excluding spec references)
2. `grep -i "fullscreen" README.md` returns nothing (if README exists)

### Implementation for User Story 2

- [X] T029 [US2] Remove "## Fullscreen TUI Mode" section from CLAUDE.md
- [X] T030 [US2] Remove fullscreen references from "## Recent Changes" section in CLAUDE.md
- [X] T031 [US2] Remove fullscreen references from "## Active Technologies" section in CLAUDE.md
- [X] T032 [US2] Search and remove any remaining fullscreen references in CLAUDE.md
- [X] T033 [US2] Check and update README.md if it contains fullscreen references

**Checkpoint**: Documentation no longer mentions fullscreen TUI.

---

## Phase 5: User Story 3 - Existing Functionality Unaffected (Priority: P1)

**Goal**: Verify that all non-fullscreen features continue to work correctly.

**Independent Test**: Full test suite passes, manual verification of core features.

### Verification for User Story 3

- [X] T034 [US3] Run `make test` and verify all remaining tests pass
- [X] T035 [US3] Run `make lint` and verify no linting errors introduced
- [X] T036 [US3] Verify application starts: `python -m pgtail_py`
- [X] T037 [US3] Verify `help` command shows no fullscreen references
- [X] T038 [US3] Verify `fullscreen` and `fs` commands show "Unknown command" error
- [X] T039 [US3] Verify autocomplete does not suggest fullscreen or fs commands

**Checkpoint**: All non-fullscreen functionality works. Feature removal complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

- [X] T040 Run final verification: `grep -r "fullscreen" pgtail_py/ tests/ --include="*.py"` returns nothing
- [X] T041 Verify net negative line change: `git diff --stat` shows deletion
- [X] T042 Clean up any pycache files in removed directories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-2**: Skipped (no setup or foundational work needed)
- **Phase 3 (US1)**: Can start immediately - core deletion work
- **Phase 4 (US2)**: Can run in parallel with Phase 3 (different files)
- **Phase 5 (US3)**: Must run after Phase 3 completes (verification)
- **Phase 6**: Must run after all phases complete

### Task Dependencies Within User Story 1

```
T001-T009 (parallel) → T010 (cleanup directory)
T011-T016 (parallel) → T017 (cleanup directory)
T010, T017 → T018-T028 (update imports after deletions)
```

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - can start immediately
- **User Story 2 (P2)**: No dependencies on US1 - different files, can run in parallel
- **User Story 3 (P1)**: Depends on US1 completion - verification requires code to be removed first

### Parallel Opportunities

All file deletions (T001-T009, T011-T016) can run in parallel.

---

## Parallel Example: User Story 1 Deletions

```bash
# Launch all source file deletions together:
Task: "Delete fullscreen package file pgtail_py/fullscreen/__init__.py"
Task: "Delete fullscreen app module pgtail_py/fullscreen/app.py"
Task: "Delete fullscreen buffer module pgtail_py/fullscreen/buffer.py"
Task: "Delete fullscreen buffer lexer pgtail_py/fullscreen/buffer_lexer.py"
Task: "Delete fullscreen keybindings pgtail_py/fullscreen/keybindings.py"
Task: "Delete fullscreen layout module pgtail_py/fullscreen/layout.py"
Task: "Delete fullscreen Pygments lexer pgtail_py/fullscreen/lexer.py"
Task: "Delete fullscreen state module pgtail_py/fullscreen/state.py"
Task: "Delete CLI fullscreen handler pgtail_py/cli_fullscreen.py"

# Then cleanup:
Task: "Remove empty pgtail_py/fullscreen/ directory"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 3 Only)

1. Complete Phase 3: Delete all fullscreen source and test files, update imports
2. Complete Phase 5: Verify application works
3. **STOP and VALIDATE**: Test that pgtail works without fullscreen
4. Commit and verify

### Full Delivery

1. Complete Phase 3: User Story 1 (code removal)
2. Complete Phase 4: User Story 2 (documentation) - can run in parallel
3. Complete Phase 5: User Story 3 (verification)
4. Complete Phase 6: Polish
5. Commit as single atomic change

### Recommended Execution

Since this is a removal feature, execute as single atomic commit:

```bash
# All deletions and modifications in one commit
git add -A
git commit -m "Remove fullscreen TUI feature

- Delete pgtail_py/fullscreen/ package (8 files)
- Delete pgtail_py/cli_fullscreen.py
- Delete tests/unit/fullscreen/ (5 files)
- Delete tests/integration/test_fullscreen.py
- Update pgtail_py/cli.py (remove imports, AppState fields, command handler)
- Update pgtail_py/commands.py (remove fullscreen/fs commands)
- Update CLAUDE.md (remove fullscreen documentation)

Closes #015"
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Most tasks are deletions - execute with `rm` or `git rm`
- cli.py modifications should be done carefully to avoid breaking remaining code
- Run tests frequently to catch any missed dependencies
- Commit after each phase or as single atomic commit
