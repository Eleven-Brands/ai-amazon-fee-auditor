# Requirements: AI Amazon Fee Auditor

**Defined:** 2026-05-27
**Core Value:** Detect FBA fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

---

## v1 Requirements

### Data Access

- [x] **DATA-01**: Agent queries Power BI for FBA Fulfillment Fee by SKU/ASIN (weekly granularity, rolling 8-12 week window) via `powerbi-query` skill
- [x] **DATA-02**: Queries segment data by **Sales Region** (not a single marketplace filter — OrganiHaus sells US, UK, CA, EU, MX)

### Anomaly Detection

- [x] **DETECT-01**: System calculates a rolling 8-week median baseline per SKU per Sales Region, normalized by units shipped (fee per unit)
- [ ] **DETECT-02**: System flags SKUs where current fee per unit deviates from baseline beyond a configurable % threshold (threshold to be calibrated empirically from first data run)
- [ ] **DETECT-03**: System classifies SKUs that flag anomaly in the same direction for N consecutive weeks as "sustained shift" — prevents repeated alerts on permanent fee changes (e.g. size tier reclassification)

### Output

- [ ] **OUT-01**: System posts a ClickUp comment with AI-generated run summary (Claude, under 150 words) upon run completion
- [ ] **OUT-02**: System attaches a CSV report to the ClickUp comment with full anomaly list (SKU, ASIN, Sales Region, deviation %, absolute delta, fee per unit, baseline fee per unit)
- [ ] **OUT-03**: Output target (ClickUp task ID and notification recipients) is configurable — testing phase sends to Lucca only; recipients updated without code changes

### Escalation

- [ ] **ESC-01**: ClickUp comment includes a human-in-the-loop escalation prompt asking if an investigation task should be opened for the top flagged SKUs

### Execution

- [ ] **EXEC-01**: System runs automatically on a weekly schedule via Windows Task Scheduler on the local machine
- [ ] **EXEC-02**: System supports on-demand execution via CLI (`python run_audit.py --trigger manual`)

---

## v2 Requirements

### Storage Fee Monitoring

- **STOR-01**: Agent retrieves Monthly Storage Fee data by SKU/ASIN/Inventory Region from manually downloaded reports
- **STOR-02**: System calculates storage fee baseline per SKU per Inventory Region (monthly granularity, different cadence from FBA Fee)
- **STOR-03**: System detects storage fee anomalies vs seasonal-aware baseline (Q4 Oct-Dec surcharge bucket vs Jan-Sep baseline)
- **STOR-04**: System supports monthly on-demand execution for storage fee audits (separate from weekly FBA Fee automation)

### Detection Quality

- **DETECT-04**: Dual-gate threshold — flag only if `(deviation_pct > X%) AND (absolute_delta > $Y)` — eliminates noise on low-volume SKUs
- **DETECT-05**: Seasonal Q4 baseline bucket — separate Oct-Dec baseline from Jan-Sep to prevent Q4 storage surcharge from generating false positives
- **DETECT-06**: Fee policy events table — suppress system-wide alerts when Amazon announces a rate change; post "policy change — baseline reset in progress" comment instead

### Reliability

- **REL-01**: BigQuery run log — every run records run_id, date, status, anomaly count, SKUs processed
- **REL-02**: n8n error branches — explicit failure path posts "AUDIT RUN FAILED" comment to ClickUp on unhandled exception
- **REL-03**: Run heartbeat — "run started" ClickUp comment at the start of every run; detects silent n8n failures

### Audience Routing

- **ESC-02**: Configurable notification routing by anomaly severity — low severity → Lucca only; high severity → Lucca + Victor (Inventory)

---

## Out of Scope

| Feature | Reason |
|---|---|
| Rate card reconciliation (Amazon published rates vs charged) | Historical baseline catches anomaly regardless of cause; rate card data changes frequently and adds maintenance cost |
| Automatic investigation task creation | Removes human judgment from escalation; human decides after reading the comment |
| Slack notifications | ClickUp is sufficient for v1; adds a second output channel to maintain |
| Multi-agent decomposition | Single agent MVP until complexity proves it necessary; over-engineering before first run |
| Referral fee / advertising fee monitoring | Different data model, cadence, and team owner; separate project |
| Real-time monitoring (sub-hourly) | FBA fees settle weekly; real-time adds infrastructure complexity for no operational gain |
| UI / dashboard | Team already has Power BI and ClickUp; another surface to build and maintain |
| Direct Amazon SP-API integration | Power BI is the source of truth; direct SP-API adds a second pipeline to maintain |
| Reimbursement claim filing | Distinct workflow with separate compliance considerations; different owner |
| Multi-marketplace rate normalization | MVP focuses on anomaly detection within each region, not cross-region fee comparison |

---

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DETECT-01 | Phase 1 | Complete |
| DETECT-02 | Phase 2 | Pending |
| DETECT-03 | Phase 2 | Pending |
| OUT-01 | Phase 2 | Pending |
| OUT-02 | Phase 2 | Pending |
| OUT-03 | Phase 2 | Pending |
| ESC-01 | Phase 2 | Pending |
| EXEC-01 | Phase 3 | Pending |
| EXEC-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---

*Requirements defined: 2026-05-27*
*Last updated: 2026-05-27 after roadmap creation*
