from __future__ import annotations
from pathlib import Path

import pdfplumber

from paychecks.models import ExtractionError, Paycheck
from paychecks.extractor.pdf import extract_paycheck as _extract_pdfplumber
from paychecks.extractor.ocr import extract_paycheck_ocr as _extract_ocr
from paychecks.extractor.claude_fallback import extract_paycheck_claude as _extract_claude


def extract(path: Path) -> Paycheck | ExtractionError:
    """Run extraction cascade: pdfplumber → OCR → claude CLI."""
    # Primary: pdfplumber
    result = _extract_pdfplumber(path)
    if isinstance(result, Paycheck):
        return result

    # Secondary: OCR
    ocr_result = _extract_ocr(path)
    if isinstance(ocr_result, Paycheck):
        return ocr_result

    # Final: claude CLI — pass pdfplumber extracted text as context
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        text = ""
    claude_result = _extract_claude(path, text)
    if isinstance(claude_result, Paycheck):
        return claude_result

    # All failed — return the primary error (most informative)
    return result
