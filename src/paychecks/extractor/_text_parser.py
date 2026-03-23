from __future__ import annotations
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from paychecks.models import Deduction, ExtractionError, Paycheck
from paychecks.models.enums import ExtractionMethod


def _parse_amount(text: str) -> Decimal | None:
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return Decimal(cleaned) if cleaned else None
    except InvalidOperation:
        return None


def _parse_date_str(text: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {text!r}")


def parse_paycheck_from_text(
    path: Path, text: str, method: ExtractionMethod
) -> Paycheck | ExtractionError:
    """Parse paycheck fields from plain text using regex patterns."""

    period_match = re.search(
        r"pay\s*period[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*(?:to|[-–]|through)\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if not period_match:
        return ExtractionError(
            source_file=path,
            field_name="pay_period_start",
            message=f"Pay period dates not found in {path.name}. Check PDF format.",
            page_number=1,
        )
    try:
        period_start = _parse_date_str(period_match.group(1))
        period_end = _parse_date_str(period_match.group(2))
    except ValueError:
        return ExtractionError(
            source_file=path,
            field_name="pay_period_start",
            message=f"Could not parse pay period dates in {path.name}.",
            page_number=1,
        )

    def find_amount(pattern: str, field: str) -> Decimal | ExtractionError:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return ExtractionError(
                source_file=path,
                field_name=field,
                message=f"{field} not found in {path.name} — check PDF version or format.",
                page_number=1,
            )
        val = _parse_amount(m.group(1))
        if val is None:
            return ExtractionError(source_file=path, field_name=field,
                                   message=f"Could not parse {field} in {path.name}.", page_number=1)
        return val

    gross = find_amount(r"gross\s*(?:pay|earnings)[:\s]+\$?([\d,]+\.\d{2})", "gross_pay")
    if isinstance(gross, ExtractionError): return gross
    net = find_amount(r"net\s*pay[:\s]+\$?([\d,]+\.\d{2})", "net_pay")
    if isinstance(net, ExtractionError): return net
    federal = find_amount(r"federal\s*(?:income\s*)?tax[:\s]+\$?([\d,]+\.\d{2})", "federal_tax_withheld")
    if isinstance(federal, ExtractionError): return federal
    ss = find_amount(r"social\s*security\s*(?:tax)?[:\s]+\$?([\d,]+\.\d{2})", "social_security_tax_withheld")
    if isinstance(ss, ExtractionError): return ss
    medicare = find_amount(r"medicare[:\s]+\$?([\d,]+\.\d{2})", "medicare_tax_withheld")
    if isinstance(medicare, ExtractionError): return medicare
    state = find_amount(r"state\s*(?:income\s*)?tax[:\s]+\$?([\d,]+\.\d{2})", "state_tax_withheld")
    if isinstance(state, ExtractionError): return state

    deduction_pattern = re.compile(
        r"(401\(k\)|health\s*insurance|dental|vision|hsa|fsa|life\s*insurance|disability)[:\s]+\$?([\d,]+\.\d{2})",
        re.IGNORECASE,
    )
    deductions = tuple(
        Deduction(name=m.group(1), amount=Decimal(m.group(2).replace(",", "")))
        for m in deduction_pattern.finditer(text)
    )

    return Paycheck(
        source_file=path,
        pay_period_start=period_start,
        pay_period_end=period_end,
        gross_pay=gross,
        federal_tax_withheld=federal,
        social_security_tax_withheld=ss,
        medicare_tax_withheld=medicare,
        state_tax_withheld=state,
        other_deductions=deductions,
        net_pay=net,
        extraction_method=method,
    )
