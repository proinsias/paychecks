"""Edge-case tests for extractors, validators, reporters, and batch processing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from paychecks.extractor._text_parser import parse_paycheck_from_text
from paychecks.extractor.pdf import extract_paycheck, extract_w2
from paychecks.models import ExtractionError, Paycheck
from paychecks.models.enums import ExtractionMethod, PayFrequency
from paychecks.models.salary import SalarySchedule
from paychecks.reporter.csv_export import write_batch_csv, write_validation_csv
from paychecks.reporter.text_export import write_batch_txt, write_validation_txt
from paychecks.validator.paycheck import validate_batch


def _make_paycheck(period_start: date, period_end: date) -> Paycheck:
    gross = Decimal("4615.38")
    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    total = federal + ss + medicare + state
    return Paycheck(
        source_file=Path("/tmp/test.pdf"),
        pay_period_start=period_start,
        pay_period_end=period_end,
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=(gross - total).quantize(Decimal("0.01")),
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )


class TestCorruptPDF:
    def test_corrupt_pdf_returns_extraction_error(self, tmp_path):
        """A corrupt PDF file returns ExtractionError, not raises."""
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4 corrupt data")
        result = extract_paycheck(bad_pdf)
        assert isinstance(result, ExtractionError)

    def test_zero_byte_pdf_returns_extraction_error(self, tmp_path):
        """A zero-byte file returns ExtractionError, not raises."""
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")
        result = extract_paycheck(empty_pdf)
        assert isinstance(result, ExtractionError)


class TestW2cDetection:
    def test_w2c_returns_extraction_error_with_not_supported(self, tmp_path):
        """W-2c document returns ExtractionError with 'not supported' in message."""
        fake_pdf = tmp_path / "w2c.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 placeholder")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "W-2c corrected wage statement Box 1 $50000.00"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = extract_w2(fake_pdf)

        assert isinstance(result, ExtractionError)
        assert "not supported" in result.message.lower()


class TestDuplicatePayPeriodDates:
    def test_duplicate_pay_periods_both_returned(self, tmp_path):
        """Two paychecks with identical pay period dates are both validated without raising."""
        # Build two valid paycheck PDFs with the same pay period
        from tests.fixtures.builders.paycheck_builder import PaycheckBuilder

        pdf1 = PaycheckBuilder(
            annual_salary=120_000,
            frequency="biweekly",
            period_start="2025-01-01",
            period_end="2025-01-14",
        ).save(tmp_path / "paycheck_a.pdf")

        pdf2 = PaycheckBuilder(
            annual_salary=120_000,
            frequency="biweekly",
            period_start="2025-01-01",
            period_end="2025-01-14",
        ).save(tmp_path / "paycheck_b.pdf")

        schedule = SalarySchedule(
            base_annual_salary=Decimal("120000"),
            frequency=PayFrequency.BIWEEKLY,
        )

        results = validate_batch([pdf1, pdf2], schedule)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Text parser coverage
# ---------------------------------------------------------------------------

_VALID_PAYCHECK_TEXT = """\
Pay Period: 01/01/2025 to 01/14/2025

Gross Pay: $4,615.38
Federal Income Tax: $1,015.38
Social Security Tax: $286.15
Medicare: $66.92
State Income Tax: $276.92
401(k): $230.77

Net Pay: $2,740.24
"""


class TestTextParser:
    def test_parse_valid_paycheck_text(self):
        result = parse_paycheck_from_text(
            Path("/tmp/test.pdf"), _VALID_PAYCHECK_TEXT, ExtractionMethod.PDFPLUMBER
        )
        assert isinstance(result, Paycheck)
        assert result.gross_pay == Decimal("4615.38")
        assert result.net_pay == Decimal("2740.24")
        assert len(result.other_deductions) == 1  # 401(k)

    def test_parse_missing_pay_period_returns_error(self):
        result = parse_paycheck_from_text(
            Path("/tmp/test.pdf"), "No dates here at all", ExtractionMethod.PDFPLUMBER
        )
        assert isinstance(result, ExtractionError)
        assert result.field_name == "pay_period_start"

    def test_parse_missing_gross_pay_returns_error(self):
        text = "Pay Period: 01/01/2025 to 01/14/2025\nNet Pay: $1000.00"
        result = parse_paycheck_from_text(Path("/tmp/test.pdf"), text, ExtractionMethod.PDFPLUMBER)
        assert isinstance(result, ExtractionError)
        assert result.field_name == "gross_pay"

    def test_parse_missing_federal_tax_returns_error(self):
        text = "Pay Period: 01/01/2025 to 01/14/2025\nGross Pay: $4615.38\nNet Pay: $3000.00\n"
        result = parse_paycheck_from_text(Path("/tmp/test.pdf"), text, ExtractionMethod.OCR)
        assert isinstance(result, ExtractionError)
        assert result.field_name == "federal_tax_withheld"


# ---------------------------------------------------------------------------
# Reporter coverage: text_export and csv_export
# ---------------------------------------------------------------------------


def _make_validation_result():
    """Build a minimal PaycheckValidationResult for reporter tests."""
    from paychecks.models import PaycheckValidationResult
    from paychecks.models.results import FieldResult, ValidationStatus

    gross = Decimal("4615.38")
    federal = (gross * Decimal("0.22")).quantize(Decimal("0.01"))
    ss = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
    medicare = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
    state = (gross * Decimal("0.06")).quantize(Decimal("0.01"))
    total = federal + ss + medicare + state
    paycheck = Paycheck(
        source_file=Path("/tmp/paycheck.pdf"),
        pay_period_start=date(2025, 1, 1),
        pay_period_end=date(2025, 1, 14),
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=(),
        net_pay=(gross - total).quantize(Decimal("0.01")),
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
    field_results = (
        FieldResult("gross_pay", gross, gross, ValidationStatus.PASS, None),
        FieldResult("net_pay", gross - total, gross - total, ValidationStatus.PASS, None),
    )
    return PaycheckValidationResult(
        paycheck=paycheck,
        salary_used=Decimal("120000"),
        pay_periods_per_year=26,
        field_results=field_results,
    )


class TestTextExport:
    def test_write_validation_txt_creates_file(self, tmp_path):
        result = _make_validation_result()
        out = tmp_path / "report.txt"
        write_validation_txt(result, out)
        assert out.exists()
        content = out.read_text()
        assert "gross_pay" in content
        assert "PASS" in content

    def test_write_batch_txt_creates_file(self, tmp_path):
        result = _make_validation_result()
        out = tmp_path / "batch.txt"
        write_batch_txt([result], out)
        assert out.exists()
        content = out.read_text()
        assert "paycheck.pdf" in content
        assert "PASS" in content


class TestCsvExport:
    def test_write_validation_csv_creates_file(self, tmp_path):
        result = _make_validation_result()
        out = tmp_path / "report.csv"
        write_validation_csv(result, out)
        assert out.exists()
        content = out.read_text()
        assert "field" in content
        assert "status" in content
        assert "gross_pay" in content

    def test_write_batch_csv_creates_file(self, tmp_path):
        result = _make_validation_result()
        out = tmp_path / "batch.csv"
        write_batch_csv([result], out)
        assert out.exists()
        content = out.read_text()
        assert "file" in content
        assert "paycheck.pdf" in content
