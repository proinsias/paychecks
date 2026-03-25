"""Unit tests for W-2 reconciliation logic."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from paychecks.models import (
    ExtractionMethod,
    Paycheck,
    PayFrequency,
    SalarySchedule,
    ValidationStatus,
)
from paychecks.models.enums import ExtractionMethod
from paychecks.models.w2 import W2


def make_w2(annual: float = 120_000, tax_year: int = 2025, **overrides) -> W2:
    salary = Decimal(str(annual))
    return W2(
        source_file=Path("/tmp/w2.pdf"),
        tax_year=tax_year,
        box1_wages=overrides.get("box1_wages", salary),
        box2_federal_tax_withheld=overrides.get(
            "box2", (salary * Decimal("0.22")).quantize(Decimal("0.01"))
        ),
        box3_social_security_wages=overrides.get("box3", salary),
        box4_social_security_tax=overrides.get(
            "box4", (salary * Decimal("0.062")).quantize(Decimal("0.01"))
        ),
        box5_medicare_wages=overrides.get("box5", salary),
        box6_medicare_tax=overrides.get(
            "box6", (salary * Decimal("0.0145")).quantize(Decimal("0.01"))
        ),
        box16_state_wages=overrides.get("box16", salary),
        box17_state_tax=overrides.get(
            "box17", (salary * Decimal("0.06")).quantize(Decimal("0.01"))
        ),
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )


def make_paycheck(period_start: date, gross: Decimal, annual: float = 120_000) -> Paycheck:
    from datetime import timedelta

    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    net = (gross - federal - ss - medicare - state).quantize(Decimal("0.01"))
    return Paycheck(
        source_file=Path(f"/tmp/paycheck_{period_start}.pdf"),
        pay_period_start=period_start,
        pay_period_end=period_start + timedelta(days=13),
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=net,
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )


class TestW2Reconciliation:
    def _make_year_paychecks(self, annual: float = 120_000, periods: int = 26) -> list:
        from datetime import timedelta

        gross = (Decimal(str(annual)) / periods).quantize(Decimal("0.01"))
        start = date(2025, 1, 1)
        return [
            make_paycheck(start + timedelta(days=i * 14), gross, annual) for i in range(periods)
        ]

    def test_matching_paychecks_all_pass(self):
        from paychecks.validator.w2 import reconcile

        paychecks = self._make_year_paychecks()
        w2 = make_w2(120_000)
        schedule = SalarySchedule(
            base_annual_salary=Decimal("120000"),
            frequency=PayFrequency.BIWEEKLY,
        )
        report = reconcile(paychecks, w2, schedule)
        assert report.overall_status == ValidationStatus.PASS

    def test_mismatch_detected(self):
        from paychecks.validator.w2 import reconcile

        paychecks = self._make_year_paychecks()
        w2 = make_w2(120_000, box2=Decimal("99999.00"))  # wrong federal tax
        schedule = SalarySchedule(
            base_annual_salary=Decimal("120000"),
            frequency=PayFrequency.BIWEEKLY,
        )
        report = reconcile(paychecks, w2, schedule)
        assert report.overall_status == ValidationStatus.FAIL
        box2_field = next(
            f
            for f in report.fields
            if "federal" in f.field_name.lower() or "box 2" in f.field_name.lower()
        )
        assert box2_field.status == ValidationStatus.FAIL

    def test_missing_periods_detected(self):
        from paychecks.validator.w2 import reconcile

        # Only 20 of 26 biweekly paychecks
        paychecks = self._make_year_paychecks()[:20]
        w2 = make_w2(120_000)
        schedule = SalarySchedule(
            base_annual_salary=Decimal("120000"),
            frequency=PayFrequency.BIWEEKLY,
        )
        report = reconcile(paychecks, w2, schedule)
        assert len(report.missing_periods) > 0
