# Data Model: Paycheck & W-2 Validator

**Branch**: `001-paycheck-w2-validator` | **Date**: 2026-03-22

All models are Python dataclasses (immutable where possible). No persistence layer —
all instances are created at runtime from PDF extraction and discarded after reporting.

---

## Paycheck

Represents a single pay period extracted from a paycheck PDF.

```python
@dataclass(frozen=True)
class Paycheck:
    source_file: Path                    # Absolute path to the source PDF
    pay_period_start: date               # ISO 8601
    pay_period_end: date                 # ISO 8601
    gross_pay: Decimal                   # USD, 2 decimal places
    federal_tax_withheld: Decimal        # Box 2 equivalent on paycheck
    social_security_tax_withheld: Decimal
    medicare_tax_withheld: Decimal
    state_tax_withheld: Decimal
    other_deductions: list[Deduction]    # Named additional deductions
    net_pay: Decimal                     # USD, 2 decimal places
    extraction_method: ExtractionMethod  # pdfplumber | ocr | claude_cli
```

**Validation rules**:
- `pay_period_start` MUST be before `pay_period_end`
- All monetary fields MUST be ≥ 0
- `gross_pay` MUST be > 0
- `net_pay` MUST be > 0 and ≤ `gross_pay`

---

## Deduction

A named pre-tax or post-tax deduction line item on a paycheck.

```python
@dataclass(frozen=True)
class Deduction:
    name: str       # e.g., "401(k)", "Health Insurance", "Dental"
    amount: Decimal # USD, always positive (subtracted from gross)
```

---

## ExtractionMethod (enum)

```python
class ExtractionMethod(enum.Enum):
    PDFPLUMBER = "pdfplumber"
    OCR        = "ocr"
    CLAUDE_CLI = "claude_cli"
```

---

## FieldResult

The outcome of extracting or validating a single named field.

```python
class ValidationStatus(enum.Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    WARNING = "WARNING"  # e.g., supplemental pay detected

@dataclass(frozen=True)
class FieldResult:
    field_name: str
    expected: Decimal | None
    actual: Decimal | None
    status: ValidationStatus
    note: str | None  # Human-readable explanation for FAIL or WARNING
```

---

## PaycheckValidationResult

The complete validation outcome for a single paycheck.

```python
@dataclass(frozen=True)
class PaycheckValidationResult:
    paycheck: Paycheck
    salary_used: Decimal          # Annual salary applied to this period
    pay_periods_per_year: int     # 52 | 26 | 24 | 12
    field_results: list[FieldResult]
    overall_status: ValidationStatus  # Worst status across all field_results

    # Derived
    @property
    def passed(self) -> bool:
        return self.overall_status == ValidationStatus.PASS
```

**Validated fields** (one `FieldResult` per):
- `gross_pay` — expected = `salary_used / pay_periods_per_year`
- `net_pay` — expected = `gross_pay - sum(deductions)`
- `federal_tax_withheld` — validated for presence only (no expected calculation)
- `social_security_tax_withheld` — validated for presence
- `medicare_tax_withheld` — validated for presence
- `state_tax_withheld` — validated for presence

---

## W2

Fields extracted from a standard IRS Form W-2 PDF.

```python
@dataclass(frozen=True)
class W2:
    source_file: Path
    tax_year: int
    box1_wages: Decimal                    # Wages, tips, other compensation
    box2_federal_tax_withheld: Decimal     # Federal income tax withheld
    box3_social_security_wages: Decimal
    box4_social_security_tax: Decimal
    box5_medicare_wages: Decimal
    box6_medicare_tax: Decimal
    box16_state_wages: Decimal
    box17_state_tax: Decimal
    extraction_method: ExtractionMethod
```

**Validation rules**:
- All box values MUST be ≥ 0
- `box1_wages` MUST be > 0

---

## ReconciliationField

One line in the W-2 reconciliation report.

```python
@dataclass(frozen=True)
class ReconciliationField:
    field_name: str        # e.g., "Box 1 — Wages"
    w2_value: Decimal
    paycheck_total: Decimal
    difference: Decimal    # paycheck_total - w2_value
    status: ValidationStatus
    tolerance: Decimal     # Threshold used (default $1.00)
```

---

## ReconciliationReport

Year-end comparison of aggregated paycheck totals vs. W-2.

```python
@dataclass(frozen=True)
class ReconciliationReport:
    w2: W2
    paychecks: list[Paycheck]
    fields: list[ReconciliationField]
    missing_periods: list[date]         # Expected pay dates with no matching paycheck
    overall_status: ValidationStatus    # Worst status across all fields
    pay_periods_per_year: int
    salary_schedule: SalarySchedule
```

---

## SalarySchedule

Encodes annual salary with optional mid-year changes.

```python
@dataclass(frozen=True)
class SalaryChange:
    effective_date: date
    annual_salary: Decimal

@dataclass(frozen=True)
class SalarySchedule:
    base_annual_salary: Decimal       # Salary from Jan 1 (or employment start)
    frequency: PayFrequency
    changes: list[SalaryChange]       # Sorted ascending by effective_date

    def salary_for_period(self, period_start: date) -> Decimal:
        """Return the applicable annual salary for a given pay period start date."""
        ...
```

---

## PayFrequency (enum)

```python
class PayFrequency(enum.Enum):
    WEEKLY       = 52
    BIWEEKLY     = 26
    SEMIMONTHLY  = 24
    MONTHLY      = 12

    @property
    def periods_per_year(self) -> int:
        return self.value
```

---

## ExtractionError

Raised (or returned) when a required field cannot be extracted from a PDF.

```python
@dataclass(frozen=True)
class ExtractionError:
    source_file: Path
    page_number: int | None
    field_name: str
    message: str   # Human-readable, actionable
```

---

## Relationships

```
SalarySchedule ──── SalaryChange (0..*)
Paycheck ──────────── Deduction (0..*)
Paycheck ──────────── ExtractionMethod
PaycheckValidationResult ── Paycheck (1)
PaycheckValidationResult ── FieldResult (1..*)
W2 ─────────────────── ExtractionMethod
ReconciliationReport ── W2 (1)
ReconciliationReport ── Paycheck (1..*)
ReconciliationReport ── ReconciliationField (1..*)
ReconciliationReport ── SalarySchedule (1)
```

---

## Constants (src/paychecks/constants.py)

```python
DEFAULT_PAYCHECK_TOLERANCE = Decimal("0.02")   # ±$0.02 for per-paycheck validation
DEFAULT_W2_TOLERANCE       = Decimal("1.00")   # ±$1.00 for W-2 reconciliation
CURRENCY_SYMBOL            = "$"
DATE_FORMAT                = "%Y-%m-%d"        # ISO 8601
CLAUDE_CLI_TIMEOUT_SECONDS = 30
```
