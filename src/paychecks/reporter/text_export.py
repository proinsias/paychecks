from __future__ import annotations
from pathlib import Path
from paychecks.models import PaycheckValidationResult
from paychecks.constants import CURRENCY_SYMBOL
from paychecks.models.results import ValidationStatus
from decimal import Decimal


def _fmt(value: Decimal | None) -> str:
    return f"{CURRENCY_SYMBOL}{value:,.2f}" if value is not None else "—"


def _status(s: ValidationStatus) -> str:
    return s.value


def write_validation_txt(result: PaycheckValidationResult, path: Path) -> None:
    p = result.paycheck
    lines = [
        f"Paycheck Validation: {p.source_file.name}",
        f"Period: {p.pay_period_start} - {p.pay_period_end}",
        f"Salary: {_fmt(result.salary_used)}/yr  Periods/yr: {result.pay_periods_per_year}",
        "",
        f"{'Field':<30} {'Expected':>12} {'Actual':>12} {'Status':>8}",
        "-" * 66,
    ]
    for fr in result.field_results:
        lines.append(
            f"{fr.field_name:<30} {_fmt(fr.expected):>12} {_fmt(fr.actual):>12} {_status(fr.status):>8}"
        )
    lines += ["", f"Overall: {_status(result.overall_status)}"]
    path.write_text("\n".join(lines))


def write_reconciliation_txt(report, path: Path) -> None:
    w2 = report.w2
    lines = [
        f"W-2 Reconciliation Report: Tax Year {w2.tax_year}",
        f"Paychecks: {len(report.paychecks)} found  Missing: {len(report.missing_periods)}",
        "",
        f"{'W-2 Field':<30} {'Paycheck Total':>15} {'W-2 Value':>12} {'Diff':>10} {'Status':>8}",
        "-" * 80,
    ]
    for f in report.fields:
        diff_str = f"${abs(f.difference):,.2f}"
        if f.difference < 0:
            diff_str = f"-{diff_str}"
        lines.append(
            f"{f.field_name:<30} {_fmt(f.paycheck_total):>15} {_fmt(f.w2_value):>12} {diff_str:>10} {_status(f.status):>8}"
        )
    if report.missing_periods:
        lines += ["", f"Missing periods: {', '.join(str(d) for d in report.missing_periods)}"]
    lines += ["", f"Overall: {_status(report.overall_status)}"]
    path.write_text("\n".join(lines))


def write_batch_txt(results: list, path: Path) -> None:
    lines = [
        f"Batch Validation Summary \u2014 {len(results)} paychecks",
        "",
        f"{'File':<24} {'Period':<24} {'Gross':>12} {'Net':>12} {'Status':>8}",
        "-" * 84,
    ]
    for r in results:
        p = r.paycheck
        period = f"{p.pay_period_start} \u2013 {p.pay_period_end}"
        lines.append(
            f"{p.source_file.name:<24} {period:<24} {_fmt(p.gross_pay):>12} {_fmt(p.net_pay):>12} {_status(r.overall_status):>8}"
        )
    passed = sum(1 for r in results if r.overall_status.value == "PASS")
    failed = sum(1 for r in results if r.overall_status.value == "FAIL")
    lines += ["", f"Summary: {passed} PASS  |  {failed} FAIL"]
    path.write_text("\n".join(lines))
