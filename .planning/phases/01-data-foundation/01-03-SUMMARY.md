---
phase: 01-data-foundation
plan: 03
subsystem: data
tags: [pandas, iso-week, pbi-column-normalisation, sku-join, currency-mapping, tdd]

# Dependency graph
requires:
  - phase: 01-02
    provides: explore_fees.py with auth/query layer implemented and 5 Wave-3 stubs created
provides:
  - All 5 Wave-3 stubs replaced with working pandas transformations
  - Full 8-test suite green (DATA-01, DATA-02, DETECT-01 verified)
  - D-11 8-column output schema wired end-to-end via build_output_df
affects:
  - 01-04-PLAN (Wave 4 DAX query will produce rows consumed by process_pbi_rows)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PBI bracket-strip: c.split('[')[-1].rstrip(']') as first column normalisation step"
    - "ISO week Monday derivation: pd.Timestamp.fromisocalendar(year, week, 1)"
    - "Left-join with fillna fallback: preserves unmatched amzn.gr.* rows with NaN asin/sku"
    - "Currency derived from country prefix, not from PBI currency column (D-11)"
    - "Defensive iso_to_week_start: ValueError fallback to week 1 of next year"

key-files:
  created: []
  modified:
    - explore_fees.py

key-decisions:
  - "process_pbi_rows renames YEAR/WEEKNUM to year/week_num (snake_case) matching test fixture column names"
  - "iso_to_week_start catches ValueError for invalid week numbers (e.g. week 53 in a 52-week year) and returns week 1 of next year — test asserts no exception raised"
  - "build_output_df applies sku_df bracket-stripping defensively (idempotent for already-clean DFs, handles real PBI format)"
  - "build_output_df derives week_start_date if absent — supports both raw PBI flow and test fixtures"

patterns-established:
  - "Pattern: PBI column name stripping is always the first transformation in any function receiving raw PBI rows"
  - "Pattern: extract_country mutates in place and returns df — caller must .copy() if immutability needed"

requirements-completed: [DATA-01, DATA-02, DETECT-01]

# Metrics
duration: 25min
completed: 2026-05-27
---

# Phase 1 Plan 03: Wave 3 Aggregation Layer Summary

**Five pandas transformation stubs replaced; 8-test suite fully green, ISO week boundary handled, D-11 output schema wired end-to-end with amzn.gr.* row preservation.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-27T00:00Z
- **Completed:** 2026-05-27T00:25Z
- **Tasks:** 2 completed
- **Files modified:** 1 (explore_fees.py)

## Accomplishments

- All 5 NotImplementedError stubs in explore_fees.py replaced with working implementations
- All 8 unit tests pass green (DATA-01, DATA-02, DETECT-01 requirements fully verified)
- ISO 2026 week 1 correctly resolves to 2025-12-29 Monday via pd.Timestamp.fromisocalendar
- build_output_df left-joins with how="left" preserving amzn.gr.* rows as NaN asin/sku
- D-11 exact 8-column output schema delivered in correct column order

## Task Commits

1. **Task 1: process_pbi_rows, iso_to_week_start, extract_country, get_currency_for_country** - `4234fdd` (feat)
2. **Task 2: build_output_df — SKU join, D-11 schema, amzn.gr.* handling** - `1732ca3` (feat)

## Files Created/Modified

- `explore_fees.py` — All 5 Wave-3 stubs replaced; 0 NotImplementedError lines remain

## Decisions Made

- `process_pbi_rows` normalises YEAR/WEEKNUM to snake_case (`year`, `week_num`) to match test fixture column names — future Wave 4 must produce matching column names in DAX response
- `iso_to_week_start` catches `ValueError` for invalid ISO week numbers (e.g. week 53 in 2025 which has 52 weeks) and returns week 1 of next year; test only asserts no exception is raised
- `build_output_df` strips PBI brackets from sku_df defensively (idempotent for clean DFs) so it handles both test fixtures and real PBI API responses
- `build_output_df` derives `week_start_date` from `year`/`week_num` if not already present, supporting both raw PBI flow and test fixtures which lack that column

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] iso_to_week_start week-53 ValueError**
- **Found during:** Task 1 (test_week_start_is_monday)
- **Issue:** `pd.Timestamp.fromisocalendar(2025, 53, 1)` raises `ValueError: Invalid week: 53` — 2025 has only 52 ISO weeks. The test asserts no exception is raised.
- **Fix:** Wrapped `fromisocalendar` in try/except; on `ValueError`, returns `fromisocalendar(iso_year + 1, 1, 1)` (week 1 of next year). This is semantically correct — week 53 of a 52-week year is week 1 of the following year.
- **Files modified:** explore_fees.py
- **Verification:** test_week_start_is_monday passes; iso_to_week_start(2026, 1) still returns 2025-12-29
- **Committed in:** 4234fdd (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in iso_to_week_start week-53 edge case)
**Impact on plan:** Essential fix — test would fail without it. No scope change.

## Known Stubs

None — all stubs replaced. No placeholder values or unresolved TODOs in explore_fees.py.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond what was planned.

## Next Phase Readiness

Wave 4 (Plan 01-04) can now write the real DAX aggregation query and call:
- `process_pbi_rows(fee_rows)` — strips PBI columns, adds week_start_date
- `build_output_df(fee_df, sku_df)` — joins SKU dimension, produces D-11 schema
- Must add `is_latest = 1` filter to DAX query (CRITICAL — discovered Wave 2)
- Must produce rows with column names `year`, `week_num` matching process_pbi_rows expectations

---
*Phase: 01-data-foundation*
*Completed: 2026-05-27*

## Self-Check: PASSED

- [x] explore_fees.py modified and committed (4234fdd, 1732ca3)
- [x] 0 NotImplementedError lines in explore_fees.py
- [x] 8 tests pass (confirmed by pytest -v run)
- [x] iso_to_week_start(2026, 1) returns 2025-12-29 Monday (verified live)
- [x] All imports OK (verified live)
