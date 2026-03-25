from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from paychecks.constants import DEFAULT_PAYCHECK_TOLERANCE
from paychecks.models import (
    FieldResult,
    Paycheck,
    PaycheckValidationResult,
    SalarySchedule,
    ValidationStatus,
)


def validate_paycheck(
    paycheck: Paycheck,
    salary_schedule: SalarySchedule,
    tolerance: Decimal = DEFAULT_PAYCHECK_TOLERANCE,
) -> PaycheckValidationResult:
    """Validate a single paycheck against the salary schedule."""
    periods = salary_schedule.frequency.periods_per_year
    salary = salary_schedule.salary_for_period(paycheck.pay_period_start)
    expected_gross = (salary / periods).quantize(Decimal("0.01"))

    results: list[FieldResult] = []

    # --- Gross pay ---
    diff = abs(paycheck.gross_pay - expected_gross)
    # Supplemental pay threshold: gross must exceed expected by more than 110% (i.e.,
    # more than 2.1x the expected amount) to be classified as WARNING (likely a bonus
    # or supplemental pay). Overages at or below this ratio are FAIL (wrong salary).
    _supplemental_threshold = expected_gross * Decimal("2.1")
    if diff <= tolerance:
        status = ValidationStatus.PASS
        note = None
    elif paycheck.gross_pay > _supplemental_threshold:
        # Supplemental pay: gross greatly exceeds expected — warning, not fail
        status = ValidationStatus.WARNING
        note = (
            f"Gross ${paycheck.gross_pay:,.2f} exceeds expected "
            f"${expected_gross:,.2f} — possible supplemental pay"
        )
    else:
        status = ValidationStatus.FAIL
        note = (
            f"Expected ${expected_gross:,.2f}, got ${paycheck.gross_pay:,.2f} (diff: ${diff:,.2f})"
        )
    results.append(FieldResult("gross_pay", expected_gross, paycheck.gross_pay, status, note))

    # --- Net pay ---
    all_deductions = (
        paycheck.federal_tax_withheld
        + paycheck.social_security_tax_withheld
        + paycheck.medicare_tax_withheld
        + paycheck.state_tax_withheld
        + sum(d.amount for d in paycheck.other_deductions)
    )
    expected_net = (paycheck.gross_pay - all_deductions).quantize(Decimal("0.01"))
    net_diff = abs(paycheck.net_pay - expected_net)
    net_status = ValidationStatus.PASS if net_diff <= tolerance else ValidationStatus.FAIL
    net_note = (
        None
        if net_status == ValidationStatus.PASS
        else f"Expected ${expected_net:,.2f}, got ${paycheck.net_pay:,.2f} (diff: ${net_diff:,.2f})"
    )
    results.append(FieldResult("net_pay", expected_net, paycheck.net_pay, net_status, net_note))

    # --- Tax fields (presence only — no expected calculation) ---
    for field_name, value in [
        ("federal_tax_withheld", paycheck.federal_tax_withheld),
        ("social_security_tax_withheld", paycheck.social_security_tax_withheld),
        ("medicare_tax_withheld", paycheck.medicare_tax_withheld),
        ("state_tax_withheld", paycheck.state_tax_withheld),
    ]:
        s = ValidationStatus.PASS if value >= Decimal("0") else ValidationStatus.FAIL
        results.append(FieldResult(field_name, None, value, s))

    return PaycheckValidationResult(
        paycheck=paycheck,
        salary_used=salary,
        pay_periods_per_year=periods,
        field_results=tuple(results),
    )


def validate_batch(
    paths: list[Path],
    salary_schedule: SalarySchedule,
    tolerance: Decimal = DEFAULT_PAYCHECK_TOLERANCE,
) -> list[PaycheckValidationResult]:
    """Validate all paychecks in a list. Extraction errors are skipped with stderr output."""
    import sys

    from paychecks.extractor import extract
    from paychecks.models import ExtractionError

    results = []
    for path in paths:
        extracted = extract(path)
        if isinstance(extracted, ExtractionError):
            print(
                f"Error: {extracted.message}",
                file=sys.stderr,
            )
            continue
        results.append(validate_paycheck(extracted, salary_schedule, tolerance))
    return results
