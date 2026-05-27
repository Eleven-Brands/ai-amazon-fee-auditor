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
  1. Running the data pull script returns structured FBA Fulfillment Fee rows by SKU/ASIN across all Sales Regions (US, UK, CA, EU, MX) without authentication errors
  2. The exploratory output shows at minimum 4 weeks of history per SKU, confirming rolling median baseline is viable
  3. Per-unit fee normalization (fee / units shipped) is validated against at least one known SKU with a confirmed units figure
  4. An exploratory notebook or script documents the observed fee variance distribution and recommends an initial anomaly threshold range for Phase 2 calibration
  5. BigQuery tables `fee_audit_runs` and `fee_anomalies` exist with correct schemas (empty, ready to receive data)
**Plans**: TBD

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
**Goal**: The audit runs automatically every week via n8n and can be triggered on demand via webhook or CLI, with no manual intervention required under normal conditions
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: EXEC-01, EXEC-02
**Success Criteria** (what must be TRUE):
  1. An n8n workflow on `elevenbrands.app.n8n.cloud` triggers the audit automatically on a weekly schedule and a ClickUp comment appears without manual action
  2. Sending a POST request to the n8n webhook URL (or running `python run_audit.py --trigger manual`) completes a full audit run on demand
  3. The FastAPI endpoint `POST /run-audit` returns HTTP 202 and the audit completes asynchronously
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/? | Not started | - |
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
*Last updated: 2026-05-27 after initialization*
