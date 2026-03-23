from __future__ import annotations
import sys
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Optional

import typer

from paychecks.models import ExtractionError, PayFrequency, SalaryChange, SalarySchedule

app = typer.Typer(name="paychecks", help="Validate paycheck PDFs and reconcile with W-2.")


def _parse_salary_change(value: str) -> SalaryChange:
    """Parse 'YYYY-MM-DD:AMOUNT' into a SalaryChange."""
    from datetime import datetime
    try:
        date_str, amount_str = value.split(":")
        effective_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        amount = Decimal(amount_str.strip())
        return SalaryChange(effective_date=effective_date, annual_salary=amount)
    except (ValueError, AttributeError):
        raise typer.BadParameter(f"Invalid salary-change format: {value!r}. Use YYYY-MM-DD:AMOUNT")


def _build_schedule(
    salary: float,
    frequency: str,
    salary_changes: list[str],
) -> SalarySchedule:
    freq_map = {
        "weekly": PayFrequency.WEEKLY,
        "biweekly": PayFrequency.BIWEEKLY,
        "semimonthly": PayFrequency.SEMIMONTHLY,
        "monthly": PayFrequency.MONTHLY,
    }
    if frequency not in freq_map:
        raise typer.BadParameter(f"Unknown frequency: {frequency!r}")
    changes = tuple(_parse_salary_change(c) for c in (salary_changes or []))
    return SalarySchedule(
        base_annual_salary=Decimal(str(salary)),
        frequency=freq_map[frequency],
        changes=changes,
    )


def _dispatch_output(result, output: Path | None) -> None:
    """Write report to file if --output given; always also print to terminal."""
    from paychecks.reporter import terminal
    terminal.render_validation_result(result)

    if output is not None:
        suffix = output.suffix.lower()
        if suffix == ".csv":
            from paychecks.reporter.csv_export import write_validation_csv
            write_validation_csv(result, output)
        elif suffix == ".txt":
            from paychecks.reporter.text_export import write_validation_txt
            write_validation_txt(result, output)
        else:
            typer.echo(f"Error: unsupported output format '{suffix}'. Use .txt or .csv", err=True)
            raise typer.Exit(2)


@app.command()
def validate(
    pdf_path: Annotated[Path, typer.Argument(help="Path to the paycheck PDF file")],
    salary: Annotated[float, typer.Option("--salary", help="Annual gross salary in USD")],
    frequency: Annotated[str, typer.Option("--frequency", help="Pay frequency: weekly, biweekly, semimonthly, monthly")],
    salary_change: Annotated[Optional[list[str]], typer.Option("--salary-change", help="Mid-year change: YYYY-MM-DD:AMOUNT")] = None,
    tolerance: Annotated[float, typer.Option("--tolerance", help="Per-field tolerance in USD")] = 0.02,
    output: Annotated[Optional[Path], typer.Option("--output", help="Save report to .txt or .csv file")] = None,
) -> None:
    """Validate a single paycheck PDF against an annual salary."""
    from rich.status import Status
    from paychecks.extractor.pdf import extract_paycheck as _primary

    # Show spinner only when fallback extractors may be invoked
    with Status("Extracting paycheck data…", spinner="dots") as status:
        extracted = _primary(pdf_path)
        if isinstance(extracted, ExtractionError):
            status.update("Extracting via OCR…")
            from paychecks.extractor.ocr import extract_paycheck_ocr
            extracted = extract_paycheck_ocr(pdf_path)
        if isinstance(extracted, ExtractionError):
            status.update("Extracting via Claude CLI…")
            import pdfplumber
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            except Exception:
                text = ""
            from paychecks.extractor.claude_fallback import extract_paycheck_claude
            extracted = extract_paycheck_claude(pdf_path, text)

    if isinstance(extracted, ExtractionError):
        typer.echo(
            f"Error: {extracted.message}",
            err=True,
        )
        raise typer.Exit(2)

    schedule = _build_schedule(salary, frequency, salary_change or [])
    from paychecks.validator.paycheck import validate_paycheck
    result = validate_paycheck(extracted, schedule, Decimal(str(tolerance)))

    _dispatch_output(result, output)

    from paychecks.models.results import ValidationStatus
    if result.overall_status == ValidationStatus.FAIL:
        raise typer.Exit(1)
    if result.overall_status == ValidationStatus.WARNING:
        raise typer.Exit(1)


