from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from .enums import ExtractionMethod
from .results import ValidationStatus


@dataclass(frozen=True)
class W2:
    source_file: Path
    tax_year: int
    box1_wages: Decimal
    box2_federal_tax_withheld: Decimal
    box3_social_security_wages: Decimal
    box4_social_security_tax: Decimal
    box5_medicare_wages: Decimal
    box6_medicare_tax: Decimal
    box16_state_wages: Decimal
    box17_state_tax: Decimal
    extraction_method: ExtractionMethod


@dataclass(frozen=True)
class ReconciliationField:
    field_name: str
    w2_value: Decimal
    paycheck_total: Decimal
    difference: Decimal  # paycheck_total - w2_value
    status: ValidationStatus
    tolerance: Decimal


@dataclass(frozen=True)
class ReconciliationReport:
    w2: W2
    paychecks: tuple
    fields: tuple[ReconciliationField, ...]
    missing_periods: tuple
    overall_status: ValidationStatus
    pay_periods_per_year: int
    salary_schedule: object  # SalarySchedule — avoid circular import
