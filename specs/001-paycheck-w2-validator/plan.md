# Implementation Plan: Paycheck & W-2 Validator

**Branch**: `001-paycheck-w2-validator` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-paycheck-w2-validator/spec.md`

## Summary

A stateless Python CLI tool that extracts financial data from paycheck PDFs using
`pdfplumber` (primary), `pytesseract` (secondary), and the `claude` CLI (final fallback),
validates per-paycheck calculations against a user-declared annual salary, and performs
year-end reconciliation of aggregated paycheck data against a W-2 PDF. Output is formatted
with `Rich` to the terminal; reports can optionally be saved as plain text or CSV.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Typer (CLI), Rich (terminal output), pdfplumber (PDF extraction),
pytesseract + pdf2image (OCR fallback), reportlab (synthetic test PDFs), hypothesis (property tests)
**Storage**: N/A — stateless; no data persisted between runs
**Testing**: pytest + pytest-cov (≥80% coverage) + hypothesis
**Target Platform**: macOS / Linux (local desktop, personal use)
**Project Type**: CLI tool
**Performance Goals**: <2s per PDF parse; <10s for 52-PDF batch + W-2 reconciliation; <3s startup
**Constraints**: <200MB peak memory; stateless; no network calls; `claude` CLI only as last-resort fallback
**Scale/Scope**: Personal use; up to 52 paycheck PDFs + 1 W-2 per year

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Code Quality | All constants named; single-responsibility functions; ruff linting configured | ✅ PASS |
| II. Testing Standards | pytest + pytest-cov; TDD order enforced in tasks; synthetic fixtures only (reportlab); ≥80% coverage target | ✅ PASS |
| III. UX Consistency | Rich used for all output; ISO 8601 dates; $X.XX currency; actionable error messages with filename/page/field | ✅ PASS |
| IV. Performance | pdfplumber is fast (<2s typical); claude CLI only as fallback (not primary path); Rich progress bar for batch | ✅ PASS |

No violations. Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-paycheck-w2-validator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-schema.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pyproject.toml           # uv project config + entry point
src/
└── paychecks/
    ├── __init__.py
    ├── cli.py                  # Typer app; validate / reconcile / batch subcommands
    ├── constants.py            # Named constants (tolerances, pay period counts, field names)
    ├── models/
    │   ├── __init__.py
    │   ├── paycheck.py         # Paycheck, PaycheckValidationResult dataclasses
    │   ├── w2.py               # W2, ReconciliationReport dataclasses
    │   └── salary.py           # SalarySchedule, SalaryChange dataclasses
    ├── extractor/
    │   ├── __init__.py
    │   ├── pdf.py              # pdfplumber extraction (primary)
    │   ├── ocr.py              # pytesseract + pdf2image fallback
    │   └── claude_fallback.py  # claude CLI subprocess fallback
    ├── validator/
    │   ├── __init__.py
    │   ├── paycheck.py         # Per-paycheck calculation validation
    │   └── w2.py               # Aggregation + W-2 reconciliation logic
    └── reporter/
        ├── __init__.py
        ├── terminal.py         # Rich-based terminal output
        ├── text_export.py      # Plain text file export
        └── csv_export.py       # CSV file export

tests/
├── conftest.py                 # Shared fixtures (synthetic PDF builders via reportlab)
├── unit/
│   ├── test_models.py
│   ├── test_extractor_pdf.py
│   ├── test_extractor_ocr.py
│   ├── test_validator_paycheck.py
│   ├── test_validator_w2.py
│   └── test_reporter.py
├── integration/
│   ├── test_validate_command.py   # US1: single paycheck validate
│   ├── test_reconcile_command.py  # US2: year-end W-2 reconcile
│   └── test_batch_command.py      # US3: batch folder validation
└── fixtures/
    └── builders/
        ├── paycheck_builder.py    # reportlab paycheck PDF factory
        └── w2_builder.py          # reportlab W-2 PDF factory
```

**Structure Decision**: Single Python package under `src/` layout, managed by uv. The
`paychecks` entry point is declared in `pyproject.toml` and installed with `uv pip install -e .`.
Modules are separated by concern: extraction, validation, reporting. No shared state between
modules — all functions are pure or accept explicit inputs.

## Complexity Tracking

> No violations — table not required.
