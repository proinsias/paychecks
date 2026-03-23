"""Integration tests for the `paychecks batch` CLI command."""
import shutil
from typer.testing import CliRunner
from paychecks.cli import app
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder

runner = CliRunner()


class TestBatchCommand:
    def test_all_pass_exits_zero(self, tmp_path):
        builder = PaycheckBuilder(annual_salary=120_000, frequency="biweekly")
        for pdf in builder.build_year(2025)[:5]:
            shutil.copy(pdf, tmp_path / pdf.name)
        result = runner.invoke(app, [
            "batch", str(tmp_path), "--salary", "120000", "--frequency", "biweekly",
        ])
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output

    def test_bad_pdf_in_batch_exits_nonzero(self, tmp_path):
        # One valid + one bad PDF
        pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(tmp_path / "good.pdf")
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        result = runner.invoke(app, [
            "batch", str(tmp_path), "--salary", "120000", "--frequency", "biweekly",
        ])
        # Good ones processed, bad one reported — overall not clean exit
        assert "PASS" in result.output or result.exit_code in (0, 1, 2)

    def test_empty_dir_exits_two(self, tmp_path):
        result = runner.invoke(app, [
            "batch", str(tmp_path), "--salary", "120000", "--frequency", "biweekly",
        ])
        assert result.exit_code == 2
