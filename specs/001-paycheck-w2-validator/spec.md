# Feature Specification: Paycheck & W-2 Validator

**Feature Branch**: `001-paycheck-w2-validator`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "Build an application that can: (i) extract paycheck data
from pdfs and validate the calculations based on the annual salary, (ii) compare paycheck
data from a year's worth of pdfs with the W2 at the end of year and ensure the W2
calculations match the paycheck data."

## Clarifications

### Session 2026-03-22

- Q: What is the interaction modality of the application? → A: Command-line interface (CLI) — arguments in, formatted report out to terminal.
- Q: What is the report output format? → A: Terminal output by default; optional `--output <file>` flag saves report to plain text or CSV.
- Q: How is pay frequency determined? → A: User declares it as a required CLI argument (e.g., `--frequency biweekly`); no auto-detection.
- Q: Is parsed paycheck data persisted between runs? → A: Stateless — user provides PDF paths on every run; no data is persisted between sessions.
- Q: Is Form W-2c (corrected W-2) supported? → A: Out of scope — W-2c not supported; CLI must print a clear unsupported-format message if a W-2c is detected.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate a Single Paycheck PDF (Priority: P1)

A user has received a paycheck PDF and wants to confirm that the calculations on it are
internally consistent with their known annual salary. They run a CLI command providing the
PDF path and their annual salary; the application prints a report to the terminal showing
whether gross pay, net pay, tax withholdings, and deductions are mathematically correct
for the pay period.

**Why this priority**: This is the foundational value of the tool — giving users confidence
that each individual paycheck is accurate before doing any year-end aggregation.

**Independent Test**: Load a single paycheck PDF with a known annual salary. Verify the
application correctly identifies whether gross pay matches the salary divided by the number
of pay periods, and whether net pay equals gross pay minus all deductions. Can be run
without any W-2 data.

**Acceptance Scenarios**:

1. **Given** a valid paycheck PDF and correct annual salary, **When** the user runs the
   validate command, **Then** the CLI prints a pass/fail result for each calculation
   (gross pay, net pay, federal tax, state tax, other deductions) with expected and
   actual values shown side-by-side in the terminal.
2. **Given** a paycheck PDF where net pay does not equal gross pay minus deductions,
   **When** the user validates it, **Then** the application flags the specific discrepancy
   with the calculated vs. stated amounts.
