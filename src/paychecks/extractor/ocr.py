from __future__ import annotations

from pathlib import Path

from paychecks.models import ExtractionError, Paycheck


def extract_paycheck_ocr(path: Path) -> Paycheck | ExtractionError:
    """OCR fallback using pytesseract + pdf2image."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        return ExtractionError(
            source_file=path,
            field_name="<ocr>",
            message=f"OCR dependencies not available: {e}",
        )

    try:
        images = convert_from_path(str(path))
    except Exception as exc:
        return ExtractionError(
            source_file=path,
            field_name="<file>",
            message=f"Cannot convert PDF to images for OCR: {exc}",
        )

    from paychecks.models.enums import ExtractionMethod

    # Write OCR text into a searchable PDF via a temp text file,
    # then re-run pdfplumber-style regex on the combined OCR text.
    texts = []
    for i, img in enumerate(images):
        try:
            text = pytesseract.image_to_string(img)
            texts.append(text)
        except Exception as exc:
            return ExtractionError(
                source_file=path,
                field_name="<ocr>",
                message=f"OCR failed on page {i + 1} of {path.name}: {exc}",
                page_number=i + 1,
            )

    # Reuse pdfplumber regex logic on OCR text by writing to a temp file
    # and parsing with the same patterns via a thin adapter.
    from paychecks.extractor._text_parser import parse_paycheck_from_text

    result = parse_paycheck_from_text(path, "\n".join(texts), ExtractionMethod.OCR)
    return result
