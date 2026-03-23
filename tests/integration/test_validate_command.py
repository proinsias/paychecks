"""Integration tests for the `paychecks validate` CLI command."""
from typer.testing import CliRunner

from paychecks.cli import app
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder

runner = CliRunner()


class TestValidateCommand:
    def test_valid_paycheck_exits_zero(self, tmp_path):
        pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "paycheck.pdf"
        )
        result = runner.invoke(
            app,
            ["validate", str(pdf), "--salary", "120000", "--frequency", "biweekly"],
        )
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output

    def test_mismatched_salary_exits_one(self, tmp_path):
        pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "paycheck.pdf"
        )
        # Wrong salary provided
        result = runner.invoke(
            app,
            ["validate", str(pdf), "--salary", "60000", "--frequency", "biweekly"],
        )
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_bad_pdf_exits_two(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        result = runner.invoke(
            app,
            ["validate", str(bad), "--salary", "120000", "--frequency", "biweekly"],
        )
        assert result.exit_code == 2

    def test_output_csv_creates_file(self, tmp_path):
        pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "paycheck.pdf"
        )
        out = tmp_path / "report.csv"
        result = runner.invoke(
            app,
            ["validate", str(pdf), "--salary", "120000", "--frequency", "biweekly", "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "field" in content
        assert "status" in content

    def test_output_txt_creates_file(self, tmp_path):
        pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
            tmp_path / "paycheck.pdf"
        )
        out = tmp_path / "report.txt"
        result = runner.invoke(
            app,
            ["validate", str(pdf), "--salary", "120000", "--frequency", "biweekly", "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()
