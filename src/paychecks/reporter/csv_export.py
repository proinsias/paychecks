from __future__ import annotations

import csv
from pathlib import Path

from paychecks.models import PaycheckValidationResult


def write_validation_csv(result: PaycheckValidationResult, path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "expected", "actual", "status", "note"])
        for fr in result.field_results:
            writer.writerow(
                [
                    fr.field_name,
                    str(fr.expected) if fr.expected is not None else "",
                    str(fr.actual) if fr.actual is not None else "",
                    fr.status.value,
                    fr.note or "",
                ]
            )


def write_reconciliation_csv(report, path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "w2_value", "paycheck_total", "difference", "status"])
        for field in report.fields:
            writer.writerow(
                [
                    field.field_name,
                    str(field.w2_value),
                    str(field.paycheck_total),
                    str(field.difference),
                    field.status.value,
                ]
            )


def write_batch_csv(results: list, path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "period_start", "period_end", "gross_pay", "net_pay", "status"])
        for r in results:
            p = r.paycheck
            writer.writerow(
                [
                    p.source_file.name,
                    str(p.pay_period_start),
                    str(p.pay_period_end),
                    str(p.gross_pay),
                    str(p.net_pay),
                    r.overall_status.value,
                ]
            )
