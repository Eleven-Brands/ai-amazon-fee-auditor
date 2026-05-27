# Roadmap: AI Amazon Fee Auditor

**Milestone:** v1 — Automated FBA Fee Anomaly Detection
**Granularity:** Standard
**Mode:** mvp
**Total phases:** 3
**Requirements covered:** 11/11

---

## Phases

- [ ] **Phase 1: Data Foundation** - Prove Power BI data access works, understand fee variance distribution, and establish the baseline design before writing any anomaly logic
- [ ] **Phase 2: Detection + Output Pipeline** - Build the full audit pipeline end-to-end: statistical anomaly detection, Claude narrative, ClickUp comment + CSV output
- [ ] **Phase 3: Scheduling + Operationalization** - Deploy to n8n, expose on-demand trigger, and make the system autonomous

---

## Phase Details

### Phase 1: Data Foundation
**Goal**: Data access is proven and the fee variance distribution is understood well enough to make calibrated design decisions for the detection layer
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DETECT-01
**Success Criteria** (what must be TRUE):
  1. Data access method is decided and working: either (a) BigQuery direct query on `vw_full_fee_preview`, or (b) custom DAX via PBI REST API — returns multi-week FBA Fee rows by SKU/ASIN/Sales Region without errors
  2. The exploratory output shows at minimum 4 weeks of history per SKU, confirming rolling median baseline is viable
  3. `$_total_fba_fee_fee_preview` dependency on `f.AllOrders[unit_fba_fee]` is validated — confirmed returning real values or flagged as unusable and replaced with `$_unit_fba_fee_fee_preview` × units
  4. An exploratory script documents observed fee variance distribution and recommends an initial % threshold range for Phase 2 calibration
  5. BigQuery criterion superseded by D-17/D-18 (no BigQuery — local CSV state instead)
**Plans**: 4 plans in 4 waves

**Wave 1**
- [x] 01-01-PLAN.md — Project scaffold: .gitignore, .env.example, requirements.txt, pytest.ini, 9-test unit suite

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-02-PLAN.md — Walking skeleton + auth layer: skeleton.py, get_token(), run_dax(), validate_value_count()

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 01-03-PLAN.md — Core aggregation: process_pbi_rows, iso_to_week_start, extract_country, get_currency_for_country, build_output_df

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 01-04-PLAN.md — CSV output + main() entrypoint: FeeRow Pydantic model, DAX constants, full wiring

**Cross-cutting constraints:**
- No BigQuery imports in any plan (D-17/D-18)
- All tasks run `pytest tests/ -x -q` after every change (Nyquist sampling)
- MSAL device-code auth pattern from `powerbi-query` skill used verbatim (D-09)

### Phase 2: Detection + Output Pipeline
**Goal**: A single end-to-end audit run can be triggered locally, detects anomalies from real data, and posts a ClickUp comment with an AI-generated summary and a CSV attachment
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: DETECT-02, DETECT-03, OUT-01, OUT-02, OUT-03, ESC-01
**Success Criteria** (what must be TRUE):
  1. Running `python run_audit.py` locally produces a ClickUp comment under 150 words summarising anomalies found in the latest week
  2. A CSV file is attached to the same ClickUp comment listing every flagged SKU with columns: SKU, ASIN, Sales Region, deviation %, absolute delta, fee per unit, baseline fee per unit
  3. The ClickUp comment includes a human-in-the-loop escalation prompt asking whether to open an investigation task for the top flagged SKUs
  4. Changing `OUT-03` config (ClickUp task ID, notification recipients) requires only a config file edit — no code changes
  5. A SKU that has flagged in the same direction for N consecutive weeks is classified as "sustained shift" and does not re-alert as a new anomaly
**Plans**: TBD

### Phase 3: Scheduling + Operationalization
**Goal**: The audit runs automatically every week via Windows Task Scheduler and can be triggered on demand via CLI, with no manual intervention required under normal conditions
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: EXEC-01, EXEC-02
**Success Criteria** (what must be TRUE):
  1. A Windows Task Scheduler task fires the audit script on a weekly schedule and a ClickUp comment appears without manual action
  2. Running `python run_audit.py --trigger manual` completes a full on-demand audit run and posts results to ClickUp
  3. The scheduled task and CLI entrypoint share identical execution logic — same `run_audit()` function, no divergent code paths
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 1/4 | In progress | 01-01: 2026-05-27 |
| 2. Detection + Output Pipeline | 0/? | Not started | - |
| 3. Scheduling + Operationalization | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| DATA-01 | Phase 1 |
| DATA-02 | Phase 1 |
| DETECT-01 | Phase 1 |
| DETECT-02 | Phase 2 |
| DETECT-03 | Phase 2 |
| OUT-01 | Phase 2 |
| OUT-02 | Phase 2 |
| OUT-03 | Phase 2 |
| ESC-01 | Phase 2 |
| EXEC-01 | Phase 3 |
| EXEC-02 | Phase 3 |

**Coverage:** 11/11 v1 requirements mapped

---

*Roadmap created: 2026-05-27*
*Last updated: 2026-05-27 — Plan 01-01 complete (scaffold + 8-test RED harness)*
