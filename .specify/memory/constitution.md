<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - I. Code Quality
  - II. Testing Standards
  - III. User Experience Consistency
  - IV. Performance Requirements
  - Quality Gates
  - Development Workflow
  - Governance
Removed sections: N/A
Templates reviewed:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check section present)
  - .specify/templates/spec-template.md ✅ aligned (mandatory User Scenarios & Success Criteria match principles)
  - .specify/templates/tasks-template.md ✅ aligned (test-first ordering, logging, performance tasks present)
Follow-up TODOs: None — all fields resolved.
-->

# Paychecks Constitution

## Core Principles

### I. Code Quality

Every piece of code merged into this project MUST be readable, maintainable, and purposeful.

- Functions and methods MUST have a single, clearly defined responsibility.
- Magic numbers and strings are forbidden; all constants MUST be named and documented.
- Dependencies MUST be minimal and each one MUST be explicitly justified; prefer standard
  library solutions before introducing third-party packages.
- All code MUST pass configured linting and formatting checks before merging.
- Complexity MUST be justified. If a simpler approach exists, it MUST be used.

**Rationale**: Paycheck and W2 data is sensitive financial information. Code that is hard
to read is hard to audit, increasing the risk of silent bugs in critical calculations.

### II. Testing Standards (NON-NEGOTIABLE)

Tests MUST be written and confirmed to fail before the implementation they cover is written
(test-driven development).

- Unit tests MUST cover all core business logic (parsing, comparison, calculations).
- Test coverage for core modules MUST be ≥ 80%.
- Integration tests MUST cover all end-to-end workflows (PDF ingestion → comparison → report).
- Edge cases involving malformed PDFs, missing fields, currency rounding, and mismatched
  periods MUST each have at least one dedicated test.
- The full unit test suite MUST complete in under 30 seconds.
- Tests MUST be independent: no test may rely on side effects from another test.

**Rationale**: Financial validation tools MUST be provably correct. Regressions in
comparison logic could cause users to miss paycheck errors or over/under-report income.

### III. User Experience Consistency

All user-facing interactions MUST follow consistent patterns throughout the application.

- Date formats MUST use ISO 8601 (YYYY-MM-DD) everywhere unless locale display requires
  otherwise, in which case formatting MUST be applied in a single, shared utility.
- Currency values MUST always display with two decimal places and an explicit currency symbol.
- Error messages MUST be human-readable, specific, and include actionable guidance
  (e.g., "Page 2 of paycheck_jan.pdf is missing the gross pay field — check the PDF version").
- All asynchronous operations (PDF parsing, file loading) MUST provide visible progress
  feedback and a clear completion or error state.
- Terminology MUST be consistent: use "paycheck" (not "pay stub"), "W-2" (not "W2" or "w2"),
  and "gross pay / net pay" throughout all UI and messages.

**Rationale**: Users rely on this tool for year-end financial accuracy. Inconsistent
presentation or confusing errors erode trust and increase the chance of user mistakes.

### IV. Performance Requirements

The application MUST remain responsive under normal personal-use workloads.

- PDF parsing MUST complete within 2 seconds per document on a modern consumer laptop.
- Year-end W-2 comparison (up to 52 paycheck PDFs) MUST complete within 10 seconds total.
- Application startup MUST complete within 3 seconds.
- Peak memory usage MUST stay below 200 MB during normal operation.
- Performance MUST be validated as part of integration tests; any regression beyond 20%
  of these thresholds MUST be investigated before merging.

**Rationale**: Sluggish tools get abandoned. Personal-finance workflows happen infrequently
(once a year for W-2 comparison) so startup and batch-processing speed matter more than
sustained throughput.

## Quality Gates

Every pull request MUST pass the following gates before merge:

- **Linting & Formatting**: All linting and formatter checks pass with zero warnings.
- **Test Suite**: Full test suite passes; no test may be skipped without a documented reason.
- **Coverage**: Core business logic modules maintain ≥ 80% line coverage.
- **Constitution Check**: The plan-template Constitution Check section MUST be reviewed
  and all violations documented in the Complexity Tracking table before Phase 0 may begin.
- **No Regressions**: Performance benchmarks within 20% of thresholds defined in Principle IV.

No gate may be bypassed without a written justification and explicit reviewer sign-off.

## Development Workflow

- Features MUST follow the speckit workflow: specify → clarify → plan → tasks → implement.
- Each user story MUST be independently implementable and testable before the next begins.
- Tests MUST be written first (red), then implementation (green), then refactor (clean).
- Commits MUST be atomic: one logical change per commit with a descriptive message.
- All sensitive financial data used in tests MUST be synthetic (anonymized or generated);
  real paycheck or W-2 data MUST never be committed to the repository.

## Governance

This constitution supersedes all other informal practices or prior verbal agreements.
Any amendment requires:

1. A written proposal describing the change and rationale.
2. Documented impact on existing features or tests.
3. Version bump following semantic versioning:
   - **MAJOR**: Removal or redefinition of an existing principle.
   - **MINOR**: New principle or section added; material expansion of guidance.
   - **PATCH**: Clarifications, wording fixes, non-semantic refinements.
4. Update to `LAST_AMENDED_DATE` upon ratification.

All PRs and design reviews MUST verify compliance with this constitution.
Complexity exceptions MUST be recorded in the plan's Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-03-22 | **Last Amended**: 2026-03-22
