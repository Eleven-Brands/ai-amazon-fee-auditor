---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase_complete
last_updated: "2026-05-27"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 33
---

# Project State: AI Amazon Fee Auditor

**Last updated:** 2026-05-27
**Session:** Phase 1 complete — all 4 waves executed, CSV verified, ready for Phase 2 planning

---

## Project Reference

**Core value:** Detect FBA fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

**Current focus:** Phase 2 — Detection + Output Pipeline (planning next)

**Repository:** AI Amazon Fee Auditor (gsd/phase-01-data-foundation branch)

---

## Current Position

**Phase:** 1 — Data Foundation — COMPLETE
**Plan:** All 4 plans complete
**Status:** Phase complete — awaiting Phase 2 planning

```
Progress: [████████████░░░░░░░░] 33%
Phase 1: [x] Data Foundation  ← COMPLETE (4/4 plans)
Phase 2: [ ] Detection + Output Pipeline
Phase 3: [ ] Scheduling + Operationalization
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 3 |
| Phases complete | 1 |
| Plans total | 4 (Phase 1) |
| Plans complete | 4 |
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
| is_latest=1 filter required in build_fee_dax | fact_fee_preview stores 3.7M historical fee schedule rows; is_latest=1 isolates 5,274 current fee rates |
| process_pbi_rows normalises YEAR/WEEKNUM to year/week_num (snake_case) | Matches test fixture column names; isocalendar() derivation happens in Python not DAX |
| iso_to_week_start catches ValueError for week 53 in 52-week years | Returns week 1 of next year; test asserts no exception raised for iso_to_week_start(2025, 53) |
| build_output_df handles both raw PBI and pre-cleaned DataFrames | Bracket-strip on sku_df is idempotent; week_start_date derived if absent |
| SUMMARIZECOLUMNS groupBy must use real column references | YEAR()/WEEKNUM() expressions rejected as groupBy args; group on [date_fee_preview] and derive year/week in Python |
| fact_fee_preview is a fee schedule HISTORY table not a transaction table | is_latest=1 gives one row per key (current fee); historical data requires marketplace-batched queries to stay under 1M PBI limit |
| Phase 2 baseline strategy: accumulate weekly is_latest=1 snapshots | Query is small (5,274 rows), stays under PBI limit, builds rolling history over time; compare current snapshot vs. N prior snapshots |
| Pydantic gate validate_output_df() runs before to_csv() | T-04-02 mitigation: schema validation failure halts before any CSV is written |

### Open Questions (Phase 2 Must Resolve)

- Which ClickUp task ID receives the reports? (Required before Phase 2)
- Does `powerbi-query` skill already have credentials configured in n8n?
- Are FBA fee credits/reimbursements already netted in Power BI, or separate line items?
- Does `fact_fee_preview[currency]` match COUNTRY_CURRENCY mapping for CA/MX/GB, or are there discrepancies?
- What does the `BE` country prefix represent — active Belgium marketplace or EU bundle key?
- How many weekly snapshots must accumulate before anomaly detection is viable? (need N >= 4 for rolling median)
- Phase 2 query strategy decision: snapshot accumulation vs. marketplace-batched historical queries

### Calibration Pending

- Anomaly threshold % — to be set empirically after reviewing Phase 1 CSV (expected range: 10-20%)
- Sustained-shift N value — number of consecutive weeks before reclassifying as permanent change
- Minimum snapshot history before first alert run (recommend: wait for 4 weekly snapshots before alerting)

### Known Pitfalls to Address

- Q4 seasonal spikes: separate Q4 vs non-Q4 baseline buckets (defer to v2 — DETECT-05 is v2 scope)
- Uncalibrated threshold: dual-gate (% AND absolute dollar floor) calibrated from Phase 1 run
- LLM hallucination: Claude uses "may indicate" language; data before interpretation; standard disclaimer
- Baseline staleness: DETECT-03 sustained-shift classification prevents repeated alerts on permanent changes
- Context window: Claude receives anomaly JSON only, never raw fee tables
- Historical batch query limit: 16-week query on all keys exceeds 1M PBI limit — must partition by marketplace

### Todos

- [ ] Confirm ClickUp task ID for output target with Lucca + Victor
- [ ] Verify `powerbi-query` skill credential status in n8n
- [ ] Decide Phase 2 baseline strategy (snapshot accumulation vs. batched historical) before planning
- [ ] Review Phase 1 CSV to calibrate anomaly threshold range

---

## Session Continuity

### Last Session

**What was accomplished:** Plan 01-04 executed. Added `build_fee_dax()`, `SKU_QUERY`, `FeeRow` Pydantic v2 model, `validate_output_df()`, and `main()` to explore_fees.py. Added 9th test `test_validate_output_df_raises_on_missing_column`. All 9 unit tests GREEN. Live run verified: 5,274 rows, 8 D-11 columns, CSV written to output/explore_fees_20260527.csv. Critical discovery: `fact_fee_preview` is a fee schedule history table — is_latest=1 gives snapshot, not time-series. DAX bug fixed: SUMMARIZECOLUMNS groupBy must use column references not expressions.

**Stopping point:** Phase 1 complete. SUMMARY.md written (01-04-SUMMARY.md). STATE.md and ROADMAP.md updated.

**Next action:** Plan Phase 2 — Detection + Output Pipeline. Must first decide baseline strategy given the data model discovery (snapshot accumulation recommended).

---

*State initialized: 2026-05-27*
*Phase 1 completed: 2026-05-27*
