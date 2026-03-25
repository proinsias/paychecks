"""Unit tests for batch paycheck validation."""

from datetime import date
from decimal import Decimal

from paychecks.models import PayFrequency, SalarySchedule, ValidationStatus


def make_schedule() -> SalarySchedule:
    return SalarySchedule(
        base_annual_salary=Decimal("120000"),
        frequency=PayFrequency.BIWEEKLY,
    )


class TestValidateBatch:
    def test_batch_with_valid_pdfs(self, tmp_path):
        from datetime import timedelta

        from paychecks.validator.paycheck import validate_batch
        from tests.fixtures.builders.paycheck_builder import PaycheckBuilder

        base = date(2025, 1, 1)
        pdfs = [
            PaycheckBuilder(
                annual_salary=120_000,
                frequency="biweekly",
                period_start=base + timedelta(days=i * 14),
                period_end=base + timedelta(days=i * 14 + 13),
            ).save(tmp_path / f"p{i}.pdf")
            for i in range(3)
        ]
        results = validate_batch(pdfs, make_schedule())
        assert len(results) == 3
        assert all(r.overall_status == ValidationStatus.PASS for r in results)

    def test_batch_skips_extraction_errors(self, tmp_path, capsys):
        from paychecks.validator.paycheck import validate_batch

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        results = validate_batch([bad], make_schedule())
        # Extraction error is skipped; no crash
        assert results == []

    def test_batch_continues_after_error(self, tmp_path):
        from paychecks.validator.paycheck import validate_batch
        from tests.fixtures.builders.paycheck_builder import PaycheckBuilder

        good = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "good.pdf"
        )
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        results = validate_batch([bad, good], make_schedule())
        # bad is skipped, good is processed
        assert len(results) == 1
