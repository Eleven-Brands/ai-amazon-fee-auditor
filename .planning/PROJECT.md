# AI Amazon Fee Auditor

## What This Is

An AI agent system that automatically audits Amazon FBA fees for OrganiHaus, detecting anomalies in FBA Fee and Storage Fee at the SKU/ASIN level by comparing current charges against historical baselines. It runs weekly (and on-demand), posts findings to ClickUp for the Data Team and Victor (Inventory), and escalates unusual charges for human investigation.

## Core Value

Detect fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Query FBA Fee and Storage Fee data from Power BI by SKU/ASIN via `powerbi-query` skill
- [ ] Calculate historical baseline per SKU (rolling average/median over recent periods)
- [ ] Detect anomalies: fee change exceeds configurable threshold vs baseline (threshold TBD — calibrate from first data run)
- [ ] Generate periodic fee evolution report (trend by SKU/ASIN)
- [ ] Post ClickUp comment with concise anomaly summary on completion
- [ ] Attach detailed anomaly report file (CSV or HTML) to ClickUp task
- [ ] Ask human analyst in ClickUp whether to create an investigation sub-task for flagged SKUs
- [ ] Support weekly scheduled execution via n8n
- [ ] Support on-demand execution (manual trigger)

### Out of Scope

- Rate card reconciliation (Amazon published rates vs charged) — deferred; historical baseline is sufficient for MVP and avoids external data dependency
- Automatic investigation task creation — system asks; human decides
- Slack notifications — ClickUp only for MVP; revisit if team requests
- Multi-agent decomposition — start single agent, decompose when complexity justifies it
- Non-FBA fee types (referral fees, advertising) — out of scope for v1; FBA Fee + Storage Fee first

## Context

**Brand:** OrganiHaus (Amazon FBA — US, UK, CA, EU, MX). Primary focus is the US marketplace for MVP.

**Data source:** Power BI is the source of truth. FBA Fee and Storage Fee available at SKU/ASIN level with historical data. Access via `powerbi-query` skill; schema navigation via `dashboard-guide` skill.

**Stack:** Python, BigQuery, Power BI, ClickUp, n8n (`elevenbrands.app.n8n.cloud`).

**Team:** Lucca and Gustavo (Data Team) are primary owners. Victor (Inventory) receives anomaly alerts. Data Team filters and escalates as needed.

**Current state:** No automated fee monitoring exists. Reviews are manual and ad hoc, meaning fee spikes can go undetected for extended periods.

**Open calibration:** Anomaly threshold percentage has not been formally set. Will be determined empirically after the first data exploration run (likely in the 10–20% range per period).

## Constraints

- **Execution:** n8n cloud (`elevenbrands.app.n8n.cloud`) — no dependency on local machine; use simple n8n workflows to minimize maintenance overhead
- **Data access:** Power BI only via `powerbi-query` skill — no direct DB connection to Amazon Seller Central
- **Token budget:** Each agent must receive only the context it needs — no large data dumps in prompts; summaries and structured outputs only
- **Fallback:** Windows Task Scheduler + Python script if n8n is unavailable
- **Output format:** ClickUp comments must be concise; verbose detail in attached file only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Historical baseline (not rate card) for anomaly detection | No external rate card dependency; faster to implement; catches all fee changes regardless of cause | — Pending |
| Single agent MVP, decompose later | Avoids over-engineering before complexity is proven necessary | — Pending |
| n8n for scheduled execution | Cloud-hosted, retry logic, logging, no local machine dependency | — Pending |
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
