# Feature Landscape: Amazon FBA Fee Auditor

**Domain:** Internal AI-powered fee auditing tool for Amazon FBA seller (OrganiHaus)
**Researched:** 2026-05-27
**Confidence:** MEDIUM — based on training knowledge of commercial tools (Sellerboard, Helium 10 Profits, SellerApp, Fetcher) and Amazon SP-API/Seller Central report ecosystem through August 2025.

---

## What Commercial Tools Actually Do (Benchmark)

### Sellerboard
Real-time profit/loss per ASIN, breakdown of FBA fulfillment fees, storage fees, referral fees, advertising cost, COGS, returns. Long-term fee trend charts per product. Monthly/weekly PnL snapshots. Email alert when margin drops below threshold. Inventory restock alerts. Refund/reimbursement tracking.

### Helium 10 Profits
Per-ASIN profit dashboard, fee breakdown (fulfillment, storage, referral, inbound shipping, removal fees), time-series trend view, marketplace filters. No dedicated anomaly detection — relies on manual chart inspection. CSV export.

### SellerApp
PnL dashboard, fee categorization by type, product-level drill-down, advertising attribution. Some rule-based alerts on margin thresholds. No statistical anomaly detection.

### Fetcher / A2X / Jungle Scout Sales Analytics
Primarily accounting-oriented: reconcile Amazon disbursements to fee categories. Designed for accountants, not operational monitoring.

**Common pattern across all:** These tools aggregate and display fees. None applies statistical anomaly detection. Alerts are threshold-based on margin, not on fee behavior change. **This is the gap OrganiHaus's tool addresses.**

---

## Fee Types in the Ecosystem

| Fee Type | Amazon Report Source | Relevance to MVP |
|---|---|---|
| FBA Fulfillment Fee (per unit) | FBA Fee Preview, Settlement report | **In scope — primary** |
| Monthly Inventory Storage Fee | FBA Storage Fee report | **In scope — primary** |
| Long-Term Storage Fee (LTSF) | FBA Long-Term Storage Fee report | High value, deferred |
| Referral Fee | Settlement report | Out of scope v1 |
| Variable Closing Fee | Settlement | Out of scope v1 |
| Inbound Transportation Fee | FBA Inbound report | Out of scope v1 |
| Removal/Disposal Order Fee | Removal report | Out of scope v1 |
| Returns Processing Fee | Settlement | Out of scope v1 |
| Advertising fees (SP, SB, SD) | Advertising reports | Explicitly out of scope |

**Note:** FBA fulfillment fee per unit changes when Amazon re-measures a product's dimensions/weight — most common source of unexpected fee spikes. LTSF is triggered on Feb 15 and Aug 15 snapshots and can be catastrophically large.

---

## Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Historical baseline per SKU | Core of anomaly detection — without it, no comparison | Low-Med | Rolling N-week median/mean; threshold TBD |
| Anomaly flag: fee change vs baseline | Primary output of the system | Low | Configurable percentage deviation |
| Per-SKU/ASIN granularity | Aggregate totals hide individual spikes | Low | Already in Power BI data model |
| Fee trend report (time-series by SKU) | Without trend, can't distinguish spike from drift | Med | Periodic snapshots over rolling window |
| Scheduled execution (weekly) | Manual runs are never reliable long-term | Low | n8n handles this |
| Output to ClickUp (summary comment) | Team lives in ClickUp; no output = no action | Low | Already decided |
| Attached detailed report (CSV/HTML) | Comment too concise to investigate from | Low | ClickUp attachment |
| Configurable anomaly threshold | First run calibration needed; hardcoding = brittle | Low | Config file or env var |
| On-demand trigger | Debugging and ad-hoc investigation | Low | n8n webhook |

---

## Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Statistical anomaly detection (rolling baseline) | Commercial tools use margin alerts only; this detects fee behavior change regardless of volume | Med | Rolling median + % deviation is v1; z-score is v2 |
| Natural language anomaly summary | AI generates "SKU X FBA fee +34% vs 8-week average — possible re-measurement" | Med | High value for non-analysts (Victor) |
| Human-in-the-loop escalation via ClickUp | No commercial tool asks "should I open an investigation?" | Low | Key differentiator in practice |
| FBA dimension re-measurement detection signal | Fulfillment fee spike without COGS/volume change → likely re-measurement | Med | Inferred from fee delta pattern |
| Root cause hypothesis in alert | "Storage fee spike matches Feb 15 LTSF snapshot" | Med | Requires seasonal calendar logic + prompt |
| Multi-marketplace awareness | US, UK, CA, EU, MX — fee structures differ | Med | Out of scope MVP; architecturally easy to add |

