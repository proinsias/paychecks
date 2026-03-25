"""Unit tests for paycheck validation logic — write first, must fail before T026 implementation."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from paychecks.models import (
    ExtractionMethod,
    Paycheck,
    PayFrequency,
    SalaryChange,
    SalarySchedule,
    ValidationStatus,
)


def make_paycheck(
    gross_pay: Decimal = Decimal("4615.38"),
    net_pay: Decimal | None = None,
    other_deductions: tuple = (),
    period_start: date = date(2025, 1, 1),
) -> Paycheck:
    federal = (gross_pay * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross_pay * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross_pay * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross_pay * Decimal("0.06")).quantize(Decimal("0.01"))
    total_deductions = federal + ss + medicare + state + sum(d.amount for d in other_deductions)
    return Paycheck(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=period_start,
        pay_period_end=period_start.replace(day=period_start.day + 13),
        gross_pay=gross_pay,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=other_deductions,
        net_pay=net_pay
        if net_pay is not None
        else (gross_pay - total_deductions).quantize(Decimal("0.01")),
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )


def make_schedule(
    annual: float = 120_000, freq: PayFrequency = PayFrequency.BIWEEKLY
) -> SalarySchedule:
    return SalarySchedule(
        base_annual_salary=Decimal(str(annual)),
        frequency=freq,
    )


class TestGrossPayValidation:
    def test_gross_pay_pass(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        paycheck = make_paycheck(gross_pay=Decimal("4615.38"))
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.PASS

    def test_gross_pay_fail(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(100_000)  # wrong salary
        paycheck = make_paycheck(gross_pay=Decimal("4615.38"))  # actual is $120k/26
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.FAIL

    def test_gross_pay_within_tolerance(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        # 120000/26 = 4615.384..., rounded gives 4615.38; with $0.01 diff still PASS
        paycheck = make_paycheck(gross_pay=Decimal("4615.39"))
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.PASS

    def test_supplemental_pay_is_warning(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        # Gross significantly higher than expected = supplemental pay
        paycheck = make_paycheck(gross_pay=Decimal("10000.00"))
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.WARNING


class TestNetPayValidation:
    def test_net_pay_pass(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        paycheck = make_paycheck()  # net_pay computed correctly
        result = validate_paycheck(paycheck, schedule)
        net_result = next(r for r in result.field_results if r.field_name == "net_pay")
        assert net_result.status == ValidationStatus.PASS

    def test_net_pay_fail(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        paycheck = make_paycheck(net_pay=Decimal("100.00"))  # obviously wrong
        result = validate_paycheck(paycheck, schedule)
        net_result = next(r for r in result.field_results if r.field_name == "net_pay")
        assert net_result.status == ValidationStatus.FAIL


class TestMidYearSalaryChange:
    def test_uses_correct_salary_before_change(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = SalarySchedule(
            base_annual_salary=Decimal("100000"),
            frequency=PayFrequency.BIWEEKLY,
            changes=(SalaryChange(date(2025, 7, 1), Decimal("120000")),),
        )
        # Period before change — should use $100k
        paycheck = make_paycheck(
            gross_pay=(Decimal("100000") / 26).quantize(Decimal("0.01")),
            period_start=date(2025, 6, 1),
        )
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.PASS

    def test_uses_correct_salary_after_change(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = SalarySchedule(
            base_annual_salary=Decimal("100000"),
            frequency=PayFrequency.BIWEEKLY,
            changes=(SalaryChange(date(2025, 7, 1), Decimal("120000")),),
        )
        # Period after change — should use $120k
        paycheck = make_paycheck(
            gross_pay=(Decimal("120000") / 26).quantize(Decimal("0.01")),
            period_start=date(2025, 8, 1),
        )
        result = validate_paycheck(paycheck, schedule)
        gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
        assert gross_result.status == ValidationStatus.PASS


class TestOverallStatus:
    def test_all_pass_means_passed(self):
        from paychecks.validator.paycheck import validate_paycheck

        schedule = make_schedule(120_000)
        paycheck = make_paycheck()
        result = validate_paycheck(paycheck, schedule)
        assert result.overall_status == ValidationStatus.PASS
        assert result.passed is True


# ---------------------------------------------------------------------------
# Property-based tests (hypothesis)
# ---------------------------------------------------------------------------
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st


@given(
    annual_salary=st.integers(min_value=1000, max_value=500_000),
    frequency=st.sampled_from(list(PayFrequency)),
)
@settings(max_examples=100)
def test_gross_pay_equals_salary_divided_by_periods(annual_salary: int, frequency: PayFrequency):
    """gross_pay = annual_salary / periods_per_year within $0.02 tolerance."""
    from paychecks.validator.paycheck import validate_paycheck

    salary_dec = Decimal(str(annual_salary))
    periods = frequency.periods_per_year
    gross = (salary_dec / periods).quantize(Decimal("0.01"))

    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    total_deductions = federal + ss + medicare + state
    net = (gross - total_deductions).quantize(Decimal("0.01"))

    paycheck = Paycheck(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=date(2025, 1, 1),
        pay_period_end=date(2025, 1, 14),
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=net,
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
    schedule = SalarySchedule(base_annual_salary=salary_dec, frequency=frequency)
    result = validate_paycheck(paycheck, schedule)

    gross_result = next(r for r in result.field_results if r.field_name == "gross_pay")
    expected_gross = salary_dec / Decimal(str(periods))
    diff = abs(gross - expected_gross)
    assert diff <= Decimal("0.02"), (
        f"gross {gross} differs from expected {expected_gross} by {diff}"
    )
    assert gross_result.status == ValidationStatus.PASS


@given(
    annual_salary=st.integers(min_value=1000, max_value=500_000),
    frequency=st.sampled_from(list(PayFrequency)),
)
@settings(max_examples=100)
def test_net_pay_never_exceeds_gross_pay(annual_salary: int, frequency: PayFrequency):
    """net_pay <= gross_pay for any valid salary and frequency."""
    from paychecks.validator.paycheck import validate_paycheck

    salary_dec = Decimal(str(annual_salary))
    periods = frequency.periods_per_year
    gross = (salary_dec / periods).quantize(Decimal("0.01"))

    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    total_deductions = federal + ss + medicare + state
    net = (gross - total_deductions).quantize(Decimal("0.01"))

    paycheck = Paycheck(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=date(2025, 1, 1),
        pay_period_end=date(2025, 1, 14),
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=net,
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
    schedule = SalarySchedule(base_annual_salary=salary_dec, frequency=frequency)
    result = validate_paycheck(paycheck, schedule)

    net_result = next(r for r in result.field_results if r.field_name == "net_pay")
    assert paycheck.net_pay <= paycheck.gross_pay, (
        f"net {paycheck.net_pay} > gross {paycheck.gross_pay}"
    )
    assert net_result.status == ValidationStatus.PASS


@given(
    annual_salary=st.integers(min_value=1000, max_value=500_000),
    frequency=st.sampled_from(list(PayFrequency)),
)
@settings(max_examples=100)
def test_decimal_calculations_never_raise(annual_salary: int, frequency: PayFrequency):
    """Decimal financial calculations never raise exceptions for valid inputs."""
    from paychecks.validator.paycheck import validate_paycheck

    salary_dec = Decimal(str(annual_salary))
    periods = frequency.periods_per_year
    gross = (salary_dec / periods).quantize(Decimal("0.01"))

    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    total_deductions = federal + ss + medicare + state
    net = (gross - total_deductions).quantize(Decimal("0.01"))

    paycheck = Paycheck(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=date(2025, 1, 1),
        pay_period_end=date(2025, 1, 14),
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=net,
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
    schedule = SalarySchedule(base_annual_salary=salary_dec, frequency=frequency)
    # Must not raise
    result = validate_paycheck(paycheck, schedule)
    assert result is not None
