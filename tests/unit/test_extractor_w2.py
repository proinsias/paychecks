"""Unit tests for W-2 PDF extractor."""

from decimal import Decimal

from paychecks.models import ExtractionError
from paychecks.models.w2 import W2
from tests.fixtures.builders.w2_builder import W2Builder


class TestW2Extractor:
    def test_extract_valid_w2(self, tmp_path):
        from paychecks.extractor.pdf import extract_w2

        w2_path = W2Builder(annual_salary=120_000, tax_year=2025).save(tmp_path / "w2.pdf")
        result = extract_w2(w2_path)
        assert isinstance(result, W2), f"Expected W2, got: {result}"
        assert result.box1_wages == Decimal("120000.00")
        assert result.tax_year == 2025

    def test_extract_returns_error_for_bad_file(self, tmp_path):
        from paychecks.extractor.pdf import extract_w2

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        result = extract_w2(bad)
        assert isinstance(result, ExtractionError)

    def test_w2c_detection_returns_error(self, tmp_path):
        from reportlab.pdfgen import canvas

        from paychecks.extractor.pdf import extract_w2

        w2c_path = tmp_path / "w2c.pdf"
        c = canvas.Canvas(str(w2c_path))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "W-2c Corrected Wage and Tax Statement 2025")
        c.drawString(50, 720, "Box 1 Wages: $120,000.00")
        c.save()
        result = extract_w2(w2c_path)
        assert isinstance(result, ExtractionError)
        assert "W-2c" in result.message or "not supported" in result.message.lower()
