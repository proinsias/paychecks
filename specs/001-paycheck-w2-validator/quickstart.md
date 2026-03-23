# Quickstart: Paycheck & W-2 Validator

**Branch**: `001-paycheck-w2-validator` | **Date**: 2026-03-22

Use this guide to verify the implementation is working end-to-end after each user story is complete.

---

## Prerequisites

- Python 3.12+
- `uv` installed (`pip install uv` or `brew install uv`)
- (Optional) Tesseract OCR installed for OCR fallback: `brew install tesseract` (macOS)
- (Optional) `claude` CLI installed and authenticated for final-fallback extraction

---

## Installation

```bash
# Clone and set up the project
git clone <repo-url>
cd paychecks

# Install with uv (creates virtualenv automatically)
uv pip install -e .

# Verify installation
paychecks --version
```

---

## Run the Test Suite

```bash
# All tests with coverage report
uv run pytest --cov=src/paychecks --cov-report=term-missing

# Unit tests only (fast — must complete in <30s)
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v
```

Expected: all tests pass, coverage ≥ 80% on core modules.

---

## User Story 1 — Validate a Single Paycheck (P1)

Generate a synthetic paycheck PDF and validate it:

```bash
# Generate a synthetic paycheck (uses the test fixture builder)
uv run python -c "
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder
PaycheckBuilder(
    annual_salary=120000,
    frequency='biweekly',
    period_start='2025-01-01',
    period_end='2025-01-15',
).save('/tmp/paycheck_test.pdf')
print('Created /tmp/paycheck_test.pdf')
"

# Validate it
paychecks validate /tmp/paycheck_test.pdf \
  --salary 120000 \
  --frequency biweekly
```

**Expected output**: All fields show ✅ PASS, exit code 0.

```bash
# Validate with a deliberate discrepancy (wrong salary)
paychecks validate /tmp/paycheck_test.pdf \
  --salary 100000 \
  --frequency biweekly
```

**Expected output**: Gross Pay shows ❌ FAIL with expected vs. actual values, exit code 1.

```bash
# Save report to CSV
paychecks validate /tmp/paycheck_test.pdf \
  --salary 120000 \
  --frequency biweekly \
  --output /tmp/report.csv

cat /tmp/report.csv
```

**Expected**: CSV file with headers `field,expected,actual,status,note`.

---

## User Story 2 — Year-End W-2 Reconciliation (P2)

```bash
# Generate a full year of synthetic paychecks + W-2
uv run python -c "
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder
from tests.fixtures.builders.w2_builder import W2Builder
import os

os.makedirs('/tmp/paychecks2025', exist_ok=True)
builder = PaycheckBuilder(annual_salary=120000, frequency='biweekly')
for i, pdf in enumerate(builder.build_year(2025)):
    pdf.save(f'/tmp/paychecks2025/paycheck_{i+1:02d}.pdf')

W2Builder(annual_salary=120000, tax_year=2025).save('/tmp/w2_2025.pdf')
print('Created 26 paychecks and W-2 in /tmp/')
"

# Run reconciliation
paychecks reconcile /tmp/paychecks2025/ /tmp/w2_2025.pdf \
  --salary 120000 \
  --frequency biweekly
```

**Expected output**: All 8 W-2 fields show ✅ PASS, 0 missing periods, exit code 0.

```bash
# Test mismatch detection (W-2 with wrong federal tax)
uv run python -c "
from tests.fixtures.builders.w2_builder import W2Builder
W2Builder(annual_salary=120000, tax_year=2025, federal_tax_override=99999).save('/tmp/w2_mismatch.pdf')
"

paychecks reconcile /tmp/paychecks2025/ /tmp/w2_mismatch.pdf \
  --salary 120000 \
  --frequency biweekly
```

**Expected output**: Box 2 shows ❌ FAIL with paycheck total vs. W-2 value and difference, exit code 1.

---

## User Story 3 — Batch Validation (P3)

```bash
# Batch validate all paychecks in the folder
paychecks batch /tmp/paychecks2025/ \
  --salary 120000 \
  --frequency biweekly
```

**Expected output**: Summary table with 26 rows all ✅ PASS, progress bar shown during processing, exit code 0.

```bash
# Test with a corrupted PDF in the batch
cp /tmp/paycheck_test.pdf /tmp/paychecks2025/bad.pdf
echo "not a pdf" > /tmp/paychecks2025/bad.pdf

paychecks batch /tmp/paychecks2025/ \
  --salary 120000 \
  --frequency biweekly
```

**Expected**: `bad.pdf` shown with ❌ ERROR and actionable message on stderr, other paychecks still processed, exit code 2.

---

## Mid-Year Salary Change

```bash
paychecks validate /tmp/paycheck_after_raise.pdf \
  --salary 100000 \
  --frequency biweekly \
  --salary-change 2025-07-01:120000
```

**Expected**: Gross pay validated against $120,000 salary if pay period starts on or after 2025-07-01.

---

## Performance Check

```bash
# Time the full 52-paycheck reconciliation
time paychecks reconcile /tmp/paychecks2025/ /tmp/w2_2025.pdf \
  --salary 120000 \
  --frequency biweekly
```

**Expected**: Completes in under 10 seconds (constitution Principle IV).

```bash
# Single paycheck
time paychecks validate /tmp/paycheck_test.pdf --salary 120000 --frequency biweekly
```

**Expected**: Completes in under 2 seconds (constitution Principle IV).
