# Phase 1: Data Foundation - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove that historical FBA fee data is accessible via the Power BI REST API and understand the fee variance distribution well enough to design the detection layer. Phase 1 is exploratory — it produces a working Python script and a CSV, not a production pipeline.

</domain>

<decisions>
## Implementation Decisions

### Historical Data Source

- **D-01:** Data access path = **Power BI REST API with custom DAX** on `fact_fee_preview`. BigQuery direct query is NOT the approach. The `powerbi-query` skill pattern (MSAL device-code auth + `executeQueries` endpoint) is the confirmed access method.
- **D-02:** Date column for historical slicing = `fact_fee_preview[date_fee_preview]` (daily granularity, range confirmed as 2023-07-01 → present — nearly 3 years of history).
- **D-03:** Fee metric = `fact_fee_preview[expected_fulfillment_fee_per_unit]` — already per-unit. No units-sold normalization needed for the fee rate itself.
- **D-04:** Weekly baseline granularity = **average of all daily fee values within each calendar week** per SKU/country key. Not last-day-of-week.
- **D-05:** Include all 5,274 distinct keys, including `amzn.gr.*` prefixed Amazon grouping codes. Do not filter them out — audit everything in the table.
- **D-06:** ASIN lookup: join `fact_fee_preview[key_sales_marketplace_sku]` to `SKUs[Key Column: Country | SKU]`. ASIN is at `SKUs[ASIN]`. Sales Region grouping is at `SKUs[Sales Region]` (maps individual country codes to EU / US / CA / MX / UK regions). `amzn.gr.*` keys will NOT join — flag unjoined rows and count them in the exploration output.

### Power BI API Identifiers (confirmed live)

- **D-07:** Workspace ID = `47144ee2-02f9-4408-9ed5-57acf6a9f44d` (OrganiHaus Marketing Intelligence Center - MIC)
- **D-08:** Dataset ID = `a95798aa-a3ec-4a89-9816-63cde534cdd7` (OrganiHaus - Operations)
- **D-09:** Auth = MSAL device-code flow. Env vars `POWERBI_TENANT_ID` and `POWERBI_CLIENT_ID` already set. Token cached at `~/.claude/powerbi_token_cache.json`. Use the standard auth block from the `powerbi-query` skill.

### Exploratory Output Form

- **D-10:** Phase 1 produces a single Python script `explore_fees.py` + one CSV output. No Jupyter notebook.
- **D-11:** CSV contains: per-SKU, per-country, per-week rows: `key_sales_marketplace_sku`, `country` (2-letter), `sales_region` (EU/US/CA/MX/UK from SKUs table), `sku`, `asin` (null for unjoined keys), `week_start_date`, `avg_fee_per_unit`, `currency`.
- **D-12:** Reviewer = Lucca only. No review gate before Phase 2.
- **D-13:** The exploration CSV covers a lookback window of at least 16 weeks to allow threshold calibration. The full 3-year history is available but not all of it needs to be in the exploration output.

### Marketplace Scope

- **D-14:** All marketplaces from the start — all 5,274 keys. No US-only filter for Phase 1.
- **D-15:** "Sales Region" label in output CSV = the 2-letter country code (from the key prefix, e.g., `US`, `GB`, `DE`) for the raw exploration. The `SKUs[Sales Region]` dimension (EU/US/CA/MX/UK) is used for grouping when computing per-SKU-per-region baselines in Phase 2.
- **D-16:** Data lives at the **country level** in `fact_fee_preview` (e.g., DE and FR have separate fee rows for the same EU SKU). Phase 1 explores this country-level granularity as-is. The grouping decision (country-level vs. Sales Region-level baseline) is a Phase 2 calibration concern.

### State Persistence

- **D-17:** **No BigQuery** — dropping this dependency entirely. The original roadmap success criterion #5 (BigQuery tables) is overridden by this decision.
- **D-18:** State persistence = local CSV files only:
  - `run_YYYYMMDD.csv` — one file per audit run with its anomaly list
  - `anomaly_history.csv` — cumulative append of all flagged anomalies across runs (needed for sustained-shift detection in Phase 2)
- **D-19:** No BigQuery service account or GCP project config needed for Phase 1.

