# Project State: AI Amazon Fee Auditor

**Last updated:** 2026-05-27
**Session:** Phase 1 executing — Wave 1 complete, Wave 2 next

---

## Project Reference

**Core value:** Detect FBA fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

**Current focus:** Phase 1 — Data Foundation

**Repository:** AI Amazon Fee Auditor (gsd/phase-01-data-foundation branch)

---

## Current Position

**Phase:** 1 — Data Foundation
**Plan:** Wave 2 — Plan 01-02 (next to execute)
**Status:** Executing

```
Progress: [██········] 25%
Phase 1: [►] Data Foundation  ← EXECUTING — Wave 2/4
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
| Plans complete | 1 |
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

### Open Questions (Phase 1 Must Resolve)

- Does Power BI expose fee-per-unit or only total fee per period per SKU?
- Are FBA fee credits/reimbursements already netted in Power BI, or separate line items?
- How many weeks of history are available per SKU? (Need ≥4 for rolling median)
- How many active US SKUs? (>500 may need top-N filter to manage alert volume)
- Does Power BI require explicit marketplace filter? (Avoid mixing fee structures across regions)
- Which ClickUp task ID receives the reports? (Required before Phase 2)
- Does `powerbi-query` skill already have credentials configured in n8n?

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

**What was accomplished:** Plan 01-01 executed. Project scaffold created (.gitignore, .env.example, requirements.txt, pytest.ini, output/.gitkeep). 8 unit tests written in RED state (ImportError) with conftest.py fixtures. All files committed atomically per task. T-01-01 (.env disclosure) mitigated and verified.

**Stopping point:** Plan 01-01 complete. SUMMARY.md written. STATE.md and ROADMAP.md updated.

**Next action:** Execute Plan 01-02 (Wave 2) — implement `explore_fees.py` to turn all 8 tests GREEN.

---

*State initialized: 2026-05-27*
