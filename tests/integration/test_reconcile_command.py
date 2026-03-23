"""Integration tests for the `paychecks reconcile` CLI command."""
from typer.testing import CliRunner
from paychecks.cli import app
from tests.fixtures.builders.paycheck_builder import PaycheckBuilder
from tests.fixtures.builders.w2_builder import W2Builder

runner = CliRunner()


class TestReconcileCommand:
    def test_matching_year_exits_zero(self, tmp_path):
        builder = PaycheckBuilder(annual_salary=120_000, frequency="biweekly")
        pdfs = builder.build_year(2025)
        # Move PDFs to tmp_path
        import shutil
        for p in pdfs:
            shutil.copy(p, tmp_path / p.name)
        w2 = W2Builder(annual_salary=120_000, tax_year=2025).save(tmp_path / "w2.pdf")
        result = runner.invoke(app, [
            "reconcile", str(tmp_path), str(w2),
            "--salary", "120000", "--frequency", "biweekly",
        ])
        assert result.exit_code == 0, result.output
        assert "PASS" in result.output

    def test_w2_mismatch_exits_one(self, tmp_path):
        builder = PaycheckBuilder(annual_salary=120_000, frequency="biweekly")
        pdfs = builder.build_year(2025)
        import shutil
        for p in pdfs:
            shutil.copy(p, tmp_path / p.name)
        w2 = W2Builder(annual_salary=120_000, tax_year=2025, federal_tax_override=99999).save(tmp_path / "w2.pdf")
        result = runner.invoke(app, [
            "reconcile", str(tmp_path), str(w2),
            "--salary", "120000", "--frequency", "biweekly",
        ])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_missing_periods_warning(self, tmp_path):
        # Only first 10 paychecks
        builder = PaycheckBuilder(annual_salary=120_000, frequency="biweekly")
        pdfs = builder.build_year(2025)[:10]
        import shutil
        for p in pdfs:
            shutil.copy(p, tmp_path / p.name)
        w2 = W2Builder(annual_salary=120_000, tax_year=2025).save(tmp_path / "w2.pdf")
        result = runner.invoke(app, [
            "reconcile", str(tmp_path), str(w2),
            "--salary", "120000", "--frequency", "biweekly",
        ])
        # Should warn about missing periods — exit 1 since mismatch due to incomplete data
        assert "missing" in result.output.lower() or "Missing" in result.output
