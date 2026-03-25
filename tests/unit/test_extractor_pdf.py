"""Unit tests for pdfplumber PDF extractor."""



from paychecks.models import ExtractionError, ExtractionMethod, Paycheck
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder


class TestPdfExtractor:
    def test_extract_valid_paycheck(self, tmp_path):
        from paychecks.extractor.pdf import extract_paycheck

        pdf_path = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "paycheck.pdf"
        )
        result = extract_paycheck(pdf_path)
        assert isinstance(result, Paycheck), f"Expected Paycheck, got: {result}"
        assert result.gross_pay > 0
        assert result.net_pay > 0
        assert result.extraction_method == ExtractionMethod.PDFPLUMBER

    def test_extract_returns_error_for_bad_file(self, tmp_path):
        from paychecks.extractor.pdf import extract_paycheck

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        result = extract_paycheck(bad)
        assert isinstance(result, ExtractionError)
        assert bad.name in result.source_file.name or result.source_file == bad

    def test_extraction_error_has_filename(self, tmp_path):
        from paychecks.extractor.pdf import extract_paycheck

        bad = tmp_path / "missing_fields.pdf"
        # Empty PDF with no paycheck content
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(bad))
        c.drawString(50, 750, "This is not a paycheck")
        c.save()
        result = extract_paycheck(bad)
        assert isinstance(result, ExtractionError)
        assert result.source_file == bad
        assert result.field_name  # must have a field name
        assert "missing_fields.pdf" in result.message or result.source_file.name in result.message
