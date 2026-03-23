"""Unit tests for all model dataclasses. Write first — must fail before T009–T012 are implemented."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest

from paychecks.models import (
    Deduction,
    ExtractionError,
    ExtractionMethod,
    FieldResult,
    Paycheck,
    PaycheckValidationResult,
    PayFrequency,
    SalaryChange,
    SalarySchedule,
    ValidationStatus,
)


def make_paycheck(**overrides) -> Paycheck:
    defaults = dict(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=date(2025, 1, 1),
        pay_period_end=date(2025, 1, 14),
        gross_pay=Decimal("4615.38"),
        federal_tax_withheld=Decimal("1015.38"),
        social_security_tax_withheld=Decimal("286.15"),
        medicare_tax_withheld=Decimal("66.92"),
        state_tax_withheld=Decimal("276.92"),
        other_deductions=(),
        net_pay=Decimal("2969.70"),  # just a plausible number
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
    defaults.update(overrides)
    return Paycheck(**defaults)


class TestPayFrequency:
    def test_periods_per_year(self):
        assert PayFrequency.WEEKLY.periods_per_year == 52
        assert PayFrequency.BIWEEKLY.periods_per_year == 26
        assert PayFrequency.SEMIMONTHLY.periods_per_year == 24
        assert PayFrequency.MONTHLY.periods_per_year == 12


class TestSalarySchedule:
    def test_base_salary_no_changes(self):
        s = SalarySchedule(
            base_annual_salary=Decimal("120000"),
            frequency=PayFrequency.BIWEEKLY,
        )
        assert s.salary_for_period(date(2025, 1, 1)) == Decimal("120000")

    def test_mid_year_change(self):
        s = SalarySchedule(
            base_annual_salary=Decimal("100000"),
            frequency=PayFrequency.BIWEEKLY,
            changes=(SalaryChange(date(2025, 7, 1), Decimal("120000")),),
        )
        assert s.salary_for_period(date(2025, 6, 15)) == Decimal("100000")
        assert s.salary_for_period(date(2025, 7, 1)) == Decimal("120000")
        assert s.salary_for_period(date(2025, 12, 1)) == Decimal("120000")

    def test_multiple_changes(self):
        s = SalarySchedule(
            base_annual_salary=Decimal("80000"),
            frequency=PayFrequency.MONTHLY,
            changes=(
                SalaryChange(date(2025, 4, 1), Decimal("90000")),
                SalaryChange(date(2025, 10, 1), Decimal("100000")),
            ),
        )
        assert s.salary_for_period(date(2025, 1, 1)) == Decimal("80000")
        assert s.salary_for_period(date(2025, 5, 1)) == Decimal("90000")
        assert s.salary_for_period(date(2025, 11, 1)) == Decimal("100000")


class TestPaycheckValidationResult:
    def make_result(self, statuses: list[ValidationStatus]) -> PaycheckValidationResult:
        field_results = tuple(
            FieldResult(f"field_{i}", None, None, s)
            for i, s in enumerate(statuses)
        )
        return PaycheckValidationResult(
            paycheck=make_paycheck(),
            salary_used=Decimal("120000"),
            pay_periods_per_year=26,
            field_results=field_results,
        )

    def test_all_pass(self):
        r = self.make_result([ValidationStatus.PASS, ValidationStatus.PASS])
        assert r.overall_status == ValidationStatus.PASS
        assert r.passed is True

    def test_one_fail(self):
        r = self.make_result([ValidationStatus.PASS, ValidationStatus.FAIL])
        assert r.overall_status == ValidationStatus.FAIL
        assert r.passed is False

    def test_warning_no_fail(self):
        r = self.make_result([ValidationStatus.PASS, ValidationStatus.WARNING])
        assert r.overall_status == ValidationStatus.WARNING
        assert r.passed is False

    def test_fail_beats_warning(self):
        r = self.make_result([ValidationStatus.WARNING, ValidationStatus.FAIL])
        assert r.overall_status == ValidationStatus.FAIL


class TestDeduction:
    def test_basic(self):
        d = Deduction(name="401(k)", amount=Decimal("500.00"))
        assert d.name == "401(k)"
        assert d.amount == Decimal("500.00")


class TestExtractionError:
    def test_basic(self):
        e = ExtractionError(
            source_file=Path("/tmp/p.pdf"),
            field_name="gross_pay",
            message="Not found in page 1 — check PDF format.",
            page_number=1,
        )
        assert "gross_pay" in e.field_name
        assert e.page_number == 1
