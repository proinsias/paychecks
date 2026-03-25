# paychecks

A command-line tool that validates paycheck PDFs against your salary and reconciles a full year of paychecks with your W-2.

## What it does

- **Validates** individual paycheck PDFs — extracts gross pay, deductions, and tax withholdings, then checks them against your expected salary and pay frequency
- **Reconciles** a year's worth of paycheck PDFs against your W-2 to confirm the totals match
- **Batch-validates** an entire folder of paychecks in one command
- Supports mid-year salary changes
- Exports reports to `.csv` or `.txt`

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management (`pip install uv` or `brew install uv`)
- (Optional) [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for scanned/image-based PDFs (`brew install tesseract` on macOS)
- (Optional) [`claude` CLI](https://github.com/anthropics/claude-code) installed and authenticated — used as a last-resort fallback for difficult PDFs

## Installation

```bash
git clone https://github.com/proinsias/paychecks.git
cd paychecks
uv pip install -e .
```

Verify:

```bash
paychecks --help
```

## Try it with the included examples

The `examples/` directory contains 26 synthetic bi-weekly paycheck PDFs for a $95,000 salary (tax year 2025) plus a matching W-2. Use these to explore all three commands without needing your own PDFs.

```bash
# Validate a single paycheck
paychecks validate examples/paycheck_01_2025-01-01.pdf \
  --salary 95000 \
  --frequency biweekly

# Reconcile the full year against the W-2
paychecks reconcile examples/ examples/w2_2025.pdf \
  --salary 95000 \
  --frequency biweekly

# Batch-validate all 26 paychecks at once
paychecks batch examples/ \
  --salary 95000 \
  --frequency biweekly
```

All three commands should exit 0 and show all fields as ✅ PASS.

## Usage

### Validate a single paycheck

```bash
paychecks validate paycheck_jan.pdf \
  --salary 120000 \
  --frequency biweekly
```

Supported frequencies: `weekly`, `biweekly`, `semimonthly`, `monthly`.

**With a mid-year raise:**

```bash
paychecks validate paycheck_aug.pdf \
  --salary 100000 \
  --frequency biweekly \
  --salary-change 2025-07-01:120000
```

**Save the report:**

```bash
paychecks validate paycheck_jan.pdf \
  --salary 120000 \
  --frequency biweekly \
  --output report.csv       # or report.txt
```

### Reconcile paychecks against your W-2

```bash
paychecks reconcile ./paychecks_2025/ w2_2025.pdf \
  --salary 120000 \
  --frequency biweekly
```

The directory should contain all paycheck PDFs for the year. The W-2 PDF is passed separately.

### Batch-validate a folder

```bash
paychecks batch ./paychecks_2025/ \
  --salary 120000 \
  --frequency biweekly
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more fields failed or produced warnings |
| `2` | Extraction error (unreadable PDF or no files found) |

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run all tests with coverage
uv run pytest --cov=src/paychecks --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit/ -v

# Lint and format check
uv run ruff check .
uv run ruff format --check .
```

## Project structure

```
src/paychecks/
  cli.py              # Typer CLI entry point (validate, reconcile, batch)
  extractor/          # PDF text extraction (pdfplumber → OCR → Claude fallback)
  validator/          # Paycheck and W-2 validation logic
  reporter/           # Terminal output, CSV and text export
  models/             # Data models (Paycheck, W2, SalarySchedule, results)
tests/
  unit/
  integration/
  fixtures/
```

---

## How this project was built — spec-kit

This project was generated using [spec-kit](https://github.com/github/spec-kit), a workflow for AI-assisted software development that works by building structured specification artifacts before writing any code.

The process follows these steps:

1. **Constitution** — defines governing principles (code quality, testing standards, performance requirements) that all subsequent development must follow
2. **Specify** — a natural-language description of what the tool should do is turned into a formal feature spec (`specs/001-paycheck-w2-validator/spec.md`)
3. **Clarify** — underspecified areas are identified and resolved before planning begins
4. **Plan** — the spec is turned into a concrete implementation plan with tech-stack decisions (`plan.md`)
5. **Tasks** — the plan is broken into a dependency-ordered task list (`tasks.md`)
6. **Analyze** — cross-artifact consistency check ensures the spec, plan, and tasks are aligned
7. **Implement** — all tasks are executed to produce the working implementation

### Regenerating or extending the project

Install spec-kit and initialize it:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify init . --ai claude
specify check
```

Then in `claude`:

```text
# Create or update the project's governing principles
/speckit.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements

# Describe a new feature to build
/speckit.specify Build an application that can: (i) extract paycheck data from pdfs and validate the calculations based on the annual salary, (ii) compare paycheck data from a year's worth of pdfs with the W2 at the end of year and ensure the W2 calculations match the paycheck data.

# Clarify underspecified areas (recommended before /speckit.plan)
/speckit.clarify

# Provide tech stack and architecture choices
/speckit.plan The application uses a python TUI module with pytest tests. Use python OCR libraries to extract information from pdfs. Only if necessary, call out to the `claude` CLI command to extract information from pdfs. Use `uv` for project dependency management.

# Create an actionable task list from the implementation plan
/speckit.tasks

# Cross-artifact consistency and coverage analysis
/speckit.analyze

# Execute all tasks and build the feature
/speckit.implement

# Generate quality checklists that validate requirements completeness
/speckit.checklist
```
