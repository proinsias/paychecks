from __future__ import annotations
import json
import subprocess
from decimal import Decimal
from datetime import date
from pathlib import Path

from paychecks.constants import CLAUDE_CLI_TIMEOUT_SECONDS
from paychecks.models import ExtractionError, Paycheck, Deduction
from paychecks.models.enums import ExtractionMethod


_PROMPT_TEMPLATE = """\
Extract paycheck fields from the following text and return a JSON object with these exact keys:
pay_period_start (YYYY-MM-DD), pay_period_end (YYYY-MM-DD), gross_pay (float),
federal_tax_withheld (float), social_security_tax_withheld (float),
medicare_tax_withheld (float), state_tax_withheld (float), net_pay (float),
other_deductions (list of {{"name": str, "amount": float}}).

Return ONLY valid JSON, no explanation.

Text:
{text}
"""


def extract_paycheck_claude(path: Path, extracted_text: str) -> Paycheck | ExtractionError:
    """Final fallback: call claude CLI to extract paycheck fields from text."""
    prompt = _PROMPT_TEMPLATE.format(text=extracted_text[:8000])
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return ExtractionError(
            source_file=path,
            field_name="<claude>",
            message="claude CLI not found. Install claude CLI to enable final-fallback extraction.",
        )
    except subprocess.TimeoutExpired:
        return ExtractionError(
            source_file=path,
            field_name="<claude>",
            message=f"claude CLI timed out after {CLAUDE_CLI_TIMEOUT_SECONDS}s for {path.name}.",
        )

    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return ExtractionError(
            source_file=path,
            field_name="<claude>",
            message=f"claude CLI returned non-JSON response for {path.name}.",
        )

    try:
        from paychecks.extractor._text_parser import _parse_date_str
        return Paycheck(
            source_file=path,
            pay_period_start=_parse_date_str(data["pay_period_start"]),
            pay_period_end=_parse_date_str(data["pay_period_end"]),
            gross_pay=Decimal(str(data["gross_pay"])),
            federal_tax_withheld=Decimal(str(data["federal_tax_withheld"])),
            social_security_tax_withheld=Decimal(str(data["social_security_tax_withheld"])),
            medicare_tax_withheld=Decimal(str(data["medicare_tax_withheld"])),
            state_tax_withheld=Decimal(str(data["state_tax_withheld"])),
            other_deductions=tuple(
                Deduction(name=d["name"], amount=Decimal(str(d["amount"])))
                for d in data.get("other_deductions", [])
            ),
            net_pay=Decimal(str(data["net_pay"])),
            extraction_method=ExtractionMethod.CLAUDE_CLI,
        )
    except (KeyError, ValueError) as exc:
        return ExtractionError(
            source_file=path,
            field_name="<claude>",
            message=f"claude CLI response missing required field: {exc}",
        )
