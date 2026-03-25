---
description: "Task list for Paycheck & W-2 Validator"
---

# Tasks: Paycheck & W-2 Validator

**Input**: Design documents from `specs/001-paycheck-w2-validator/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Included — constitution Principle II mandates TDD (tests written first, must fail before implementation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are relative to repository root

## Path Conventions

- Source: `src/paychecks/`
- Tests: `tests/`
- Fixtures: `tests/fixtures/builders/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — uv, package structure, tooling config.

- [x] T001 Initialize uv project: create `pyproject.toml` with `[project]` metadata, `[project.scripts]` entry `paychecks = "paychecks.cli:app"`, and dependency groups for runtime and dev
- [x] T002 Create `src/paychecks/` package with `__init__.py`, `cli.py` (empty Typer app stub), and sub-package stubs: `models/`, `extractor/`, `validator/`, `reporter/`
- [x] T003 [P] Configure ruff in `pyproject.toml` (`[tool.ruff]`): enable linting + formatting rules; add `pre-commit` hook or `mise` lint target
- [x] T004 [P] Configure pytest in `pyproject.toml` (`[tool.pytest.ini_options]`): set `testpaths = ["tests"]`, `addopts = "--strict-markers"`; configure `pytest-cov` with `--cov=src/paychecks --cov-fail-under=80`
- [x] T005 [P] Create `tests/` directory structure: `tests/conftest.py` (empty), `tests/unit/`, `tests/integration/`, `tests/fixtures/builders/` with `__init__.py` files

**Checkpoint**: `uv pip install -e .` succeeds; `paychecks --help` prints stub help; `uv run pytest` collects 0 tests and exits 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, extractor cascade, and reporter base — MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Create `src/paychecks/constants.py` with all named constants: `DEFAULT_PAYCHECK_TOLERANCE = Decimal("0.02")`, `DEFAULT_W2_TOLERANCE = Decimal("1.00")`, `CURRENCY_SYMBOL = "$"`, `DATE_FORMAT = "%Y-%m-%d"`, `CLAUDE_CLI_TIMEOUT_SECONDS = 30`
- [x] T007 [P] Create `PayFrequency` enum and `ExtractionMethod` enum in `src/paychecks/models/enums.py`
- [x] T008 [P] Create `ValidationStatus` enum and `FieldResult` frozen dataclass in `src/paychecks/models/results.py`
- [x] T009 Create `Deduction` and `Paycheck` frozen dataclasses in `src/paychecks/models/paycheck.py` (imports from enums.py)
- [x] T010 Create `SalaryChange` and `SalarySchedule` frozen dataclasses in `src/paychecks/models/salary.py`; implement `salary_for_period(period_start: date) -> Decimal` method
- [x] T011 Create `PaycheckValidationResult` frozen dataclass in `src/paychecks/models/paycheck.py`; add `overall_status` derived property (worst FieldResult status); add `passed` property
- [x] T012 Create `ExtractionError` frozen dataclass in `src/paychecks/models/errors.py`; update `src/paychecks/models/__init__.py` to export all public model types
- [x] T013 Implement `pdfplumber` paycheck extractor in `src/paychecks/extractor/pdf.py`: extract pay period dates, gross pay, all deductions, net pay, federal/SS/Medicare/state tax from text-based PDFs; return `Paycheck | ExtractionError`
- [x] T014 [P] Implement `pytesseract` + `pdf2image` OCR fallback extractor in `src/paychecks/extractor/ocr.py`: convert PDF pages to images, apply Tesseract, re-run field extraction on OCR text; return `Paycheck | ExtractionError`
- [x] T015 [P] Implement `claude` CLI subprocess fallback in `src/paychecks/extractor/claude_fallback.py`: build structured prompt with extracted text, call `subprocess.run(["claude", "-p", prompt], timeout=CLAUDE_CLI_TIMEOUT_SECONDS)`, parse JSON response; return `Paycheck | ExtractionError`
- [x] T016 Implement extraction cascade in `src/paychecks/extractor/__init__.py`: try pdf.py → ocr.py → claude_fallback.py; stop at first success; return final `ExtractionError` only if all three fail; tag result with `ExtractionMethod`
- [x] T017 [P] Create `Rich`-based terminal reporter base in `src/paychecks/reporter/terminal.py`: define `render_validation_result(result: PaycheckValidationResult)` and `render_reconciliation_report(report: ReconciliationReport)` stubs using `rich.table.Table`
- [x] T018 [P] Create plain-text export in `src/paychecks/reporter/text_export.py`: `write_validation_txt(result, path)` and `write_reconciliation_txt(report, path)` — same content as terminal output, no Rich styling
- [x] T019 [P] Create CSV export in `src/paychecks/reporter/csv_export.py`: `write_validation_csv(result, path)` and `write_reconciliation_csv(report, path)` with headers `field,expected,actual,status,note`
- [x] T020 Create paycheck PDF fixture builder in `tests/fixtures/builders/paycheck_builder.py` using `reportlab`: `PaycheckBuilder(annual_salary, frequency, period_start, period_end).save(path)` — produces a synthetic paycheck PDF with all required fields; supports `build_year(year)` for full-year generation
- [x] T021 [P] Create W-2 PDF fixture builder in `tests/fixtures/builders/w2_builder.py` using `reportlab`: `W2Builder(annual_salary, tax_year, **overrides).save(path)` — produces a synthetic IRS Form W-2 PDF; supports field overrides for mismatch testing
- [x] T022 [P] Write unit tests for all model dataclasses in `tests/unit/test_models.py`: field validation rules, `salary_for_period` with and without mid-year changes, `overall_status` derivation; run `pytest tests/unit/test_models.py` — MUST fail before T009–T012 are implemented

