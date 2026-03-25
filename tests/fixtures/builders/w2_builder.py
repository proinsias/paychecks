from __future__ import annotations

from decimal import Decimal
from pathlib import Path


class W2Builder:
    """Build synthetic W-2 PDFs for testing."""

    def __init__(
        self,
        annual_salary: float = 120_000,
        tax_year: int = 2025,
        federal_tax_override: float | None = None,
        **overrides,
    ):
        salary = Decimal(str(annual_salary))
        self.tax_year = tax_year
        self.box1_wages = overrides.get("box1_wages", salary)
        self.box2_federal = (
            Decimal(str(federal_tax_override))
            if federal_tax_override is not None
            else (salary * Decimal("0.22")).quantize(Decimal("0.01"))
        )
        self.box3_ss_wages = overrides.get("box3_ss_wages", salary)
        self.box4_ss_tax = overrides.get(
            "box4_ss_tax", (salary * Decimal("0.062")).quantize(Decimal("0.01"))
        )
        self.box5_medicare_wages = overrides.get("box5_medicare_wages", salary)
        self.box6_medicare_tax = overrides.get(
            "box6_medicare_tax", (salary * Decimal("0.0145")).quantize(Decimal("0.01"))
        )
        self.box16_state_wages = overrides.get("box16_state_wages", salary)
        self.box17_state_tax = overrides.get(
            "box17_state_tax", (salary * Decimal("0.06")).quantize(Decimal("0.01"))
        )

    def save(self, path: str | Path) -> Path:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, f"W-2 Wage and Tax Statement — {self.tax_year}")
        c.setFont("Helvetica", 12)
        y = 710

        def line(text: str) -> None:
            nonlocal y
            c.drawString(50, y, text)
            y -= 20

        line(f"Box 1  Wages, tips, other compensation: ${self.box1_wages:,.2f}")
        line(f"Box 2  Federal income tax withheld: ${self.box2_federal:,.2f}")
        line(f"Box 3  Social security wages: ${self.box3_ss_wages:,.2f}")
        line(f"Box 4  Social security tax withheld: ${self.box4_ss_tax:,.2f}")
        line(f"Box 5  Medicare wages and tips: ${self.box5_medicare_wages:,.2f}")
        line(f"Box 6  Medicare tax withheld: ${self.box6_medicare_tax:,.2f}")
        line(f"Box 16 State wages, tips, etc.: ${self.box16_state_wages:,.2f}")
        line(f"Box 17 State income tax: ${self.box17_state_tax:,.2f}")
        c.save()
        return path
