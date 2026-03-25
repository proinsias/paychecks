"""Performance benchmark tests — constitution Principle IV thresholds.

Mark with @pytest.mark.slow so they can be excluded from regular runs:
    uv run pytest -m "not slow"
"""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path

import pytest

from tests.fixtures.builders.paycheck_builder import PaycheckBuilder


@pytest.mark.slow
def test_single_pdf_validates_under_two_seconds(tmp_path: Path) -> None:
    """Single PDF extraction + validation completes in < 2 seconds."""
    from paychecks.extractor.pdf import extract_paycheck
    from paychecks.models import ExtractionError
    from paychecks.models.enums import PayFrequency
    from paychecks.models.salary import SalarySchedule
    from paychecks.validator.paycheck import validate_paycheck

    pdf = PaycheckBuilder(annual_salary=120_000, frequency="biweekly").save(
        tmp_path / "paycheck.pdf"
    )
    schedule = SalarySchedule(
        base_annual_salary=Decimal("120000"),
        frequency=PayFrequency.BIWEEKLY,
    )

    start = time.perf_counter()
    result = extract_paycheck(pdf)
    assert not isinstance(result, ExtractionError), f"Extraction failed: {result}"
    validate_paycheck(result, schedule)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"Single PDF took {elapsed:.2f}s — expected < 2s"


@pytest.mark.slow
def test_batch_of_ten_pdfs_validates_under_ten_seconds(tmp_path: Path) -> None:
    """Batch of 10 PDFs validates in < 10 seconds."""
    from paychecks.models.enums import PayFrequency
    from paychecks.models.salary import SalarySchedule
    from paychecks.validator.paycheck import validate_batch

    builder = PaycheckBuilder(annual_salary=120_000, frequency="biweekly")
    pdfs = [builder.save(tmp_path / f"paycheck_{i:02d}.pdf") for i in range(10)]
    schedule = SalarySchedule(
        base_annual_salary=Decimal("120000"),
        frequency=PayFrequency.BIWEEKLY,
    )

    start = time.perf_counter()
    results = validate_batch(pdfs, schedule)
    elapsed = time.perf_counter() - start

    assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    assert elapsed < 10.0, f"Batch of 10 took {elapsed:.2f}s — expected < 10s"
