# AI Amazon Fee Auditor

## What This Is

An AI agent system that automatically audits Amazon FBA fees for OrganiHaus, detecting anomalies in FBA Fulfillment Fee at the SKU/ASIN level by comparing current charges against historical baselines. It runs weekly via Windows Task Scheduler (and on-demand via CLI), posts findings to ClickUp, and escalates unusual charges for human investigation.

## Core Value

Detect fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Query FBA Fulfillment Fee from Power BI by SKU/ASIN, segmented by Sales Region, via `powerbi-query` skill
- [ ] Calculate rolling 8-week median baseline per SKU per Sales Region, normalized by units shipped
- [ ] Detect anomalies: fee per unit deviates beyond configurable % threshold vs baseline (calibrate from first data run)
- [ ] Classify sustained shifts (N consecutive same-direction flags) to avoid repeated alerts on permanent fee changes
- [ ] Post ClickUp comment with concise anomaly summary (<150 words, Claude-generated) on completion
- [ ] Attach CSV report to ClickUp with full anomaly list (SKU, ASIN, region, deviation, delta, fee/unit)
- [ ] Ask human analyst in ClickUp whether to open an investigation task for top flagged SKUs
- [ ] Support weekly scheduled execution via Windows Task Scheduler (local machine)
- [ ] Support on-demand execution via CLI (`python run_audit.py --trigger manual`)

### Out of Scope

- Rate card reconciliation (Amazon published rates vs charged) — deferred; historical baseline is sufficient for MVP and avoids external data dependency
- Automatic investigation task creation — system asks; human decides
- Slack notifications — ClickUp only for MVP; revisit if team requests
- Multi-agent decomposition — start single agent, decompose when complexity justifies it
- Non-FBA fee types (referral fees, advertising) — out of scope for v1; FBA Fee + Storage Fee first

## Context

**Brand:** OrganiHaus (Amazon FBA — US, UK, CA, EU, MX). Primary focus is the US marketplace for MVP.

**Data source:** Power BI is the source of truth. FBA Fee and Storage Fee available at SKU/ASIN level with historical data. Access via `powerbi-query` skill; schema navigation via `dashboard-guide` skill.

**Stack:** Python, BigQuery, Power BI, ClickUp. Scheduled via Windows Task Scheduler on local machine.

**Team:** Lucca and Gustavo (Data Team) are primary owners. Victor (Inventory) receives anomaly alerts. Data Team filters and escalates as needed.

**Current state:** No automated fee monitoring exists. Reviews are manual and ad hoc, meaning fee spikes can go undetected for extended periods.

**Open calibration:** Anomaly threshold percentage has not been formally set. Will be determined empirically after the first data exploration run (likely in the 10–20% range per period).

## Constraints

- **Execution:** Windows Task Scheduler on local machine — simple, no additional infrastructure. Requires machine to be on at scheduled time.
- **Data access:** Power BI only via `powerbi-query` skill — no direct DB connection to Amazon Seller Central
- **Token budget:** Each agent must receive only the context it needs — no large data dumps in prompts; summaries and structured outputs only
- **Output format:** ClickUp comments must be concise; verbose detail in attached CSV only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Historical baseline (not rate card) for anomaly detection | No external rate card dependency; faster to implement; catches all fee changes regardless of cause | — Pending |
| Single agent MVP, decompose later | Avoids over-engineering before complexity is proven necessary | — Pending |
| Windows Task Scheduler for execution (not n8n) | Simpler to set up and maintain; no additional infrastructure; acceptable trade-off since the local machine is available | — Pending |
| Thresholds are configurable, not hardcoded | No established threshold exists; must be calibrated empirically | — Pending |
| ClickUp as primary output channel | Victor and Data Team already live in ClickUp; minimal friction | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-27 after initialization*
