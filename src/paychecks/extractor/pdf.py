from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from paychecks.models import (
    Deduction,
    ExtractionError,
    ExtractionMethod,
    Paycheck,
)
from paychecks.models.errors import ExtractionError


def _parse_amount(text: str) -> Decimal | None:
    """Extract a USD amount from text like '$1,234.56' or '1234.56'."""
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return Decimal(cleaned) if cleaned else None
    except InvalidOperation:
        return None


def _parse_date(text: str):
    """Parse a date string in MM/DD/YYYY or YYYY-MM-DD format."""

    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_paycheck(path: Path) -> Paycheck | ExtractionError:
    """Extract paycheck fields from a text-based PDF using pdfplumber."""
    try:
        with pdfplumber.open(path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        return ExtractionError(
            source_file=path,
            field_name="<file>",
            message=f"Cannot open PDF: {exc}",
            page_number=None,
        )

    # --- Pay period dates ---
    period_match = re.search(
        r"pay\s*period[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*(?:to|[-–]|through)\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        full_text,
        re.IGNORECASE,
    )
    if not period_match:
        return ExtractionError(
            source_file=path,
            field_name="pay_period_start",
            message=f"Pay period dates not found in {path.name}. Check PDF format.",
            page_number=1,
        )
    period_start = _parse_date(period_match.group(1))
    period_end = _parse_date(period_match.group(2))
    if not period_start or not period_end:
        return ExtractionError(
            source_file=path,
            field_name="pay_period_start",
            message=f"Could not parse pay period dates in {path.name}.",
            page_number=1,
        )

    def find_amount(pattern: str, field: str) -> Decimal | ExtractionError:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if not m:
            return ExtractionError(
                source_file=path,
                field_name=field,
                message=f"{field} not found in {path.name} — check PDF version or format.",
                page_number=1,
            )
        val = _parse_amount(m.group(1))
        if val is None:
            return ExtractionError(
                source_file=path,
                field_name=field,
                message=f"Could not parse {field} value in {path.name}.",
                page_number=1,
            )
        return val

    gross = find_amount(r"gross\s*(?:pay|earnings)[:\s]+\$?([\d,]+\.\d{2})", "gross_pay")
    if isinstance(gross, ExtractionError):
        return gross

    net = find_amount(r"net\s*pay[:\s]+\$?([\d,]+\.\d{2})", "net_pay")
    if isinstance(net, ExtractionError):
        return net

    federal = find_amount(
        r"federal\s*(?:income\s*)?tax[:\s]+\$?([\d,]+\.\d{2})", "federal_tax_withheld"
    )
    if isinstance(federal, ExtractionError):
        return federal

    ss = find_amount(
        r"social\s*security\s*(?:tax)?[:\s]+\$?([\d,]+\.\d{2})", "social_security_tax_withheld"
    )
    if isinstance(ss, ExtractionError):
        return ss

    medicare = find_amount(r"medicare[:\s]+\$?([\d,]+\.\d{2})", "medicare_tax_withheld")
    if isinstance(medicare, ExtractionError):
        return medicare

    state = find_amount(r"state\s*(?:income\s*)?tax[:\s]+\$?([\d,]+\.\d{2})", "state_tax_withheld")
    if isinstance(state, ExtractionError):
        return state

    # Other deductions (lines like "401(k): $500.00" or "Health Insurance $200.00")
    deduction_pattern = re.compile(
        r"(401\(k\)|health\s*insurance|dental|vision|hsa|fsa|life\s*insurance|disability)[:\s]+\$?([\d,]+\.\d{2})",
        re.IGNORECASE,
    )
    deductions = tuple(
        Deduction(name=m.group(1), amount=Decimal(m.group(2).replace(",", "")))
        for m in deduction_pattern.finditer(full_text)
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
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )


def extract_w2(path: Path) -> W2 | ExtractionError:
    """Extract W-2 fields from a standard IRS Form W-2 PDF."""
    from paychecks.models.w2 import W2

    try:
        with pdfplumber.open(path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        return ExtractionError(
            source_file=path,
            field_name="<file>",
            message=f"Cannot open W-2 PDF: {exc}",
        )

    # Detect W-2c (corrected W-2) — not supported
    if re.search(r"w-?2c|corrected\s+wage", full_text, re.IGNORECASE):
        return ExtractionError(
            source_file=path,
            field_name="<w2c>",
            message=(
                f"Form W-2c (corrected W-2) is not supported. "
                f"Please use the original Form W-2 or the final corrected copy reissued as a standard W-2. "
                f"File: {path.name}"
            ),
        )

    # Detect tax year
    year_match = re.search(r"\b(20\d{2})\b", full_text)
    tax_year = int(year_match.group(1)) if year_match else 0

    def find_box_simple(label: str, field: str) -> Decimal | ExtractionError:
        m = re.search(rf"{re.escape(label)}[^$\n]*\$?([\d,]+\.\d{{2}})", full_text, re.IGNORECASE)
        if not m:
            return ExtractionError(
                source_file=path,
                field_name=field,
                message=f"W-2 {field} ({label}) not found in {path.name}.",
                page_number=1,
            )
        val = _parse_amount(m.group(1))
        if val is None:
            return ExtractionError(
                source_file=path,
                field_name=field,
                message=f"Could not parse W-2 {field} in {path.name}.",
                page_number=1,
            )
        return val

    box1 = find_box_simple("Box 1", "box1_wages")
    if isinstance(box1, ExtractionError):
        return box1
    box2 = find_box_simple("Box 2", "box2_federal_tax_withheld")
    if isinstance(box2, ExtractionError):
        return box2
    box3 = find_box_simple("Box 3", "box3_social_security_wages")
    if isinstance(box3, ExtractionError):
        return box3
    box4 = find_box_simple("Box 4", "box4_social_security_tax")
    if isinstance(box4, ExtractionError):
        return box4
    box5 = find_box_simple("Box 5", "box5_medicare_wages")
    if isinstance(box5, ExtractionError):
        return box5
    box6 = find_box_simple("Box 6", "box6_medicare_tax")
    if isinstance(box6, ExtractionError):
        return box6
    box16 = find_box_simple("Box 16", "box16_state_wages")
    if isinstance(box16, ExtractionError):
        return box16
    box17 = find_box_simple("Box 17", "box17_state_tax")
    if isinstance(box17, ExtractionError):
        return box17

    return W2(
        source_file=path,
        tax_year=tax_year,
        box1_wages=box1,
        box2_federal_tax_withheld=box2,
        box3_social_security_wages=box3,
        box4_social_security_tax=box4,
        box5_medicare_wages=box5,
        box6_medicare_tax=box6,
        box16_state_wages=box16,
        box17_state_tax=box17,
        extraction_method=ExtractionMethod.PDFPLUMBER,
    )