---

## Anti-Features (Deliberately NOT build in v1)

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| Rate card reconciliation | Requires maintaining Amazon fee schedule data that changes frequently | Historical baseline catches anomaly regardless of cause |
| Automatic sub-task creation in ClickUp | Removes human judgment; creates noise if threshold miscalibrated | Ask the analyst; they create manually |
| Slack notifications | Second output channel to maintain; ClickUp sufficient for v1 | Revisit only if team requests |
| Multi-agent decomposition | Coordination overhead before complexity justifies it | Single agent MVP; decompose when latency/context window is real problem |
| Referral fee / advertising fee monitoring | Different data model, different cadence, different owner | Separate tool if needed |
| UI/dashboard | Another surface to build; team already has Power BI and ClickUp | Output to existing tools |
| Automatic Amazon SP-API integration | Power BI is source of truth; direct SP-API adds second pipeline | Use Power BI via powerbi-query skill |
| Reimbursement claim filing | Distinct workflow with separate compliance considerations | Separate project |
| Real-time monitoring (sub-hourly) | FBA fees settle daily/weekly; real-time adds infra complexity | Weekly scheduled run is appropriate |

---

## Anomaly Detection Approaches (Ecosystem Survey)

1. **Rolling window baseline** — most common. Compute median over 4-8 weeks; flag if current week deviates >X%. Simple, interpretable, low false positive rate.
2. **YoY comparison** — useful for seasonal storage fee spikes; compare current month to same month prior year.
3. **Absolute dollar threshold** — crude but fast for small catalogs.
4. **Volume-normalized comparison** — fee per unit shipped (not total fee), removes volume-driven variation. Critical for growing SKUs.
5. **Z-score / IQR** — statistically principled; requires 12+ data points. Good v2 target.

**Recommended for v1:** Rolling median (8-week window) on fee-per-unit, configurable % threshold. Volume normalization is important to avoid false positives on growing SKUs.

---

## Feature Dependencies

```
Power BI data access (powerbi-query skill)
  └── Historical baseline calculation (requires >=4 weeks of fee data per SKU)
        └── Anomaly detection (requires baseline)
              └── Anomaly summary generation (requires anomaly flags)
                    └── ClickUp comment post (requires summary)
                          └── Detailed report attachment (requires full anomaly dataset)
                                └── Human escalation prompt (requires comment posted)

Configurable threshold → Anomaly detection

n8n scheduled/manual trigger → Entire pipeline (entry point)
```

---

## MVP Prioritization

**Must ship in v1:**
1. Power BI data fetch per SKU (FBA Fee + Storage Fee, weekly granularity, rolling 8-12 week window)
2. Volume-normalized baseline per SKU (fee per unit, rolling median)
3. Configurable % threshold anomaly flag
4. Natural language summary of anomalies (AI-generated, concise)
5. ClickUp comment with summary
6. Attached detailed report (CSV preferred over HTML for simplicity)
7. Human escalation prompt in comment
8. n8n weekly schedule + manual webhook trigger

**Defer to v2:**
- LTSF detection with seasonal calendar
- Z-score / IQR-based detection
- Multi-marketplace support
- Root cause hypothesis with Amazon fee calendar

---

## Key Open Questions

1. **Units shipped data in Power BI:** Volume normalization requires units shipped per SKU per week. Confirm this is in the Power BI data model.
2. **History depth available:** Rolling median quality degrades below 4 data points. How many weeks per SKU?
3. **SKU count:** Large catalogs (>500 active) could produce noisy alerts — may need top-N filter.
4. **Marketplace scope:** Confirm Power BI fee data requires marketplace filter to avoid mixing fee structures.
5. **ClickUp task structure:** Each weekly run appends to a single recurring task OR creates a new task per run?
