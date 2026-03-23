from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from .enums import ExtractionMethod
from .results import FieldResult, ValidationStatus

@dataclass(frozen=True)
class Deduction:
    name: str
    amount: Decimal  # always positive

@dataclass(frozen=True)
class Paycheck:
    source_file: Path
    pay_period_start: date
    pay_period_end: date
    gross_pay: Decimal
    federal_tax_withheld: Decimal
    social_security_tax_withheld: Decimal
    medicare_tax_withheld: Decimal
    state_tax_withheld: Decimal
    other_deductions: tuple[Deduction, ...]
    net_pay: Decimal
    extraction_method: ExtractionMethod

@dataclass(frozen=True)
class PaycheckValidationResult:
    paycheck: Paycheck
    salary_used: Decimal
    pay_periods_per_year: int
    field_results: tuple[FieldResult, ...]

    @property
    def overall_status(self) -> ValidationStatus:
        statuses = [r.status for r in self.field_results]
        if ValidationStatus.FAIL in statuses:
            return ValidationStatus.FAIL
        if ValidationStatus.WARNING in statuses:
            return ValidationStatus.WARNING
        return ValidationStatus.PASS

    @property
    def passed(self) -> bool:
        return self.overall_status == ValidationStatus.PASS