**Checkpoint**: Foundation ready — `uv run pytest tests/unit/test_models.py` red (tests fail); all model, extractor, reporter stubs importable; fixture builders produce valid PDFs.

---

## Phase 3: User Story 1 — Validate Single Paycheck (Priority: P1) 🎯 MVP

**Goal**: User runs `paychecks validate <pdf> --salary N --frequency biweekly` and gets a terminal table showing pass/fail per field.

**Independent Test**: Generate one synthetic paycheck PDF with known values, run `paychecks validate`, assert all fields PASS and exit code is 0. Change gross pay to introduce a discrepancy, assert FAIL and exit code 1.

### Tests for User Story 1 (write first — MUST fail before implementation)

- [x] T023 [P] [US1] Write failing unit tests for paycheck validation logic in `tests/unit/test_validator_paycheck.py`: test gross pay pass/fail/warning, net pay pass/fail, tolerance boundary, supplemental pay warning, mid-year salary change routing
- [x] T024 [P] [US1] Write failing unit tests for pdfplumber PDF extractor in `tests/unit/test_extractor_pdf.py`: test field extraction from a synthetic PDF, missing field returns ExtractionError with correct filename/page/field
- [x] T025 [P] [US1] Write failing integration test for `validate` command in `tests/integration/test_validate_command.py`: invoke CLI via `typer.testing.CliRunner`; assert stdout contains pass/fail table; assert exit code 0 on matching PDF, 1 on mismatch, 2 on bad PDF

### Implementation for User Story 1

- [x] T026 [US1] Implement per-paycheck validation logic in `src/paychecks/validator/paycheck.py`: `validate_paycheck(paycheck, salary_schedule) -> PaycheckValidationResult`; enforce tolerance from constants; handle supplemental pay as WARNING
- [x] T027 [US1] Implement `validate` Typer subcommand in `src/paychecks/cli.py`: wire `--salary`, `--frequency`, `--salary-change`, `--tolerance`, `--output` options; call extractor cascade → validator → reporter; set exit code per contract; show a `rich.status.Status` spinner with the current extraction method ("Extracting via OCR…" / "Extracting via Claude CLI…") when a fallback extractor is invoked (constitution Principle III: all async operations MUST show progress)
- [x] T028 [US1] Implement `render_validation_result` in `src/paychecks/reporter/terminal.py`: Rich Table with columns field/expected/actual/status; color-code ✅/❌/⚠️ status badges; ISO 8601 dates; `$X.XX` currency format
- [x] T029 [US1] Implement `--output` dispatch in `src/paychecks/cli.py`: detect `.txt` vs `.csv` extension; call `text_export.write_validation_txt` or `csv_export.write_validation_csv`; always also print to terminal

**Checkpoint**: `paychecks validate /tmp/paycheck_test.pdf --salary 120000 --frequency biweekly` prints a complete pass/fail table to terminal and exits 0. All US1 tests pass. Run `uv run pytest tests/unit/test_validator_paycheck.py tests/unit/test_extractor_pdf.py tests/integration/test_validate_command.py` — all green.

---

