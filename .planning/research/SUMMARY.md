# Research Summary: AI Amazon Fee Auditor

**Synthesized:** 2026-05-27
**Source files:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Overall confidence:** MEDIUM-HIGH

---

## Executive Summary

Single-agent Python pipeline: Power BI fetch → pure-Python statistical anomaly detection → Claude receives only pre-computed anomaly list → ClickUp output. The AI layer does **narrative generation only** — all math in Python, all decisions in code, Claude never sees raw rows. Dominant risks are alert fatigue (Q4 seasonal spikes, uncalibrated threshold) and n8n silent failures; both are mitigated by concrete Phase 1 design decisions before any code is written.

---

## Recommended Stack

| Component | Technology | Version | Confidence |
|---|---|---|---|
| Agent orchestration | Anthropic Python SDK (direct) | `anthropic>=0.28.0` | HIGH |
| LLM | `claude-sonnet-4-6` | — | HIGH |
| Data pipeline | `pandas`, `pandas-gbq` | Latest stable | HIGH |
| Power BI access | `requests` + `msal` | `msal>=1.28.0` | HIGH |
| Anomaly detection | Pure Python (statistics module / pandas rolling) | No ML | HIGH |
| State store | BigQuery | — | HIGH |
| ClickUp integration | `requests` (no official SDK) | Raw REST | MEDIUM |
| Execution | FastAPI + n8n HTTP trigger | FastAPI 0.100+ | MEDIUM |
| Fallback execution | Python CLI | — | HIGH |

**Do NOT use:** LangChain/LangGraph/CrewAI (unnecessary complexity), `powerbiclient` (unmaintained), scikit-learn IsolationForest (overkill for MVP).

---

## Table Stakes Features (Must Ship v1)

1. Power BI data fetch per SKU — FBA Fee + Storage Fee, weekly granularity, rolling 8-12 week window
2. Volume-normalized baseline per SKU — fee per unit, rolling **median** (8-week default)
3. Configurable dual-gate anomaly threshold — `(deviation_pct > X) AND (absolute_delta > $Y)`
4. AI-generated natural language summary — concise, under 150 words, Claude only sees anomaly list
5. ClickUp comment post — summary + run metadata, notify Victor and Data Team
6. CSV report attachment — full anomaly list with per-unit fees and deviations
7. Human escalation prompt in comment — "Should I open an investigation task?"
8. n8n weekly schedule + manual webhook trigger

---

## Architecture Decision

**Pattern:** Single Python orchestrator. Linear pipeline. Claude is the narrative layer only.

```
n8n trigger → Python orchestrator → Power BI query → Statistical Engine (Python)
  → Claude API (anomaly list only) → ClickUp (comment + CSV) → BigQuery (run log)
```

**Critical boundaries:**
- Claude never receives raw fee rows — only pre-computed anomaly list (bounded token budget)
- Statistical logic is 100% Python — reproducible, auditable, unit-testable
- BigQuery stores audit trail and run log — not the authoritative baseline (recomputed from Power BI each run)
- n8n owns trigger + failure alert only — not business logic

---

## Top 5 Pitfalls (Phase 1 Must-Address)

| # | Pitfall | Prevention |
|---|---|---|
| P1 | **Q4 seasonal spikes** flagged as anomalies — alert fatigue in October | Separate Q4 vs non-Q4 baseline buckets |
| P7 | **Uncalibrated threshold** — % threshold fires constantly on low-volume SKUs | Dual-gate: % AND absolute dollar floor; calibrate from exploratory run |
| P6 | **LLM hallucination** in root cause narrative — Victor acts on wrong explanation | Claude uses "may indicate" not "caused by"; data before interpretation; standard disclaimer |
| P2 | **Baseline staleness** — permanent tier change = 12 weeks of false alerts | Sustained-shift detection: N consecutive same-direction flags → reclassify, not repeat |
| P8 | **Context window violation** — raw data dumped into LLM prompt | Data/LLM boundary enforced: LLM receives anomaly JSON, never raw tables |

---

## Phase Implications

### Phase 1 — Foundation: Data Access + Calibration
- Resolve Power BI schema unknowns (units shipped, credits netting, history depth, marketplace filter)
- Build exploratory data run to understand fee variance distribution before writing anomaly logic
- Design baseline: Q4 vs non-Q4 buckets, per-unit normalization
- Create BigQuery tables: `fee_audit_runs`, `fee_anomalies`, `fee_policy_events` (empty)
- Establish data/LLM boundary in architecture — enforce from the start

### Phase 2 — Detection + Output Pipeline
- Statistical Engine: rolling median, dual-gate threshold, sustained-shift classification
- Seasonal baseline buckets
- ClickUp output: comment + CSV attachment + Claude narrative call
- Integration test end-to-end on real data
- Threshold calibration from first production runs

### Phase 3 — Scheduling + Hardening
- FastAPI endpoint (`POST /run-audit`, returns 202)
- n8n HTTP trigger + error branches + heartbeat pattern
- Threshold tuning after 4+ production runs
- Acknowledged anomaly suppression (BigQuery `fee_acknowledged` table)

---

## Open Questions (Must Resolve in Phase 1)

| Question | Why It Matters | Owner |
|---|---|---|
| Does Power BI expose fee-per-unit or only total fee per period per SKU? | Per-unit normalization (volume-adjusted baseline) depends on this | Gustavo — `dashboard-guide` skill |
| Are FBA fee credits/reimbursements already netted in Power BI, or separate line items? | Affects baseline contamination (Pitfall P5) | Gustavo |
| How many weeks of history are available per SKU? | Rolling median needs ≥4 data points; fewer = insufficient history | Gustavo |
| How many active US SKUs? | Sets alert volume expectations; >500 may need top-N filter | Gustavo |
| Does Power BI require explicit marketplace filter? | Avoid mixing fee structures from different marketplaces | Gustavo — `dashboard-guide` skill |
| Which ClickUp task ID receives the reports? | Required before building output layer | Lucca + Victor |
| Does `powerbi-query` skill already have credentials configured in n8n? | May be able to call n8n skill via HTTP instead of re-implementing `msal` auth | Lucca |
