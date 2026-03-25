from __future__ import annotations

from decimal import Decimal

from rich import box
from rich.console import Console
from rich.table import Table

from paychecks.constants import CURRENCY_SYMBOL
from paychecks.models import PaycheckValidationResult
from paychecks.models.results import ValidationStatus

console = Console()


def _fmt_currency(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{CURRENCY_SYMBOL}{value:,.2f}"


def _status_badge(status: ValidationStatus) -> str:
    return {
        ValidationStatus.PASS: "✅ PASS",
        ValidationStatus.FAIL: "❌ FAIL",
        ValidationStatus.WARNING: "⚠️  WARN",
    }[status]


def render_validation_result(result: PaycheckValidationResult) -> None:
    """Print a per-paycheck validation report to the terminal."""
    p = result.paycheck
    title = f"Paycheck Validation: {p.source_file.name}"
    header = (
        f"Period: {p.pay_period_start} – {p.pay_period_end}  |  "
        f"Salary: {_fmt_currency(result.salary_used)}/yr  |  "
        f"Periods/yr: {result.pay_periods_per_year}"
    )
    console.print(f"\n[bold]{title}[/bold]")
    console.print(header)

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
    table.add_column("Field", style="cyan", min_width=28)
    table.add_column("Expected", justify="right", min_width=12)
    table.add_column("Actual", justify="right", min_width=12)
    table.add_column("Status", min_width=10)

    for fr in result.field_results:
        badge = _status_badge(fr.status)
        row_style = "red" if fr.status == ValidationStatus.FAIL else ""
        table.add_row(
            fr.field_name,
            _fmt_currency(fr.expected),
            _fmt_currency(fr.actual),
            badge,
            style=row_style,
        )

    console.print(table)
    overall = _status_badge(result.overall_status)
    console.print(f"Overall: {overall}\n")


def render_reconciliation_report(report) -> None:
    """Print a W-2 reconciliation report to the terminal."""
    w2 = report.w2
    title = f"W-2 Reconciliation Report: Tax Year {w2.tax_year}"
    found = len(report.paychecks)
    expected = report.pay_periods_per_year
    missing_count = len(report.missing_periods)
    header = f"Paychecks: {found} found  |  Expected: {expected}  |  Missing: {missing_count}"

    console.print(f"\n[bold]{title}[/bold]")
    console.print(header)

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
    table.add_column("W-2 Field", style="cyan", min_width=28)
    table.add_column("Paycheck Total", justify="right", min_width=14)
    table.add_column("W-2 Value", justify="right", min_width=14)
    table.add_column("Difference", justify="right", min_width=12)
    table.add_column("Status", min_width=10)

    for f in report.fields:
        badge = _status_badge(f.status)
        row_style = "red" if f.status == ValidationStatus.FAIL else ""
        diff_str = f"{CURRENCY_SYMBOL}{abs(f.difference):,.2f}"
        if f.difference < 0:
            diff_str = f"-{diff_str}"
        table.add_row(
            f.field_name,
            _fmt_currency(f.paycheck_total),
            _fmt_currency(f.w2_value),
            diff_str,
            badge,
            style=row_style,
        )

    console.print(table)

    if report.missing_periods:
        extra = (
            f" (+{len(report.missing_periods) - 5} more)" if len(report.missing_periods) > 5 else ""
        )
        periods_str = ", ".join(str(d) for d in report.missing_periods[:5])
        console.print(f"[yellow]Missing periods: {periods_str}{extra}[/yellow]")

    overall = _status_badge(report.overall_status)
    console.print(f"Overall: {overall}\n")


def render_batch_summary(results: list) -> None:
    """Print batch validation summary table."""
    if not results:
        console.print("[yellow]No paychecks were successfully processed.[/yellow]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
        title=f"Batch Validation Summary — {len(results)} paychecks",
    )
    table.add_column("File", style="cyan", min_width=24)
    table.add_column("Period", min_width=24)
    table.add_column("Gross Pay", justify="right", min_width=12)
    table.add_column("Net Pay", justify="right", min_width=12)
    table.add_column("Status", min_width=10)

    for r in results:
        p = r.paycheck
        badge = _status_badge(r.overall_status)
        row_style = "red" if r.overall_status.value == "FAIL" else ""
        table.add_row(
            p.source_file.name,
            f"{p.pay_period_start} \u2013 {p.pay_period_end}",
            _fmt_currency(p.gross_pay),
            _fmt_currency(p.net_pay),
            badge,
            style=row_style,
        )
        if r.overall_status.value == "FAIL":
            for fr in r.field_results:
                if fr.status.value == "FAIL" and fr.note:
                    table.add_row("", f"  \u2514\u2500 {fr.note}", "", "", "", style="red")

    console.print(table)

    passed = sum(1 for r in results if r.overall_status.value == "PASS")
    failed = sum(1 for r in results if r.overall_status.value == "FAIL")
    warned = sum(1 for r in results if r.overall_status.value == "WARNING")
    console.print(f"Summary: {passed} PASS  |  {failed} FAIL  |  {warned} WARNING\n")