@app.command()
def reconcile(
    paychecks_dir: Annotated[Path, typer.Argument(help="Directory of paycheck PDFs")],
    w2_pdf: Annotated[Path, typer.Argument(help="Path to the W-2 PDF file")],
    salary: Annotated[float, typer.Option("--salary", help="Annual gross salary in USD")],
    frequency: Annotated[str, typer.Option("--frequency", help="Pay frequency")],
    salary_change: Annotated[Optional[list[str]], typer.Option("--salary-change")] = None,
    w2_tolerance: Annotated[float, typer.Option("--w2-tolerance")] = 1.00,
    output: Annotated[Optional[Path], typer.Option("--output")] = None,
) -> None:
    """Year-end W-2 reconciliation against aggregated paycheck data."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from paychecks.extractor import extract
    from paychecks.extractor.pdf import extract_w2
    from paychecks.models import ExtractionError
    from paychecks.validator.w2 import reconcile as do_reconcile
    from paychecks.reporter.terminal import render_reconciliation_report

    schedule = _build_schedule(salary, frequency, salary_change or [])

    # Collect PDF files (exclude W-2 PDF itself)
    pdf_files = sorted(
        p for p in paychecks_dir.glob("*.pdf") if p.resolve() != w2_pdf.resolve()
    )
    if not pdf_files:
        typer.echo(f"Error: No PDF files found in {paychecks_dir}", err=True)
        raise typer.Exit(2)

    # Extract all paychecks
    paychecks = []
    errors = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Extracting {len(pdf_files)} paycheck PDFs…", total=len(pdf_files))
        for pdf in pdf_files:
            result = extract(pdf)
            if isinstance(result, ExtractionError):
                errors.append(result)
            else:
                paychecks.append(result)
            progress.advance(task)

    for err in errors:
        typer.echo(f"Warning: {err.message}", err=True)

    if not paychecks:
        typer.echo("Error: Could not extract any paycheck data.", err=True)
        raise typer.Exit(2)

    # Extract W-2
    w2_result = extract_w2(w2_pdf)
    if isinstance(w2_result, ExtractionError):
        typer.echo(f"Error: {w2_result.message}", err=True)
        raise typer.Exit(2)

    report = do_reconcile(paychecks, w2_result, schedule, Decimal(str(w2_tolerance)))
    render_reconciliation_report(report)

    if output:
        suffix = output.suffix.lower()
        if suffix == ".csv":
            from paychecks.reporter.csv_export import write_reconciliation_csv
            write_reconciliation_csv(report, output)
        elif suffix == ".txt":
            from paychecks.reporter.text_export import write_reconciliation_txt
            write_reconciliation_txt(report, output)
        else:
            typer.echo(f"Error: unsupported output format '{suffix}'. Use .txt or .csv", err=True)
            raise typer.Exit(2)

    from paychecks.models.results import ValidationStatus
    if report.overall_status == ValidationStatus.FAIL:
        raise typer.Exit(1)
    if report.overall_status == ValidationStatus.WARNING:
        raise typer.Exit(1)


@app.command()
def batch(
    paychecks_dir: Annotated[Path, typer.Argument(help="Directory of paycheck PDFs")],
    salary: Annotated[float, typer.Option("--salary", help="Annual gross salary in USD")],
    frequency: Annotated[str, typer.Option("--frequency", help="Pay frequency")],
    salary_change: Annotated[Optional[list[str]], typer.Option("--salary-change")] = None,
    tolerance: Annotated[float, typer.Option("--tolerance")] = 0.02,
    output: Annotated[Optional[Path], typer.Option("--output")] = None,
) -> None:
    """Validate all paycheck PDFs in a folder."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from paychecks.extractor import extract
    from paychecks.models import ExtractionError
    from paychecks.validator.paycheck import validate_paycheck
    from paychecks.reporter.terminal import render_batch_summary

    schedule = _build_schedule(salary, frequency, salary_change or [])
    pdf_files = sorted(paychecks_dir.glob("*.pdf"))
    if not pdf_files:
        typer.echo(f"Error: No PDF files found in {paychecks_dir}", err=True)
        raise typer.Exit(2)

    results = []
    extraction_errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task(f"Processing {len(pdf_files)} paychecks…", total=len(pdf_files))
        for pdf in pdf_files:
            extracted = extract(pdf)
            if isinstance(extracted, ExtractionError):
                extraction_errors.append(extracted)
                typer.echo(f"Warning: {extracted.message}", err=True)
            else:
                results.append(validate_paycheck(extracted, schedule, Decimal(str(tolerance))))
            progress.advance(task)

    render_batch_summary(results)

    if output:
        suffix = output.suffix.lower()
        if suffix == ".csv":
            from paychecks.reporter.csv_export import write_batch_csv
            write_batch_csv(results, output)
        elif suffix == ".txt":
            from paychecks.reporter.text_export import write_batch_txt
            write_batch_txt(results, output)

    from paychecks.models.results import ValidationStatus
    has_errors = bool(extraction_errors)
    has_failures = any(r.overall_status == ValidationStatus.FAIL for r in results)
    has_warnings = any(r.overall_status == ValidationStatus.WARNING for r in results)

    if has_errors:
        raise typer.Exit(2)
    if has_failures or has_warnings:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
