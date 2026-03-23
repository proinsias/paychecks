# CLI Contract: paychecks

**Branch**: `001-paycheck-w2-validator` | **Date**: 2026-03-22

The `paychecks` CLI exposes three subcommands. All subcommands:
- Print structured reports to **stdout**
- Print warnings and errors to **stderr**
- Exit **0** if all validations pass
- Exit **1** if any validation fails or a W-2 mismatch is found
- Exit **2** on input/extraction errors (unreadable PDF, missing required argument)

---

## Global Options

```
paychecks [--version] [--help]
```

| Flag | Description |
|------|-------------|
| `--version` | Print version and exit |
| `--help` | Print help and exit |

---

## `paychecks validate` — Validate a single paycheck PDF

**User Story**: US1 (P1)

```
paychecks validate <PDF_PATH>
    --salary FLOAT
    --frequency {weekly,biweekly,semimonthly,monthly}
    [--salary-change DATE:FLOAT ...]
    [--tolerance FLOAT]
    [--output FILE]
    [--help]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PDF_PATH` | path | Yes | Path to the paycheck PDF file |

### Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--salary` | float | Yes | — | Annual gross salary in USD |
| `--frequency` | enum | Yes | — | Pay frequency: `weekly`, `biweekly`, `semimonthly`, `monthly` |
| `--salary-change` | DATE:FLOAT | No | — | Mid-year salary change; format `YYYY-MM-DD:AMOUNT`; repeatable |
| `--tolerance` | float | No | `0.02` | Per-field tolerance in USD for pass/fail |
| `--output` | path | No | — | Save report to file (`.txt` or `.csv` inferred from extension) |

### Stdout (terminal table — Rich)

```
Paycheck Validation: paycheck_jan.pdf
Period: 2025-01-01 – 2025-01-15  |  Frequency: biweekly  |  Salary: $120,000.00

Field                      Expected      Actual       Status
─────────────────────────────────────────────────────────────
Gross Pay                  $4,615.38    $4,615.38    ✅ PASS
Net Pay                    $3,201.14    $3,201.14    ✅ PASS
Federal Tax Withheld       —            $812.00      ✅ PASS
Social Security Tax        —            $286.15      ✅ PASS
Medicare Tax               —            $66.92       ✅ PASS
State Tax Withheld         —            $276.92      ✅ PASS

Overall: ✅ PASS
```

### Stdout (CSV — when --output report.csv)

```csv
field,expected,actual,status,note
Gross Pay,4615.38,4615.38,PASS,
Net Pay,3201.14,3201.14,PASS,
Federal Tax Withheld,,812.00,PASS,
...
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All fields PASS |
| 1 | One or more fields FAIL or WARNING |
| 2 | PDF could not be read or required argument missing |

---

## `paychecks reconcile` — Year-end W-2 reconciliation

**User Story**: US2 (P2)

```
paychecks reconcile <PAYCHECKS_DIR> <W2_PDF>
    --salary FLOAT
    --frequency {weekly,biweekly,semimonthly,monthly}
    [--salary-change DATE:FLOAT ...]
    [--w2-tolerance FLOAT]
    [--output FILE]
    [--help]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PAYCHECKS_DIR` | path | Yes | Directory containing all paycheck PDFs for the year |
| `W2_PDF` | path | Yes | Path to the W-2 PDF file |

### Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--salary` | float | Yes | — | Annual gross salary in USD |
| `--frequency` | enum | Yes | — | Pay frequency |
| `--salary-change` | DATE:FLOAT | No | — | Mid-year salary change; repeatable |
| `--w2-tolerance` | float | No | `1.00` | Tolerance in USD for W-2 field matching |
| `--output` | path | No | — | Save report to file (`.txt` or `.csv`) |

### Stdout (terminal — Rich)

```
W-2 Reconciliation Report: Tax Year 2025
Paychecks: 26 found  |  Expected: 26  |  Missing: 0
Frequency: biweekly  |  Salary: $120,000.00

W-2 Field                  Paycheck Total   W-2 Value    Difference   Status
───────────────────────────────────────────────────────────────────────────────
Box 1 — Wages              $120,000.00      $120,000.00  $0.00        ✅ PASS
Box 2 — Federal Tax        $21,112.00       $21,112.00   $0.00        ✅ PASS
Box 3 — SS Wages           $120,000.00      $120,000.00  $0.00        ✅ PASS
Box 4 — SS Tax             $7,440.00        $7,440.00    $0.00        ✅ PASS
Box 5 — Medicare Wages     $120,000.00      $120,000.00  $0.00        ✅ PASS
Box 6 — Medicare Tax       $1,740.00        $1,740.00    $0.00        ✅ PASS
Box 16 — State Wages       $120,000.00      $120,000.00  $0.00        ✅ PASS
Box 17 — State Tax         $7,200.00        $7,200.00    $0.00        ✅ PASS

Overall: ✅ PASS
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All W-2 fields match within tolerance |
| 1 | One or more W-2 fields mismatch, or missing pay periods detected |
| 2 | PDF(s) unreadable, directory empty, or required argument missing |

---

## `paychecks batch` — Validate all paychecks in a folder

**User Story**: US3 (P3)

```
paychecks batch <PAYCHECKS_DIR>
    --salary FLOAT
    --frequency {weekly,biweekly,semimonthly,monthly}
    [--salary-change DATE:FLOAT ...]
    [--tolerance FLOAT]
    [--output FILE]
    [--help]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PAYCHECKS_DIR` | path | Yes | Directory containing paycheck PDFs |

### Options

Same as `validate` except `PDF_PATH` is replaced by `PAYCHECKS_DIR`.

### Stdout (terminal — Rich)

```
Batch Validation: /home/user/paychecks/2025/
Processing 26 paychecks... ████████████████████ 100%

File                    Period                Gross Pay    Net Pay     Status
──────────────────────────────────────────────────────────────────────────────
paycheck_01.pdf         2025-01-01–01-15      $4,615.38    $3,201.14   ✅ PASS
paycheck_02.pdf         2025-01-16–01-31      $4,615.38    $3,150.00   ❌ FAIL
  └─ Net Pay: expected $3,201.14, got $3,150.00 (diff: $51.14)
paycheck_03.pdf         2025-02-01–02-15      $4,615.38    $3,201.14   ✅ PASS
...

Summary: 25 PASS  |  1 FAIL  |  0 WARNING
Missing periods: none detected
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All paychecks PASS |
| 1 | One or more paychecks FAIL or WARNING |
| 2 | Directory unreadable, no PDFs found, or required argument missing |

---

## Shared Behaviors

### `--salary-change` format

Repeatable flag for mid-year salary changes:

```
paychecks validate paycheck_aug.pdf \
  --salary 100000 \
  --frequency biweekly \
  --salary-change 2025-07-01:120000
```

Interpretation: salary is $100,000/year before 2025-07-01, then $120,000/year from that date onwards.

### `--output` format detection

| Extension | Format |
|-----------|--------|
| `.txt` | Plain text (same content as terminal, no Rich styling) |
| `.csv` | CSV with headers: `field,expected,actual,status,note` |
| Other | Error: unsupported output format |

### W-2c detection

If a W-2 PDF is identified as Form W-2c (corrected W-2), the CLI MUST:
1. Print to stderr: `Error: Form W-2c (corrected W-2) is not supported. Please use the original Form W-2 or the final corrected copy reissued as a standard W-2.`
2. Exit with code 2.