## Phase 4: User Story 2 — Year-End W-2 Reconciliation (Priority: P2)

**Goal**: User runs `paychecks reconcile <dir> <w2.pdf> --salary N --frequency biweekly` and gets a line-by-line W-2 reconciliation report.

**Independent Test**: Generate 26 synthetic paycheck PDFs + 1 matching W-2, run `paychecks reconcile`, assert all 8 W-2 boxes show PASS and exit 0. Override one W-2 box value, assert FAIL and exit 1.

### Tests for User Story 2 (write first — MUST fail before implementation)

- [x] T030 [P] [US2] Write failing unit tests for W-2 extractor in `tests/unit/test_extractor_pdf.py`: assert all 8 W-2 boxes extracted correctly from synthetic W-2 PDF; assert W-2c detection returns ExtractionError with unsupported-format message
- [x] T031 [P] [US2] Write failing unit tests for W-2 reconciliation logic in `tests/unit/test_validator_w2.py`: test aggregation of paycheck totals, tolerance boundary (default $1.00), missing period detection for weekly/biweekly/semimonthly/monthly
- [x] T032 [US2] Write failing integration test for `reconcile` command in `tests/integration/test_reconcile_command.py`: full pipeline with synthetic PDFs; assert reconciliation table in stdout; assert mismatch detection; assert missing period warning on stderr

### Implementation for User Story 2

- [x] T033 [P] [US2] Create `W2`, `ReconciliationField`, `ReconciliationReport` dataclasses in `src/paychecks/models/w2.py`; update `src/paychecks/models/__init__.py`
- [x] T034 [US2] Extend pdfplumber extractor in `src/paychecks/extractor/pdf.py`: add `extract_w2(path) -> W2 | ExtractionError`; detect W-2c and return ExtractionError immediately
- [x] T035 [US2] Implement W-2 reconciliation logic in `src/paychecks/validator/w2.py`: `reconcile(paychecks, w2, salary_schedule) -> ReconciliationReport`; aggregate per-field paycheck totals; compare to W-2 boxes within tolerance; detect missing pay periods from declared frequency + date range
- [x] T036 [US2] Implement `reconcile` Typer subcommand in `src/paychecks/cli.py`: wire `--salary`, `--frequency`, `--salary-change`, `--w2-tolerance`, `--output`; extract all PDFs in directory; call w2 reconciler → reporter
- [x] T037 [US2] Implement `render_reconciliation_report` in `src/paychecks/reporter/terminal.py`: Rich Table with W-2 field/paycheck-total/W-2-value/difference/status columns; warn on missing periods; print period count header

**Checkpoint**: `paychecks reconcile /tmp/paychecks2025/ /tmp/w2_2025.pdf --salary 120000 --frequency biweekly` prints complete reconciliation table and exits 0. All US2 tests pass.

---

## Phase 5: User Story 3 — Batch Validation (Priority: P3)

**Goal**: User runs `paychecks batch <dir> --salary N --frequency biweekly` and gets a summary table with per-paycheck pass/fail and a Rich progress bar during processing.

**Independent Test**: Generate a folder of 26 synthetic paychecks, run `paychecks batch`, assert summary table has 26 rows all PASS and exit 0. Corrupt one PDF, assert it shows ERROR in the table and exit 2, while other 25 still process.

### Tests for User Story 3 (write first — MUST fail before implementation)

- [x] T038 [P] [US3] Write failing unit tests for batch processing in `tests/unit/test_validator_paycheck.py`: test `validate_batch()` returns list of results; one corrupted PDF yields ExtractionError; missing period detection across the batch
- [x] T039 [US3] Write failing integration test for `batch` command in `tests/integration/test_batch_command.py`: assert summary table with per-file rows; assert Rich progress output; assert correct exit codes for all-pass, partial-fail, extraction-error scenarios

### Implementation for User Story 3

- [x] T040 [US3] Implement `validate_batch(paths, salary_schedule) -> list[PaycheckValidationResult | ExtractionError]` in `src/paychecks/validator/paycheck.py`; continue processing remaining files on single-file extraction failure
- [x] T041 [US3] Implement `batch` Typer subcommand in `src/paychecks/cli.py`: collect all `.pdf` files from directory; show `rich.progress.Progress` bar during processing; call `validate_batch`; render summary table; set exit code (0=all pass, 1=any fail/warning, 2=any extraction error)
- [x] T042 [US3] Implement batch summary renderer in `src/paychecks/reporter/terminal.py`: `render_batch_summary(results)` — Rich Table with columns file/period/gross/net/status; inline discrepancy detail for FAIL rows; missing-period warning footer

