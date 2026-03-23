from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal

from paychecks.constants import DEFAULT_W2_TOLERANCE
from paychecks.models import Paycheck, SalarySchedule, ValidationStatus
from paychecks.models.w2 import ReconciliationField, ReconciliationReport, W2


def reconcile(
    paychecks: list[Paycheck],
    w2: W2,
    salary_schedule: SalarySchedule,
    tolerance: Decimal = DEFAULT_W2_TOLERANCE,
) -> ReconciliationReport:
    """Aggregate paycheck totals and compare against W-2 fields."""

    # Aggregate paycheck totals
    total_wages = sum(p.gross_pay for p in paychecks)
    total_federal = sum(p.federal_tax_withheld for p in paychecks)
    total_ss_wages = sum(p.gross_pay for p in paychecks)  # same as wages
    total_ss_tax = sum(p.social_security_tax_withheld for p in paychecks)
    total_medicare_wages = sum(p.gross_pay for p in paychecks)
    total_medicare_tax = sum(p.medicare_tax_withheld for p in paychecks)
    total_state_wages = sum(p.gross_pay for p in paychecks)
    total_state_tax = sum(p.state_tax_withheld for p in paychecks)

    def make_field(name: str, w2_val: Decimal, paycheck_total: Decimal) -> ReconciliationField:
        diff = paycheck_total - w2_val
        status = ValidationStatus.PASS if abs(diff) <= tolerance else ValidationStatus.FAIL
        return ReconciliationField(
            field_name=name,
            w2_value=w2_val,
            paycheck_total=paycheck_total,
            difference=diff,
            status=status,
            tolerance=tolerance,
        )

    fields = (
        make_field("Box 1 — Wages", w2.box1_wages, Decimal(str(total_wages)).quantize(Decimal("0.01"))),
        make_field("Box 2 — Federal Tax", w2.box2_federal_tax_withheld, Decimal(str(total_federal)).quantize(Decimal("0.01"))),
        make_field("Box 3 — SS Wages", w2.box3_social_security_wages, Decimal(str(total_ss_wages)).quantize(Decimal("0.01"))),
        make_field("Box 4 — SS Tax", w2.box4_social_security_tax, Decimal(str(total_ss_tax)).quantize(Decimal("0.01"))),
        make_field("Box 5 — Medicare Wages", w2.box5_medicare_wages, Decimal(str(total_medicare_wages)).quantize(Decimal("0.01"))),
        make_field("Box 6 — Medicare Tax", w2.box6_medicare_tax, Decimal(str(total_medicare_tax)).quantize(Decimal("0.01"))),
        make_field("Box 16 — State Wages", w2.box16_state_wages, Decimal(str(total_state_wages)).quantize(Decimal("0.01"))),
        make_field("Box 17 — State Tax", w2.box17_state_tax, Decimal(str(total_state_tax)).quantize(Decimal("0.01"))),
    )

    # Detect missing pay periods
    missing = _find_missing_periods(paychecks, salary_schedule)

    statuses = [f.status for f in fields]
    if ValidationStatus.FAIL in statuses:
        overall = ValidationStatus.FAIL
    elif missing:
        overall = ValidationStatus.WARNING
    else:
        overall = ValidationStatus.PASS

    return ReconciliationReport(
        w2=w2,
        paychecks=tuple(paychecks),
        fields=fields,
        missing_periods=tuple(missing),
        overall_status=overall,
        pay_periods_per_year=salary_schedule.frequency.periods_per_year,
        salary_schedule=salary_schedule,
    )


def _find_missing_periods(paychecks: list[Paycheck], schedule: SalarySchedule) -> list[date]:
    """Identify expected pay period start dates not represented in the paycheck list.

    Generates the full expected schedule from the earliest paycheck date and
    compares against what was provided. Also flags when count < expected periods/year.
    """
    if not paychecks:
        return []

    period_starts = {p.pay_period_start for p in paychecks}
    min_date = min(period_starts)

    days_map = {52: 7, 26: 14, 24: 15, 12: 30}
    step = days_map.get(schedule.frequency.periods_per_year, 14)
    total_expected = schedule.frequency.periods_per_year

    # Generate the full expected schedule for the year from the first paycheck date
    expected = []
    current = min_date
    for _ in range(total_expected):
        expected.append(current)
        current += timedelta(days=step)

    return [d for d in expected if d not in period_starts]
