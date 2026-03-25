from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


class PaycheckBuilder:
    """Build synthetic paycheck PDFs for testing."""

    def __init__(
        self,
        annual_salary: float = 120_000,
        frequency: str = "biweekly",
        period_start: str | date | None = None,
        period_end: str | date | None = None,
        gross_pay_override: float | None = None,
        net_pay_override: float | None = None,
    ):
        self.annual_salary = Decimal(str(annual_salary))
        self.frequency = frequency
        self._periods = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}
        self.periods_per_year = self._periods[frequency]
        self.gross_pay = (
            Decimal(str(gross_pay_override))
            if gross_pay_override is not None
            else (self.annual_salary / self.periods_per_year).quantize(Decimal("0.01"))
        )

        if isinstance(period_start, str):
            from datetime import datetime

            period_start = datetime.strptime(period_start, "%Y-%m-%d").date()
        if isinstance(period_end, str):
            from datetime import datetime

            period_end = datetime.strptime(period_end, "%Y-%m-%d").date()

        self.period_start: date = period_start or date(2025, 1, 1)
        self.period_end: date = period_end or date(2025, 1, 14)

        # Fixed deductions for testing
        self.federal_tax = (self.gross_pay * Decimal("0.22")).quantize(Decimal("0.01"))
        self.ss_tax = (self.gross_pay * Decimal("0.062")).quantize(Decimal("0.01"))
        self.medicare_tax = (self.gross_pay * Decimal("0.0145")).quantize(Decimal("0.01"))
        self.state_tax = (self.gross_pay * Decimal("0.06")).quantize(Decimal("0.01"))
        self.retirement = (self.gross_pay * Decimal("0.05")).quantize(Decimal("0.01"))
        total_deductions = (
            self.federal_tax + self.ss_tax + self.medicare_tax + self.state_tax + self.retirement
        )
        self.net_pay = (
            Decimal(str(net_pay_override))
            if net_pay_override is not None
            else (self.gross_pay - total_deductions).quantize(Decimal("0.01"))
        )

    def save(self, path: str | Path) -> Path:
        """Save synthetic paycheck PDF to path."""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "ACME CORP — PAYCHECK")
        c.setFont("Helvetica", 12)
        y = 710

        def line(text: str) -> None:
            nonlocal y
            c.drawString(50, y, text)
            y -= 20

        start_str = self.period_start.strftime("%m/%d/%Y")
        end_str = self.period_end.strftime("%m/%d/%Y")
        line(f"Pay Period: {start_str} to {end_str}")
        line("")
        line(f"Gross Pay: ${self.gross_pay:,.2f}")
        line(f"Federal Income Tax: ${self.federal_tax:,.2f}")
        line(f"Social Security Tax: ${self.ss_tax:,.2f}")
        line(f"Medicare: ${self.medicare_tax:,.2f}")
        line(f"State Income Tax: ${self.state_tax:,.2f}")
        line(f"401(k): ${self.retirement:,.2f}")
        line("")
        line(f"Net Pay: ${self.net_pay:,.2f}")
        c.save()
        return path

    def build_year(self, year: int) -> list[Path]:
        """Generate full year of paycheck PDFs into a temp directory."""
        import tempfile

        tmpdir = Path(tempfile.mkdtemp(prefix=f"paychecks_{year}_"))
        days_map = {"weekly": 7, "biweekly": 14, "semimonthly": 15, "monthly": 30}
        period_days = days_map[self.frequency]
        start = date(year, 1, 1)
        paths = []
        for i in range(self.periods_per_year):
            ps = start + timedelta(days=i * period_days)
            pe = ps + timedelta(days=period_days - 1)
            if pe.year > year:
                pe = date(year, 12, 31)
            b = PaycheckBuilder(
                annual_salary=float(self.annual_salary),
                frequency=self.frequency,
                period_start=ps,
                period_end=pe,
            )
            p = b.save(tmpdir / f"paycheck_{i + 1:02d}.pdf")
            paths.append(p)
        return paths