3. **Given** a malformed or unreadable PDF, **When** the user submits it, **Then** the
   application shows a clear error message identifying which field(s) could not be extracted
   and suggests corrective action (e.g., "Gross pay field not found on page 1 — check PDF
   version or format").

---

### User Story 2 - Year-End W-2 Reconciliation (Priority: P2)

A user has accumulated paycheck PDFs throughout the year and has received their W-2. They
run a CLI command providing a directory of paycheck PDFs and the W-2 PDF path; the
application aggregates the paycheck data, compares it against the W-2 totals, and prints
a reconciliation report to the terminal confirming whether wages, federal withholding,
Social Security, Medicare, and state taxes all match.

**Why this priority**: This is the primary year-end use case. Discrepancies between
paychecks and the W-2 can affect tax filings and require correction before submission.

**Independent Test**: Provide a set of paycheck PDFs whose aggregated totals are known, plus
a matching (or intentionally mismatched) W-2. Verify the application correctly reports
matches and flags discrepancies for each W-2 box independently.

**Acceptance Scenarios**:

1. **Given** a full set of paycheck PDFs for the year and a matching W-2, **When** the
   user runs the comparison, **Then** the application shows a line-by-line reconciliation
   report confirming each W-2 field matches the aggregated paycheck data.
2. **Given** paycheck PDFs whose aggregated federal withholding differs from W-2 Box 2,
   **When** the user runs the comparison, **Then** the application highlights the mismatch
   with the summed paycheck value, the W-2 value, and the difference.
3. **Given** an incomplete year of paychecks (some PDFs missing), **When** the user runs
   the comparison, **Then** the application warns that the paycheck set may be incomplete
   and shows which pay periods appear to be missing.

---

### User Story 3 - Batch Validation of Full-Year Paychecks (Priority: P3)

A user wants to validate all paychecks for the year at once before starting the W-2
reconciliation. They run a CLI command pointing to a folder of paycheck PDFs; the
application validates each one against the annual salary and prints a summary table to
the terminal showing which paychecks passed and which have issues.

**Why this priority**: Catching individual paycheck errors before year-end makes
reconciliation cleaner and helps users identify payroll problems earlier.

**Independent Test**: Load a folder of 26 paycheck PDFs (bi-weekly cadence). Verify that
the application processes each one and produces a summary with pass/fail per paycheck,
without requiring W-2 data.

**Acceptance Scenarios**:

1. **Given** a folder of paycheck PDFs and an annual salary, **When** the user requests
   batch validation, **Then** the application processes all PDFs and shows a summary table
   with one row per paycheck (date, gross pay, net pay, status: Pass/Fail/Warning).
2. **Given** a batch where some paychecks have calculation errors, **When** the batch
   completes, **Then** the summary highlights the failing paychecks with the specific
   discrepancy for each.

---

### Edge Cases

- What happens when a PDF is password-protected or encrypted?
- How does the system handle a mid-year salary change when gross pay amounts shift partway
  through the year?
- What happens when supplemental pay (bonus, commission) appears on a paycheck and causes
  gross pay to exceed the prorated salary amount?
- What if the W-2 covers a partial year (user started employment mid-year)?
- What happens when a pay period spans two calendar years (e.g., Dec 28 – Jan 10)?
- How does the system behave when two paychecks share the same pay period date?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extract the following fields from paycheck PDFs: pay period
  start date, pay period end date, gross pay, federal income tax withheld, Social Security
  tax withheld, Medicare tax withheld, state income tax withheld, other named deductions,
  and net pay.
- **FR-002**: The system MUST validate that gross pay equals annual salary divided by the
  number of pay periods, within a configurable tolerance (default ±$0.02 for rounding).
- **FR-003**: The system MUST validate that net pay equals gross pay minus all itemized
  deductions within a configurable tolerance (default ±$0.02).
- **FR-004**: The system MUST extract the following fields from standard IRS Form W-2 PDFs
  (Form W-2c is explicitly not supported — see Assumptions): Box 1 (wages),
  Box 2 (federal tax withheld), Box 3 (Social Security wages), Box 4 (Social Security tax
  withheld), Box 5 (Medicare wages), Box 6 (Medicare tax withheld), Box 16 (state wages),
  Box 17 (state income tax withheld).
- **FR-005**: The system MUST compare each W-2 field against the aggregated paycheck total
  for the corresponding value and report any difference exceeding a configurable tolerance
  (default ±$1.00 for year-end rounding).
- **FR-006**: The system MUST support the following pay frequencies, declared by the user
  via a required `--frequency` CLI argument: `weekly` (52 periods), `biweekly` (26),
  `semimonthly` (24), and `monthly` (12). The system MUST NOT attempt to auto-detect
  frequency from PDF dates.
- **FR-007**: The system MUST produce a structured validation report per paycheck showing
  expected vs. actual values and a pass/fail/warning status for each validated field.
- **FR-008**: The system MUST produce a year-end reconciliation report showing aggregated
  paycheck totals vs. W-2 values for each tracked field, with difference amounts.
- **FR-009**: The system MUST detect and report missing pay periods based on the detected
  pay frequency and the date range covered by the provided paycheck PDFs.
- **FR-010**: The system MUST support mid-year salary changes when the user provides the
  effective date and new annual salary amount; paychecks after the effective date are
  validated against the new salary.
- **FR-011**: The system MUST provide clear, actionable error messages when a PDF field
  cannot be extracted, including the filename, page number, and field name.
- **FR-012**: The system MUST expose all functionality through a CLI with named subcommands
  (e.g., `validate`, `reconcile`, `batch`); all reports MUST be printed to stdout; errors
  and warnings MUST be printed to stderr; the CLI MUST exit with a non-zero code on
  validation failures or extraction errors.
- **FR-013**: All CLI subcommands MUST accept an optional `--output <file>` flag; when
  provided, the report MUST be saved to the specified file path in either plain text
  (`.txt`) or CSV (`.csv`) format, inferred from the file extension; terminal output
  is always produced regardless of whether `--output` is specified.

### Key Entities

- **Paycheck**: A single pay period record — pay dates, earnings breakdown, deductions, net
  pay, and employer identifier.
- **PaycheckValidationResult**: The outcome of validating one paycheck — per-field expected
  vs. actual values and pass/fail/warning statuses.
- **W2**: The annual IRS tax form — employer, employee, and box values for wages, taxes, and
  contributions.
- **ReconciliationReport**: Year-end comparison of aggregated paycheck totals vs. W-2 box
  values, including per-field match status and difference amounts.
- **SalarySchedule**: Annual salary configuration — base salary, pay frequency, and optional
  mid-year change events with effective dates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can validate a single paycheck PDF and receive a complete pass/fail
  report in under 2 seconds.
- **SC-002**: A user can complete a full year-end W-2 reconciliation of up to 52 paycheck
  PDFs plus one W-2 PDF in under 10 seconds.
- **SC-003**: The application correctly identifies calculation discrepancies of $0.02 or
  greater on individual paychecks.
- **SC-004**: The application correctly identifies W-2 mismatches of $1.00 or greater
  against aggregated paycheck data.
- **SC-005**: 90% or more of standard paycheck PDF formats from common US payroll processors
  are parsed successfully without manual field mapping.
- **SC-006**: 100% of field extraction failures produce an error message that identifies
  the specific PDF filename, page number, and unextracted field name.
- **SC-007**: The application detects missing pay periods with 100% accuracy for regular
  pay schedules (weekly, bi-weekly, semi-monthly, monthly).

## Assumptions

- Paycheck PDFs are US-based and use USD currency.
- Pay frequency is always user-declared via CLI argument; the application does not attempt
  to infer it. Irregular or off-cycle paychecks may appear in batches but do not affect
  the declared frequency used for validation.
- The W-2 is provided as a PDF in the standard IRS Form W-2 layout.
- Users know their annual salary and can enter multiple values for mid-year changes.
- The application is a stateless CLI tool that runs locally — no paycheck or W-2 data
  is persisted between runs, cached, or transmitted outside the user's machine. The PDF
  files themselves are always the source of truth.
- Multi-employer scenarios (multiple W-2s from different employers) are out of scope for
  this feature iteration.
- Form W-2c (corrected W-2) is out of scope; if a W-2c is detected, the CLI MUST exit
  with a clear unsupported-format error rather than attempting to parse it.
- Supplemental pay (bonuses, commissions) on a paycheck is flagged with a warning but does
  not cause the paycheck to fail validation, since gross pay will legitimately exceed the
  prorated salary.
