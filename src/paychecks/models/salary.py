from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from .enums import PayFrequency

@dataclass(frozen=True)
class SalaryChange:
    effective_date: date
    annual_salary: Decimal

@dataclass(frozen=True)
class SalarySchedule:
    base_annual_salary: Decimal
    frequency: PayFrequency
    changes: tuple[SalaryChange, ...] = ()

    def salary_for_period(self, period_start: date) -> Decimal:
        """Return applicable annual salary for a given pay period start date."""
        applicable = self.base_annual_salary
        for change in sorted(self.changes, key=lambda c: c.effective_date):
            if period_start >= change.effective_date:
                applicable = change.annual_salary
        return applicable
