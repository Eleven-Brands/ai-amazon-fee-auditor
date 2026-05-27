---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-05-27T20:55:00.425Z"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 4
  completed_plans: 3
  percent: 0
---

# Project State: AI Amazon Fee Auditor

**Last updated:** 2026-05-27
**Session:** Phase 1 executing — Wave 3 complete, Wave 4 next

---

## Project Reference

**Core value:** Detect FBA fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

**Current focus:** Phase 1 — Data Foundation

**Repository:** AI Amazon Fee Auditor (gsd/phase-01-data-foundation branch)

---

## Current Position

**Phase:** 1 — Data Foundation
**Plan:** Wave 4 — Plan 01-04 (next to execute)
**Status:** Executing

```
Progress: [████████░░] 75%
Phase 1: [►] Data Foundation  ← EXECUTING — Wave 4/4
Phase 2: [ ] Detection + Output Pipeline
Phase 3: [ ] Scheduling + Operationalization
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 3 |
| Phases complete | 0 |
| Plans total | 4 (Phase 1) |
| Plans complete | 3 |
| Requirements mapped | 11/11 |

---

## Accumulated Context

### Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| 3-phase structure (not 5-8) | Sequential dependencies make 3 natural delivery boundaries — data → detection → execution; splitting further would create non-deliverable phases |
| Historical baseline (not rate card) | No external rate card dependency; faster; catches all fee changes regardless of cause |
| Single agent MVP | Avoids over-engineering before complexity is proven |
| Claude is narrative layer only | All math in Python; Claude receives anomaly list, never raw rows; respects token budget |
| n8n for scheduling | Cloud-hosted, retry logic, no local machine dependency |
| Rolling 8-week median per SKU per Sales Region | Median is more robust to outliers than mean; per-unit normalization needed for volume-adjusted fairness |
| output/* with !output/.gitkeep gitignore pattern | Tracks sentinel file to preserve output/ in git while ignoring all CSV contents |
| 8 tests use natural ImportError RED state | No @pytest.mark.skip or xfail — enforces TDD discipline for Wave 2 implementation |
| fact_fee_preview[currency] column exists (A2 resolved) | D-11 country-derived currency kept; PBI column available as direct source for Phase 2 if preferred |
| Wave 4 DAX MUST filter is_latest = 1 | fact_fee_preview stores current + historical fee schedules; is_latest = 0 rows are stale and must be excluded from aggregation |
| process_pbi_rows normalises YEAR/WEEKNUM to year/week_num (snake_case) | Wave 4 DAX column aliases must match these names — document in 01-04-PLAN.md |
| iso_to_week_start catches ValueError for week 53 in 52-week years | Returns week 1 of next year; test asserts no exception raised for iso_to_week_start(2025, 53) |
| build_output_df handles both raw PBI and pre-cleaned DataFrames | Bracket-strip on sku_df is idempotent; week_start_date derived if absent |

### Open Questions (Phase 1 Must Resolve)

- Does Power BI expose fee-per-unit or only total fee per period per SKU? — RESOLVED (Wave 2): `expected_fulfillment_fee_per_unit` confirmed in schema
- Are FBA fee credits/reimbursements already netted in Power BI, or separate line items?
- How many weeks of history are available per SKU? (Need ≥4 for rolling median)
- How many active US SKUs? (>500 may need top-N filter to manage alert volume)
- Does Power BI require explicit marketplace filter? (Avoid mixing fee structures across regions)
- Which ClickUp task ID receives the reports? (Required before Phase 2)
- Does `powerbi-query` skill already have credentials configured in n8n?
- [CRITICAL — Wave 4] Does `is_latest = 1` filter correctly isolate current fee schedule rows? Confirm row count with vs. without filter before writing the main aggregation DAX query.
- Does `fact_fee_preview[currency]` match COUNTRY_CURRENCY mapping for CA/MX/GB, or are there discrepancies?
- What does the `BE` country prefix represent — active Belgium marketplace or EU bundle key?

### Calibration Pending

- Anomaly threshold % — to be set empirically after Phase 1 exploratory run (expected range: 10-20%)
- Sustained-shift N value — number of consecutive weeks before reclassifying as permanent change

### Known Pitfalls to Address

- Q4 seasonal spikes: separate Q4 vs non-Q4 baseline buckets (defer to v2 — DETECT-05 is v2 scope)
- Uncalibrated threshold: dual-gate (% AND absolute dollar floor) calibrated from Phase 1 run
- LLM hallucination: Claude uses "may indicate" language; data before interpretation; standard disclaimer
- Baseline staleness: DETECT-03 sustained-shift classification prevents repeated alerts on permanent changes
- Context window: Claude receives anomaly JSON only, never raw fee tables

### Todos

- [ ] Resolve open Power BI schema questions before writing detection logic
- [ ] Confirm ClickUp task ID for output target with Lucca + Victor
- [ ] Verify `powerbi-query` skill credential status in n8n

---

## Session Continuity

### Last Session

**What was accomplished:** Plan 01-03 executed. All 5 NotImplementedError stubs in explore_fees.py replaced: process_pbi_rows, iso_to_week_start, extract_country, get_currency_for_country, build_output_df. All 8 unit tests now GREEN (DATA-01, DATA-02, DETECT-01). D-11 8-column output schema wired end-to-end. One auto-fix: iso_to_week_start week-53 edge case (ValueError caught, fallback to week 1 of next year).

**Stopping point:** Plan 01-03 complete. SUMMARY.md written. STATE.md and ROADMAP.md updated.

**Next action:** Execute Plan 01-04 (Wave 4) — FeeRow Pydantic model, DAX constants with is_latest=1 filter, main() entrypoint, full wiring to produce output CSV.

---

*State initialized: 2026-05-27*