### Auth & Credentials

- **D-20:** Power BI auth is already operational on this machine (MSAL + cached token). The Phase 1 script uses the same auth pattern from the `powerbi-query` skill.
- **D-21:** No additional credential setup needed for Phase 1 — PBI auth is sufficient for the exploratory script.

### PBI Measure Validation (Success Criterion #3)

- **D-22:** The validation of `$_total_fba_fee_fee_preview` (which may return null due to `f.AllOrders[unit_fba_fee]` empty column) is covered implicitly: the Phase 1 script uses `fact_fee_preview[expected_fulfillment_fee_per_unit]` directly via raw DAX, not via PBI measures. The exploration script should confirm non-null row counts and sample values to satisfy this criterion.

### Claude's Discretion

- DAX query structure (SUMMARIZECOLUMNS vs CALCULATETABLE, ISO week vs calendar week) — Claude decides.
- File naming convention for output CSVs beyond `explore_fees.py` — Claude decides.
- Python package choices within the approved stack (pandas, requests, msal) — Claude decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundations
- `.planning/PROJECT.md` — Core constraints, data source context, Power BI schema notes, key decisions
- `.planning/REQUIREMENTS.md` — DATA-01, DATA-02, DETECT-01 (the 3 Phase 1 requirements)
- `.planning/ROADMAP.md` — Phase 1 success criteria (note: criterion #5 on BigQuery is overridden by D-17/D-18)

### Research (domain context)
- `.planning/research/STACK.md` — Approved library stack and rationale
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow direction, anti-patterns
- `.planning/research/PITFALLS.md` — Top pitfalls to avoid (token budget, uncalibrated threshold, etc.)

### Power BI Model
- Power BI dataset: **OrganiHaus - Operations** (IDs in D-07/D-08)
- Key tables used: `fact_fee_preview` (fee history), `SKUs` (dimension — ASIN, Sales Region, Country)
- No reference file on disk — schema confirmed live via `executeQueries` in this session

### Auth Pattern
- `powerbi-query` skill (`~/.claude/commands/powerbi-query.md`) — authentication helper pattern to follow for MSAL + token cache

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No Python code exists yet — this is the first phase.

### Established Patterns
- MSAL device-code flow: confirmed working, token cached at `~/.claude/powerbi_token_cache.json`. Re-use the auth block from `powerbi-query` skill verbatim.
- DAX `TOPN(N, 'table')` works for schema inspection.
- DAX `EVALUATE ROW(...)` works for scalar aggregates.

### Integration Points
- Phase 2 will extend `explore_fees.py` into `run_audit.py`. The data pull function written in Phase 1 becomes the ingestion layer for Phase 2.
- The `anomaly_history.csv` schema designed in Phase 1 becomes the sustained-shift detection input for Phase 2.

</code_context>

<specifics>
## Specific Ideas

- The join between `fact_fee_preview` and `SKUs` uses `SKUs[Key Column: Country | SKU]` (exact column name confirmed live).
- `amzn.gr.*` keys will not join to `SKUs` — the script should count and log unjoined keys but not fail on them.
- The weekly average should aggregate all daily rows within a `YEARWEEK` bucket (ISO week recommended for consistency).
- The 16-week lookback for the exploration CSV covers the minimum needed for rolling 8-week median + 8 weeks of "current" comparison periods.

</specifics>

<deferred>
## Deferred Ideas

- **Sales Region-level vs. Country-level baseline grouping** — EU has different fees per country for the same SKU. Decision on whether to baseline at country or EU region level deferred to Phase 2 calibration (D-16).
- **`amzn.gr.*` key investigation** — understanding what these keys represent (bundles? virtual ASINs?) deferred to Phase 2 unless Phase 1 exploration shows them generating anomalous results.
- **Dual-gate threshold** (`pct AND absolute dollar floor`) — DETECT-04 is v2 scope. Phase 2 starts with pct-only threshold, calibrated from Phase 1 CSV.
- **Seasonal Q4 baseline** — DETECT-05 is v2 scope.

</deferred>

---

*Phase: 1-Data-Foundation*
*Context gathered: 2026-05-27*
