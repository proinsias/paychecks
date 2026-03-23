# Research: Paycheck & W-2 Validator

**Branch**: `001-paycheck-w2-validator` | **Date**: 2026-03-22

## PDF Extraction Library

**Decision**: `pdfplumber` as primary extractor; `pytesseract` + `pdf2image` as secondary fallback; `claude` CLI as final fallback.

**Rationale**:
- `pdfplumber` excels at structured text extraction from digital PDFs — it preserves layout and can extract text by region/bounding box, which is critical for paycheck PDFs where fields appear in fixed positions or tables.
- Most US payroll system PDFs (ADP, Gusto, Paychex, Workday) are digital (not scanned), so pdfplumber handles them without OCR.
- `pytesseract` + `pdf2image` handles scanned or image-based PDFs by converting pages to images and applying Tesseract OCR.
- `claude` CLI is reserved for cases where both pdfplumber and pytesseract fail to extract required fields — it can interpret free-form paycheck layouts using vision capabilities.

**Alternatives considered**:
- `pymupdf` (PyMuPDF / fitz): Faster, but AGPL licensed — acceptable for personal tool but noted.
- `pypdf`: Too basic; poor table/layout support for structured paycheck data.
- `pdfminer.six`: What pdfplumber builds on; lower-level API with no real advantage here.

**Extraction cascade**:
1. Attempt pdfplumber text extraction → if all required fields found, stop.
2. If any required field missing → attempt pytesseract OCR on page images.
3. If still missing → invoke `claude` CLI with extracted text + page image as context.
4. If still missing → report extraction failure with specific field name, filename, page.

## CLI Framework

**Decision**: `Typer`

**Rationale**: Type-hint based API produces clean subcommand CLIs with automatic `--help` generation and validation. Subcommands (`validate`, `reconcile`, `batch`) map naturally to Typer `app.command()` decorators. Installed via uv with no transitive dependency concerns.

**Alternatives considered**:
- `argparse`: stdlib, no extra deps, but verbose for nested subcommands.
- `Click`: Mature but decorator-heavy; Typer wraps Click and is cleaner for typed Python.

## Terminal Output / TUI

**Decision**: `Rich`

**Rationale**: Rich is the standard Python library for structured terminal output. Provides `Table`, `Progress`, `Panel`, and color/style primitives needed for: side-by-side validation tables, batch summary tables, progress bars during PDF processing, and colored Pass/Fail/Warning status badges.

**Alternatives considered**:
- `tabulate`: Only tables, no progress or styling.
- `curses`: Full TUI but massive overkill for a reporting CLI.

## Testing Strategy

**Decision**: `pytest` + `pytest-cov` + `hypothesis`

**Rationale**:
- `pytest` is the standard; fixtures for synthetic PDF data, parametrize for edge cases.
- `pytest-cov` enforces ≥80% line coverage per the constitution.
- `hypothesis` for property-based tests on financial calculations (e.g., gross - deductions = net within tolerance, regardless of randomly generated values).
- Synthetic test PDFs generated programmatically (using `reportlab`) so no real financial data is committed (constitution requirement).

## Dependency Management

**Decision**: `uv` with `pyproject.toml`

**Rationale**: User-specified. uv provides fast installs, lockfile management, and `uv run` for isolated execution. Project installed as editable package (`uv pip install -e .`) with `[project.scripts]` entry point for the `paychecks` CLI command.

## Python Version

**Decision**: Python 3.12

**Rationale**: Current stable release. Pattern matching (`match`/`case`) available for clean extraction result handling. Full type hint support. uv supports it natively.

## Claude CLI Integration

**Decision**: Subprocess call to `claude` CLI with structured prompt.

**Rationale**: The `claude` CLI is available in the user's environment. When invoked as fallback, the extractor will:
1. Serialize extracted text from pdfplumber as context.
2. Construct a structured prompt requesting specific field values in JSON format.
3. Call `subprocess.run(["claude", "-p", prompt], capture_output=True)` with a timeout.
4. Parse JSON response; if parsing fails, treat as extraction failure.

**Constraint**: Claude CLI fallback MUST only be invoked when primary and secondary extraction both fail. It MUST NOT be used as the primary path (performance: 2s/PDF would be violated).

## Financial Calculation Rules

**Gross pay validation**:
- `expected_gross = annual_salary / pay_periods_per_year`
- Tolerance: ±$0.02 (configurable)
- Mid-year salary change: split year at effective date; each period uses applicable salary.

**Net pay validation**:
- `expected_net = gross_pay - sum(all_itemized_deductions)`
- Tolerance: ±$0.02 (configurable)

**W-2 reconciliation**:
- Sum all paycheck values per field across the year.
- Compare each sum to corresponding W-2 box.
- Tolerance: ±$1.00 (configurable, accounts for year-end rounding by payroll processors).

**Supplemental pay**:
- If `gross_pay > expected_gross + tolerance` → emit Warning (not Fail).
- Excess amount shown as "possible supplemental pay" in report.

**Missing period detection**:
- Derive expected pay dates from declared frequency and date range of provided PDFs.
- Report any expected dates with no matching paycheck PDF.