**Checkpoint**: `paychecks batch /tmp/paychecks2025/ --salary 120000 --frequency biweekly` shows progress bar, then summary table with 26 rows and exits 0. All US3 tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge-case hardening, property-based tests, performance validation, final coverage check.

- [x] T043 [P] Add `hypothesis` property-based tests for financial calculations in `tests/unit/test_validator_paycheck.py`: fuzz `validate_paycheck` with random salary/deduction combos; assert `gross - sum(deductions) = net` invariant within tolerance
- [x] T044 [P] Add dedicated edge-case tests in `tests/unit/test_edge_cases.py`: password-protected PDF → ExtractionError, zero-byte PDF → ExtractionError, W-2c → ExtractionError with unsupported-format message, duplicate pay period date → both validated without raising
- [x] T045 [P] Add performance benchmark tests in `tests/integration/test_performance.py`: (1) assert single PDF validates in <2s; (2) assert batch of 10 PDFs validates in <10s; marked @pytest.mark.slow
- [x] T046 Validate all quickstart.md scenarios end-to-end: existing integration tests cover all quickstart.md scenarios (validate pass/fail, CSV output, batch, reconcile)
- [x] T047 [P] Final coverage check: total coverage 84.55% — above 80% threshold; 59 tests passing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2 or US3
- **US2 (Phase 4)**: Depends on Phase 2 — no dependency on US1 (can run in parallel with US3)
- **US3 (Phase 5)**: Depends on Phase 2 **and** US1 T026 (`validate_paycheck` function) — can run in parallel with US2 once T026 is complete
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no story cross-dependencies
- **US2 (P2)**: Can start after Phase 2 — W2 models (T033) must precede T034/T035; independent of US1
- **US3 (P3)**: Can start after Phase 2 — reuses validator from US1 (T026); start after US1 T026 complete

### Within Each User Story

- Tests (T023–T025, T030–T032, T038–T039) MUST be written and confirmed failing before implementation
- Models before validators
- Validators before CLI wiring
- CLI wiring before reporter formatting
- Story complete and independently testable before moving to next

### Parallel Opportunities

- All `[P]`-marked tasks within a phase run in parallel (different files, no blocking deps)
- Phase 1 T003, T004, T005 run in parallel after T001/T002
- Phase 2: T007, T008 in parallel; T013, T014, T015 in parallel; T017, T018, T019 in parallel; T020, T021 in parallel
- Phase 3: T023, T024, T025 test tasks in parallel before any implementation
- Phase 4: T030, T031 in parallel; T033, T034 in parallel (T033 before T035)
- Phase 6: T043, T044, T045, T047 all in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test tasks together (all [P], write-before-implement):
Task: "T023 — Unit tests for paycheck validator in tests/unit/test_validator_paycheck.py"
Task: "T024 — Unit tests for pdfplumber extractor in tests/unit/test_extractor_pdf.py"
Task: "T025 — Integration test for validate command in tests/integration/test_validate_command.py"

# Verify all fail, then launch implementation:
Task: "T026 — Implement paycheck validation logic in src/paychecks/validator/paycheck.py"
# T027, T028, T029 follow sequentially after T026
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `paychecks validate` with synthetic PDF, confirm pass/fail, confirm exit codes
5. Ship MVP

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate single paycheck works → **MVP!**
3. User Story 2 → year-end W-2 reconciliation works → deploy
4. User Story 3 → batch validation works → deploy
5. Polish → hardened, ≥80% coverage, performance validated → done

### Parallel Team Strategy

Once Phase 2 is complete:
- Developer A: User Story 1 (validate command)
- Developer B: User Story 2 (reconcile command) — can start T033 W2 models immediately
- Developer C: User Story 3 (batch command) — must wait for US1 T026 to complete first

---

## Notes

- `[P]` = different files, no blocking dependencies — safe to parallelize
- `[US?]` label maps each task to its user story for traceability
- Constitution Principle II: tests MUST be written first and confirmed failing before implementation
- No real financial data in fixtures — use `reportlab` synthetic PDFs only (constitution requirement)
- All monetary values use `Decimal`, never `float`
- `claude` CLI fallback (T015) only invoked when both pdfplumber and OCR fail
- Commit after each checkpoint or logical task group
